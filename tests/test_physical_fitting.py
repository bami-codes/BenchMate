"""Constructed offline fixtures; these tests are never physical evidence."""
import copy
import shutil
import numpy as np
import pytest
from scipy.optimize import brentq
from benchmate.physical_fitting import (fit_linear_families,linear_prediction,
    score_prediction,fit_physical_proposal,validate_observation)
from benchmate.physical_netlist import simulate_physical_netlist


def constructed_fixture(kind='sine',amplitude=.8,load=None,*,purpose='training'):
    n=512;dt=.004 if kind=='sine' else .0005;t=np.arange(n)*dt
    u=-.008+(amplitude*np.sin(2*np.pi*t)+.004*np.cos(6*np.pi*t) if kind=='sine'
              else np.where(np.arange(n)<n//10,-amplitude,amplitude))
    template={'source':'physical_input_only','settings':{'kind':kind,'period_us':round(dt*1e6),'samples':n,
        'frequency_hz':1. if kind=='sine' else None,'step_index':None if kind=='sine' else n//10,'load_ohm':load},
        'data':{'frame_time_s':t.tolist(),'input_minus_ref_v':u.tolist(),
            'input_delay_s':[50e-6]*n,'output_delay_s':[105e-6]*n}}
    return {'source':'physical','voltage_basis':'independent_DMM_minus_REF',
        'all_guards_passed':True,'purpose':purpose,'input_template':template,
        'output_minus_ref_v':[0.]*n,'test_only_constructed_fixture':True}


def training_set():
    return [constructed_fixture('step',.5),constructed_fixture(amplitude=.2),
            constructed_fixture(),constructed_fixture(load=4683.)]


def diode_out(capture,r=12000.,is_a=3e-9,n=1.9):
    u=capture['input_template']['data']['input_minus_ref_v'];load=capture['input_template']['settings']['load_ohm']
    gl=0. if load is None else 1/load;vt=1.380649e-23*300.15/1.602176634e-19
    result=[]
    for drive in u:
        def equation(out):
            current=(drive-out)/r-out*gl
            return current-is_a*np.expm1((out-current)/(n*vt))
        result.append(brentq(equation,min(0,drive)-.01,max(0,drive)+.01))
    return result


def proposal():
    return [dict(name='R1',kind='R',a='IN',b='OUT',value=10000.,model='none'),
            dict(name='D1',kind='D',a='OUT',b='REF',value=0,model='generic_diode')]


@pytest.mark.parametrize('role',['verification','control'])
def test_reserved_and_control_observations_cannot_be_fitted(role):
    c=constructed_fixture(purpose=role)
    with pytest.raises(ValueError):fit_linear_families([c])
    with pytest.raises(ValueError):fit_physical_proposal(proposal(),[c])


def test_five_families_keep_input_branch_ties_and_identify_rc_from_load():
    captures=training_set()
    for c in captures:c['output_minus_ref_v']=linear_prediction(c,r_ohm=12300.,c_f=1.3e-6)
    result=fit_linear_families(captures)
    assert len(result['candidates'])==5
    assert result['adequate_families']==['rc','rc_input_branch']
    rc,branch=result['candidates'][:2]
    assert rc['parameters']['r_ohm']==pytest.approx(12300.,rel=1e-5)
    assert rc['parameters']['c_f']==pytest.approx(1.3e-6,rel=1e-5)
    assert rc['parameters_identifiable'] and not branch['parameters_identifiable']
    assert rc['training_OUT_used_for_component_fit'] and not rc['OUT_offset_or_gain_fitted']
    assert all(s['observation_role']=='training' and not s['scorer_refits_prediction'] for s in rc['checks'])
    assert branch['input_branch_not_fitted']
    np.testing.assert_allclose(rc['training_predictions'],branch['training_predictions'],atol=1e-10)


def test_all_linear_families_fail_constructed_diode_observations():
    captures=training_set()
    for c in captures:c['output_minus_ref_v']=diode_out(c)
    result=fit_linear_families(captures)
    assert result['status']=='all_candidates_inadequate'
    assert result['verification_observations_used']==0


def test_region_failure_and_output_bias_are_not_fitted_away():
    c=constructed_fixture();pred=np.array(linear_prediction(c,r_ohm=10000.))
    c['output_minus_ref_v']=(pred+.02).tolist()
    assert score_prediction(c,pred)['RMS_mV']==pytest.approx(20)
    assert not score_prediction(c,pred)['passed']
    t=np.array(c['input_template']['data']['frame_time_s']);mask=(t%1)<.125
    c['output_minus_ref_v']=(pred+np.where(mask,.02,0)).tolist()
    score=score_prediction(c,pred)
    assert score['RMS_mV']<9 and not score['passed']


def test_prediction_is_independent_of_scored_out():
    c=constructed_fixture();first=linear_prediction(c,r_ohm=10000.,c_f=1e-6)
    c['output_minus_ref_v']=[999.]*512
    assert linear_prediction(c,r_ohm=10000.,c_f=1e-6)==first
    with pytest.raises(ValueError):validate_observation(c)


@pytest.mark.skipif(shutil.which('ngspice') is None,reason='ngspice missing')
def test_generated_proposal_fit_then_two_untouched_conditions():
    captures=training_set()
    for c in captures:c['output_minus_ref_v']=diode_out(c)
    generated=proposal();original=copy.deepcopy(generated)
    fitted,result=fit_physical_proposal(generated,captures)
    assert generated==original and result['training_passed']
    assert fitted[0]['value']==pytest.approx(12000.,rel=.015)
    assert result['diode_parameters']['is_a']==pytest.approx(3e-9,rel=.06)
    assert result['diode_parameters']['n']==pytest.approx(1.9,rel=.01)
    assert result['generated_topology_sha256']==result['fitted_topology_sha256']
    assert result['simulator_calls']<=420
    assert result['training_OUT_used_for_component_fit'] and result['verification_observations_used']==0
    before=copy.deepcopy((fitted,result['diode_parameters']))
    reserved=[constructed_fixture('step',.35,purpose='verification'),
              constructed_fixture(load=9990.,purpose='verification')]
    for c in reserved:
        predicted=simulate_physical_netlist(fitted,c['input_template'],diode=result['diode_parameters'])
        c['output_minus_ref_v']=diode_out(c)
        score=score_prediction(c,predicted['predicted_output_minus_ref_v'])
        assert score['passed'] and score['RMS_mV']<.1
        assert score['observation_role']=='verification' and not score['scorer_refits_prediction']
    assert before==(fitted,result['diode_parameters'])
