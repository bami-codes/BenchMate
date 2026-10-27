import numpy as np
import pytest
from benchmate.inference import Family, families_for, infer, integrate_family, prior_grid, mean_prediction
from benchmate.noise import NoiseModel
from benchmate.physics import Acquisition
from benchmate.stimulus import command_template
from benchmate.vector import predict_many
from benchmate.linearity import amplitude_scaling
from benchmate.nonlinear_simulation import acquire_nonlinear


def resistive_capture(r,settings,*,rp=None,ro=None):
    """Independent two-node DC conductance solve, repeated at each input level."""
    c=command_template(settings);d=c['data'];u=np.asarray(d['drive_v'])-d['ref_v']
    go=(1/ro if ro else 0)+(1/settings.load_ohm if settings.load_ohm else 0)
    gp=1/rp if rp else 0
    if settings.shunt_ohm:
        gs=1/settings.shunt_ohm
        vin,out=np.linalg.solve([[gs+gp+1/r,-1/r],[-1/r,go+1/r]],[gs,0])[:,None]*u
    else:
        vin=u;out=u/(1+r*go)
    d.update(in_v=(np.asarray(d['ref_v'])+vin).tolist(),out_v=(np.asarray(d['ref_v'])+out).tolist())
    if settings.kind=='dc_pair':d['shunt_drop_v']=(u-vin).tolist()
    c['source']='synthetic'
    return c


@pytest.mark.parametrize('settings',[Acquisition(),Acquisition(load_ohm=10000),
    Acquisition(shunt_ohm=1000,load_ohm=4700),Acquisition(kind='dc_pair',shunt_ohm=1000)])
def test_zero_capacitance_is_exact_algebraic_circuit(settings):
    c=resistive_capture(12300,settings,rp=23000,ro=16000)
    p=predict_many([[12300,0,23000,16000]],c)
    for k,v in p.items():np.testing.assert_allclose(v[0],c['data'][k],atol=1e-12)


def test_absent_capacitor_has_discrete_mass_and_unobserved_resistance_keeps_prior():
    f=Family('resistor',c_bounds=None)
    rows,w=prior_grid(f,10)
    assert np.all(rows[:,1:]==0) and w.sum()==pytest.approx(1)
    assert w@rows[:,0]==pytest.approx((47000-4700)/np.log(10),rel=1e-10)
    p=integrate_family(f,[resistive_capture(10000,Acquisition())])
    assert p.converged and not p.fit['identifiable']
    r=p.report()
    assert r['identifiability']['capacitance_absent']
    assert 'c_f' not in r['posterior_intervals_2_5_50_97_5_percent']
    assert p.weights@p.models[:,0]==pytest.approx((47000-4700)/np.log(10),rel=1e-6)
    prediction=mean_prediction(p,Acquisition(amplitude_v=.3))
    np.testing.assert_allclose(prediction['mean']['out_v'],prediction['mean']['drive_v'])


@pytest.mark.parametrize('load',[None,10000])
def test_output_leak_single_load_keeps_ridge_but_evidence_converges(load):
    f=Family('resistor_output_leak',c_bounds=None,output_bounds=(4700,47000))
    capture=resistive_capture(10000,Acquisition(load_ohm=load),ro=22000)
    p=integrate_family(f,[capture])
    assert p.fit['fit_passed'] and not p.fit['identifiable']
    assert p.converged
    rows,w=prior_grid(f,7,p.fit)
    assert w.sum()==pytest.approx(1)
    assert p.report()['posterior_intervals_2_5_50_97_5_percent']['r_ohm'][2]>p.report()['posterior_intervals_2_5_50_97_5_percent']['r_ohm'][0]*1.5


def test_common_candidates_identify_resistive_leak_after_second_load():
    captures=[resistive_capture(10000,s,ro=22000) for s in (Acquisition(),Acquisition(load_ohm=10000))]
    result,_=infer(captures)
    assert result['supported_candidates']==['resistor_output_leak']
    assert result['status']=='verification_required'
    assert len(families_for())==5 and len(families_for('repair'))==3


def test_amplitude_scaling_removes_dc_offset_and_checks_the_actual_input():
    settings=[Acquisition(kind='sine',frequency_hz=1,amplitude_v=a,duration_s=2,sample_period_s=.002) for a in (.2,1)]
    captures=[resistive_capture(10000,s,ro=22000) for s in settings]
    captures[0]['data']['out_v']=[v+.02 for v in captures[0]['data']['out_v']]
    checks=amplitude_scaling(captures)['checks']
    assert checks[0]['status']=='scaling_consistent'
    nonlinear=[acquire_nonlinear(s,rng=np.random.default_rng(8)) for s in settings]
    check=amplitude_scaling(nonlinear)['checks'][0]
    assert check['status']=='output_scaling_mismatch' and check['channels']['out_v']['dc_removed_rms_mv']>150
    assert not check['independent_verification']
    nonlinear[1]['data']['in_v']=[1.6+.8*(v-1.6) for v in nonlinear[1]['data']['in_v']]
    assert amplitude_scaling(nonlinear)['checks'][0]['status']=='input_scaling_mismatch'
    nonlinear[1]['settings']['load_ohm']=10000
    assert not amplitude_scaling(nonlinear)['checks']
