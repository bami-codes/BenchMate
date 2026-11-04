"""Restored-only v4 numerical continuation after the completed v5 photo reading."""
import argparse
import json
from pathlib import Path
import shutil
import sys
from types import SimpleNamespace

from .records import Recorder, decode_events
from .reading_rules import digest
from .reading_timing_verify_v4 import chain, check_file, require
from .reading_photo_observation_v5 import verify as verify_reading, sha, save
from . import verify as numerical

ROOT=Path(__file__).resolve().parents[2]
SOURCES=('src/benchmate/reading_restored_after_photo_v5.py',
         'tests/test_reading_restored_after_photo_v5.py',
         'docs/2026-11-04-case03-restored-after-photo.md')
ACTIVE=False


def runtime():
    sys.path.insert(0,str(ROOT))
    from scripts import reading_experiment_timing_v4 as r
    return r


def eligible(audit,score,result):
    require(audit['passed'] and audit['run_status']=='run_completed','completed_reading_required')
    require(score['outcome']=='one_explanation_remains' and len(score['fits'])==1
            and score['refitted'] is False,'unique_unmodified_reading_required')
    require(result['reading_outcome']==score['outcome'] and result['original_failed_status_preserved'] is True
            and result['repair_completed'] is False and result['restored_diagnosis_completed'] is False,'unrun_restored_stage_required')


def prepare(reading):
    r=runtime();r.check_freeze();reading=Path(reading).resolve()
    audit=verify_reading(reading);score=json.loads((reading/'reading-score.json').read_text())
    result=json.loads((reading/'result.json').read_text());eligible(audit,score,result)
    old=reading/'history/original';old_state=json.loads((old/'state.json').read_text())
    data=r.index();case=result['case_id']
    require(case=='03','separately_qualified_passive03_scope_only')
    require(not any(a['case_id']==case and a['status'] not in ('completed','failed') for a in data['attempts']),'another_attempt_active')
    original=chain(old/'events.jsonl')
    boot=next(e['payload']['boot_id'] for e in original if e['kind']=='diagnosis_finished' and e['payload']['state']=='faulted')
    log=Recorder(ROOT/'runs/reading-cohort',mode='restored_only_after_photo_reading_v5')
    shutil.copytree(reading,log.path/'history/reading',ignore=shutil.ignore_patterns('*-local-only.json'))
    for n in ('reviewed-design.json','schematic.png','timing-backend-scope.json','photo-candidate-scope.json'):
        shutil.copyfile(old/n,log.path/n)
    for n in ('prepared','probe-prepared'):
        shutil.copytree(old/n,log.path/n)
    context=log.path/'photo-faulted/prepared';context.mkdir(parents=True)
    for n in ('input.png','clean-full.png','plan.json'):
        shutil.copyfile(old/'photo-faulted/prepared'/n,context/n)
    reg={'schema':'benchmate.restored_after_photo_observation.v5','cohort':r.COHORT,'case_id':case,
         'run_id':log.path.name,'attempt':1+sum(a['case_id']==case for a in data['attempts']),
         'state':'restored_only','official':True,'counted':True,'selected_first_attempt':False,'blind_test':False,
         'followup_of':result['parent_run_id'],'original_primary_status':'failed','original_selection_unchanged':True,
         'reading_record_head_sha256':audit['head_sha256'],'previous_boot_id':boot,
         'source_sha256':{n:sha(ROOT/n) for n in SOURCES},
         'original_freeze_sha256':digest(r.check_freeze()),'protocol_sha256':digest(json.loads((old/'prepared/protocol.json').read_text())),
         'timing_scope_sha256':sha(old/'timing-backend-scope.json'),'photo_scope_sha256':sha(old/'photo-candidate-scope.json'),
         'inherited_faulted_diagnosis':'history/reading/history/original/'+old_state['faulted_diagnosis'],
         'prior_data_supplied_to_diagnostic_model':False,'diagnostic_Spark_max':8,'restored_photo_SAM_max':1,
         'consistent_restored_binding_Spark_max':0,'consistent_restored_operator_readings':0,
         'restored_photo_required':True,'restored_SAM_role':'documentary_display_only',
         'public_registration':str(r.PUBLIC/'registrations'/(log.path.name+'.json'))}
    save(log.path/'registration.json',reg);save(ROOT/reg['public_registration'],reg)
    log.add('restored_after_photo_registered',reg)
    log.add('completed_reading_record_bound',{'file':'history/reading/events.jsonl','sha256':sha(log.path/'history/reading/events.jsonl'),
        'head_sha256':audit['head_sha256'],'original_failed_pair_unchanged':True})
    log.add('inherited_faulted_photo_context_bound',{'file':'photo-faulted/prepared/input.png','sha256':sha(context/'input.png'),
        'new_photo':False,'purpose':'Original fault photo comparison only; not relabelled as restored.'})
    r.state(log,'awaiting_restoration_confirmation',case_id=case,requested_component=score['component'],
        reading_outcome=score['outcome'],faulted_diagnosis=reg['inherited_faulted_diagnosis'],last_boot=boot)
    data['attempts'].append({'run_id':log.path.name,'case_id':case,'attempt':reg['attempt'],'status':'registered',
        'counted':True,'selected_first_attempt':False,'execution_scope':'restored_only_after_confirmed_photo_reading',
        'followup_of':result['parent_run_id'],'original_primary_status':'failed'})
    save(ROOT/r.INDEX,data)
    print(json.dumps({'record':str(log.path),'public_registration':reg['public_registration'],'API_calls':0,'hardware_commands':0}))


def opened(record,phases):
    r=runtime();log=r.open_pair(record,phases);reg=json.loads((log.path/'registration.json').read_text())
    for n,h in reg['source_sha256'].items():require(sha(ROOT/n)==h,'restored_stage_source_changed')
    require(sha(log.path/'timing-backend-scope.json')==reg['timing_scope_sha256'],'timing_scope_changed')
    require(sha(log.path/'photo-candidate-scope.json')==reg['photo_scope_sha256'],'photo_scope_changed')
    return r,log,reg


def restore(record,report_file):
    r,log,_=opened(record,['awaiting_restoration_confirmation'])
    report=json.loads(Path(report_file).read_text())
    require(set(report)=={'USB_off_wiring_confirmed','USB_reconnected','remaining_wiring_maintained','R1_10k_at_B3_B8','operator_verbatim'}
        and all(report[k] is True for k in report if k!='operator_verbatim')
        and isinstance(report['operator_verbatim'],str) and bool(report['operator_verbatim'].strip()),'actual_restoration_confirmation_required')
    save(log.path/'operator-restoration-report.json',report)
    log.add('operator_restoration_reported',{'file':'operator-restoration-report.json','sha256':sha(log.path/'operator-restoration-report.json')})
    r.restoration(SimpleNamespace(record=record,power_off_restored_confirmed=True))


def diagnose(args):
    global ACTIVE
    r,log,reg=opened(args.record,['awaiting_restored_setup'])
    r.committed(ROOT/reg['public_registration']);ACTIVE=True
    args.state='restored';args.previous_boot_id=reg['previous_boot_id']
    # Unchanged qualified runtime: only intended design, menu, tool outputs and
    # fresh measurements enter its new model. Inherited reading/history do not.
    r.diagnose(args)


def verify(record,allow_active=False):
    path=Path(record);events=decode_events((path/'events.jsonl').read_bytes(),require_terminal=not allow_active,include_hash=True)
    require(not any(e['kind'] in ('run_completed','run_failed') for e in events[:-1]),'event_after_terminal')
    reg=next(e['payload'] for e in events if e['kind']=='restored_after_photo_registered')
    require(json.loads((path/'registration.json').read_text())==reg and reg['selected_first_attempt'] is False
        and reg['original_primary_status']=='failed' and reg['prior_data_supplied_to_diagnostic_model'] is False,'registration_changed')
    for n,h in reg['source_sha256'].items():require(sha(ROOT/n)==h,'restored_source_changed')
    require(sha(path/'timing-backend-scope.json')==reg['timing_scope_sha256'] and sha(path/'photo-candidate-scope.json')==reg['photo_scope_sha256'],'inherited_qualification_changed')
    require(digest(json.loads((path/'prepared/protocol.json').read_text()))==reg['protocol_sha256'],'numerical_protocol_changed')
    inherited=verify_reading(path/'history/reading')
    require(inherited['head_sha256']==reg['reading_record_head_sha256'],'inherited_reading_changed')
    result={'passed':True,'events':len(events)+inherited['events'],'forecasts':0,'measurements':0,'order_checks':0,
        'prediction_files':0,'run_status':events[-1]['kind'],'head_sha256':events[-1]['sha256'],'error':None}
    restored=diagnosis=photo=decoded=scope=documentary=None
    children={};sam=None
    for e in events:
        k,p=e['kind'],e['payload']
        if k=='completed_reading_record_bound':
            check_file(path,p);require(p['head_sha256']==reg['reading_record_head_sha256'],'reading_head_changed')
        elif k=='inherited_faulted_photo_context_bound':check_file(path,p)
        elif k=='operator_restoration_reported':check_file(path,p)
        elif k=='operator_restoration_confirmed':
            require(restored is None and p['USB_off'] is True and p['restored_intended_design'] is True and p['reading_isolation_reconnected'] is True,'unconfirmed_restoration')
            restored=p
        elif k=='child_record_bound':
            f=check_file(path,p);ce=chain(f,p['head_sha256']);result['events']+=len(ce);children[p['file']]=ce
            if p['kind'].startswith('terminal_diagnosis'):
                a=numerical.verify_run(f,expected_head=p['head_sha256']);require(a['passed'],'numerical_child_'+str(a['error']))
                if ce[-1]['kind']=='run_completed':
                    require(any(c['kind']=='channel_timing_model_bound' and c['payload']['version']=='frame-anchored-channel-timing-v4' for c in ce),'missing_qualified_v4_backend')
                for key in ('forecasts','measurements','order_checks','prediction_files'):result[key]+=a[key]
            elif p['kind']=='SAM_localization':sam=ce
        elif k=='diagnosis_finished':
            require(restored is not None and p['state']=='restored' and diagnosis is None,'restored_diagnosis_order')
            ce=children[p['record']+'/events.jsonl'];require(ce[-1]['payload']['agent_report']==p['agent_report'],'diagnosis_not_child_result')
            diagnosis=p
        elif k=='restored_photo_scope_declared':
            require(diagnosis is not None and diagnosis['agent_report']['verdict']=='consistent' and photo is None and scope is None,'omission_after_photo_or_inconsistent')
            check_file(path,p);require(p['Spark_binding_requests']==0 and p['operator_value_requests']==0 and p['component_identity_claimed'] is False,'invented_restored_reference');scope=p
        elif k=='board_photo_received':
            require(scope is not None and p['state']=='restored' and photo is None and p['new_capture_operator_confirmed'] is True,'photo_before_scope_or_duplicate')
            check_file(path,p)
            for a in p['artifacts']:check_file(path,a)
            require(p['sha256']!=sha(path/'photo-faulted/prepared/input.png'),'fault_pixels_relabelled_restored');photo=p
        elif k=='bodies_decoded':
            require(photo is not None and p['state']=='restored' and decoded is None,'restored_decode_order')
            check_file(path,{'file':p['manifest'],'sha256':p['sha256']})
            for a in p['artifacts']:check_file(path,a)
            decoded=p
        elif k=='restored_documentary_completed':
            require(decoded is not None and scope is not None and sam is not None,'documentary_before_SAM')
            require(p['SAM_role']=='documentary_display_only' and p['Spark_binding_requests']==0 and p['operator_value_requests']==0 and p['component_identity_claimed'] is False,'documentary_identity_overclaim')
            req=next(c['payload'] for c in sam if c['kind']=='sam_request_frozen')
            require(req['concept']=='electronic component' and req['image_sha256']==photo['sha256'] and sam[-1]['payload']['requests']==1,'documentary_SAM_request_changed')
            documentary=p
        elif k=='run_completed':
            require(documentary is not None and p==json.loads((path/'result.json').read_text()),'incomplete_restored_completion')
            require(p['restored_verdict']==diagnosis['agent_report']['verdict'] and p['faulted_diagnosis']==reg['inherited_faulted_diagnosis'],'completion_result_changed')
            require(p['restored_caption']=='No mismatch in the tests Spark chose' and p['native_diagnostic_repair_claim_overwritten'] is False,'restored_caption_or_native_claim_changed')
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='command',required=True)
    a=sub.add_parser('prepare');a.add_argument('--reading',required=True)
    for name in ('restore','diagnose','verify'):
        a=sub.add_parser(name);a.add_argument('record')
        if name=='restore':a.add_argument('--report',required=True)
        if name=='diagnose':
            for k in ('initial-report','assembly-record','preflight-run'):a.add_argument('--'+k,required=True)
            a.add_argument('--execute',action='store_true')
        if name=='verify':a.add_argument('--allow-active',action='store_true')
    args=p.parse_args()
    try:
        if args.command=='prepare':prepare(args.reading)
        elif args.command=='restore':restore(args.record,args.report)
        elif args.command=='diagnose':diagnose(args)
        else:print(json.dumps(verify(args.record,args.allow_active)))
    except (Exception,KeyboardInterrupt) as exc:
        if ACTIVE:
            r=runtime();path=Path(args.record);phase=json.loads((path/'state.json').read_text())['phase']
            log=r.open_pair(path,[phase]);log.add('run_failed',{'stage':args.command,'error':str(exc) if isinstance(exc,(ValueError,RuntimeError)) else type(exc).__name__,'automatic_retry':False})
            r.update_index(path.name,status='failed',failed_stage=args.command)
        raise


if __name__=='__main__':main()
