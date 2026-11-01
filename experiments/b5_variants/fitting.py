"""Selection-only multistart fits; copied frozen residuals with explicit starts.

The live B5 session still uses its original fitting functions. This module only
extends the comparator/selection initial points; it never sees reserved OUT in
optimization. Source of residuals: cf33122 src/benchmate/b5_models.py.
"""
from copy import deepcopy
import time
import numpy as np
from scipy.optimize import least_squares
from benchmate.inference import families_for
from benchmate.b5_models import training_set, predict, score, rank_info, ALLOWANCE, REF_BOUND, OFFSET_BOUND
from benchmate.netlist import validate_netlist, topology_fingerprint, DIODE_BOUNDS, DIODE_INITIAL

def fit_linear_start(captures, fraction=.5):
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
        result=least_squares(residual,np.r_[lo+(hi-lo)*fraction,0.,0.],bounds=(np.r_[lo,-1,-1],np.r_[hi,1,1]),max_nfev=120)
        model=decode(result.x);checks=[score(c,predict(model,c['input_template'])) for c in captures]
        results.append({'model':model,'training_passed':bool(result.success) and all(c['passed'] for c in checks),
                        'checks':checks,'training_cost':float(result.cost),'optimizer_converged':bool(result.success),**rank_info(result.jac),
                        'input_branch_unobserved':family.rp_bounds is not None})
    return {'status':'all_candidates_inadequate' if all(not r['training_passed'] for r in results) else 'some_candidates_adequate',
            'candidates':results,'verification_observations_used':0}


def fit_proposal_start(elements,captures, diode_start=None):
    training_set(captures);generated=validate_netlist(elements); diode_start=dict(diode_start or DIODE_INITIAL)
    indices=[i for i,e in enumerate(generated) if e['kind'] in ('R','C')]
    if len(indices)>2:raise ValueError('At most two R/C values may be fitted')
    has_diode=any(e['kind']=='D' for e in generated)
    bounds=[[1000,100000] if generated[i]['kind']=='R' else [1e-9,10e-6] for i in indices]
    initial=[generated[i]['value'] for i in indices]
    if has_diode:bounds+=list(DIODE_BOUNDS.values());initial+=list(diode_start.values())
    lo,hi=np.log(bounds).T if bounds else (np.array([]),np.array([]))
    start=np.r_[np.clip(np.log(initial),lo+1e-10,hi-1e-10),0.,0.];lower=np.r_[lo,-1.,-1.];upper=np.r_[hi,1.,1.]
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
            'checks':checks,'training_cost':float(result.cost),'optimizer_converged':bool(result.success),**rank_info(result.jac),
            'simulator_calls':calls,'generated_topology_sha256':fingerprint,
            'generated_elements':generated,'initial_generated_predictions':initial_curves,
            'nuisance_bounds_v':{'reference':[-REF_BOUND,REF_BOUND],'output_offset':[-OFFSET_BOUND,OFFSET_BOUND]},
            'verification_observations_used':0,
            'scope':'Unloaded predictive behavior; R, effective IS and REF can be confounded. No unique topology or part characterization.'}
