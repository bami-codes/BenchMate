"""Repair control, prospective evidence and fake serial; no API or USB access."""
from copy import deepcopy
import hashlib
import importlib.util
import json
import math
from pathlib import Path
from types import SimpleNamespace
import numpy as np
import pytest
from benchmate.agent import ToolRejected,drive_agent
from benchmate.d01_repair import D01RepairSession,POLICY,REPAIR_SINE,command_template,reviewed_design
from benchmate.d01_repair_bench import MockRepairBench,PhysicalRepairBench,validate_initial,validate_repair_report
from benchmate.known_design import confirm_design
from benchmate.physical_rc import STEP,SINE
from benchmate.records import canonical
from test_physical_rc import Log
from test_physical_bench import FakeBoard,make_bench,protocol

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('repair_runner',ROOT/'scripts/physical_d01_repair.py')
runner=importlib.util.module_from_spec(spec);spec.loader.exec_module(runner)

@pytest.fixture
def design():
    original,_=runner.vision_design(ROOT/runner.VISION)
    return confirm_design(original,original['candidate'],reviewer_note='SOFTWARE REHEARSAL ONLY: test review')

def fixture(protocol,design,fault='none'):
    log=Log();bench=MockRepairBench(protocol,log,fault=fault)
    def publish(f,d):
        if fault=='publication_failure':raise ValueError('Injected publication failure')
        assert hashlib.sha256(canonical(f)).hexdigest()==d
        assert bench.count==3 and not bench.repaired
        return {'sha256':d,'published':True,'remote':False}
    session=D01RepairSession(bench,log,design,publish,actor='scripted_controller')
    return session,bench,log

def diagnose(session):
    session.dispatch('inspect_experiment',{})
    for action in ['unloaded_step','attach_output_load_step']:
        session.dispatch('measure',{'action':action,'reason':'software test'})
    session.dispatch('verify_prediction',{})

def repair(session):
    session.dispatch('request_repair',{'action':'restore_nominal_capacitance','reason':'software test'})

def test_full_mock_preserves_order_provenance_models_and_bounded_context(protocol,design):
    s,b,log=fixture(protocol,design);model=runner.ScriptedController();states=[]
    submit=model.submit_result
    def capture(call,result):states.append(deepcopy(result));submit(call,result)
    model.submit_result=capture
    result=drive_agent(s,model)
    assert result['repair_verified'] and model.calls==7 and b.count==5
    assert not result['llm_used'] and result['source']=='mock'
    assert not result['agent_report']['physical_repair_demonstrated']
    assert s.frozen['post_repair_scored_OUT_used']==0
    names=[k for k,v in log.events]
    frozen=names.index('repair_prediction_frozen');published=names.index('repair_prediction_publication')
    requested=next(i for i,(k,v) in enumerate(log.events) if k=='operator_action_requested' and v['action']=='restore_nominal_capacitance')
    observed=next(i for i,(k,v) in enumerate(log.events) if k=='mock_rc_observation' and v['phase']=='repair_step')
    assert frozen<published<requested<observed
    assert s.frozen['point_models']['restored_nominal']=={'R_ohm':10000.,'C_f':1e-6}
    assert s.frozen['point_models']['unchanged']==s.diagnostic.models['c_changed']
    assert s.checks[1]['settings']==REPAIR_SINE and REPAIR_SINE!=SINE
    assert all(x['conditional']['restored_nominal']['passed'] for x in s.checks)
    serialized=json.dumps(states)
    for secret in ['predicted_output_v','input_v','output_v','I8','D8','additional_capacitor','serial_command']:
        assert secret not in serialized
    assert len(serialized.encode())+len(json.dumps(runner.TOOLS).encode())+len(runner.PROMPT.encode())<64000

@pytest.mark.parametrize('fault',['repair_failed','reserved_failure'])
def test_failed_repair_abstains_without_refit_or_retry(protocol,design,fault):
    s,b,log=fixture(protocol,design,fault);result=drive_agent(s,runner.ScriptedController())
    assert not result['repair_verified'] and result['agent_report']['verdict']=='abstained'
    assert b.count==5 and s.frozen['point_models']['unchanged']==s.diagnostic.models['c_changed']
    with pytest.raises(ToolRejected):s.dispatch('verify_repair',{})

@pytest.mark.parametrize('fault,count,repaired',[
    ('publication_failure',3,False),('missing_confirmation',3,False),('wrong_confirmation',3,False),
    ('cancelled',3,False),('timeout',3,False),('stale_boot',4,True),('reset_during_reserved',5,True)])
def test_external_fault_is_terminal(protocol,design,fault,count,repaired):
    s,b,log=fixture(protocol,design,fault)
    with pytest.raises(ValueError):drive_agent(s,runner.ScriptedController())
    assert s.fatal and not s.repair_verified and b.count==count and b.repaired==repaired
    if fault=='publication_failure':assert not any(k=='repair_operator_confirmation' for k,v in log.events)
    with pytest.raises(ToolRejected):s.dispatch('verify_repair',{})
    assert b.count==count

def test_no_repair_before_verified_c_diagnosis_or_for_r_change(protocol,design):
    s,b,log=fixture(protocol,design);s.dispatch('inspect_experiment',{})
    with pytest.raises(ToolRejected):repair(s)
    b.resistance=20000.;b.capacitance=1e-6;diagnose(s)
    assert s.diagnostic.supported==['r_changed'] and s.diagnostic.verified
    with pytest.raises(ToolRejected):repair(s)
    assert not b.repaired

def test_no_refit_after_repair_requested_and_no_forged_success(protocol,design):
    s,b,log=fixture(protocol,design);diagnose(s);repair(s)
    with pytest.raises(ToolRejected):s.dispatch('measure',{'action':'repeat_unloaded_step','reason':'refit'})
    with pytest.raises(ToolRejected):s.dispatch('finish_report',{'verdict':'repair_verified','current_explanation':'x','unresolved':'x','next_observation':'x'})

@pytest.mark.parametrize('field,value',[('schema','unreviewed'),('source','assembly_photo'),('measurement_verified',True),
    ('hardware_IO',True),('reviewer_note',''),('nominal_design',{'R_ohm':20000.,'C_f':1e-6,'tau_s':.02})])
def test_unreviewed_or_unsupported_design_rejected(design,field,value):
    design[field]=value
    with pytest.raises(ValueError):reviewed_design(design)

def test_repair_confirmation_requires_exact_fields():
    report={'action':'restore_nominal_capacitance','fixture':'output_load','prediction_sha256':'d'*64,
        'USB_connected':True,'USB_off_wiring_confirmed':True,'additional_capacitor_removed':True,
        'original_capacitor_and_load_retained':True,'remaining_wiring_unchanged':True,'verbatim':'test only'}
    validate_repair_report(report,'d'*64)
    for field in report:
        altered=deepcopy(report);del altered[field]
        with pytest.raises(ValueError):validate_repair_report(altered,'d'*64)
    with pytest.raises(ValueError):validate_repair_report(report,'e'*64)

class RepairBoard(FakeBoard):
    """Independent analytical waveform encoded through the real JSON byte protocol."""
    def __init__(self,p):super().__init__(p);self.capacitance=2e-6
    def write(self,command):
        count=super().write(command);w=command.decode().split()
        if w[0]!='CAPTURE' or w[2]=='HOLD':return count
        p=json.loads(self.response);n=int(w[3]);dt=int(w[4])*1e-6;amp=int(w[5]);freq=int(w[6])/1000
        t=np.arange(n)*dt;g=9990/19990 if self.loaded else 1.;tau=10000*self.capacitance*g
        if w[2]=='STEP':
            codes=np.where(np.arange(n)<n//10,-amp,amp);u=codes*self.cfg.vref_v/4095
            rel=t+105e-6-(n//10)*dt;amplitude=amp*self.cfg.vref_v/4095
            y=np.where(rel<0,-amplitude*g,amplitude*g-2*amplitude*g*np.exp(-np.maximum(rel,0)/tau))
        else:
            warmup=math.ceil(max(self.cfg.settle_ms*.001,2/freq)/dt)
            phase=2*np.pi*freq*(np.arange(n)+warmup)*dt;raw=amp*np.sin(phase)
            codes=np.where(raw>=0,np.floor(raw+.5),np.ceil(raw-.5));u=codes*self.cfg.vref_v/4095
            # Independent periodic steady state with quantized command samples.
            a=math.exp(-dt/tau);ad=math.exp(-105e-6/tau);cycle=round(1/(freq*dt));state=0.
            for x in np.tile(u[:cycle],40):state=a*state+(1-a)*g*x
            y=[]
            for x in u:y.append(ad*state+(1-ad)*g*x);state=a*state+(1-a)*g*x
            y=np.asarray(y)
        maps=self.p['voltage_conversion']['channels']
        for i,row in enumerate(p['rows']):
            row[1]=int(self.cfg.ref_code+codes[i])
            for j,ch,v in [(2,'A1',1.63+u[i]),(3,'A2',1.64+y[i]),(4,'A3',1.63+u[i])]:
                row[j]=round((v-maps[ch]['offset_v'])/maps[ch]['gain_v_per_count'])
        self.response=(json.dumps(p)+'\n').encode();return count

def physical_fixture(protocol,design,fault=None):
    log=Log();board=RepairBoard(protocol);digest=reviewed_design(design)[1]
    initial={'fixture':'unloaded','USB_connected':True,'USB_off_wiring_confirmed':True,
        'nominal_design_confirmed':True,'reviewed_design_sha256':digest,'verbatim':'TEST ONLY OPERATOR_TRUTH_HIDDEN'}
    def confirm(action,prediction):
        if action=='restore_nominal_capacitance' and fault=='missing_confirmation':return {'action':action}
        board.armed=False;board.code=0;board.loaded=True;board.uptime=0
        board.boot=('d' if action=='attach_output_load' or fault=='stale_boot' else 'e')*32
        if action=='restore_nominal_capacitance':board.capacitance=1e-6
        return {**initial,'fixture':'output_load','action':action,'prediction_sha256':prediction,
            'additional_capacitor_removed':True,'original_capacitor_and_load_retained':True,'remaining_wiring_unchanged':True}
    bench=PhysicalRepairBench(protocol,log,confirm,initial_report=initial,previous_boot_id='a'*32,design_sha=digest,
        serial_factory=board.factory,ports=lambda:[SimpleNamespace(vid=9025,pid=105,serial_number=protocol['USB_identity'][2],device='FAKE_NOT_A_DEVICE')],sleep=lambda _:None)
    s=D01RepairSession(bench,log,design,lambda f,d:{'sha256':d,'published':True,'remote':True,'scope':'TEST FAKE RECEIPT'},actor='scripted_controller')
    return s,bench,board,log

def test_fake_serial_runs_five_waveforms_and_three_explicit_boots(protocol,design):
    s,b,board,log=physical_fixture(protocol,design);model=runner.ScriptedController();states=[]
    original=model.submit_result
    model.submit_result=lambda call,r:(states.append(deepcopy(r)),original(call,r))
    drive_agent(s,model)
    assert s.repair_verified and b.metadata()['retained_frames']==12800
    assert b.metadata()['capture_attempts']==25 and b.metadata()['human_interventions_completed']==2
    assert sum(c[0]=='ARM' for c in board.commands)==3 and board.opens==5
    assert 'OPERATOR_TRUTH_HIDDEN' not in json.dumps(states)
    obs=[v for k,v in log.events if k=='physical_observation']
    assert [o['boot_id'] for o in obs]==['b'*32,'d'*32,'d'*32,'e'*32,'e'*32]
    assert obs[-1]['settings']==REPAIR_SINE

@pytest.mark.parametrize('fault,opens,arms',[('missing_confirmation',3,2),('stale_boot',4,2)])
def test_fake_serial_refuses_missing_confirmation_or_old_boot(protocol,design,fault,opens,arms):
    s,b,board,log=physical_fixture(protocol,design,fault)
    with pytest.raises(ValueError):drive_agent(s,runner.ScriptedController())
    assert not s.repair_verified and board.opens==opens and sum(c[0]=='ARM' for c in board.commands)==arms
    assert b.metadata()['retained_frames']==7680

def test_default_adapter_does_not_enable_new_waveform(protocol):
    bench,board,log=make_bench(protocol)
    with pytest.raises(ValueError):bench.acquire(REPAIR_SINE,{},'output_load','repair_reserved_sine')
    assert board.opens==0

def test_real_operator_channel_rejects_wrong_request_and_timeout(tmp_path,monkeypatch):
    log=Log();log.path=tmp_path
    class FixedID:hex='1'*32
    monkeypatch.setattr(runner.uuid,'uuid4',lambda:FixedID())
    response=tmp_path/('operator-response-'+'1'*32+'.json')
    response.write_text(json.dumps({'request_id':'wrong','action':'restore_nominal_capacitance'}))
    with pytest.raises(ValueError,match='Unmatched'):runner.operator_channel(log,'restore_nominal_capacitance','d'*64)
    response.unlink()
    with pytest.raises(ValueError,match='timeout'):runner.operator_channel(log,'restore_nominal_capacitance','d'*64,timeout_s=-1)

def test_physical_cli_missing_review_cannot_construct_provider_or_bench(monkeypatch):
    def forbidden(*a,**k):pytest.fail('Live provider/port must not be constructed')
    monkeypatch.setattr(runner,'MetaToolSession',forbidden);monkeypatch.setattr(runner,'PhysicalRepairBench',forbidden)
    args=SimpleNamespace(bench='physical',execute=True,provider='meta',publish_freeze=True,protocol='frozen.json',
        initial_report='fresh.json',previous_boot_id='a'*32,reviewed_design=None,vision_record=None,fault='none')
    with pytest.raises(ValueError,match='Physical execution needs'):runner.run(args)


def test_source_freeze_covers_all_runtime_imports_but_not_presentation():
    import ast
    seen=set();queue=[]
    def imports(path):
        dependencies=[]
        for node in ast.walk(ast.parse(path.read_text())):
            if isinstance(node,ast.ImportFrom):
                if node.level==1:dependencies.extend([node.module.split('.')[0]] if node.module else [a.name for a in node.names])
                elif node.module and node.module.startswith('benchmate.'):dependencies.append(node.module.split('.')[1])
            elif isinstance(node,ast.Import):dependencies.extend(a.name.split('.')[1] for a in node.names if a.name.startswith('benchmate.'))
        return dependencies
    queue=imports(ROOT/'scripts/physical_d01_repair.py')
    while queue:
        name=queue.pop()
        if name in seen:continue
        seen.add(name);queue.extend(imports(ROOT/'src/benchmate'/(name+'.py')))
    assert seen|{'__init__'}==set(runner.EXPERIMENT_MODULES)
    frozen=runner.source_hashes()
    assert len(frozen)==len(seen)+2
    assert 'src/benchmate/viewer.py' not in frozen and 'src/benchmate/physical_bench.py' in frozen

def test_vision_record_read_is_independent_of_unrelated_display_sidecar(tmp_path):
    import shutil
    source=ROOT/runner.VISION;run=tmp_path/'vision';run.mkdir()
    for name in ['events.jsonl','result.json']:shutil.copyfile(source/name,run/name)
    (run/'translations.json').write_text('invalid presentation-only draft')
    actual,digest=runner.vision_design(run)
    assert actual==json.loads((source/'result.json').read_text())
    assert digest==hashlib.sha256((source/'events.jsonl').read_bytes()).hexdigest()
    data=json.loads((run/'result.json').read_text());data['candidate']['summary']='tampered'
    (run/'result.json').write_text(json.dumps(data))
    with pytest.raises(ValueError):runner.vision_design(run)
