"""Prospective counted passive follow-up using the qualified v4 timing model.

Registration and verification are keyless and stdlib-only. Physical/model
imports occur only in the explicitly executed run stage. Prior terminal records
are referenced by committed hashes, never reopened or relabelled.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

from .records import Recorder, decode_events

ROOT = Path(__file__).resolve().parents[2]
PUBLIC = Path('examples/channel-timing/2026-11-04')
QUALIFICATION = PUBLIC/'candidate02/manifest.json'
SOURCES = ('src/benchmate/channel_timing_v4.py', 'src/benchmate/channel_timing_session_v4.py',
           'src/benchmate/channel_timing_followup_v4.py', 'scripts/timing_regression_v4.py',
           'scripts/timing_synthetic_v4.py', 'tests/test_channel_timing_v4.py',
           'docs/2026-11-04-frame-anchored-timing-v4.md')


def sha(file):return hashlib.sha256(Path(file).read_bytes()).hexdigest()


def save(file, value):
    p=Path(file);p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n')


def runtime():
    sys.path.insert(0,str(ROOT))
    from scripts import reading_experiment
    return reading_experiment


def qualification():
    p=ROOT/QUALIFICATION;q=json.loads(p.read_text())
    if (q.get('qualified') is not True or q.get('hardware_enabled') is not True
            or q['same_action_verdict_flips']!=0 or q['synthetic_other_design_flips']!=0
            or q['synthetic_05_old_fail_new_pass'] is not True or q['timing_parameters']!=[]):
        raise ValueError('Passing general model qualification required.')
    for n,h in q['source_sha256'].items():
        if sha(ROOT/n)!=h:raise ValueError('Qualified source changed: '+n)
    for n,h in q['artifacts_sha256'].items():
        if sha(p.parent/n)!=h:raise ValueError('Qualification evidence changed: '+n)
    return q


def register(original):
    r=runtime();r.check_freeze();qualification()
    from .reading_wire_stage import verify as prior_verify
    old=Path(original).resolve();audited=prior_verify(old)
    if not audited['passed'] or audited['run_status']!='run_completed':
        raise ValueError('Complete verified original pair required.')
    state=json.loads((old/'state.json').read_text())
    if state.get('restored_verdict')!='abstained':
        raise ValueError('This follow-up requires an original restored abstention.')
    attempts=[a for a in r.index()['attempts'] if a['case_id']==state['case_id']]
    if any(a['status'] not in ('completed','failed') for a in attempts):
        raise ValueError('Another case attempt is still active.')
    ordinal=max(a['attempt'] for a in attempts)+1
    prior_public=r.PUBLIC/'records'/old.name
    if sha(ROOT/prior_public/'events.jsonl')!=sha(old/'events.jsonl'):
        raise ValueError('Original public record does not match local terminal record.')
    log=Recorder(ROOT/'runs/channel-timing-followup',mode='counted_restored_only_timing_followup_v4')
    d=json.loads((old/'reviewed-design.json').read_text());p=json.loads((old/'prepared/protocol.json').read_text())
    sources={**r.check_freeze()['source_sha256'],**{n:sha(ROOT/n) for n in SOURCES}}
    reg={'schema':'benchmate.frame_timing_restored_followup.v4','run_id':log.path.name,
         'case_id':state['case_id'],'state':'restored','attempt_ordinal':ordinal,'cohort':r.COHORT,
         'counted':True,'official':True,'selected_first_attempt':False,'blind_test':False,
         'source':'physical','actor':'muse_spark',
         'original_pair':str(prior_public),'original_pair_head_sha256':audited['head_sha256'],
         'original_pair_event_sha256':sha(old/'events.jsonl'),'original_restored_verdict':'abstained',
         'original_first_selection_unchanged':True,'previous_boot_id':state['last_boot'],
         'qualification_file':str(QUALIFICATION),'qualification_sha256':sha(ROOT/QUALIFICATION),
         'source_sha256':sources,'protocol_sha256':r.digest(p),'reviewed_design_sha256':r.digest(d),
         'public_registration':str(PUBLIC/'registrations'/(log.path.name+'.json')),
         'registered_UTC':datetime.now(timezone.utc).isoformat(),'requests_max':8,
         'paid_requests_before_assignment':0,'stimuli_before_assignment':0,
         'prior_measurements_or_readings_supplied_to_diagnosis':False,
         'extra_photo_or_reading_requests':0,'mini_board_unchanged_external_only_repair':True}
    save(log.path/'registration.json',reg);save(ROOT/reg['public_registration'],reg)
    save(log.path/'reviewed-design.json',d);save(log.path/'protocol.json',p)
    log.add('frame_timing_followup_registered',reg)
    index=r.index();index['attempts'].append({'run_id':log.path.name,'case_id':state['case_id'],
         'attempt':ordinal,'status':'registered','counted':True,'selected_first_attempt':False,
         'followup_of':old.name,'execution_scope':'restored_only_frame_timing_v4',
         'record':str(PUBLIC/'records'/log.path.name),'original_restored_verdict':'abstained'})
    r.save(ROOT/r.INDEX,index)
    print(json.dumps({'record':str(log.path),'public_registration':reg['public_registration'],
                      'attempt':ordinal,'Spark_requests':0,'hardware_commands':0}))


def open_record(path):
    root=Path(path).resolve();es=decode_events((root/'events.jsonl').read_bytes(),require_terminal=False,include_hash=True)
    if es[-1]['kind'] in ('run_completed','run_failed'):raise ValueError('Terminal follow-up; no retry.')
    reg=json.loads((root/'registration.json').read_text());runtime().check_freeze();qualification()
    for n,h in reg['source_sha256'].items():
        if sha(ROOT/n)!=h:raise ValueError('Registered source changed: '+n)
    if sha(ROOT/reg['qualification_file'])!=reg['qualification_sha256']:
        raise ValueError('Qualification hash changed after registration.')
    log=Recorder.__new__(Recorder);log.path=root;log.file=root/'events.jsonl'
    log.previous=es[-1]['sha256'];log.sequence=len(es)
    return log,reg


def run(args):
    if not args.execute:raise ValueError('Explicit --execute required for paid/physical work.')
    r=runtime();log,reg=open_record(args.record)
    r.committed(ROOT/reg['public_registration']);r.committed(ROOT/QUALIFICATION)
    initial=json.loads(Path(args.initial_report).read_text());assembly=json.loads(Path(args.assembly_record).read_text())
    d=json.loads((log.path/'reviewed-design.json').read_text());p=json.loads((log.path/'protocol.json').read_text())
    r.preserved.base.validate_assembly(d,initial,assembly)
    pre=Path(args.preflight_run);es=decode_events((pre/'events.jsonl').read_bytes());pong=es[-1]['payload']
    if (es[-1]['kind']!='run_completed' or pong.get('commands')!=['PING'] or pong.get('armed') is not False
            or pong.get('stimuli')!=0 or pong.get('boot_id')==reg['previous_boot_id']):
        raise ValueError('Fresh unarmed PING-only preflight required.')
    with (log.path/'execution-started.json').open('x') as f:json.dump({'one_attempt':True,'automatic_retry':False},f)
    import shutil
    shutil.copytree(pre,log.path/'preflight')
    log.add('frame_timing_preflight_bound',{'file':'preflight/events.jsonl','sha256':sha(log.path/'preflight/events.jsonl')})
    save(log.path/'assembly-local-only.json',assembly)
    log.add('frame_timing_assembly_sealed',{'sha256':r.digest(assembly),'transmitted_to_model':False})
    model=None
    try:
        from serial.tools import list_ports
        from .channel_timing_session_v4 import PhysicalSession
        ports=[x for x in list_ports.comports() if (x.vid,x.pid,x.serial_number)==tuple(p['USB_identity'])]
        if len(ports)!=1:raise ValueError('Expected Minima absent or ambiguous; no serial opened.')
        bench=r.preserved.SettledBench(p,log,lambda f:r.preserved.base.intervention(log,d,f),
            design=d,initial_report=initial,approved=True,previous_boot_id=reg['previous_boot_id'],preflight_boot_id=pong['boot_id'])
        def publish(frozen,expected):
            open_record(log.path)
            if r.digest(frozen)!=expected:raise ValueError('Timing forecast hash mismatch.')
            save(log.path/'predictions-frozen.json',frozen)
            return r.publish(log,frozen,'frame-timing-followup-v4')
        session=PhysicalSession(bench,log,d,publish)
        prompt=r.preserved.PROMPT+'\nMeasured-IN conditional simulation holds IN until recorded DAC-write frames, then interpolates to recorded A1 reads and between no-change frames. Actual A2 timestamps are used. This fixed rule has no OUT-fitted timing/gain/offset parameters. All guards, 9mV regional scoring and experiment choices remain unchanged.\n'
        model=r.preserved.OfficialModel(prompt=prompt,tools=session.tools,log=log,effort='medium',
            env_path=ROOT/'.env',budget_path=r.MODEL_BUDGET,max_requests=8)
        result=model.sanitize({**r.preserved.base.drive_agent(session,model),**model.metadata()})
        result.update(followup_schema=reg['schema'],case_id=reg['case_id'],restored_attempt=reg['attempt_ordinal'],
            original_pair=reg['original_pair'],original_restored_verdict='abstained',original_first_selection_unchanged=True,
            counted=True,restored_caption=result['display_caption'],output_at_REF_confirmed=True,
            original_mini_photo_retained=True,new_photo_or_reading_requested=False)
        save(log.path/'result.json',result);log.add('run_completed',result)
        r.update_index(log.path.name,status='completed',restored_verdict=result['agent_report']['verdict'])
        print(json.dumps({'record':str(log.path),'agent_report':result['agent_report'],
                          'requests':result['http_requests'],'output_at_REF_confirmed':True}))
    except (Exception,KeyboardInterrupt) as exc:
        value={'error':str(exc) if isinstance(exc,(ValueError,RuntimeError)) else type(exc).__name__,
               'automatic_retry':False,**(model.metadata() if model else {})}
        save(log.path/'failure.json',value);log.add('run_failed',value)
        r.update_index(log.path.name,status='failed',failed_stage='frame_timing_followup')
        raise
    finally:
        if model:model.close()


def verify(path):
    from .verify import verify_run, format_result
    from .reading_verify import chain, require
    from .reading_wire_stage import verify as old_verify
    root=Path(path);events=chain(root/'events.jsonl');result=verify_run(root)
    require(result['passed'],'diagnostic_order_integrity')
    reg=next(e['payload'] for e in events if e['kind']=='frame_timing_followup_registered')
    require(reg==json.loads((root/'registration.json').read_text()),'registration_artifact')
    require(reg['counted'] and not reg['selected_first_attempt'] and reg['original_first_selection_unchanged'],'accounting')
    require(reg['source']=='physical' and reg['actor']=='muse_spark','registered_source_actor')
    require(sha(ROOT/reg['qualification_file'])==reg['qualification_sha256'],'qualification_hash')
    qualification()
    for n,h in reg['source_sha256'].items():require(sha(ROOT/n)==h,'source_hash:'+n)
    prior=old_verify(ROOT/reg['original_pair'])
    require(prior['passed'] and prior['head_sha256']==reg['original_pair_head_sha256'],'original_pair_preserved')
    require(sha(ROOT/reg['original_pair']/'events.jsonl')==reg['original_pair_event_sha256'],'original_events_preserved')
    if events[-1]['kind']=='run_completed':
        require(any(e['kind']=='channel_timing_model_bound' for e in events),'timing_backend_bound')
        require(events[-1]['payload']['original_restored_verdict']=='abstained','original_verdict_preserved')
        require(events[-1]['payload']['source']=='physical' and events[-1]['payload']['actor']=='muse_spark','result_source_actor')
    result['prior_events_checked']=prior['events']
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='action',required=True)
    q=sub.add_parser('register');q.add_argument('--original',required=True)
    q=sub.add_parser('run');q.add_argument('--record',required=True);q.add_argument('--execute',action='store_true')
    for n in ('initial-report','assembly-record','preflight-run'):q.add_argument('--'+n,required=True)
    q=sub.add_parser('verify');q.add_argument('record');a=p.parse_args()
    if a.action=='register':register(a.original)
    elif a.action=='run':run(a)
    else:
        from .verify import format_result
        try:value=verify(a.record)
        except (ValueError,OSError,KeyError,TypeError,StopIteration) as exc:
            print('FAIL '+str(exc)+' scope=internal_integrity+recorded_order creation_time=unproven');return 1
        print(format_result(value)+' prior_events_checked='+str(value['prior_events_checked']))
    return 0


if __name__=='__main__':raise SystemExit(main())
