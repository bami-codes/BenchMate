"""Explicit post-diagnosis photo waiver; never modify frozen experiment sources."""
import argparse
import json
from pathlib import Path
import shutil

from . import reading_followup as prior
from .reading_verify import chain, check_file, verify_run
from .verify import verify_run as numerical, format_result

NOTE = 'docs/2026-11-03-reading-photo-closeout.md'
SOURCE = 'src/benchmate/reading_closeout.py'
CAPTION = 'No mismatch in the tests Spark chose'
STATEMENT = '미니보드 건든게 하나도 없는데 왜 다시찍어 이건 진짜 억지 아니야?'


def close(record):
    log,reg=prior.open_record(record,['awaiting_restored_photo'])
    prior.check_publication(prior.ROOT/NOTE)
    events=prior.decode_events(log.file.read_bytes(),require_terminal=False,include_hash=True)
    if any(e['kind'].startswith('followup_photo_') for e in events):
        raise ValueError('New photo stage already started; this waiver does not apply.')
    report=json.loads((log.path/'diagnostic-result.json').read_text())
    completed=next(e['payload'] for e in reversed(events) if e['kind']=='restored_followup_diagnosis_completed')
    check_file(log.path,completed['artifact'])
    if report['agent_report']!=completed['agent_report']:raise ValueError('Diagnostic result changed.')
    artifacts=[]
    for name in (NOTE,SOURCE):
        target=log.path/'closeout'/Path(name).name;target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(prior.ROOT/name,target)
        artifacts.append({'file':str(target.relative_to(log.path)),'sha256':prior.sha(target)})
    log.add('post_diagnosis_photo_requirement_waived',{
        'schema':'benchmate.photo_closeout_amendment.v1','timing':'after_diagnosis_results_known',
        'operator_statement':STATEMENT,'original_photo_requirement_satisfied':False,
        'existing_image_scope':'Original fault-state image only; no restored-state image claim.',
        'restoration_evidence':'Recorded operator wiring reports and subsequent physical re-execution.',
        'earlier_R1_isolation_and_reinstallation_preserved':True,
        'preceding_head_sha256':events[-1]['sha256'],'artifacts':artifacts,
        'additional_hardware_actions':0,'additional_Spark_requests':0,'additional_SAM_requests':0,'added_usd':0.})
    verdict=report['agent_report']['verdict']
    result={'schema':'benchmate.restored_followup_photo_waived.v1','source':'physical',
        'original_pair':reg['followup_of'],'original_pair_status':'failed','original_failure_counted':True,
        'restored_followup_counted':True,'original_first_selection_unchanged':True,'blind_test':False,
        'restored_verdict':verdict,'operator_restored_and_rerun_consistent':verdict=='consistent',
        'display_caption':CAPTION if verdict=='consistent' else None,
        'native_diagnostic_repair_claim_overwritten':False,
        'restored_photo_and_correspondence_recorded':False,'post_diagnosis_photo_requirement_waived':True,
        'fault_and_reading_evidence':'history/original','existing_photo_relabelled_as_restored':False}
    prior.save(log.path/'result.json',result);log.add('run_completed',result)
    prior.save(log.path/'state.json',{'phase':'completed_with_explicit_photo_waiver','restored_verdict':verdict})
    print(json.dumps({'record':str(log.path),**result}),flush=True)


def verify(path,expected_head=None):
    path=Path(path);events=chain(path/'events.jsonl',expected_head)
    base=numerical(path,expected_head=expected_head)
    if not base['passed']:raise ValueError(base['error'])
    reg=events[1]['payload']
    if (events[1]['kind']!='restored_followup_registered'
            or json.loads((path/'registration.json').read_text())!=reg
            or reg['original_primary_status']!='failed' or reg['original_selection_unchanged'] is not True
            or reg['counted'] is not True or reg['selected_first_attempt'] is not False):
        raise ValueError('Changed registration or first-attempt accounting.')
    original=qa=preflight=False;report=None;seen=set();waiver=None
    for e in events:
        k,p=e['kind'],e['payload']
        if k=='followup_record_bound':
            if p['file'] in seen:raise ValueError('Duplicate record.')
            seen.add(p['file']);file=check_file(path,p);child=chain(file,p['head_sha256'])
            if p['record_kind']=='original_failed_pair':
                audited=verify_run(file.parent,expected_head=reg['original_head_sha256'])
                if not audited['passed'] or audited['run_status']!='run_failed':raise ValueError('Original failure changed.')
                for key in ('events','forecasts','measurements','order_checks','prediction_files'):base[key]+=audited[key]
                original=True
            elif p['record_kind']=='recovery_QA':
                _,q,plan=prior.qa_checked(file.parent)
                if (child[-1]['sha256']!=reg['QA_head_sha256'] or q['boot_id']!=reg['QA_boot_id']
                        or plan['failed_pair_head_sha256']!=reg['original_head_sha256']):raise ValueError('Wrong recovery QA.')
                base['events']+=len(child);qa=True
            elif p['record_kind']=='preflight':
                q=child[-1]['payload']
                if (child[-1]['kind']!='run_completed' or q.get('armed') is not False
                        or q.get('commands')!=['PING'] or q.get('stimuli')!=0
                        or q.get('boot_id')==reg['QA_boot_id']):raise ValueError('No fresh unarmed boot.')
                base['events']+=len(child);preflight=True
            else:raise ValueError('Unexpected child in waived-photo closeout.')
        elif k=='netlist_v2_protocol' and not (original and qa and preflight):
            raise ValueError('Diagnosis before preserved history and fresh setup.')
        elif k=='restored_followup_diagnosis_completed':
            if report is not None:raise ValueError('Duplicate diagnosis.')
            report=json.loads(check_file(path,p['artifact']).read_text())
            if report['agent_report']!=p['agent_report']:raise ValueError('Changed diagnostic report.')
        elif k.startswith('followup_photo_') or k in ('followup_bodies_decoded','body_binding_proposed','body_binding'):
            raise ValueError('Waiver cannot pretend a new photo stage occurred.')
        elif k=='post_diagnosis_photo_requirement_waived':
            if (waiver is not None or report is None or e['sequence']!=len(events)-2
                    or p['preceding_head_sha256']!=e['previous_sha256']
                    or p['timing']!='after_diagnosis_results_known'
                    or p['original_photo_requirement_satisfied'] is not False
                    or p['operator_statement']!=STATEMENT
                    or any(p[n]!=0 for n in ('additional_hardware_actions','additional_Spark_requests','additional_SAM_requests','added_usd'))):
                raise ValueError('Missing or misleading post-diagnosis amendment.')
            for f in p['artifacts']:check_file(path,f)
            waiver=p;base['order_checks']+=1
    result=events[-1]['payload'];verdict=report['agent_report']['verdict'] if report else None
    if (events[-1]['kind']!='run_completed' or waiver is None or not (original and qa and preflight)
            or result['original_pair_status']!='failed' or result['restored_verdict']!=verdict
            or result['operator_restored_and_rerun_consistent']!=(verdict=='consistent')
            or result['display_caption']!=(CAPTION if verdict=='consistent' else None)
            or result['restored_photo_and_correspondence_recorded'] is not False
            or result['post_diagnosis_photo_requirement_waived'] is not True
            or result['existing_photo_relabelled_as_restored'] is not False
            or result['original_failure_counted'] is not True
            or result['restored_followup_counted'] is not True
            or result['original_first_selection_unchanged'] is not True
            or result['native_diagnostic_repair_claim_overwritten'] is not False
            or json.loads((path/'result.json').read_text())!=result):
        raise ValueError('Incomplete or rewritten closeout.')
    return base


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);s=p.add_subparsers(dest='action',required=True)
    a=s.add_parser('close');a.add_argument('record')
    a=s.add_parser('verify');a.add_argument('record');a.add_argument('--expected-head')
    args=p.parse_args(argv)
    if args.action=='close':close(args.record);return 0
    try:r=verify(args.record,args.expected_head)
    except (ValueError,OSError,KeyError,TypeError,IndexError) as exc:
        print('FAIL '+type(exc).__name__+' scope=internal_integrity+recorded_order creation_time=unproven');return 1
    print(format_result(r));return 0


if __name__=='__main__':raise SystemExit(main())
