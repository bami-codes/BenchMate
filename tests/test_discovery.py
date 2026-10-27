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
from benchmate.discovery import run_discovery,fit_proposal,TRAINING,VERIFICATION,DISCOVERY_PROMPT
from benchmate.stimulus import command_template
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


@pytest.mark.parametrize('version',[42,None,47])
def test_simulator_rejects_unsupported_or_unknown_version(monkeypatch,version):
    import subprocess
    from benchmate.netlist import ngspice_version
    executable=f'/test/ngspice-{version}'
    output=f'** ngspice-{version} : Circuit level simulation program' if version else 'unknown simulator'
    monkeypatch.setattr(subprocess,'run',lambda *a,**kw:subprocess.CompletedProcess(a,0,output,''))
    if version==47:assert ngspice_version(executable)==47
    else:
        with pytest.raises(RuntimeError,match='ngspice 47'):ngspice_version(executable)
    ngspice_version.cache_clear()


@pytest.mark.skipif(shutil.which('ngspice') is None,reason='ngspice not installed')
def test_generated_topology_is_executed_and_wrong_direction_fails():
    observation=acquire_nonlinear(Acquisition(kind='sine',frequency_hz=1,amplitude_v=1,duration_s=2,sample_period_s=.002),rng=np.random.default_rng(3),noise_sd_v=0)
    p=proposal();predicted,_=simulate_netlist(p,observation)
    assert not adequacy(predicted,observation)['passed']  # Deliberate library mismatch.
    matched,_=simulate_netlist(p,observation,diode={'is_a':3e-9,'n':1.9})
    assert adequacy(matched,observation)['passed']
    # Check the harness independently of parameter fitting: close PWL edges
    # must not silently turn into a different stimulus on non-XSPICE builds.
    np.testing.assert_allclose(matched['in_v'],observation['data']['drive_v'],atol=1e-6,rtol=0)
    np.testing.assert_allclose(matched['out_v'],observation['data']['out_v'],atol=1e-6,rtol=0)
    p[1]['a'],p[1]['b']=p[1]['b'],p[1]['a']
    wrong,_=simulate_netlist(p,observation)
    assert not adequacy(wrong,observation)['passed']


@pytest.mark.parametrize('parameters',[{'is_a':0,'n':1.8},{'is_a':3e-9,'n':9},
                                      {'is_a':float('nan'),'n':1.8},
                                      {'is_a':3e-9,'n':1.9,'directive':'.include secret'}])
def test_diode_parameters_cannot_escape_numeric_library(parameters):
    from benchmate.netlist import diode_parameters
    with pytest.raises(ValueError):diode_parameters(parameters)


def test_discovery_prompt_is_neutral_and_command_template_has_no_answer():
    assert 'nonlinear' not in DISCOVERY_PROMPT.lower()
    assert 'two amplitudes' not in DISCOVERY_PROMPT.lower()
    for settings in VERIFICATION:
        template=command_template(settings)
        assert set(template['data'])=={'time_s','drive_v','ref_v'}
        assert 'out_v' not in template['data'] and 'in_v' not in template['data']
    assert all(a.to_dict()!=b.to_dict() for a in TRAINING for b in VERIFICATION)
    assert any(a.load_ohm==4700 for a in TRAINING)
    assert not any(a.load_ohm==10000 for a in TRAINING)


@pytest.mark.skipif(shutil.which('ngspice') is None,reason='ngspice not installed')
def test_fit_separates_resistance_and_mismatched_diode_without_verification_data():
    observations=[acquire_nonlinear(s,rng=np.random.default_rng(4),noise_sd_v=0,r_ohm=12000)
                  for s in TRAINING]
    fitted,result=fit_proposal(proposal(),observations)
    assert result['training_passed'] and result['parameters_identifiable']
    assert fitted[0]['value']==pytest.approx(12000,rel=.015)
    assert result['diode_parameters']['is_a']==pytest.approx(3e-9,rel=.06)
    assert result['diode_parameters']['n']==pytest.approx(1.9,rel=.01)
    frozen=copy.deepcopy((fitted,result['diode_parameters']))
    for settings in VERIFICATION:
        pred,_=simulate_netlist(fitted,command_template(settings),diode=result['diode_parameters'])
        unseen=acquire_nonlinear(settings,rng=np.random.default_rng(8),r_ohm=12000)
        assert adequacy(pred,unseen)['passed']
    assert frozen==(fitted,result['diode_parameters'])


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
    assert fitted['diode_parameters']['is_a']!=1e-9
    assert result['total_physical_acquisitions']==6
    predictions=[e['payload'] for e in events if e['kind']=='prediction_committed']
    assert all(p['diode_parameters']==fitted['diode_parameters'] for p in predictions)
    assert all(p['input_provenance'].startswith('ideal_command') for p in predictions)
    assert 'test-discovery-secret' not in (path/'events.jsonl').read_text()
