import copy
import shutil
import json
import numpy as np
import httpx
import pytest
from benchmate.netlist import validate_netlist,render_proposal,simulate_netlist,topology_fingerprint
from benchmate.physics import Acquisition
from benchmate.nonlinear_simulation import acquire_nonlinear
from benchmate.noise import adequacy
from benchmate.discovery import run_discovery
from benchmate.records import read_events


def proposal():
    return [dict(name='R1',kind='R',a='IN',b='OUT',value=10000,model='none'),
            dict(name='D1',kind='D',a='OUT',b='REF',value=0,model='generic_diode')]


@pytest.mark.parametrize('fault',['directive','node','value','nonfinite','model','extra','floating'])
def test_untrusted_proposal_rejects_code_and_invalid_circuit(fault):
    p=proposal()
    if fault=='directive':p[0]['name']='R1\n.include /etc/passwd'
    if fault=='node':p[0]['a']='IN; shell command'
    if fault=='value':p[0]['value']=1
    if fault=='nonfinite':p[0]['value']=float('nan')
    if fault=='model':p[1]['model']='.include model.txt'
    if fault=='extra':p[0]['spice']='.control'
    if fault=='floating':p[0]['b']='N1';p[1]['a']='N1'
    with pytest.raises(ValueError):validate_netlist(p)


def test_render_preserves_generated_orientation_and_values():
    p=proposal();p[1]['a'],p[1]['b']=p[1]['b'],p[1]['a']
    assert render_proposal(p)=='R1 in out 10000\nD1 0 out BM_DIODE'
    assert topology_fingerprint(p)!=topology_fingerprint(proposal())


@pytest.mark.skipif(shutil.which('ngspice') is None,reason='ngspice not installed')
def test_generated_topology_is_executed_and_wrong_direction_fails():
    observation=acquire_nonlinear(Acquisition(kind='sine',frequency_hz=1,amplitude_v=1,duration_s=2,sample_period_s=.002),rng=np.random.default_rng(3),noise_sd_v=0)
    p=proposal();predicted,_=simulate_netlist(p,observation)
    assert adequacy(predicted,observation)['passed']
    p[1]['a'],p[1]['b']=p[1]['b'],p[1]['a']
    wrong,_=simulate_netlist(p,observation)
    assert not adequacy(wrong,observation)['passed']


@pytest.mark.skipif(shutil.which('ngspice') is None,reason='ngspice not installed')
def test_mock_model_proposal_reaches_spice_then_two_untouched_checks(tmp_path,monkeypatch):
    monkeypatch.delenv('MODEL_API_KEY',raising=False)
    env=tmp_path/'.env';env.write_text('MODEL_API_KEY=test-discovery-secret\n')
    requests=[]
    def handler(request):
        body=json.loads(request.content);requests.append(body);i=len(requests)
        if i==1:name,args='inspect_residuals',{}
        elif i==2:
            context=json.loads(body['input'][-1]['output'])
            assert context['initial_assessment']['status']=='all_candidates_inadequate'
            assert not context['verification_data_visible']
            name,args='propose_netlist',{'elements':proposal(),'rationale':'Amplitude-dependent positive-half clipping suggests a nonlinear shunt.'}
        elif i==3:
            fitted=json.loads(body['input'][-1]['output'])
            assert fitted['training_passed'] and fitted['topology_preserved']
            assert not fitted['verification_data_visible']
            name,args='verify_proposal',{}
        else:
            verified=json.loads(body['input'][-1]['output']);assert verified['passed']
            name,args='finish_report',{'verdict':'verified','candidate':'proposed_netlist',
                'current_explanation':'합성 관측에서 생성한 연결을 검증했습니다.','unresolved':'실제 부품은 미검증입니다.','next_observation':'보정 후 재측정합니다.'}
        return httpx.Response(200,json={'status':'completed','usage':{},'output':[
            {'type':'function_call','call_id':str(i),'name':name,'arguments':json.dumps(args)}]})
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        path,result=run_discovery(client=client,env_path=env,output=tmp_path/'runs',budget_path=tmp_path/'budget.json')
    assert result['agent_report']['verdict']=='verified' and len(requests)==4
    assert result['verification']['passed'] and not result['verification']['refitted_on_verification']
    events=read_events(path);kinds=[e['kind'] for e in events]
    committed=[i for i,k in enumerate(kinds) if k=='prediction_committed']
    assert len(committed)==2 and max(committed)<kinds.index('verification_acquisition')
    fitted=next(e['payload'] for e in events if e['kind']=='proposal_fit')
    assert fitted['generated_topology_sha256']==fitted['fitted_topology_sha256']
    assert 'test-discovery-secret' not in (path/'events.jsonl').read_text()
