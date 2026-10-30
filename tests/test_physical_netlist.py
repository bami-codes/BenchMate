"""Offline prediction checks; no serial device or model provider is accessed."""
import copy
import shutil
import numpy as np
import pytest
from scipy.optimize import brentq
from benchmate.physical_netlist import simulate_physical_netlist,validate_input_template


def resistor():
    return [dict(name='R1',kind='R',a='IN',b='OUT',value=10000.,model='none')]


def template(kind='sine',*,bias=.012,load=None):
    n=512;period=.004 if kind=='sine' else .0005;t=np.arange(n)*period
    # Deliberately nonideal held input, including physical DC bias.
    u=bias+(.75*np.sin(2*np.pi*t)+.018*np.cos(6*np.pi*t) if kind=='sine'
            else np.where(np.arange(n)<n//10,-.48,.49))
    return {'source':'physical_input_only','settings':dict(kind=kind,period_us=round(period*1e6),
        samples=n,frequency_hz=1. if kind=='sine' else None,
        step_index=None if kind=='sine' else n//10,load_ohm=load),
        'data':{'frame_time_s':t.tolist(),'input_minus_ref_v':u.tolist(),
            'input_delay_s':np.full(n,50e-6).tolist(),
            'output_delay_s':np.full(n,105e-6).tolist()}}


@pytest.mark.parametrize('fault',['out','hidden_source','delay','nan','missing_cycle','unknown_load'])
def test_rejects_output_leakage_and_invalid_input(fault):
    t=template()
    if fault=='out':t['data']['output_minus_ref_v']=[0.]*512
    if fault=='hidden_source':t['source']='synthetic'
    if fault=='delay':t['data']['output_delay_s'][10]=.005
    if fault=='nan':t['data']['input_minus_ref_v'][1]=float('nan')
    if fault=='missing_cycle':t['settings']['frequency_hz']=1.1
    if fault=='unknown_load':t['settings']['load_ohm']=0
    with pytest.raises(ValueError):validate_input_template(t)


spice=pytest.mark.skipif(shutil.which('ngspice') is None,reason='ngspice is not installed')


@spice
def test_resistor_preserves_measured_bias_and_nonideal_wave_with_real_load():
    t=template(load=9990.)
    original=copy.deepcopy(t)
    result=simulate_physical_netlist(resistor(),t)
    u=np.array(t['data']['input_minus_ref_v'])
    np.testing.assert_allclose(result['predicted_input_minus_ref_v'],u,atol=1e-7,rtol=0)
    np.testing.assert_allclose(result['predicted_output_minus_ref_v'],u*9990/(9990+10000),atol=1e-7,rtol=0)
    assert t==original and result['scored_output_samples_used']==0


def analytic_rc(t,gain,tau):
    s=t['settings'];u=np.array(t['data']['input_minus_ref_v']);period=s['period_us']*1e-6
    decay=np.exp(-period/tau)
    if s['kind']=='step':state=float(u[:s['step_index']].mean())*gain
    else:
        cycle=round(1/s['frequency_hz']/period);offset=0.
        for x in u[:cycle]:offset=decay*offset+(1-decay)*gain*x
        state=offset/(1-decay**cycle)
    predicted=[]
    for x,delay in zip(u,t['data']['output_delay_s']):
        equilibrium=gain*x
        predicted.append(equilibrium+(state-equilibrium)*np.exp(-delay/tau))
        state=equilibrium+(state-equilibrium)*decay
    return np.array(predicted)


@spice
@pytest.mark.parametrize('kind',['step','sine'])
def test_capacitor_uses_measured_cycle_and_a2_delay_against_analytic_rc(kind):
    t=template(kind,load=9990.)
    p=resistor()+[dict(name='C1',kind='C',a='OUT',b='REF',value=1e-6,model='none')]
    result=simulate_physical_netlist(p,t)
    gain=9990/(10000+9990);tau=10000*gain*1e-6
    expected=analytic_rc(t,gain,tau)
    np.testing.assert_allclose(result['predicted_output_minus_ref_v'],expected,atol=60e-6,rtol=0)
    if kind=='sine':
        assert result['initialization']['numerical_convergence']
        assert result['initialization']['method']=='repeated_first_measured_input_cycle'
        assert len(result['simulator_invocations'])>=2
    else:
        changed=copy.deepcopy(t);changed['data']['output_delay_s']=[450e-6]*512
        later=simulate_physical_netlist(p,changed)
        assert abs(later['predicted_output_minus_ref_v'][51]-result['predicted_output_minus_ref_v'][51])>.02


@spice
def test_diode_orientation_is_executed_and_bias_is_not_zeroed():
    t=template(bias=.025)
    p=resistor()+[dict(name='D1',kind='D',a='OUT',b='REF',value=0,model='generic_diode')]
    result=simulate_physical_netlist(p,t,diode={'is_a':3e-9,'n':1.9})
    u=np.array(t['data']['input_minus_ref_v']);actual=np.array(result['predicted_output_minus_ref_v'])
    # Independent DC diode equation including fixed 1-ohm series resistance.
    vt=1.380649e-23*(273.15+27)/1.602176634e-19
    expected=[]
    for drive in u:
        f=lambda out:(drive-out)/10000-3e-9*np.expm1((out-(drive-out)/10000)/(1.9*vt))
        expected.append(brentq(f,min(drive,0)-.001,max(drive,0)+.001))
    np.testing.assert_allclose(actual,expected,atol=20e-6,rtol=0)
    reversed_p=copy.deepcopy(p);reversed_p[1].update(a='REF',b='OUT')
    reversed_result=simulate_physical_netlist(reversed_p,t,diode={'is_a':3e-9,'n':1.9})
    assert np.sqrt(np.mean((actual-np.array(reversed_result['predicted_output_minus_ref_v']))**2))>.1
    assert result['topology_sha256']!=reversed_result['topology_sha256']


@spice
def test_input_parallel_branch_remains_conditional_output_tie():
    t=template();p=resistor()
    base=simulate_physical_netlist(p,t)
    branch=simulate_physical_netlist(p+[dict(name='R2',kind='R',a='IN',b='REF',value=9990.,model='none')],t)
    np.testing.assert_allclose(base['predicted_output_minus_ref_v'],branch['predicted_output_minus_ref_v'],atol=1e-7,rtol=0)
    assert not branch['input_parallel_branches_identifiable']


@spice
def test_each_simulator_invocation_consumes_budget_callback():
    calls=[];t=template()
    p=resistor()+[dict(name='C1',kind='C',a='OUT',b='REF',value=1e-6,model='none')]
    result=simulate_physical_netlist(p,t,before_run=lambda:calls.append(1))
    assert len(calls)==len(result['simulator_invocations']) and len(calls)>=2
