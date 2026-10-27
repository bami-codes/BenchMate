"""Synthetic loop orchestration. Ground truth never enters engine inputs."""
import time
import numpy as np
from .simulation import FIXTURES, acquire
from .physics import Acquisition, predict, confirmation_for
from .engine import candidate_set, diagnose, rank_actions, verify_prediction
from .records import Recorder


def run_synthetic(case, *, seed=1, output="runs", noise_sd_v=0.001):
    if case not in FIXTURES: raise ValueError("Unknown development fixture")
    truth=FIXTURES[case]  # only the simulator receives this object
    task="input-branch" if case in ("b1","b6") else "rc-fault"
    candidates=candidate_set(task)
    rng=np.random.default_rng(seed)
    log=Recorder(output,mode="synthetic_engine_only")
    start=time.monotonic()
    log.add("declared_knowledge",{"task":task,"candidate_names":[c.name for c in candidates],
                                 "seed":seed,"source":"synthetic","llm_used":False})
    captures=[acquire(truth,Acquisition(),rng=rng,noise_sd_v=noise_sd_v)]
    count=1
    log.add("acquisition",captures[0])
    before=diagnose(captures,candidates)
    log.add("diagnosis",before)
    ranked=rank_actions(candidates,before["supported_candidates"])
    log.add("action_ranking",ranked)
    result=before; verification=None
    if before["status"]=="unresolved" and ranked[0]["score_per_cost"]>0:
        chosen=ranked[0]
        log.add("instrument_request",{"action":chosen["action"],"execution":"simulated", "physical_human_action":False})
        settings=Acquisition(**chosen["settings"])
        capture=acquire(truth,settings,rng=rng,noise_sd_v=noise_sd_v)
        count+=settings.physical_acquisitions
        captures.append(capture);log.add("acquisition",capture)
        result=diagnose(captures,candidates);log.add("diagnosis",result)
        if result["status"]=="verification_required":
            winner=next(c for c in candidates if c.name==result["supported_candidates"][0])
            verify_settings=confirmation_for(settings)
            prediction=predict(winner.model,verify_settings)
            log.add("prediction_committed",{"candidate":winner.name,"settings":verify_settings.to_dict(),"prediction":prediction})
            # Prediction is recorded before the simulator supplies verification observations.
            confirmation=acquire(truth,verify_settings,rng=rng,noise_sd_v=noise_sd_v)
            count+=verify_settings.physical_acquisitions
            log.add("verification_acquisition",confirmation)
            verification=verify_prediction(prediction,confirmation)
            log.add("verification",verification)
            result={**result,"status":"verified_within_declared_candidates" if verification["passed"] else "prediction_failed",
                    "unresolved":"No remaining ambiguity within these fixed synthetic candidates; broader configurations are untested." if verification["passed"] else "Independent prediction failed; do not confirm this circuit."}
    summary={"source":"synthetic","llm_used":False,"initial_report":before,
             "selected_action":ranked[0]["action"] if len(captures)>1 else None,
             "final_report":result,"verification":verification,
             "total_physical_acquisitions":count,"simulated_mountings":len(captures)-1,
             "requested_human_actions":0,"unrequested_human_interventions":0,
             "elapsed_s":time.monotonic()-start,
             "budget_note":"DC pairs count as two acquisitions. Confirmation is one fresh step. Common exploration is included in the total."}
    log.add("run_completed",summary)
    return log.path,summary


def run_agent(case, *, seed=1, output="runs", effort="medium", env_path=".env",
              budget_path=".private/api-budget.json", client=None, max_requests=8):
    """Simulator owns truth; the model/controller only receive experiment tools."""
    from .agent import ExperimentSession, PROMPT, TOOLS, drive_agent
    from .providers import MetaToolSession, ProviderError
    from .config import load_keys, redact
    if case not in FIXTURES:
        raise ValueError("Unknown development fixture")
    truth = FIXTURES[case]
    task = "input-branch" if case in ("b1", "b6") else "rc-fault"
    rng = np.random.default_rng(seed)
    log = Recorder(output, mode="live_agent_with_synthetic_instrument")
    log.add("declared_knowledge", {"task": task, "seed": seed, "source": "synthetic",
                                  "candidate_names": [c.name for c in candidate_set(task)], "llm_used": True})
    model = None
    session = None
    try:
        model = MetaToolSession(prompt=PROMPT, tools=TOOLS, log=log, effort=effort,
                                env_path=env_path, budget_path=budget_path, client=client,
                                max_requests=max_requests)
        session = ExperimentSession(candidate_set(task), lambda settings: acquire(truth, settings, rng=rng), log)
        result = drive_agent(session, model)
        summary = {**result, **model.metadata()}
        log.add("run_completed", model.sanitize(summary))
        return log.path, model.sanitize(summary)
    except Exception as exc:
        safe = str(exc) if isinstance(exc, ProviderError) else "Agent execution failed: " + type(exc).__name__
        failure = {"error": safe, "source": "synthetic", "llm_used": True}
        if session is not None:
            failure["partial_result"] = session.summary()
        if model is not None:
            failure.update(model.metadata())
        failure = redact(failure, load_keys(env_path))
        log.add("run_failed", failure)
        raise ProviderError(failure["error"] + f"; record: {log.path}") from None
    finally:
        if model is not None:
            model.close()
