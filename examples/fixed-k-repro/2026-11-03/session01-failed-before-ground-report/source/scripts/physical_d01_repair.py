#!/usr/bin/env python3
"""Reviewed schematic → bounded RC diagnosis → prospective manual repair checks.

Default run is a scripted mock with zero API/hardware calls. Physical mode
requires explicit execution, frozen sources, fresh operator confirmation and
remote prediction publication. A mock never establishes a physical repair.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time
import uuid

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from benchmate.agent import drive_agent
from benchmate.config import load_keys,redact
from benchmate.d01_repair import D01RepairSession,POLICY,PROMPT,TOOLS,reviewed_design
from benchmate.d01_repair_bench import PhysicalRepairBench,MockRepairBench,validate_initial
from benchmate.known_design import confirm_design
from benchmate.providers import MetaToolSession,ProviderError
from benchmate.records import Recorder,canonical,decode_events

VISION='examples/vision-spark/2026-10-31/20261031T060049-13a656638d/attempts/20261031T060050-8f3ccccdc9'
CALIBRATION='examples/b5-unloaded-protocol/2026-10-31-after-design-replay/protocol.json'
# Complete local import closure, verified by test; presentation is read-only and independent.
EXPERIMENT_MODULES=('__init__','agent','config','d01_repair','d01_repair_bench','engine','instrument',
    'known_design','measured_input','menu','physical_bench','physical_rc','physics','providers','recommendations','records')

def sha(raw):return hashlib.sha256(raw).hexdigest()
def save(path,value):path.write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
def source_hashes():
    paths=[ROOT/'src/benchmate'/(name+'.py') for name in EXPERIMENT_MODULES]+[Path(__file__)]
    return {str(p.relative_to(ROOT)):sha(p.read_bytes()) for p in paths}

def vision_design(path):
    path=Path(path);raw=(path/'events.jsonl').read_bytes();events=decode_events(raw);result=json.loads((path/'result.json').read_text())
    if (result.get('source_kind')!='intended_schematic' or result.get('status')!='unverified_visual_candidate'
        or events[-1]['kind']!='run_completed' or events[-1]['payload']!=result):raise ValueError('Completed intended-schematic record required')
    return result,sha(raw)

def prepare(output):
    out=Path(output);out.mkdir(parents=True,exist_ok=False)
    base=json.loads((ROOT/CALIBRATION).read_text())
    protocol={key:base[key] for key in ('configuration','voltage_conversion','guard_limits','USB_identity','calibration_provenance')}
    protocol.update(repair_policy=POLICY,source_sha256=source_hashes(),calibration_is_new=False,
        source_scope="Runner and complete local experiment import closure; read-only presentation files are excluded.")
    save(out/'protocol.json',protocol)
    candidate,digest=vision_design(ROOT/VISION)
    save(out/'design-to-review.json',{'schema':'benchmate.review_required.v1','source_record':VISION,
        'source_sha256':digest,'original_visual_result':candidate,'operator_confirmed':False,
        'instruction':'Review the intended schematic via known_design.py serve --demo and save its reviewed design. This file is not an operator confirmation.'})
    save(out/'api-plan.json',{'destination':'https://api.meta.ai/v1/responses','model':'muse-spark-1.3','effort':'medium',
        'requests_max':8,'max_output_tokens_per_request':4096,'max_payload_bytes':64000,'prompt':PROMPT,'tools':TOOLS,
        'transmitted':'Reviewed nominal R/C; newly acquired diagnostic tau/model score summaries; repair request; repair comparison summaries. Runtime explicitly identifies mock vs physical.',
        'excluded':['images','raw ADC arrays','operator assembly coordinates/truth','prior specimen results','local paths/files','API keys'],
        'automatic_retry':False,'nominal_tool_call_path':7,'authorization_status':'Not executed; physical API scope must be authorized for the actual run.'})
    save(out/'initial-report-template.json',{'fixture':'unloaded','USB_connected':False,'USB_off_wiring_confirmed':False,
        'nominal_design_confirmed':False,'reviewed_design_sha256':'REPLACE_WITH_CANONICAL_REVIEW_HASH','verbatim':'',
        'template_only':True})
    print(json.dumps({'prepared':str(out),'protocol_sha256':sha((out/'protocol.json').read_bytes()),'API_calls':0,'hardware_IO':False}))

class ScriptedController:
    """Software state-machine rehearsal, explicitly never attributed to Spark."""
    def __init__(self):self.state=None;self.calls=0
    def next_call(self):
        self.calls+=1
        if self.calls>8:raise ProviderError('Scripted call budget exhausted')
        s=self.state
        if s is None:name,args='inspect_experiment',{}
        elif s['diagnostic']['training'] is None:name,args='measure',{'action':'unloaded_step','reason':'SOFTWARE SCRIPT: measure tau.'}
        elif 'attach_output_load_step' in s['diagnostic']['allowed_measurements']:name,args='measure',{'action':'attach_output_load_step','reason':'SOFTWARE SCRIPT: distinguish loaded gains.'}
        elif s['diagnostic']['verification_available']:name,args='verify_prediction',{}
        elif s['repair_available']:name,args='request_repair',{'action':'restore_nominal_capacitance','reason':'SOFTWARE SCRIPT: restore reviewed C after verified C-change alternative.'}
        elif s['repair_verification_available']:name,args='verify_repair',{}
        else:name,args='finish_report',{'verdict':'repair_verified' if s['repair_verified'] else 'abstained',
            'current_explanation':'SOFTWARE REHEARSAL ONLY: '+('both conditional checks pass' if s['repair_verified'] else 'repair not verified'),
            'unresolved':'No real Spark decision or physical repair in a scripted mock.', 'next_observation':'Run the separately authorized physical protocol with a human operator.'}
        return {'call_id':'scripted-'+str(self.calls),'name':name,'arguments':json.dumps(args)}
    def submit_result(self,call_id,result):self.state=result
    def sanitize(self,value):return value
    def metadata(self):return {'provider':'scripted','http_requests':0,'Spark_authored':False,'scripted_tool_calls':self.calls}
    def close(self):pass

def publish(log,frozen,digest,remote):
    raw=canonical(frozen)+b'\n';(log.path/'predictions-frozen.json').write_bytes(raw)
    if sha(canonical(frozen))!=digest:raise ValueError('Freeze digest mismatch')
    if not remote:return {'sha256':digest,'published':True,'remote':False,'scope':'Local mock only'}
    def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT,text=True,stderr=subprocess.STDOUT).strip()
    if git('diff','--cached','--name-only') or git('branch','--show-current')!='main':raise ValueError('Clean index on main required')
    if git('remote','get-url','origin') not in ('https://github.com/bami-codes/BenchMate.git','https://github.com/bami-codes/BenchMate','git@github.com:bami-codes/BenchMate.git'):
        raise ValueError('Unexpected publication destination')
    text=raw.decode();keys=load_keys(ROOT/'.env')
    if redact(text,keys)!=text or any(x in text.lower() for x in ('bearer ','private key','model_api_key','baseten_api_key')):raise ValueError('Prediction secret scan failed')
    relative=Path('examples/d01-repair-freezes')/log.path.name/'predictions.json';target=ROOT/relative
    target.parent.mkdir(parents=True,exist_ok=False);target.write_bytes(raw)
    git('add','--',str(relative))
    if git('diff','--cached','--name-only')!=str(relative):raise ValueError('Unexpected staged file')
    git('diff','--cached','--check');git('commit','-m','Freeze D01 repair models and forecasts before operator intervention')
    commit=git('rev-parse','HEAD');git('push','origin','HEAD:main')
    if git('ls-remote','origin','refs/heads/main').split()[0]!=commit:raise ValueError('Remote receipt not verified')
    return {'sha256':digest,'published':True,'remote':True,'commit':commit,'path':str(relative),
        'url':f'https://github.com/bami-codes/BenchMate/blob/{commit}/{relative}'}

def operator_channel(log,action,digest,*,timeout_s=1800):
    if action=='attach_output_load':
        instruction='USB를 뽑고 LED가 꺼지면 큰 보드 E30–A55 OUT 부하 점퍼만 연결한다. A55–C35 IN 분기는 없어야 한다. 11번 B28–B35, 14번 B50–B23, D55–D60 9.99kΩ와 C23–A60 REF, 미니보드 원래 R·C 및 추가 C를 유지한다. 같은 USB 포트에 재연결 후 보고한다.'
    elif action=='restore_nominal_capacitance':
        instruction='예측의 원격 공개를 확인했다. USB를 뽑고 LED가 꺼지면 미니보드 I8–I13의 추가 커패시터만 양쪽 다리 모두 제거한다. 원래 D8–D13 C, B3–B8 R, E8–F8·E13–F13, 큰 보드 E30–A55 OUT 부하, D55–D60 9.99kΩ, C23–A60 REF, 11·14번 점퍼와 나머지 배선을 유지한다. IN 분기는 없어야 한다. 같은 USB 포트에 재연결 후 보고한다.'
    else:raise ValueError('Unknown operator action')
    request_id=uuid.uuid4().hex
    request={'request_id':request_id,'action':action,'fixture':'output_load','prediction_sha256':digest,
        'USB_off_required':True,'instruction':instruction,'response_file':'operator-response-'+request_id+'.json'}
    log.add('operator_action_requested',request);save(log.path/'operator-request.json',request)
    print(json.dumps({'stage':'awaiting_operator','request_file':str(log.path/'operator-request.json')},ensure_ascii=False),flush=True)
    path=log.path/request['response_file'];deadline=time.monotonic()+timeout_s
    while not path.exists():
        if time.monotonic()>deadline:raise ValueError('Operator timeout; no approval or acquisition')
        time.sleep(.5)
    response=json.loads(path.read_text())
    if response.get('request_id')!=request_id or response.get('action')!=action or response.get('cancelled') is True:
        raise ValueError('Unmatched or cancelled operator response')
    return response

def run(args):
    physical=args.bench=='physical'
    if physical and (not args.execute or args.provider!='meta' or not args.publish_freeze or not args.protocol
                     or not args.initial_report or not args.previous_boot_id or not args.reviewed_design or not args.vision_record or args.fault!='none'):
        raise ValueError('Physical execution needs Meta, explicit execute, publication, protocol, reviewed design/vision and fresh initial report/previous boot')
    if args.provider=='meta' and not args.execute:raise ValueError('Paid requests require --execute')
    if args.bench=='mock' and args.publish_freeze:raise ValueError('Mock predictions stay local; publish the completed rehearsal separately')
    base=json.loads((ROOT/CALIBRATION).read_text())
    protocol=json.loads(Path(args.protocol).read_text()) if args.protocol else base
    vision_path=Path(args.vision_record) if args.vision_record else ROOT/VISION
    original,vision_sha=vision_design(vision_path)
    if args.reviewed_design:design=json.loads(Path(args.reviewed_design).read_text())
    elif not physical:design=confirm_design(original,original['candidate'],reviewer_note='SOFTWARE REHEARSAL ONLY: simulated human review of intended schematic')
    else:raise ValueError('Human review missing')
    nominal,design_sha=reviewed_design(design)
    if design.get('model_original_candidate_sha256')!=sha(canonical(original['candidate'])):raise ValueError('Review does not match the supplied vision record')
    initial=json.loads(Path(args.initial_report).read_text()) if args.initial_report else None
    if physical:
        if protocol.get('repair_policy')!=POLICY or protocol.get('source_sha256')!=source_hashes():raise ValueError('Frozen policy/source mismatch; no provider or serial call')
        if initial.get('template_only') is True or 'SOFTWARE REHEARSAL' in design['reviewer_note']:raise ValueError('Mock/template is not an operator confirmation')
        validate_initial(initial,design_sha)
    log=Recorder(args.output,mode=f'{args.provider}_d01_repair_{args.bench}');model=bench=None
    save(log.path/'protocol.json',protocol);save(log.path/'reviewed-design.json',design)
    if initial:save(log.path/'initial-operator-report.json',initial)
    for name,digest in source_hashes().items():
        target=log.path/'source'/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes((ROOT/name).read_bytes())
    log.add('repair_run_protocol',{'source':args.bench,'provider':args.provider,'nominal_design':nominal,
        'reviewed_design_sha256':design_sha,'vision_record_sha256':vision_sha,'source_sha256':source_hashes(),
        'operator_review_simulated':not physical,'physical_repair_demonstrated':False,'source_is_new_observations':True})
    print(json.dumps({'stage':'started','record':str(log.path),'bench':args.bench,'provider':args.provider}),flush=True)
    try:
        if physical:bench=PhysicalRepairBench(protocol,log,lambda action,digest:operator_channel(log,action,digest),
            initial_report=initial,previous_boot_id=args.previous_boot_id,design_sha=design_sha)
        else:bench=MockRepairBench(protocol,log,fault=args.fault)
        def publication(f,d):
            if args.fault=='publication_failure':raise ValueError('Injected mock publication failure')
            return publish(log,f,d,args.publish_freeze)
        session=D01RepairSession(bench,log,design,publication,actor='muse_spark' if args.provider=='meta' else 'scripted_controller')
        model=MetaToolSession(prompt=PROMPT,tools=TOOLS,log=log,effort='medium',env_path=ROOT/'.env',
            budget_path=ROOT/'.private/api-budget.json',max_requests=8) if args.provider=='meta' else ScriptedController()
        result={**drive_agent(session,model),**model.metadata()};result=model.sanitize(result)
        save(log.path/'result.json',result);log.add('run_completed',result)
        print(json.dumps({'stage':'completed','record':str(log.path),'repair_verified':result['repair_verified'],
            'source':args.bench,'http_requests':result['http_requests'],'instrument':bench.metadata()}),flush=True)
    except (Exception,KeyboardInterrupt) as exc:
        result={'source':args.bench,'error':str(exc) if isinstance(exc,(ValueError,ProviderError)) else type(exc).__name__,
            'repair_verified':False,'automatic_retry':False,'instrument':bench.metadata() if bench else None}
        if model:result=model.sanitize({**result,**model.metadata()})
        save(log.path/'result.json',result);log.add('run_failed',result)
        print(json.dumps({'stage':'failed','record':str(log.path),**result}),flush=True);raise SystemExit(1)
    finally:
        if model:model.close()

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);sub=parser.add_subparsers(dest='command',required=True)
    p=sub.add_parser('prepare');p.add_argument('--output',required=True)
    p=sub.add_parser('run');p.add_argument('--bench',choices=['mock','physical'],default='mock')
    p.add_argument('--provider',choices=['scripted','meta'],default='scripted');p.add_argument('--execute',action='store_true')
    for name in ('protocol','initial-report','previous-boot-id','reviewed-design','vision-record'):p.add_argument('--'+name)
    p.add_argument('--publish-freeze',action='store_true');p.add_argument('--output',default=str(ROOT/'runs/d01-repair'))
    p.add_argument('--fault',choices=['none','repair_failed','reserved_failure','publication_failure','stale_boot',
        'missing_confirmation','wrong_confirmation','cancelled','timeout','reset_during_reserved'],default='none')
    args=parser.parse_args()
    if args.command=='prepare':prepare(args.output)
    else:run(args)
