"""Finite-candidate development engine; no specimen IDs or private truth access.

This deliberately precedes continuous parameter inference, AR(1) calibration,
general structural equivalence, and nonlinear proposal fitting.
"""
from dataclasses import dataclass, asdict
import itertools
import numpy as np
from scipy.special import logsumexp
from .physics import RCModel, Acquisition, predict, observation_vector, ACTION_MENU


@dataclass(frozen=True)
class Candidate:
    name: str
    model: RCModel
    description: str


def candidate_set(task: str):
    if task == "input-branch":
        return [Candidate("rc",RCModel(10000,1e-6),"RC without input parallel branch"),
                Candidate("rc_input_branch",RCModel(10000,1e-6,10000),"RC with 10 kohm input branch")]
    if task == "rc-fault":
        return [Candidate("r_changed",RCModel(20000,1e-6),"R=20 kohm, C=1 microfarad"),
                Candidate("c_changed",RCModel(10000,2e-6),"R=10 kohm, C=2 microfarad")]
    raise ValueError("Unknown declared diagnostic task")


def predicted_for(candidate: Candidate, capture: dict):
    if capture.get("source") != "synthetic":
        raise ValueError("Hardware inference awaits D2 calibration; source must be synthetic")
    acq = Acquisition(**capture["settings"])
    data = capture["data"]
    kwargs = {} if acq.kind == "dc_pair" else {
        "time_s":data["time_s"],"drive_v":data["drive_v"],"ref_v":data["ref_v"]}
    return predict(candidate.model,acq,**kwargs)


def residual(candidate: Candidate, capture: dict):
    predicted = predicted_for(candidate,capture)
    kind = capture["settings"]["kind"]
    actual = observation_vector(capture["data"],kind)
    if not np.all(np.isfinite(actual)):
        raise ValueError("Observation contains non-finite data")
    return actual-observation_vector(predicted,kind)


def diagnose(captures: list[dict], candidates: list[Candidate], *, sigma_v=0.003):
    if not captures or not candidates or not np.isfinite(sigma_v) or sigma_v <= 0:
        raise ValueError("Need observations, candidates, and a positive development noise scale")
    if len({c.name for c in candidates}) != len(candidates):
        raise ValueError("Candidate names must be unique")
    errors = [[residual(c,obs) for obs in captures] for c in candidates]
    log_likelihood = np.array([-0.5*sum(float(np.sum((r/sigma_v)**2)) for r in rs) for rs in errors])
    probabilities = np.exp(log_likelihood-logsumexp(log_likelihood))
    # Per-acquisition fit gate prevents a long good trace hiding a failed two-point DC test.
    adequate = [all(float(np.sqrt(np.mean(r*r))) <= 5*sigma_v for r in rs) for rs in errors]
    surviving = [c.name for c,ok in zip(candidates,adequate) if ok]
    if not surviving:
        status="all_candidates_inadequate"
        unresolved="The declared candidates do not explain the observations. A new model or fixture check is needed."
    elif len(surviving)>1:
        status="unresolved"
        unresolved="Multiple declared circuits explain the observations; their internal configuration is not established."
    else:
        status="verification_required"
        unresolved="One declared candidate fits; an independent prediction check is still required."
    ranked = sorted(zip(candidates,probabilities,adequate),key=lambda x:float(x[1]),reverse=True)
    return {"status":status,"supported_candidates":surviving,
            "current_explanation":[c.description for c in candidates if c.name in surviving],
            "unresolved":unresolved,
            "candidate_probabilities":[{"name":c.name,"conditional_probability":float(p),"fit_passed":bool(ok)} for c,p,ok in ranked],
            "scope":"Only these fixed candidates and synthetic independent-noise assumptions; not calibrated hardware confidence.",
            "sigma_v":sigma_v,"fit_gate_rms_v":5*sigma_v}


def rank_actions(candidates: list[Candidate], supported: list[str], *, sigma_v=0.003):
    live=[c for c in candidates if c.name in supported]
    results=[]
    for name,acq in ACTION_MENU.items():
        vectors=[observation_vector(predict(c.model,acq),acq.kind) for c in live]
        separation=max((float(np.mean(((a-b)/sigma_v)**2)) for a,b in itertools.combinations(vectors,2)),default=0.0)
        cost=1+acq.physical_acquisitions  # one simulated mounting + acquisition count
        results.append({"action":name,"settings":acq.to_dict(),
                        "separation_score":separation,"development_cost":cost,"score_per_cost":separation/cost})
    return sorted(results,key=lambda x:x["score_per_cost"],reverse=True)


def verify_prediction(prediction: dict, capture: dict, *, sigma_v=0.003):
    kind=capture["settings"]["kind"]
    r=observation_vector(capture["data"],kind)-observation_vector(prediction,kind)
    if not np.all(np.isfinite(r)):
        raise ValueError("Invalid verification data")
    rms=float(np.sqrt(np.mean(r*r)))
    return {"passed":rms <= 5*sigma_v,"rms_error_v":rms,"threshold_v":5*sigma_v,
            "refitted_on_verification":False}

