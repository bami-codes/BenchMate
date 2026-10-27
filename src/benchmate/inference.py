"""Continuous fitting and normalized, low-dimensional model evidence.

All mystery specimens share the same prior families. Repair priors require an
explicit user-selected mode. No specimen identity, truth or private assembly.
Integration uses u=log(tau), v=log(R): p(tau,R)=p_RC(R,tau/R)/R.
For independent log-uniform R,C this is constant in (u,v) on its true support,
not independent uniform priors on a rectangular tau/R domain.
"""
from dataclasses import dataclass, asdict
import numpy as np
from scipy.optimize import least_squares
from scipy.special import roots_legendre, logsumexp

from .noise import NoiseModel, whitened_vector, adequacy
from .physics import Acquisition
from .stimulus import command_template
from .vector import predict_many


@dataclass(frozen=True)
class Family:
    name: str
    r_bounds: tuple = (4700., 47000.)
    c_bounds: tuple | None = (.47e-6, 4.7e-6)
    rp_bounds: tuple | None = None
    output_bounds: tuple | None = None

    def __post_init__(self):
        for pair in (self.r_bounds, self.c_bounds, self.rp_bounds,self.output_bounds):
            if pair is not None and (len(pair) != 2 or not 0 < pair[0] < pair[1] or not all(np.isfinite(pair))):
                raise ValueError("Invalid prior support")
        if self.output_bounds is not None and (self.c_bounds is not None or self.rp_bounds is not None):
            raise ValueError('Current output-leak family is a two-resistor topology')

    def to_dict(self):
        return {**asdict(self), "density": "independent_log_uniform_over_present_components",
                'capacitance':'absent_discrete_topology' if self.c_bounds is None else 'positive_log_uniform',
                'model_row_columns':['r_ohm','c_f','input_parallel_ohm']+(['output_parallel_ohm'] if self.c_bounds is None else [])}


def families_for(mode="mystery"):
    if mode == "mystery":
        return [Family("rc"), Family("rc_input_branch", rp_bounds=(4700., 47000.)),
                Family('resistor',c_bounds=None),
                Family('resistor_input_branch',c_bounds=None,rp_bounds=(4700.,47000.)),
                Family('resistor_output_leak',c_bounds=None,output_bounds=(4700.,47000.))]
    if mode == "repair":
        return [Family("nominal", (9500., 10500.), (.9e-6, 1.1e-6)),
                Family("r_changed", (15000., 25000.), (.9e-6, 1.1e-6)),
                Family("c_changed", (9500., 10500.), (1.5e-6, 2.5e-6))]
    raise ValueError("Mode must be explicitly mystery or repair")


def observable_parameters(captures):
    # Excitation/observation geometry, never specimen identity.
    split_rc = any(c["settings"]["load_ohm"] is not None or
                   (c["settings"]["shunt_ohm"] and c["settings"]["kind"] != "dc_pair") for c in captures)
    rp = any(c["settings"]["shunt_ohm"] for c in captures)
    return bool(split_rc), bool(rp)


def validate_observations(captures):
    if not captures:
        raise ValueError("Need observations")
    for capture in captures:
        if capture.get("source") != "synthetic":
            raise ValueError("Hardware inference awaits D2 calibration")
        Acquisition(**capture["settings"])


def fit_family(family, captures, noise):
    if family.c_bounds is None:
        return fit_resistive_family(family,captures,noise)
    split_rc, observed_rp = observable_parameters(captures)
    active_rp = family.rp_bounds is not None and observed_rp
    lr, lc = np.log(family.r_bounds), np.log(family.c_bounds)
    lp = np.log(family.rp_bounds) if family.rp_bounds else None
    bounds = [lr, lc] if split_rc else [np.array([lr[0]+lc[0], lr[1]+lc[1]])]
    if active_rp:
        bounds.append(lp)
    low, high = np.array(bounds).T

    def decode(x):
        if split_rc:
            r, c = np.exp(x[:2])
        else:
            u = x[0]
            v = (max(lr[0], u-lc[1]) + min(lr[1], u-lc[0]))/2
            r, c = np.exp(v), np.exp(u-v)
        rp = np.exp(x[-1]) if active_rp else (np.sqrt(np.prod(family.rp_bounds)) if lp is not None else 0.)
        return np.array([r, c, rp])

    def residual(x):
        row = decode(x)
        return np.concatenate([whitened_vector({k:v[0] for k,v in predict_many(row,obs).items()}, obs, noise) for obs in captures])

    result = least_squares(residual, (low+high)/2, bounds=(low, high),
                           max_nfev=120, ftol=1e-10, xtol=1e-10, gtol=1e-10)
    model = decode(result.x)
    covariance = np.linalg.pinv(result.jac.T @ result.jac)
    identifiable = split_rc and np.linalg.matrix_rank(result.jac) == len(result.x)
    center = np.array([np.log(model[0]*model[1]), np.log(model[0]), np.log(model[2]) if model[2] else 0])
    width = np.array([(lr[1]-lr[0]+lc[1]-lc[0])/2, (lr[1]-lr[0])/2,
                      (lp[1]-lp[0])/2 if lp is not None else 1])
    if split_rc:
        width[0] = np.sqrt(max(1e-12, covariance[0,0]+covariance[1,1]+2*covariance[0,1]))
        width[1] = np.sqrt(max(1e-12, covariance[0,0]))
    else:
        width[0] = np.sqrt(max(1e-12, covariance[0,0]))
    if active_rp:
        width[2] = np.sqrt(max(1e-12, covariance[-1,-1]))
    gates = [adequacy({k:v[0] for k,v in predict_many(model,obs).items()},obs,noise) for obs in captures]
    return {"model": model, "center": center, "width": width,
            "success": bool(result.success), "fit_passed": all(g["passed"] for g in gates) and bool(result.success),
            "checks": gates, "split_rc": split_rc, "identifiable": bool(identifiable), "active_rp": active_rp,
            "log_likelihood": -.5*float(np.sum(result.fun**2))}


def fit_resistive_family(family,captures,noise):
    """Separate C=0 topology. Flat directions retain their normalized priors."""
    branch=family.rp_bounds or family.output_bounds
    bounds=np.log([family.r_bounds]+([branch] if branch else []))
    low,high=bounds.T
    def decode(x):
        return np.array([np.exp(x[0]),0.,np.exp(x[1]) if family.rp_bounds else 0.,
                         np.exp(x[1]) if family.output_bounds else 0.])
    def residual(x):
        return np.concatenate([whitened_vector({k:v[0] for k,v in predict_many(decode(x),c).items()},c,noise) for c in captures])
    result=least_squares(residual,(low+high)/2,bounds=(low,high),max_nfev=120,
                         ftol=1e-10,xtol=1e-10,gtol=1e-10)
    _,singular,vh=np.linalg.svd(result.jac,full_matrices=False)
    rank=int(np.sum(singular>max(1.,singular[0]*1e-6)))
    identifiable=rank==len(result.x)
    covariance=np.linalg.pinv(result.jac.T@result.jac)
    null_power=np.sum(vh[rank:]**2,axis=0)
    # Only individually observable coordinates may use the local width.
    width=np.where(null_power<1e-8,np.sqrt(np.maximum(1e-12,np.diag(covariance))),(high-low)/2)
    model=decode(result.x)
    gates=[adequacy({k:v[0] for k,v in predict_many(model,c).items()},c,noise) for c in captures]
    conditional=None
    loads={c['settings']['load_ohm'] for c in captures}
    if family.output_bounds and len(loads)==1 and not any(c['settings']['shunt_ohm'] for c in captures):
        gl=0. if next(iter(loads)) is None else 1/next(iter(loads))
        q=model[0]*(1/model[3]+gl);gradient=np.array([q,-model[0]/model[3]])
        conditional={'load_conductance':gl,'q':q,'sigma_q':float(np.sqrt(max(1e-14,gradient@covariance@gradient)))}
    return {'model':model,'center':result.x,'width':width,'success':bool(result.success),
            'conditional_output_ridge':conditional,
            'fit_passed':bool(result.success) and all(g['passed'] for g in gates),'checks':gates,
            'split_rc':False,'identifiable':bool(identifiable),
            'active_rp':bool(family.rp_bounds and any(c['settings']['shunt_ohm'] for c in captures)),
            'log_likelihood':-.5*float(np.sum(result.fun**2))}


def axis_nodes(lo, hi, order, *, center=None, width=None, breaks=()):
    points = [lo, hi, *breaks]
    if center is not None and width is not None:
        points.extend(center + width*np.array([-8., -3., -1., 0., 1., 3., 8.]))
    points = np.unique(np.clip(points, lo, hi))
    x, w = roots_legendre(order)
    left, right = points[:-1], points[1:]
    nodes = ((left+right)[:,None]/2 + (right-left)[:,None]*x/2).ravel()
    weights = ((right-left)[:,None]*w/2).ravel()
    return nodes, weights


def prior_grid(family, order=6, fit=None):
    if family.c_bounds is None:
        bounds=[family.r_bounds]+([family.rp_bounds or family.output_bounds] if family.rp_bounds or family.output_bounds else [])
        ridge=fit.get('conditional_output_ridge') if fit else None
        if ridge:
            # At one load only q=R*(1/Rout+1/Rload) is observed. Follow its
            # ridge with conditional nodes, but integrate BOTH original priors.
            lr,lo=np.log(bounds);q,sd,gl=ridge['q'],ridge['sigma_q'],ridge['load_conductance']
            breaks=[np.log(v/(1/rout+gl)) for v in (q-8*sd,q,q+8*sd) if v>0 for rout in bounds[1]]
            x,w=axis_nodes(*lr,order,breaks=breaks);rows=[];weights=[]
            for v,wv in zip(x,w):
                den=q-gl*np.exp(v)
                center=v-np.log(den) if den>0 else None
                width=sd/den if den>0 else None
                y,wy=axis_nodes(*lo,order,center=center,width=width)
                rows.append(np.column_stack([np.full(len(y),np.exp(v)),np.zeros((len(y),2)),np.exp(y)]))
                weights.append(wv*wy/(np.diff(lr)[0]*np.diff(lo)[0]))
            rows,weights=np.concatenate(rows),np.concatenate(weights)
            if not np.isclose(weights.sum(),1,atol=1e-10):raise ValueError('Prior integration failed normalization')
            return rows,weights
        axes=[axis_nodes(*np.log(b),order,center=fit['center'][i] if fit else None,
                         width=fit['width'][i] if fit else None) for i,b in enumerate(bounds)]
        x,w=axes[0];w=w/np.log(bounds[0][1]/bounds[0][0])
        if len(axes)>1:
            y,v=axes[1];v=v/np.log(bounds[1][1]/bounds[1][0])
            xx,yy=np.meshgrid(x,y,indexing='ij');weights=(w[:,None]*v[None,:]).ravel()
            rows=np.column_stack([np.exp(xx.ravel()),np.zeros(xx.size),
                np.exp(yy.ravel()) if family.rp_bounds else np.zeros(xx.size),
                np.exp(yy.ravel()) if family.output_bounds else np.zeros(xx.size)])
        else:
            rows=np.column_stack([np.exp(x),np.zeros((len(x),3))]);weights=w
        if not np.isclose(weights.sum(),1,atol=1e-10):raise ValueError('Prior integration failed normalization')
        return rows,weights
    lr, lc = np.log(family.r_bounds), np.log(family.c_bounds)
    center = fit["center"] if fit else [None]*3
    width = fit["width"] if fit else [None]*3
    u, wu = axis_nodes(lr[0]+lc[0], lr[1]+lc[1], order, center=center[0], width=width[0],
                       breaks=[lr[0]+lc[1], lr[1]+lc[0]])
    rows, weights = [], []
    norm = np.diff(lr)[0]*np.diff(lc)[0]
    if family.rp_bounds:
        lp = np.log(family.rp_bounds)
        p, wp = axis_nodes(*lp, order, center=center[2] if fit and fit["active_rp"] else None,
                           width=width[2] if fit and fit["active_rp"] else None)
        wp /= np.diff(lp)[0]
    else:
        p, wp = np.array([0.]), np.array([1.])
    for tau_log, tau_weight in zip(u, wu):
        lo, hi = max(lr[0],tau_log-lc[1]), min(lr[1],tau_log-lc[0])
        v, wv = axis_nodes(lo, hi, order, center=center[1] if fit and fit["split_rc"] else None,
                           width=width[1] if fit and fit["split_rc"] else None)
        vv, pp = np.meshgrid(v, p, indexing="ij")
        rows.append(np.column_stack([np.exp(vv.ravel()), np.exp(tau_log-vv.ravel()),
                                     np.exp(pp.ravel()) if family.rp_bounds else np.zeros(vv.size)]))
        weights.append((tau_weight * wv[:,None]*wp[None,:]/norm).ravel())
    rows, weights = np.concatenate(rows), np.concatenate(weights)
    if not np.isclose(weights.sum(), 1, atol=1e-10):
        raise ValueError("Prior integration failed normalization")
    return rows, weights


def log_likelihood_many(models, captures, noise):
    ll = np.zeros(len(models))
    for start in range(0, len(models), 256):
        stop = min(len(models), start+256)
        for obs in captures:
            z = whitened_vector(predict_many(models[start:stop], obs), obs, noise)
            ll[start:stop] -= .5*np.sum(z*z, axis=-1)
    return ll


def weighted_interval(values, weights):
    order = np.argsort(values)
    values, weights = np.asarray(values)[order], weights[order]
    cumulative = np.cumsum(weights)
    return np.interp([.025,.5,.975], cumulative, values).tolist()


@dataclass
class Posterior:
    family: Family
    fit: dict
    models: np.ndarray
    weights: np.ndarray
    log_evidence: float
    convergence_delta: float
    converged: bool

    def report(self):
        r,c,rp = self.models[:,:3].T
        intervals = {"r_ohm": weighted_interval(r,self.weights)}
        if self.family.c_bounds is not None:
            intervals.update(tau_s=weighted_interval(r*c,self.weights),c_f=weighted_interval(c,self.weights))
        if self.family.rp_bounds:
            intervals["input_parallel_ohm"] = weighted_interval(rp,self.weights)
        if self.family.output_bounds:
            intervals['output_parallel_ohm']=weighted_interval(self.models[:,3],self.weights)
        return {"name": self.family.name, "prior": self.family.to_dict(),
                "fit_passed": self.fit["fit_passed"], "optimizer_converged": self.fit["success"],
                "fit_model": {"r_ohm": float(self.fit["model"][0]), "c_f": float(self.fit["model"][1]),
                              "input_parallel_ohm": float(self.fit["model"][2]) or None,
                              'output_parallel_ohm':float(self.fit['model'][3]) if self.family.output_bounds else None},
                "regional_checks": self.fit["checks"], "log_evidence_up_to_shared_constant": self.log_evidence,
                "integration_converged": self.converged, "log_evidence_refinement_delta": self.convergence_delta,
                "posterior_intervals_2_5_50_97_5_percent": intervals,
                "identifiability": {"r_c_separately_observed": self.fit["identifiable"] and self.family.c_bounds is not None,
                                    'present_parameters_identified':self.fit['identifiable'],
                                    'capacitance_absent':self.family.c_bounds is None,
                                    "input_branch_observed": self.fit["active_rp"],
                                    "note": "Posterior intervals include prior restrictions; narrow intervals alone do not prove identification."}}


def integrate_family(family, captures, noise=NoiseModel()):
    fit = fit_family(family,captures,noise)
    previous = None
    for order in (4, 7, 10):
        models, prior_weights = prior_grid(family,order,fit)
        log_terms = log_likelihood_many(models,captures,noise) + np.log(prior_weights)
        evidence = float(logsumexp(log_terms))
        delta = abs(evidence-previous) if previous is not None else float("inf")
        weights = np.exp(log_terms-evidence)
        if delta < .05:
            break
        previous = evidence
    return Posterior(family,fit,models,weights,evidence,float(delta),bool(delta < .05))


def infer(captures, families=None, noise=NoiseModel()):
    validate_observations(captures)
    families = families if families is not None else families_for()
    posteriors = [integrate_family(f,captures,noise) for f in families]
    logs = np.array([p.log_evidence for p in posteriors])
    probabilities = np.exp(logs-logsumexp(logs))
    supported = [p.family.name for p in posteriors if p.fit["fit_passed"]]
    adequate = [p for p in posteriors if p.family.name in supported]
    converged = all(p.converged for p in adequate)
    if not supported:
        status = "all_candidates_inadequate"
    elif not converged:
        status = "integration_unresolved"
    elif len(supported) > 1 or not adequate[0].fit["identifiable"]:
        status = "unresolved"
    else:
        status = "verification_required"
    reports = [{**p.report(), "conditional_probability": float(prob)} for p,prob in zip(posteriors,probabilities)]
    analysis = {"status": status, "supported_candidates": supported, "candidates": reports,
                "noise": noise.to_dict(), "parameterization": "original_component_priors; tau_R_Jacobian_for_RC; discrete_C0_topologies",
                "scope": "Declared linear topologies and component bounds only; synthetic likelihood, not calibrated hardware confidence.",
                "unresolved": "Unloaded capacitive families identify tau; resistor-only values may remain unobserved. Prior restrictions are not measurements."
                              if not observable_parameters(captures)[0] else
                              "Candidate support and regional adequacy are separate from conditional model probabilities; independent verification is still required."}
    return analysis, posteriors


def mean_prediction(posterior, settings, *, max_draws=256, noise=NoiseModel()):
    """Deterministic posterior quadrature quantiles for prediction, never refitting."""
    positions = (np.arange(max_draws)+.5)/max_draws
    index = np.searchsorted(np.cumsum(posterior.weights), positions).clip(max=len(posterior.models)-1)
    capture=command_template(settings);base=capture['data']
    draws = predict_many(posterior.models[index],capture)
    return {"mean": {**base, **{k:v.mean(axis=0).tolist() for k,v in draws.items()}},
            "parameter_sd_v": {k:v.std(axis=0).tolist() for k,v in draws.items()},
            "parameter_whitened_sd": {k:noise.whiten(v,independent=settings.kind=='dc_pair',channel=k).std(axis=0).tolist() for k,v in draws.items()},
            "draws": max_draws, "method": "deterministic_posterior_quantiles", "refitted": False}
