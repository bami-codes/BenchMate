"""Additive restored-only follow-up. Original terminal failure is never reopened."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys

from .records import Recorder, canonical, decode_events
from .reading_rules import digest
from .reading_recovery import original_sources, check_publication, save
from .reading_verify import chain, check_file, verify_run as verify_original
from . import verify as legacy

ROOT = Path(__file__).resolve().parents[2]
PUBLIC = Path('examples/reading-followup/2026-11-03')
NOTE = 'docs/2026-11-03-reading-restored-followup.md'
IMAGE_BUDGET = ROOT/'.private/reading-cohort-api-budget.json'
ACTIVE_STAGE = False


def runtime():
    sys.path.insert(0,str(ROOT))
    from scripts import reading_experiment
    return reading_experiment


def sha(file):
    return hashlib.sha256(Path(file).read_bytes()).hexdigest()


def qa_checked(path):
    events = chain(Path(path)/'events.jsonl'); result = events[-1]['payload']
    plan = json.loads((Path(path)/'plan.json').read_text())
    guards = [e['payload'] for e in events if e['kind']=='physical_electrical_guard']
    commands = [e['payload']['request'] for e in events if e['kind']=='serial_command']
    captures = [c for c in commands if c.startswith('CAPTURE ')]
    if (events[-1]['kind']!='run_completed' or result.get('passed') is not True
            or result.get('frames')!=1536 or result.get('blocks')!=3
            or len(guards)!=3 or not all(all(g['checks'].values()) for g in guards)
            or not all(g['primary_REF_channel']=='A3' for g in guards)
            or len(captures)!=3 or any(c.split()[2]!='HOLD' for c in captures)
            or sum(c.startswith('ARM ') for c in commands)!=1):
        raise ValueError('One complete passing three-HOLD QA required.')
    return events, result, plan


def bind(log, file, kind):
    file = Path(file).resolve(); events = chain(file)
    log.add('followup_record_bound', {'file':str(file.relative_to(log.path.resolve())),
        'sha256':sha(file),'head_sha256':events[-1]['sha256'],'record_kind':kind})


def stage(log, phase, **data):
    log.control = {**getattr(log,'control',{}),**data,'phase':phase}
    log.add('followup_state',log.control);save(log.path/'state.json',log.control)
    print(json.dumps({'record':str(log.path),'phase':phase}),flush=True)


def open_record(path, phases):
    path=Path(path).resolve(); events=decode_events((path/'events.jsonl').read_bytes(),require_terminal=False,include_hash=True)
    if events[-1]['kind'] in ('run_completed','run_failed'):
        raise ValueError('Terminal follow-up; no retry.')
    control=next(e['payload'] for e in reversed(events) if e['kind']=='followup_state')
    if control['phase'] not in phases:raise ValueError('Wrong follow-up stage: '+control['phase'])
    reg=json.loads((path/'registration.json').read_text())
    original_sources()
    for name,h in reg['source_sha256'].items():
        if sha(ROOT/name)!=h:raise ValueError('Frozen follow-up source changed: '+name)
    log=Recorder.__new__(Recorder);log.path=path;log.file=path/'events.jsonl'
    log.previous=events[-1]['sha256'];log.sequence=len(events);log.control=control
    return log,reg


def prepare(args):
    old=Path(args.failed_pair).resolve(); audited=verify_original(old)
    if not audited['passed'] or audited['run_status']!='run_failed':raise ValueError('Verified terminal failed pair required.')
    qa_events,qa,qa_plan=qa_checked(args.QA_record)
    if qa_plan['failed_pair_head_sha256']!=audited['head_sha256']:raise ValueError('QA belongs to another failed attempt.')
    sources=original_sources().copy()
    for n in ('src/benchmate/reading_recovery.py','src/benchmate/reading_followup.py',
              'docs/2026-11-03-reading-recovery-protocol.md',NOTE):sources[n]=sha(ROOT/n)
    log=Recorder(ROOT/'runs/reading-followup',mode='restored_only_counted_followup_not_replacement')
    shutil.copytree(old,log.path/'history/original',ignore=shutil.ignore_patterns('*-local-only.json'))
    shutil.copytree(args.QA_record,log.path/'history/recovery-QA')
    d=json.loads((old/'reviewed-design.json').read_text());p=json.loads((old/'prepared/protocol.json').read_text())
    if qa_plan['protocol']!=p:raise ValueError('Recovery changed the measurement protocol.')
    for n,h in qa_plan['source_sha256'].items():
        if sha(ROOT/n)!=h:raise ValueError('Recovery source changed before follow-up: '+n)
    save(log.path/'reviewed-design.json',d);save(log.path/'protocol.json',p)
    shutil.copyfile(old/'schematic.png',log.path/'schematic.png')
    public=PUBLIC/'registrations'/(log.path.name+'.json')
    reg={'schema':'benchmate.restored_followup.v1','cohort':'reading-assisted-v1',
        'run_id':log.path.name,'case_id':'01','state':'restored','attempt_ordinal':2,
        'followup_of':old.name,'original_head_sha256':audited['head_sha256'],
        'original_primary_status':'failed','original_selection_unchanged':True,
        'counted':True,'selected_first_attempt':False,'source':'physical','blind_test':False,
        'QA_head_sha256':qa_events[-1]['sha256'],'QA_boot_id':qa['boot_id'],
        'source_sha256':sources,'protocol_sha256':digest(p),'reviewed_design_sha256':digest(d),
        'public_registration':str(public),'diagnostic_Spark_requests_max':8,
        'photo_SAM_requests_max':1,'photo_binding_Spark_requests_max':1,
        'requested_photo_component':'R1','prior_data_supplied_to_diagnostic_model':False}
    save(log.path/'registration.json',reg);save(ROOT/public,reg)
    for name in sources:
        target=ROOT/PUBLIC/'freezes'/log.path.name/'source'/name
        target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes((ROOT/name).read_bytes())
    log.add('restored_followup_registered',reg)
    bind(log,log.path/'history/original/events.jsonl','original_failed_pair')
    bind(log,log.path/'history/recovery-QA/events.jsonl','recovery_QA')
    stage(log,'awaiting_restored_setup')


def execute_gate(log, reg, name, execute):
    global ACTIVE_STAGE
    if not execute:raise ValueError('Explicit authorized --execute required.')
    check_publication(ROOT/reg['public_registration'])
    with (log.path/(name+'-started.json')).open('x') as f:json.dump({'one_attempt':True},f)
    ACTIVE_STAGE = True


def run_diagnosis(args):
    log,reg=open_record(args.record,['awaiting_restored_setup']);execute_gate(log,reg,'diagnosis',args.execute)
    old=runtime();p=json.loads((log.path/'protocol.json').read_text());d=json.loads((log.path/'reviewed-design.json').read_text())
    initial=json.loads(Path(args.initial_report).read_text());assembly=json.loads(Path(args.assembly_record).read_text())
    old.preserved.base.validate_assembly(d,initial,assembly)
    preflight=chain(Path(args.preflight_run)/'events.jsonl');pong=preflight[-1]['payload']
    if (preflight[-1]['kind']!='run_completed' or pong.get('armed') is not False
            or pong.get('commands')!=['PING'] or pong.get('stimuli')!=0 or pong['boot_id']==reg['QA_boot_id']):
        raise ValueError('Fresh unarmed post-QA preflight required.')
    shutil.copytree(args.preflight_run,log.path/'preflight');bind(log,log.path/'preflight/events.jsonl','preflight')
    save(log.path/'assembly-local-only.json',assembly)
    log.add('followup_assembly_sealed',{'sha256':digest(assembly),'transmitted_to_model':False})
    model=None
    try:
        from serial.tools import list_ports
        ports=[x for x in list_ports.comports() if (x.vid,x.pid,x.serial_number)==tuple(p['USB_identity'])]
        if len(ports)!=1:raise ValueError('Expected Minima absent or ambiguous; no serial opened.')
        bench=old.preserved.SettledBench(p,log,lambda f:old.preserved.base.intervention(log,d,f),
            design=d,initial_report=initial,approved=True,previous_boot_id=reg['QA_boot_id'],preflight_boot_id=pong['boot_id'])
        def publish(frozen,expected):
            open_record(log.path,['awaiting_restored_setup'])
            if digest(frozen)!=expected:raise ValueError('Follow-up prediction hash mismatch.')
            save(log.path/'predictions-frozen.json',frozen)
            return old.publish(log,frozen,'restored-followup')
        session=old.preserved.Session(bench,log,d,publish)
        model=old.preserved.OfficialModel(prompt=old.preserved.PROMPT,tools=session.tools,log=log,
            effort='medium',env_path=ROOT/'.env',budget_path=old.MODEL_BUDGET,max_requests=8)
        result=model.sanitize({**old.preserved.base.drive_agent(session,model),**model.metadata()})
        save(log.path/'diagnostic-result.json',result)
        log.add('restored_followup_diagnosis_completed',{'agent_report':result['agent_report'],
            'http_requests':result['http_requests'],'boot_id':bench.boot_id,'output_at_REF_confirmed':True,
            'artifact':{'file':'diagnostic-result.json','sha256':sha(log.path/'diagnostic-result.json')}})
        stage(log,'awaiting_restored_photo',restored_verdict=result['agent_report']['verdict'],last_boot=bench.boot_id)
    except (Exception,KeyboardInterrupt) as exc:
        events=decode_events(log.file.read_bytes(),require_terminal=False)
        firmware=next((e['payload'].get('message') for e in reversed(events)
                       if isinstance(e['payload'],dict) and e['payload'].get('type')=='error'),None)
        result={'error':str(exc) if isinstance(exc,(ValueError,RuntimeError)) else type(exc).__name__,
            'firmware_error':firmware,'automatic_retry':False,**(model.metadata() if model else {})}
        save(log.path/'failure.json',result);log.add('run_failed',result);raise
    finally:
        if model:model.close()


def photo(args):
    from . import reading_photo
    log,reg=open_record(args.record,['awaiting_restored_photo'])
    if not args.new_capture_confirmed:raise ValueError('Actual new restored-state photograph required.')
    p=reading_photo.prepare(args.image,log.path/'photo-restored/prepared',reg['source_sha256'],digest(reg))
    if p['input']['sha256']==json.loads((log.path/'history/original/photo-faulted/prepared/plan.json').read_text())['input']['sha256']:
        raise ValueError('Do not reuse the fault photograph.')
    log.add('followup_photo_received',{'artifacts':[{'file':'photo-restored/prepared/'+n,'sha256':sha(log.path/'photo-restored/prepared'/n)} for n in ('input.png','clean-full.png','plan.json')]})
    stage(log,'awaiting_segmentation')


def segment(args):
    from . import reading_photo
    log,reg=open_record(args.record,['awaiting_segmentation']);execute_gate(log,reg,'SAM',args.execute)
    p=log.path/'photo-restored/prepared';reading_photo.segment(p,IMAGE_BUDGET)
    attempt=json.loads((p/'sam-outcomes.json').read_text())[0];bind(log,p/attempt['run']/'events.jsonl','SAM')
    stage(log,'awaiting_decode')


def decode(args):
    from . import reading_photo
    log,reg=open_record(args.record,['awaiting_decode']);p=log.path/'photo-restored'
    m=reading_photo.decode(p/'prepared',p/'decoded')
    log.add('followup_bodies_decoded',{'bodies':[x['id'] for x in m['components']],
        'artifacts':[{'file':str(f.relative_to(log.path)),'sha256':sha(f)} for f in sorted((p/'decoded').rglob('*')) if f.is_file()]})
    stage(log,'awaiting_binding')


def body(args):
    from . import reading_photo
    log,reg=open_record(args.record,['awaiting_binding']);execute_gate(log,reg,'binding',args.execute)
    run,p=reading_photo.binding_request(log.path/'photo-restored/decoded',log.path/'schematic.png',
        reg['requested_photo_component'],IMAGE_BUDGET,log.path/'photo-restored/binding')
    bind(log,run/'events.jsonl','body_binding');log.add('body_binding_proposed',p)
    save(log.path/'body-binding-proposal.json',p);stage(log,'awaiting_body_confirmation')
    print(json.dumps(p),flush=True)


def confirm(args):
    log,reg=open_record(args.record,['awaiting_body_confirmation'])
    p=json.loads((log.path/'body-binding-proposal.json').read_text())
    if args.accept and p['sam_body'] is not None and not args.operator_body:
        p.update(operator_confirmed=True)
    elif not args.accept and args.operator_body:
        m=json.loads((log.path/'photo-restored/decoded/body-manifest.json').read_text())
        target=next((c for c in m['components'] if c['id']==args.operator_body),None)
        if target is None:raise ValueError('Choose an existing body; never invent a SAM mask.')
        p.update(sam_body=target['id'],chosen_by='operator',operator_confirmed=True,localizer=target['localizer'],
                 reason='Operator assigned after rejecting or receiving no Spark correspondence.')
    else:raise ValueError('Actual acceptance or explicit operator assignment required.')
    log.add('body_binding',p);save(log.path/'body-binding.json',p)
    diagnostic=json.loads((log.path/'diagnostic-result.json').read_text());verdict=diagnostic['agent_report']['verdict']
    result={'schema':'benchmate.completed_case_with_restored_followup.v1','source':'physical',
        'original_pair':reg['followup_of'],'original_pair_status':'failed','original_failure_counted':True,
        'restored_followup_counted':True,'original_first_selection_unchanged':True,'blind_test':False,
        'restored_verdict':verdict,'operator_restored_and_rerun_consistent':verdict=='consistent',
        'display_caption':'No mismatch in the tests Spark chose' if verdict=='consistent' else None,
        'native_diagnostic_repair_claim_overwritten':False,'fault_and_reading_evidence':'history/original',
        'restored_photo_and_correspondence_recorded':True}
    save(log.path/'result.json',result);log.add('run_completed',result)
    print(json.dumps({'record':str(log.path),**result}),flush=True)


def verify(path,expected_head=None):
    path=Path(path);events=chain(path/'events.jsonl',expected_head);base=legacy.verify_run(path,expected_head=expected_head)
    if not base['passed']:raise ValueError('Follow-up diagnostic audit: '+str(base['error']))
    registration=next(e['payload'] for e in events if e['kind']=='restored_followup_registered')
    if (json.loads((path/'registration.json').read_text())!=registration
            or registration['original_primary_status']!='failed'
            or registration['original_selection_unchanged'] is not True
            or registration['counted'] is not True or registration['selected_first_attempt'] is not False):
        raise ValueError('Follow-up registration or first-attempt accounting changed.')
    original=False;qa=False;diagnosis=None;photo_received=False;bodies=None;choice=None;proposal=None;confirmed=False;bound=set()
    for e in events:
        k,p=e['kind'],e['payload']
        if k=='followup_record_bound':
            if p['file'] in bound:raise ValueError('Duplicate bound record.')
            bound.add(p['file'])
            file=check_file(path,p);child=chain(file,p['head_sha256'])
            base['events']+=len(child)
            if p['record_kind']=='original_failed_pair':
                old=verify_original(file.parent,expected_head=registration['original_head_sha256'])
                if not old['passed'] or old['run_status']!='run_failed':raise ValueError('Original failed attempt changed.')
                for key in ('events','forecasts','measurements','order_checks','prediction_files'):
                    base[key]+=old[key] if key!='events' else old[key]-len(child)
                original=True
            elif p['record_kind']=='recovery_QA':
                _,result,plan=qa_checked(file.parent)
                if (child[-1]['sha256']!=registration['QA_head_sha256']
                        or result['boot_id']!=registration['QA_boot_id']
                        or plan['failed_pair_head_sha256']!=registration['original_head_sha256']):
                    raise ValueError('Recovery QA belongs to another attempt.')
                qa=True
            elif p['record_kind']=='body_binding':choice=child[-1]['payload']['arguments']
        elif k=='netlist_v2_protocol':
            if not original or not qa:raise ValueError('Diagnosis before preserved history/QA binding.')
        elif k=='restored_followup_diagnosis_completed':
            if not original or not qa or diagnosis is not None:raise ValueError('Unqualified or duplicate diagnosis.')
            result=json.loads(check_file(path,p['artifact']).read_text())
            if result['agent_report']!=p['agent_report']:raise ValueError('Diagnostic report mismatch.')
            diagnosis=p
        elif k=='followup_photo_received':
            if not diagnosis or photo_received:raise ValueError('Photo before new diagnosis or duplicate.')
            for f in p['artifacts']:check_file(path,f)
            photo_received=True
        elif k=='followup_bodies_decoded':
            if not photo_received:raise ValueError('Bodies before photograph.')
            for f in p['artifacts']:check_file(path,f)
            bodies=p['bodies']
        elif k=='body_binding_proposed':
            if bodies is None or choice!={x:p[x] for x in ('sam_body','reason')}:raise ValueError('Unbound Spark correspondence.')
            proposal=p
        elif k=='body_binding':
            if (proposal is None or p['operator_confirmed'] is not True or p['sam_body'] not in bodies
                    or p['component']!=registration['requested_photo_component']):raise ValueError('Invalid final correspondence.')
            if p['chosen_by'] not in ('muse_spark','operator'):raise ValueError('Unknown body assigner.')
            if p['chosen_by']=='muse_spark' and p['sam_body']!=proposal['sam_body']:raise ValueError('Operator override attributed to Spark.')
            confirmed=True
        elif k=='run_completed':
            verdict=diagnosis['agent_report']['verdict'] if diagnosis else None
            if (not diagnosis or not confirmed or p['original_pair_status']!='failed'
                    or p['restored_verdict']!=verdict
                    or p['operator_restored_and_rerun_consistent']!=(verdict=='consistent')
                    or p['display_caption']!=('No mismatch in the tests Spark chose' if verdict=='consistent' else None)):
                raise ValueError('Incomplete or rewritten case outcome.')
    return base


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='command',required=True)
    a=sub.add_parser('prepare');a.add_argument('--failed-pair',required=True);a.add_argument('--QA-record',required=True)
    pars={}
    for name in ('run','photo','segment','decode','bind','confirm'):
        a=sub.add_parser(name);a.add_argument('--record',required=True);pars[name]=a
    for name in ('run','segment','bind'):pars[name].add_argument('--execute',action='store_true')
    for name in ('initial-report','assembly-record','preflight-run'):pars['run'].add_argument('--'+name,required=True)
    pars['photo'].add_argument('--image',required=True);pars['photo'].add_argument('--new-capture-confirmed',action='store_true')
    pars['confirm'].add_argument('--accept',action='store_true');pars['confirm'].add_argument('--operator-body')
    a=sub.add_parser('verify');a.add_argument('path');a.add_argument('--expected-head');args=p.parse_args(argv)
    if args.command=='verify':
        try:r=verify(args.path,args.expected_head)
        except (ValueError,OSError,KeyError,TypeError) as exc:
            print('FAIL '+type(exc).__name__+' scope=internal_integrity+recorded_order creation_time=unproven');return 1
        print(legacy.format_result(r));return 0
    actions={'prepare':prepare,'run':run_diagnosis,'photo':photo,'segment':segment,'decode':decode,'bind':body,'confirm':confirm}
    try:
        actions[args.command](args)
    except (Exception,KeyboardInterrupt) as exc:
        if ACTIVE_STAGE and hasattr(args,'record'):
            path=Path(args.record).resolve()
            events=decode_events((path/'events.jsonl').read_bytes(),require_terminal=False,include_hash=True)
            if events[-1]['kind'] not in ('run_completed','run_failed'):
                log=Recorder.__new__(Recorder);log.path=path;log.file=path/'events.jsonl';log.previous=events[-1]['sha256'];log.sequence=len(events)
                bound={e['payload']['file'] for e in events if e['kind']=='followup_record_bound'}
                for file in (path/'photo-restored').rglob('events.jsonl'):
                    if str(file.relative_to(path)) not in bound:
                        try:bind(log,file,'failed_photo_stage')
                        except ValueError:pass
                log.add('run_failed',{'stage':args.command,'error':str(exc) if isinstance(exc,(ValueError,RuntimeError)) else type(exc).__name__,'automatic_retry':False})
        raise
    return 0


if __name__=='__main__':
    raise SystemExit(main())
