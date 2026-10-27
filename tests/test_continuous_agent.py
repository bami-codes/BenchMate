import json
import httpx
import pytest
from benchmate.experiments import run_experiment
from benchmate.records import read_events


def test_live_protocol_runs_common_continuous_family_with_mocked_model(tmp_path,monkeypatch):
    monkeypatch.delenv('MODEL_API_KEY',raising=False)
    env=tmp_path/'.env';env.write_text('MODEL_API_KEY=test-continuous-secret\n')
    requests=[]
    def handler(request):
        body=json.loads(request.content);requests.append(body)
        i=len(requests)
        if i==1:
            name,args='inspect_experiment',{}
        else:
            snapshot=json.loads(body['input'][-1]['output'])
            state=snapshot['analysis']['status']
            if state=='unresolved':
                chosen=next(r for r in snapshot['action_ranking'] if r['affordable'])
                name,args='measure',{'action':chosen['action'],'reason':'Use observed predictive separation'}
            elif state=='verification_required':name,args='verify_prediction',{}
            else:
                assert state=='verified_within_declared_candidates'
                name,args='finish_report',{'verdict':'verified','candidate':snapshot['analysis']['supported_candidates'][0],
                    'current_explanation':'합성 연속 후보군에서 검증했습니다.','unresolved':'실물은 미검증입니다.','next_observation':{'kind':'menu_action','action':'shunt_dc_pair','requirement':'','reason':'Repeat the current check after calibration.'}}
        return httpx.Response(200,json={'status':'completed','usage':{},'output':[
            {'type':'function_call','name':name,'call_id':str(i),'arguments':json.dumps(args)}]})
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        path,result=run_experiment('b6',mode='mystery',live=True,r_scale=1.01,c_scale=1.05,
            client=client,env_path=env,budget_path=tmp_path/'budget.json',output=tmp_path/'runs')
    assert result['agent_report']['candidate']=='rc_input_branch'
    assert result['verification']['passed'] and not result['verification']['refitted_on_verification']
    assert result['total_physical_acquisitions']<=5
    assert len(requests)<=8
    kinds=[e['kind'] for e in read_events(path)]
    assert kinds.index('prediction_committed')<kinds.index('verification_acquisition')
    assert 'test-continuous-secret' not in (path/'events.jsonl').read_text()
    assert 'b6' not in requests[0]['input'][0]['content']


def test_mystery_mode_does_not_switch_to_fault_candidates(tmp_path):
    path,result=run_experiment('d01-r',mode='mystery',output=tmp_path)
    events=read_events(path)
    config=next(e['payload'] for e in events if e['kind']=='inference_configuration')
    assert [f['name'] for f in config['families']]==['rc','rc_input_branch','resistor','resistor_input_branch','resistor_output_leak']
    assert result['diagnostic_mode']=='mystery'
    assert result['final_report']['supported_candidates']==['rc']


def test_five_common_families_keep_b1_b6_identical_until_shunt_then_separate(tmp_path):
    import numpy as np
    from benchmate.continuous_agent import ContinuousSession
    from benchmate.simulation import FIXTURES,acquire
    from benchmate.records import Recorder
    sessions=[]
    for case in ['b1','b6']:
        rng=np.random.default_rng(8)
        session=ContinuousSession(lambda s,model=FIXTURES[case],rng=rng:acquire(model,s,rng=rng),
                                  Recorder(tmp_path/case,mode='regression'))
        sessions.append(session)
        session.dispatch('inspect_experiment',{})
        assert len(session.families)==5
        assert session.analysis['status']=='unresolved'
        assert session.analysis['supported_candidates']==['rc','rc_input_branch']
    assert sessions[0].snapshot()==sessions[1].snapshot()
    for session,winner in zip(sessions,['rc','rc_input_branch']):
        session.dispatch('measure',{'action':'shunt_dc_pair','reason':'Distinguish input leakage by current.'})
        assert session.analysis['supported_candidates']==[winner]
        # The DC shunt separates structure; a loaded transient still resolves R/C.
        session.dispatch('measure',{'action':'step_a0.5_s0_l10000','reason':'Identify R and C after the structural check.'})
        assert session.analysis['status']=='verification_required'
        session.dispatch('verify_prediction',{})
        assert session.verification['passed'] and not session.verification['refitted_on_verification']
        assert session.analysis['supported_candidates']==[winner]
