"""Training-only physical-bias fits and fixed engineering adequacy checks.

No likelihood, posterior probability or calibrated confidence is reported.
Measured IN conditions OUT, so input branches remain unobserved by this layer.
"""
from copy import deepcopy
import math
import time
import numpy as np
from scipy.optimize import least_squares
from .inference import families_for
from .measured_input import predict_incremental_rc
from .netlist import (validate_netlist,topology_fingerprint,render_proposal,
                      DIODE_INITIAL,DIODE_BOUNDS)
from .physical_netlist import validate_input_template,simulate_physical_netlist

ALLOWANCE_V=.009
MAX_SIMULATOR_CALLS=420
MAX_FIT_SECONDS=60.


def validate_observation(observation,*,training=False):
    if observation.get('source')!='physical' or observation.get('voltage_basis')!='independent_DMM_minus_REF':
        raise ValueError('Physical observations with independent differential anchors required')
    if observation.get('all_guards_passed') is not True:
        raise ValueError('All acquisition guards must pass')
    if observation.get('purpose') not in ('training','verification'):
        raise ValueError('Explicit training/verification role required; controls are not training')
    if training and observation['purpose']!='training':
        raise ValueError('Reserved observations cannot enter training fitting')
    s,t,u,di,do,cycle=validate_input_template(observation['input_template'])
    y=np.asarray(observation['output_minus_ref_v'],dtype=float)
    if y.shape!=u.shape or not np.isfinite(y).all() or np.max(np.abs(y))>1.05:
        raise ValueError('Finite bounded differential OUT samples required')
    return s,t,u,di,do,y


def score_prediction(observation,prediction):
    s,t,u,di,do,y=validate_observation(observation)
    pred=np.asarray(prediction,dtype=float)
    if pred.shape!=y.shape or not np.isfinite(pred).all():raise ValueError('Matching finite prediction required')
    residual=y-pred;observed_time=t+do;masks=[]
    if s['kind']=='step':
        relative=observed_time-s['step_index']*s['period_us']*1e-6
        for name,lo,hi in [('pre',None,0),('0_to_5ms',0,5),('5_to_20ms',5,20),('20_to_80ms',20,80),('after_80ms',80,None)]:
            mask=np.ones(len(t),bool)
            if lo is not None:mask&=relative>=lo/1000
            if hi is not None:mask&=relative<hi/1000
            masks.append((name,mask))
    else:
        phase=np.floor(observed_time*s['frequency_hz']%1*8).astype(int)
        masks=[('phase_'+str(i),phase==i) for i in range(8)]
    if any(not m.any() for _,m in masks):raise ValueError('Every predeclared region needs samples')
    regions=[{'name':name,'samples':int(mask.sum()),'RMS_mV':float(np.sqrt(np.mean(residual[mask]**2)))*1000}
             for name,mask in masks]
    rms=float(np.sqrt(np.mean(residual**2)))*1000
    return {'RMS_mV':rms,'regions':regions,'passed':rms<=ALLOWANCE_V*1000 and all(r['RMS_mV']<=ALLOWANCE_V*1000 for r in regions),
            'allowance_mV':ALLOWANCE_V*1000,'scorer_refits_prediction':False,
            'observation_role':observation['purpose'],
            'interpretation':'Fixed development engineering allowance, not calibrated confidence.'}


def linear_prediction(observation,*,r_ohm,c_f=0.,output_parallel_ohm=None):
    # Prediction deliberately reads no scored output or output origin.
    s,t,u,di,do,_=validate_input_template(observation['input_template'])
    if not math.isfinite(r_ohm) or r_ohm<=0 or not math.isfinite(c_f) or c_f<0:
        raise ValueError('Positive resistance and nonnegative capacitance required')
    if output_parallel_ohm is not None and (not math.isfinite(output_parallel_ohm) or output_parallel_ohm<=0):
        raise ValueError('Positive output parallel resistance required')
    gl=(0 if s['load_ohm'] is None else 1/s['load_ohm'])+(0 if output_parallel_ohm is None else 1/output_parallel_ohm)
    gain=1/(1+r_ohm*gl)
    if c_f==0:return (gain*u).tolist()
    result=predict_incremental_rc(t,u,di,do,gain=gain,tau_s=r_ohm*c_f*gain,
        baseline_input_v=0.,baseline_output_v=0.,kind=s['kind'],
        step_index=s['step_index'],frequency_hz=s['frequency_hz'])
    # Zero here is physical REF, not a fitted HOLD origin. Nonzero measured
    # input bias remains in u and therefore in the circuit's DC prediction.
    return result['predicted_output_v']


def fit_linear_families(captures):
    if not captures:raise ValueError('Need training observations')
    for c in captures:validate_observation(c,training=True)
    results=[]
    for family in families_for('mystery'):
        names=['r_ohm'];bounds=[family.r_bounds]
        if family.c_bounds:names.append('c_f');bounds.append(family.c_bounds)
        if family.output_bounds:names.append('output_parallel_ohm');bounds.append(family.output_bounds)
        lo,hi=np.log(bounds).T
        def decode(x):return dict(zip(names,map(float,np.exp(x))))
        def residual(x):
            parameters=decode(x)
            return np.concatenate([(np.asarray(c['output_minus_ref_v'])-linear_prediction(c,**parameters))/ALLOWANCE_V for c in captures])
        result=least_squares(residual,(lo+hi)/2,bounds=(lo,hi),max_nfev=120,ftol=1e-9,xtol=1e-9,gtol=1e-9)
        parameters=decode(result.x)
        curves=[linear_prediction(c,**parameters) for c in captures]
        scores=[score_prediction(c,p) for c,p in zip(captures,curves)]
        singular=np.linalg.svd(result.jac,compute_uv=False)
        rank=int(np.sum(singular>max(1.,singular[0]*1e-6)))
        results.append({'family':family.name,'parameters':parameters,'fit_bounds':dict(zip(names,bounds)),
            'optimizer_converged':bool(result.success),'training_passed':bool(result.success) and all(s['passed'] for s in scores),
            'conditional_fit_rank':rank,'parameters_identifiable':rank==len(names) and family.rp_bounds is None,
            'unobserved_input_branch_bounds_ohm':family.rp_bounds,
            'input_branch_not_fitted':family.rp_bounds is not None,
            'checks':scores,'training_predictions':curves,'OUT_offset_or_gain_fitted':False,
            'training_OUT_used_for_component_fit':True})
    adequate=[r['family'] for r in results if r['training_passed']]
    best=min(results,key=lambda r:sum(s['RMS_mV']**2 for s in r['checks']))
    return {'status':'all_candidates_inadequate' if not adequate else 'some_candidates_adequate',
        'candidates':results,'adequate_families':adequate,'best_family':best['family'],
        'conditional_input_branch_ties':[['rc','rc_input_branch'],['resistor','resistor_input_branch']],
        'training_conditions':len(captures),'verification_observations_used':0}


def fit_physical_proposal(elements,captures):
    if not captures:raise ValueError('Need training observations')
    for c in captures:validate_observation(c,training=True)
    generated=validate_netlist(elements);fitted=deepcopy(generated)
    active=[i for i,e in enumerate(generated) if e['kind'] in ('R','C')]
    if len(active)>2:raise ValueError('At most two R/C values plus shared diode IS/N may be fitted')
    has_diode=any(e['kind']=='D' for e in generated)
    names=[generated[i]['name'] for i in active]+(['diode_IS','diode_N'] if has_diode else [])
    bounds=[[1000,100000] if generated[i]['kind']=='R' else [1e-9,10e-6] for i in active]
    initial=[generated[i]['value'] for i in active]
    if has_diode:initial+=list(DIODE_INITIAL.values());bounds+=list(DIODE_BOUNDS.values())
    diode=dict(DIODE_INITIAL);began=time.monotonic();calls=0;cache_hits=0;cache={}
    def consume():
        nonlocal calls
        if calls>=MAX_SIMULATOR_CALLS or time.monotonic()-began>MAX_FIT_SECONDS:
            raise ValueError('Physical proposal simulator budget exhausted')
        calls+=1
    def decode(x):
        for i,value in zip(active,np.exp(x[:len(active)])):fitted[i]['value']=float(value)
        if has_diode:diode.update(zip(DIODE_INITIAL,map(float,np.exp(x[-2:]))))
    def simulate(i):
        nonlocal cache_hits
        if time.monotonic()-began>MAX_FIT_SECONDS:raise ValueError('Physical proposal fitting deadline exceeded')
        key=(i,tuple(e['value'] for e in fitted),tuple(diode.values()))
        if key not in cache:cache[key]=simulate_physical_netlist(fitted,captures[i]['input_template'],diode=diode,before_run=consume)
        else:cache_hits+=1
        return cache[key]
    def evaluate(x):
        decode(x)
        return np.concatenate([(np.asarray(c['output_minus_ref_v'])-simulate(i)['predicted_output_minus_ref_v'])/ALLOWANCE_V for i,c in enumerate(captures)])
    start=np.log(initial);evaluate(start)
    initial_runs=deepcopy([simulate(i) for i in range(len(captures))])
    if initial:
        limits=np.log(bounds).T
        def jacobian(x):
            base=evaluate(x);columns=[]
            for i in range(len(x)):
                step=1e-3 if x[i]+1e-3<limits[1,i] else -1e-3
                shifted=x.copy();shifted[i]+=step;columns.append((evaluate(shifted)-base)/step)
            return np.column_stack(columns)
        result=least_squares(evaluate,start,bounds=limits,jac=jacobian,max_nfev=18,ftol=1e-6,xtol=1e-6,gtol=1e-6)
        decode(result.x);converged=bool(result.success)
        singular=np.linalg.svd(result.jac,compute_uv=False);condition=float(singular[0]/max(singular[-1],1e-12))
        identifiable=bool(singular[-1]>1 and condition<1e5)
    else:converged=identifiable=True;condition=None
    predictions=[simulate(i) for i in range(len(captures))]
    scores=[score_prediction(c,p['predicted_output_minus_ref_v']) for c,p in zip(captures,predictions)]
    assert topology_fingerprint(generated)==topology_fingerprint(fitted)
    return fitted,{'training_passed':converged and identifiable and all(s['passed'] for s in scores),
        'optimizer_converged':converged,'parameters_identifiable':identifiable,
        'log_parameter_jacobian_condition':condition,'fitted_parameter_names':names,
        'parameter_bounds':dict(zip(names,bounds)),
        'diode_parameters':dict(diode),'checks':scores,'simulator_calls':calls,'simulation_cache_hits':cache_hits,
        'initial_generated_simulations':initial_runs,'training_predictions':predictions,
        'generated_topology_sha256':topology_fingerprint(generated),'fitted_topology_sha256':topology_fingerprint(fitted),
        'rendered_generated_proposal':render_proposal(generated),'rendered_fitted_proposal':render_proposal(fitted),
        'verification_observations_used':0,'OUT_offset_or_gain_fitted':False,
        'training_OUT_used_for_component_fit':bool(initial),
        'interpretation':'Training-only physical-bias conditional fit; parameter identifiability is a local numerical check.'}
