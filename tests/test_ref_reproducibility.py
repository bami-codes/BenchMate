from copy import deepcopy

import numpy as np
import pytest

from benchmate.instrument import InstrumentConfig
from benchmate.ref_reproducibility import POLICY,digest,evaluate,fit,fault_checks,origin,raw_checks
from benchmate.reproducibility_bench import validate_qualification

CONFIG=InstrumentConfig(vref_v=4.9,ref_v=1.646)
LIMITS={'REF_mean_delta_v_max':.1,'REF_any_sample_delta_v_max':.15,
        'REF_channel_mean_spread_v_max':.05,'signal_envelope_v':.95,'A4_envelope_v':.15}


def block(kind='hold',amp=.5,k=.012,frequency=1,seed=1,label=None):
    n=512;period=500 if kind=='step' else 4000 if kind=='sine' and frequency==1 else 2000
    t=np.arange(n)*period*1e-6
    x=np.zeros(n) if kind=='hold' else amp*np.where(np.arange(n)<n//10,-1,1) if kind=='step' else amp*np.sin(2*np.pi*frequency*t)
    rng=np.random.default_rng(seed)
    volts=np.column_stack([1.646+x,1.646+.5*x,
        1.646+k*x+rng.normal(0,.0002,n),1.646+k*x+rng.normal(0,.0002,n)])
    counts=np.rint(volts*16383/4.9).astype(int)
    a=np.column_stack([np.arange(n)*period,np.full(n,1376),counts,np.tile([52,105,158,215],(n,1))])
    settings={'kind':kind,'samples':n,'period_us':period}
    if kind=='hold':settings['hold_v']=1.646
    else:settings['amplitude_v']=amp
    if kind=='sine':settings['frequency_hz']=frequency
    return {'label':label or f'{kind}_{seed}','settings':settings,'rows':a.tolist()}


def data(step_k=.012,sine_k=.012):
    return [block(seed=i) for i in range(3)] + [block('step',.2,step_k,seed=4),
        block('step',.5,step_k,seed=5),block('sine',.2,sine_k,seed=6),
        block('sine',.8,sine_k,seed=7),block('sine',.15,sine_k,frequency=5,seed=8)]


def test_joint_fixed_fit_and_real_validation_do_not_refit():
    records=data();o=origin(records[:3]);result=fit(records,o,4.9)
    assert result['passed'];c=result['candidate']
    assert c['fixed_k']==pytest.approx(.012,abs=.0002)
    before=digest(c)
    check=evaluate(records+[block('sine',.65,.012,frequency=5,seed=9)],o,4.9,c['fixed_k'])
    assert check['passed'] and not check['k_was_refitted'] and digest(c)==before


def test_different_step_and_sine_slopes_need_common_feasible_interval():
    records=data(.020,.012);result=fit(records,origin(records[:3]),4.9)
    assert result['passed']
    assert .014<result['candidate']['fixed_k']<.018
    assert len(result['candidate']['descriptive_k'])==5
    assert all(not d['used_as_per_capture_correction'] for d in result['candidate']['descriptive_k'])


def test_incompatible_slopes_fail_instead_of_adding_frequency_coefficients():
    records=data(.025,-.020);result=fit(records,origin(records[:3]),4.9)
    assert not result['passed'] and 'candidate' not in result


def test_OUT_is_not_used_to_fit_k():
    records=data();o=origin(records[:3]);first=fit(records,o,4.9)['candidate']['fixed_k']
    other=deepcopy(records)
    for b in other:
        for row in b['rows']:row[3]=12000
    second=fit(other,origin(other[:3]),4.9)['candidate']['fixed_k']
    assert first==second


def test_fixed_model_catches_input_correlated_real_fault_that_adaptive_fit_hides():
    records=data();o=origin(records[:3]);c=fit(records,o,4.9)['candidate']
    faults=fault_checks(records,o,CONFIG,LIMITS,c['fixed_k'])
    assert faults['passed'] and faults['software_only'] and not faults['physical_faults_inserted']
    changed=deepcopy(records)
    for b in changed[3:]:
        a=np.asarray(b['rows'],dtype=float);x=(a[:,2]-o['counts'][0])*4.9/16383
        a[:,4:6]+=.008*x[:,None]*16383/4.9;b['rows']=a.tolist()
    assert not evaluate(changed,o,4.9,c['fixed_k'])['passed']
    assert fit(changed,o,4.9)['passed'] # demonstrates why re-learning is forbidden


def test_sine_mean_cannot_hide_large_unmodelled_residual():
    records=data();o=origin(records[:3]);c=fit(records,o,4.9)['candidate']
    wrong=block('sine',.8,.025,seed=10)
    check=evaluate([wrong],o,4.9,c['fixed_k'])
    assert not check['passed'] and max(check['blocks'][0]['RMS_mV'])>3


@pytest.mark.parametrize('channel',[0,1,2,3])
def test_raw_HOLD_drift_remains_guarded(channel):
    b=block();a=np.asarray(b['rows'],dtype=float);base=a[:,2:6].mean(0)*4.9/16383
    a[:,2+channel]+=.004*16383/4.9
    checks,_=raw_checks(a,b['settings'],CONFIG,LIMITS,[base.tolist()])
    assert not checks['stationary_path_mean_span']


def test_unqualified_or_wrong_candidate_or_loaded_fixture_is_rejected():
    records=data();c=fit(records,origin(records[:3]),4.9)['candidate']
    q={'schema':'benchmate.fixed-k-ref-qualification.v1','passed':True,
       'candidate_sha256':digest(c),'fault_injection_passed':True,'qualified_fixtures':['unloaded'],
       'source':'physical_instrument_QA','validation_refit':False,
       'freeze_receipt':{'remote':True,'candidate_sha256':digest(c)}}
    assert validate_qualification(c,q)
    with pytest.raises(ValueError):validate_qualification(c,q,'output_load')
    with pytest.raises(ValueError):validate_qualification({**c,'fixed_k':.02},q)
    with pytest.raises(ValueError):validate_qualification(c,{**q,'passed':False})
    with pytest.raises(ValueError):validate_qualification({**c,'fixed_k':float('nan')},q)
