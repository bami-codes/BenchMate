"""Close an externally restored reading pair with its predeclared photo scope."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

from .reading_pair_audit import verify_pair
from .reading_verify import check_file
from .verify import format_result

ROOT=Path(__file__).resolve().parents[2]


def close(record,operator_report):
    # Lazy import: offline verification never imports providers, keys or serial.
    sys.path.insert(0,str(ROOT))
    from scripts import reading_experiment as old
    log=old.open_pair(record,['awaiting_restored_photo'])
    report=json.loads(Path(operator_report).read_text())
    if (report.get('mini_components_and_layout_unchanged') is not True
            or report.get('only_external_fault_removed') is not True
            or not isinstance(report.get('operator_statement'),str) or not report['operator_statement'].strip()):
        raise ValueError('Actual operator report of unchanged mini-board/external-only restoration required.')
    extension=json.loads((log.path/'photo-scope-extension.json').read_text())
    for f in extension['artifacts']:
        if hashlib.sha256((ROOT/f['source']).read_bytes()).hexdigest()!=f['sha256']:
            raise ValueError('Frozen photo closeout source changed.')
    old.committed(ROOT/extension['public_manifest'])
    events=old.decode_events(log.file.read_bytes(),require_terminal=False,include_hash=True)
    if any(e['kind']=='board_photo_received' and e['payload']['state']=='restored' for e in events):
        raise ValueError('Restored photo already recorded; use the original complete-photo closeout.')
    photo=next(e['payload'] for e in events if e['kind']=='board_photo_received' and e['payload']['state']=='faulted')
    binding=next(e['payload'] for e in events if e['kind']=='body_binding' and e['payload']['state']=='faulted')
    check_file(log.path,photo)
    waiver={'reason':'unchanged_mini_board_external_restoration',
        'operator_mini_configuration_unchanged':True,'operator_statement':report['operator_statement'],
        'new_restored_photo':False,'image_relabelled_as_restored':False,
        'new_SAM_requests':0,'new_binding_requests':0,
        'original_fault_photo_sha256':photo['sha256'],'reference_binding_sha256':old.digest(binding)}
    result={'schema':'benchmate.reading_pair_result.v1','cohort':old.COHORT,'source':'physical',
        'case_id':log.control['case_id'],'blind_test':False,
        'faulted_diagnosis':log.control['faulted_diagnosis'],
        'restored_diagnosis':log.control['restored_diagnosis'],
        'reading_outcome':log.control['reading_outcome'],'restored_verdict':log.control['restored_verdict'],
        'restored_caption':'No mismatch in the tests Spark chose' if log.control['restored_verdict']=='consistent' else None,
        'operator_restored_and_rerun_consistent':log.control['restored_verdict']=='consistent',
        'native_diagnostic_repair_claim_overwritten':False,'both_state_photos_recorded':False,
        'restored_photo_not_repeated':True,'existing_image_scope':'Original fault-state capture only.'}
    log.add('restored_photo_not_repeated',waiver)
    old.save(log.path/'result.json',result);log.add('run_completed',result)
    old.update_index(log.path.name,status='completed',reading_outcome=result['reading_outcome'],restored_verdict=result['restored_verdict'])
    print(json.dumps({'record':str(log.path),**result}),flush=True)


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);s=p.add_subparsers(dest='action',required=True)
    a=s.add_parser('close');a.add_argument('record');a.add_argument('--operator-report',required=True)
    a=s.add_parser('verify');a.add_argument('record');a.add_argument('--expected-head')
    args=p.parse_args(argv)
    if args.action=='close':close(args.record,args.operator_report);return 0
    result=verify_pair(args.record,args.expected_head);print(format_result(result));return 0 if result['passed'] else 1


if __name__=='__main__':raise SystemExit(main())
