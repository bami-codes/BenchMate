"""Unloaded ADC-coordinate discovery. No absolute REF or unique R/IS claim.

One common origin is fixed from the first stationary IN block of each boot.
Every family fits the same bounded constant REF and differential output offset
from training only. The control is a prerequisite, never a training observation.
"""
from copy import deepcopy
import math
import time
import numpy as np
from scipy.optimize import least_squares
from .inference import families_for
from .physical_fitting import linear_prediction
from .physical_netlist import validate_input_template, simulate_physical_netlist
from .netlist import validate_netlist, topology_fingerprint, DIODE_INITIAL, DIODE_BOUNDS

ALLOWANCE=.009
REF_BOUND=.080
OFFSET_BOUND=.010


def validate(capture, role=None):
    if capture.get('source') not in ('physical','mock') or capture.get('voltage_basis')!='ADC_common_boot_origin_v2':
        raise ValueError('Explicit ADC-coordinate provenance required')
    if capture.get('all_guards_passed') is not True or capture.get('purpose') not in ('control','training','verification'):
        raise ValueError('Passed guards and explicit observation role required')
    if role and capture['purpose']!=role:
        raise ValueError('Observation role mismatch; no reserved/control data in training')
    template=capture['input_template']
    expected='adc_input_only' if capture['source']=='physical' else 'mock_adc_input_only'
    if template['source']!=expected:raise ValueError('Mock/physical provenance mismatch')
    s,t,u,di,do,_=validate_input_template(template)
    y=np.asarray(capture['output_relative_origin_v'],float)
    if s['load_ohm'] is not None or y.shape!=u.shape or not np.isfinite(y).all() or np.max(abs(y))>1.05:
        raise ValueError('Bounded unloaded observation required')
    if not capture.get('boot_id') or not capture.get('origin_id'):
        raise ValueError('Boot and frozen origin required')
    return s,t,u,di,do,y


def training_set(captures):
    if not captures:raise ValueError('Training observations required')
    for c in captures:validate(c,'training')
    if len({(c['source'],c['boot_id'],c['origin_id']) for c in captures})!=1:
        raise ValueError('Training must share one source, boot and origin')


def score(capture, prediction):
    s,t,u,di,do,y=validate(capture)
    prediction=np.asarray(prediction,float)
    if prediction.shape!=y.shape or not np.isfinite(prediction).all():raise ValueError('Finite matching prediction required')
    error=y-prediction;observed=t+do
    if s['kind']=='step':
        ms=(observed-s['step_index']*s['period_us']/1e6)*1000
        masks=[(name,(ms>=lo)&(ms<hi)) for name,lo,hi in
               [('pre',-math.inf,0),('0_to_5ms',0,5),('5_to_20ms',5,20),('20_to_80ms',20,80),('after_80ms',80,math.inf)]]
    else:
        phase=np.floor(observed*s['frequency_hz']%1*8).astype(int)
        masks=[('phase_'+str(i),phase==i) for i in range(8)]
    if any(not m.any() for _,m in masks):raise ValueError('Empty predeclared score region')
    regions=[{'name':n,'RMS_mV':float(np.sqrt(np.mean(error[m]**2))*1000)} for n,m in masks]
    rms=float(np.sqrt(np.mean(error**2))*1000)
    return {'RMS_mV':rms,'regions':regions,'passed':rms<=9 and all(x['RMS_mV']<=9 for x in regions),
            'allowance_mV':9,'refitted':False,'purpose':capture['purpose']}


def shifted(template, ref_v):
    result=deepcopy(template)
    result['data']['input_relative_origin_v']=(np.asarray(result['data']['input_relative_origin_v'])-ref_v).tolist()
    return result


def predict(model, template, before_run=None):
    # Template deliberately contains no output samples or output-derived origin.
    ref=model['reference_v'];offset=model['output_offset_v']
    data=shifted(template,ref)
    if model['kind']=='linear':
        values=linear_prediction({'input_template':data},**model['parameters'])
    else:
        values=simulate_physical_netlist(model['elements'],data,diode=model['diode'],before_run=before_run)['predicted_output_minus_ref_v']
    return (np.asarray(values)+ref+offset).tolist()


def rank_info(jacobian):
    singular=np.linalg.svd(jacobian,compute_uv=False)
    rank=int(np.sum(singular>max(1.,singular[0]*1e-6)))
    return {'local_parameter_rank':rank,'fitted_parameter_count':jacobian.shape[1],
            'parameters_identifiable':rank==jacobian.shape[1],
            'unique_physical_parameters_claimed':False}


def fit_linear(captures):
    training_set(captures);results=[]
    for family in families_for('mystery'):
        names=['r_ohm'];bounds=[family.r_bounds]
        if family.c_bounds:names.append('c_f');bounds.append(family.c_bounds)
        if family.output_bounds:names.append('output_parallel_ohm');bounds.append(family.output_bounds)
        lo,hi=np.log(bounds).T
        def decode(x):
            return {'kind':'linear','family':family.name,'parameters':dict(zip(names,map(float,np.exp(x[:-2])))),
                    'reference_v':float(x[-2])*REF_BOUND,'output_offset_v':float(x[-1])*OFFSET_BOUND}
        def residual(x):
            model=decode(x)
            return np.concatenate([(np.asarray(c['output_relative_origin_v'])-predict(model,c['input_template']))/ALLOWANCE for c in captures])
        result=least_squares(residual,np.r_[(lo+hi)/2,0.,0.],bounds=(np.r_[lo,-1,-1],np.r_[hi,1,1]),max_nfev=120)
        model=decode(result.x);checks=[score(c,predict(model,c['input_template'])) for c in captures]
        results.append({'model':model,'training_passed':bool(result.success) and all(c['passed'] for c in checks),
                        'checks':checks,'optimizer_converged':bool(result.success),**rank_info(result.jac),
                        'input_branch_unobserved':family.rp_bounds is not None})
    return {'status':'all_candidates_inadequate' if all(not r['training_passed'] for r in results) else 'some_candidates_adequate',
            'candidates':results,'verification_observations_used':0}


def fit_proposal(elements,captures):
    training_set(captures);generated=validate_netlist(elements)
    indices=[i for i,e in enumerate(generated) if e['kind'] in ('R','C')]
    if len(indices)>2:raise ValueError('At most two R/C values may be fitted')
    has_diode=any(e['kind']=='D' for e in generated)
    bounds=[[1000,100000] if generated[i]['kind']=='R' else [1e-9,10e-6] for i in indices]
    initial=[generated[i]['value'] for i in indices]
    if has_diode:bounds+=list(DIODE_BOUNDS.values());initial+=list(DIODE_INITIAL.values())
    lo,hi=np.log(bounds).T if bounds else (np.array([]),np.array([]))
    start=np.r_[np.log(initial),0.,0.];lower=np.r_[lo,-1.,-1.];upper=np.r_[hi,1.,1.]
    calls=0;cache={};began=time.monotonic()
    def consume():
        nonlocal calls
        if calls>=420 or time.monotonic()-began>60:raise ValueError('Proposal simulation budget exhausted')
        calls+=1
    def decode(x):
        elements=deepcopy(generated)
        for i,value in zip(indices,np.exp(x[:len(indices)])):elements[i]['value']=float(value)
        diode=dict(DIODE_INITIAL)
        if has_diode:diode.update(zip(diode,map(float,np.exp(x[len(indices):len(indices)+2]))))
        return {'kind':'netlist','elements':elements,'diode':diode,
                'reference_v':float(x[-2])*REF_BOUND,'output_offset_v':float(x[-1])*OFFSET_BOUND}
    def curves(x):
        if time.monotonic()-began>60:raise ValueError('Proposal fitting deadline exceeded')
        key=tuple(x)
        if key not in cache:cache[key]=[predict(decode(x),c['input_template'],consume) for c in captures]
        return cache[key]
    def residual(x):
        return np.concatenate([(np.asarray(c['output_relative_origin_v'])-p)/ALLOWANCE for c,p in zip(captures,curves(x))])
    initial_curves=curves(start)
    def jac(x):
        base=residual(x);columns=[]
        for i in range(len(x)):
            step=1e-3 if x[i]+1e-3<upper[i] else -1e-3
            v=x.copy();v[i]+=step;columns.append((residual(v)-base)/step)
        return np.column_stack(columns)
    result=least_squares(residual,start,bounds=(lower,upper),jac=jac,max_nfev=18,ftol=1e-5,xtol=1e-5,gtol=1e-5)
    model=decode(result.x);checks=[score(c,p) for c,p in zip(captures,curves(result.x))]
    fingerprint=topology_fingerprint(generated)
    if fingerprint!=topology_fingerprint(model['elements']):raise RuntimeError('Topology changed during fitting')
    return {'model':model,'training_passed':bool(result.success) and all(c['passed'] for c in checks),
            'checks':checks,'optimizer_converged':bool(result.success),**rank_info(result.jac),
            'simulator_calls':calls,'generated_topology_sha256':fingerprint,
            'generated_elements':generated,'initial_generated_predictions':initial_curves,
            'nuisance_bounds_v':{'reference':[-REF_BOUND,REF_BOUND],'output_offset':[-OFFSET_BOUND,OFFSET_BOUND]},
            'verification_observations_used':0,
            'scope':'Unloaded predictive behavior; R, effective IS and REF can be confounded. No unique topology or part characterization.'}
