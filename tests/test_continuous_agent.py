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
                    'current_explanation':'합성 연속 후보군에서 검증했습니다.','unresolved':'실물은 미검증입니다.','next_observation':'보정 후 실측합니다.'}
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
    assert [f['name'] for f in config['families']]==['rc','rc_input_branch']
    assert result['diagnostic_mode']=='mystery'
    assert result['final_report']['supported_candidates']==['rc']
