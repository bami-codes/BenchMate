from copy import deepcopy
import json
import numpy as np
import pytest

from benchmate import channel_timing_v4 as timing
from benchmate.channel_timing_session_v4 import Session, PhysicalSession
from benchmate.netlist_diagnosis.design import review, CONFIRMATION
from benchmate.netlist_diagnosis.menu import MENU, RESERVED, template
from benchmate.netlist_diagnosis.models import predict as old_predict, score
from benchmate.records import Recorder
from benchmate.verify import verify_run
from scripts.timing_synthetic_v4 import analytic_capture, specimens


def test_step_does_not_rise_before_DAC_frame_but_retains_later_IN_dynamics():
    inp=template(RESERVED[0],source='mock_adc_input_only')
    _,r,rl,c,_=specimens()[0];capture=analytic_capture(RESERVED[0],r,rl,c)
    inp=capture['input_template'];_,t,u,di,do,_,times,values,_,_=timing.stimulus(inp)
    k=inp['settings']['step_index']
    assert np.interp(t[k]-1e-9,times,values)==u[k-1]
    assert np.interp(t[k]+di[k],times,values)==u[k]
    middle=(t[k]+di[k]+t[k+1]+di[k+1])/2
    assert u[k]<np.interp(middle,times,values)<u[k+1]


def test_sine_holds_to_each_write_then_ramps_only_to_actual_A1_time():
    inp=template(RESERVED[1],source='mock_adc_input_only')
    _,t,u,di,_,_,times,values,_,_=timing.stimulus(inp)
    for k in (1,17,43):
        assert np.interp(t[k]-1e-9,times,values)==u[k-1]
        assert np.interp(t[k]+di[k],times,values)==u[k]


@pytest.mark.parametrize('index',[0,1,3,5,6])
def test_independent_physics_controls_pass_with_same_rule(index):
    _,r,rl,c,elements=specimens()[index]
    capture=analytic_capture(RESERVED[0],r,rl,c)
    result=timing.simulate(elements,capture['input_template'])
    assert score(capture,result['predicted_output_minus_ref_v'])['passed']
    assert result['scored_output_samples_used']==0 and result['fitted_timing_parameters']==[]
    if index==0:assert not score(capture,old_predict({'elements':elements},capture['input_template']))['passed']


def test_command_forecasts_keep_original_hold_exactly():
    model={'elements':specimens()[1][-1]};inp=template(RESERVED[0])
    assert timing.predict(model,inp)==old_predict(model,inp)


def test_times_are_recorded_not_a_hardcoded_53us_and_no_mutation():
    inp=template(RESERVED[0],source='mock_adc_input_only')
    inp['data']['input_delay_s']=[30e-6]*512;inp['data']['output_delay_s']=[160e-6]*512
    original=deepcopy(inp)
    _,t,u,di,do,_,knots,values,samples,_=timing.stimulus(inp)
    assert inp==original
    np.testing.assert_allclose(samples,t+do)
    assert any(abs(x-(t[51]+30e-6))<1e-12 for x in knots)


@pytest.mark.parametrize('field',['output_minus_ref_v','fitted_delay_s','fitted_gain'])
def test_no_output_or_timing_nuisances_in_input(field):
    inp=template(RESERVED[0],source='mock_adc_input_only');inp['data'][field]=[0.]*512
    with pytest.raises(ValueError):timing.stimulus(inp)


def test_reserved_OUT_cannot_be_fitted():
    _,r,rl,c,elements=specimens()[0]
    with pytest.raises(ValueError,match='Reserved outputs'):
        timing.assess(elements,[analytic_capture(RESERVED[0],r,rl,c)])


def test_full_mock_tool_loop_freezes_before_holdout_and_preserves_keyless_audit(tmp_path):
    _,r,rl,c,elements=specimens()[0]
    log=Recorder(tmp_path,mode='independent_analytic_mock_not_hardware')
    class Bench:
        source='mock'
        published=False
        acquired=[]
        def acquire(self,settings,role):
            if role=='verification':assert self.published
            self.acquired.append((settings,role))
            value=analytic_capture(settings,r,rl,c);value['purpose']=role;return value
        def bind_forecast(self,h):assert self.published
        def metadata(self):return {'source':'mock','hardware_commands':0}
    bench=Bench()
    def publish(document,h):
        bench.published=True
        (log.path/'predictions-frozen.json').write_text(json.dumps(document))
        return {'sha256':h,'published':True,'remote':False}
    d=review(elements,source_sha256='0'*64,confirmation=CONFIRMATION,note='Independent analytic software test.',simulated=True)
    session=Session(bench,log,d,publish,actor='scripted_controller')
    assert session.actions==[] and bench.acquired==[]
    session.dispatch('inspect_experiment',{})
    session.dispatch('measure',{'action':'unloaded_step_small','reason':'Synthetic controller explicitly selects one action.'})
    assert session.actions==['unloaded_step_small']
    session.dispatch('verify_prediction',{})
    assert session.outcome()=={'verdict':'consistent','components':[]}
    session.dispatch('finish_report',{'verdict':'consistent','components':[],
        'explanation':'Independent analytic mock only.','limits':'Not a physical result.'})
    log.add('run_completed',session.summary())
    assert verify_run(log.path)['passed']
    with pytest.raises(ValueError,match='cannot relabel a mock'):
        PhysicalSession(bench,log,d,publish)
