"""Isolated fake-observation tests; no serial ports or provider calls."""
from copy import deepcopy
import math
import numpy as np
import pytest
from benchmate.agent import ToolRejected
from benchmate.physical_rc import PhysicalRCSession,STEP,SINE,train_unloaded,transfer_models


class Log:
    def __init__(self):self.events=[]
    def add(self,kind,payload):self.events.append((kind,deepcopy(payload)))


def observation(settings,r=10000.,c=2e-6,load=None,output_bias=.010):
    n=settings['samples'];dt=settings['period_us']*1e-6;t=np.arange(n)*dt;delay=105e-6
    g=1. if load is None else load/(load+r);tau=r*c*g;a=math.exp(-dt/tau);ad=math.exp(-delay/tau)
    amplitude=settings['amplitude_v']
    if settings['kind']=='step':
        delta=np.where(np.arange(n)<n//10,-amplitude,amplitude)
        relative=t+delay-(n//10)*dt
        out=np.where(relative<0,-amplitude*g,amplitude*g-2*amplitude*g*np.exp(-np.maximum(relative,0)/tau))
    else:
        omega=2*math.pi*settings['frequency_hz']*dt;delta=amplitude*np.sin(omega*np.arange(n))
        coefficient=(1-a)*g*amplitude/(np.exp(1j*omega)-a)
        state=np.imag(coefficient*np.exp(1j*omega*np.arange(n)))
        out=ad*state+(1-ad)*g*delta
    return {'source':'physical','fresh_measurement':True,'all_guards_passed':True,'settings':deepcopy(settings),
            'fixture':'unloaded' if load is None else 'output_load','baseline':{'input_v':1.63,'output_v':1.63+output_bias},
            'data':{'frame_time_s':t.tolist(),'input_delay_s':[50e-6]*n,'output_delay_s':[delay]*n,
                    'input_v':(1.63+delta).tolist(),'output_v':(1.63+output_bias+out).tolist()}}


@pytest.mark.parametrize('r,c,winner',[(10000.,2e-6,'c_changed'),(20000.,1e-6,'r_changed'),(10000.,1e-6,None)])
def test_first_training_then_loaded_and_fresh_reserved_waveform(r,c,winner):
    calls=[];log=Log()
    def acquire(settings,models,fixture,phase):
        assert log.events[-1][0]=='physical_measurement_selected'
        calls.append((settings,deepcopy(models),fixture,phase))
        return observation(settings,r,c,None if fixture=='unloaded' else 9990.)
    session=PhysicalRCSession(acquire,log)
    session.dispatch('inspect_experiment',{})
    session.dispatch('measure',{'action':'unloaded_step','reason':'Measure tau without assuming individual parts.'})
    assert session.training['tau_s']==pytest.approx(r*c,rel=1e-5)
    assert not session.training['individual_R_C_identified']
    before=deepcopy(session.models)
    session.dispatch('measure',{'action':'attach_output_load_step','reason':'Separate the alternatives by their loaded gain.'})
    if winner is None:
        assert len(session.supported)==3 and not session.snapshot()['verification_available']
        return
    assert session.supported==[winner]
    with pytest.raises(ToolRejected):
        session.dispatch('finish_report',{'verdict':'verified','candidate':winner,'current_explanation':'x','unresolved':'x','next_observation':'x'})
    session.dispatch('verify_prediction',{})
    assert session.verified and session.models==before
    assert calls[1][1]==calls[2][1] and calls[2][0]==SINE
    session.dispatch('finish_report',{'verdict':'verified','candidate':winner,'current_explanation':'Limited support','unresolved':'Calibration','next_observation':'Further validation'})
    assert session.summary()['scored_capture_count']==3


def test_failed_reserved_check_cannot_confirm_or_retry():
    def acquire(settings,models,fixture,phase):
        return observation(settings,c=4e-6 if phase=='reserved_sine' else 2e-6,load=None if fixture=='unloaded' else 9990.)
    s=PhysicalRCSession(acquire,Log());s.dispatch('inspect_experiment',{})
    for action in ['unloaded_step','attach_output_load_step']:s.dispatch('measure',{'action':action,'reason':'Evidence'})
    models=deepcopy(s.models);s.dispatch('verify_prediction',{})
    assert not s.verified and s.models==models
    with pytest.raises(ToolRejected):s.dispatch('verify_prediction',{})
    with pytest.raises(ToolRejected):s.dispatch('finish_report',{'verdict':'verified','candidate':'c_changed','current_explanation':'x','unresolved':'x','next_observation':'x'})


@pytest.mark.parametrize('field,value',[('source','synthetic'),('fresh_measurement',False),('all_guards_passed',False),('fixture','output_load')])
def test_wrong_provenance_stops_session(field,value):
    def acquire(settings,*args):
        obs=observation(settings);obs[field]=value;return obs
    s=PhysicalRCSession(acquire,Log());s.dispatch('inspect_experiment',{})
    with pytest.raises(ValueError):s.dispatch('measure',{'action':'unloaded_step','reason':'Evidence'})
    with pytest.raises(ToolRejected):s.dispatch('measure',{'action':'unloaded_step','reason':'Retry'})


def test_repeat_does_not_refit_and_budget_prevents_hidden_extra_acquisition():
    calls=[]
    def acquire(settings,models,fixture,phase):
        calls.append(phase);return observation(settings,c=2.5e-6 if phase=='repeat_unloaded_step' else 2e-6,load=None if fixture=='unloaded' else 9990.)
    s=PhysicalRCSession(acquire,Log());s.dispatch('inspect_experiment',{})
    s.dispatch('measure',{'action':'unloaded_step','reason':'Evidence'});frozen=deepcopy(s.models)
    s.dispatch('measure',{'action':'repeat_unloaded_step','reason':'Repeat'})
    assert s.models==frozen
    s.dispatch('measure',{'action':'repeat_unloaded_step','reason':'Repeat'})
    with pytest.raises(ToolRejected):s.dispatch('measure',{'action':'attach_output_load_step','reason':'Exhausted'})
    assert len(calls)==3


def test_model_cannot_supply_raw_commands_or_act_before_inspection():
    s=PhysicalRCSession(lambda *args:pytest.fail('Unexpected acquisition'),Log())
    with pytest.raises(ToolRejected):s.dispatch('measure',{'action':'unloaded_step','reason':'Evidence'})
    s.dispatch('inspect_experiment',{})
    with pytest.raises(ToolRejected):s.dispatch('measure',{'action':'ARM arbitrary','reason':'Evidence'})
    with pytest.raises(ToolRejected):s.dispatch('measure',{'action':'unloaded_step','reason':'Evidence','amplitude_v':'5'})
