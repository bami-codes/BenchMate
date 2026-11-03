"""Post-diagnosis withdrawal of an unneeded numeric reading, with full audit.

Preserves the published reading forecast without claiming it was exercised.
Diagnostic/reading hashes, publication order, seals and prior failures remain.
The original reading_pair_audit and all frozen diagnostic sources stay unchanged.
"""
import argparse
import json
from pathlib import Path
import re
import sys
from .reading_verify import chain, check_file, require, legacy
from .reading_rules import digest, validate_forecast, score_reading
from .reading_pair_audit import PHOTO_RULE

def verify_pair(path, expected_head=None):
    result = {'passed': False, 'events': 0, 'forecasts': 0, 'prediction_files': 0,
        'measurements': 0, 'order_checks': 0, 'head_sha256': '0'*64, 'run_status': 'unknown', 'error': None}
    try:
        path = Path(path); file = path/'events.jsonl' if path.is_dir() else path; root = file.parent
        events = chain(file, expected_head)
        result.update(events=len(events), head_sha256=events[-1]['sha256'], run_status=events[-1]['kind'])
        registered = requested = frozen = publication = observed = scored = revealed = restored = None
        photos = {}; decoded = {}; proposals = {}; bound = {}; diagnoses = {}; child_files = set()
        child_reading_choice = child_binding_choice = None
        workflow = waived = cancelled = None
        native_reports = {}
        for event in events:
            kind, p = event['kind'], event['payload']
            if kind == 'reading_pair_registered':
                require(registered is None and p['cohort'] == 'reading-assisted-v1', 'duplicate_or_unknown_registration')
                registered = p
            elif kind == 'case_workflow_scope_frozen':
                require(workflow is None and not child_files and not diagnoses,
                        'workflow_scope_declared_after_intake_or_diagnosis')
                check_file(root, p)
                require(p['frozen_before_schematic_intake'] is True and
                        p['frozen_before_hardware_measurements'] is True and
                        p['original_runtime_sources_changed'] is False and
                        p['optional_restored_photo'] == PHOTO_RULE,
                        'unqualified_workflow_amendment')
                workflow = p
            elif kind == 'restored_photo_not_repeated':
                require(workflow is not None and restored is not None and
                        'restored' in diagnoses and 'faulted' in bound and
                        'restored' not in photos and waived is None,
                        'photo_waiver_before_qualified_restored_diagnosis')
                require(p['reason'] == 'unchanged_mini_board_external_restoration' and
                        p['operator_mini_configuration_unchanged'] is True and
                        p['new_restored_photo'] is False and
                        p['image_relabelled_as_restored'] is False and
                        p['new_SAM_requests'] == 0 and p['new_binding_requests'] == 0 and
                        p['original_fault_photo_sha256'] == photos['faulted']['sha256'] and
                        p['reference_binding_sha256'] == digest(bound['faulted']),
                        'false_or_unbound_reused_photo_claim')
                waived = p; result['order_checks'] += 1
            elif kind == 'child_record_bound':
                file = check_file(root, p)
                require(p['file'] not in child_files, 'duplicate_child_record')
                child_files.add(p['file'])
                children = chain(file, p['head_sha256']); result['events'] += len(children)
                if p['kind'].startswith('terminal_diagnosis'):
                    c = legacy.verify_run(file, expected_head=p['head_sha256'])
                    require(c['passed'], 'child_diagnosis_'+str(c['error']))
                    native_reports[p['file'].removesuffix('/events.jsonl')] = children[-1]['payload'].get('agent_report')
                    for key in ('forecasts', 'measurements', 'order_checks', 'prediction_files'):
                        result[key] += c[key]
                elif p['kind'] == 'reading_selection':
                    child_reading_choice = children[-1]['payload'].get('arguments')
                elif p['kind'] == 'body_binding':
                    child_binding_choice = children[-1]['payload'].get('arguments')
            elif kind == 'diagnosis_finished':
                require(p['state'] not in diagnoses, 'duplicate_diagnosis')
                require(p['record']+'/events.jsonl' in child_files, 'unbound_diagnosis_record')
                require(native_reports.get(p['record']) == p['agent_report'], 'diagnostic_report_child_mismatch')
                if p['state'] == 'restored':
                    require(restored is not None, 'restored_diagnosis_before_restoration')
                diagnoses[p['state']] = p
            elif kind == 'reading_requested':
                require(requested is None and 'faulted' in diagnoses, 'reading_request_before_diagnosis_or_duplicate')
                require(child_reading_choice is not None and {**child_reading_choice, 'chosen_by': 'muse_spark'} == p,
                        'reading_request_not_bound_to_Spark_choice')
                requested = p; result['order_checks'] += 1
            elif kind == 'reading_forecast_frozen':
                require(requested is not None and frozen is None and not photos, 'reading_freeze_out_of_order')
                frozen = {k: v for k, v in p.items() if k != 'sha256'}
                validate_forecast(frozen)
                require(digest(frozen) == p['sha256'], 'reading_forecast_hash_mismatch')
                require(frozen['request'] == requested, 'reading_request_forecast_mismatch')
                require(json.loads((root/'reading-forecast.json').read_text(), object_pairs_hook=legacy._object,
                                  parse_constant=legacy._constant) == frozen, 'reading_forecast_file_mismatch')
                result['forecasts'] += 1; result['prediction_files'] += 1
            elif kind == 'reading_forecast_publication':
                require(frozen is not None and publication is None and p['sha256'] == digest(frozen)
                        and p['published'] is True and p['remote'] is True
                        and re.fullmatch('[0-9a-f]{40}', p['commit']), 'invalid_reading_publication')
                publication = p; result['order_checks'] += 1
            elif kind == 'board_photo_received':
                require(publication is not None and p['state'] not in photos, 'photo_before_reading_publication_or_duplicate')
                if p['state'] == 'restored':
                    require('restored' in diagnoses, 'restored_photo_before_diagnosis')
                check_file(root, p)
                for artifact in p['artifacts']:
                    check_file(root, artifact)
                photos[p['state']] = p; result['order_checks'] += 1
            elif kind == 'bodies_decoded':
                require(p['state'] in photos and p['state'] not in decoded, 'decode_before_photo_or_duplicate')
                check_file(root, {'file': p['manifest'], 'sha256': p['sha256']})
                for artifact in p['artifacts']:
                    check_file(root, artifact)
                decoded[p['state']] = p
            elif kind == 'body_binding_proposed':
                require(p['state'] in decoded and p['state'] not in proposals, 'body_proposal_before_decode_or_duplicate')
                require(p['chosen_by'] == 'muse_spark', 'invalid_body_proposer')
                require(child_binding_choice == {k: p[k] for k in ('sam_body', 'reason')},
                        'body_proposal_not_bound_to_Spark_choice')
                child_binding_choice = None
                proposals[p['state']] = p
            elif kind == 'body_binding':
                tag = p['state']
                require(tag in proposals and tag not in bound and p['operator_confirmed'] is True,
                        'body_binding_before_proposal_or_duplicate')
                require(p['sam_body'] in decoded[tag]['bodies'] and p['component'] == requested['component'], 'body_binding_component_mismatch')
                require(p['chosen_by'] in ('muse_spark', 'operator'), 'unknown_body_assigner')
                if p['chosen_by'] == 'muse_spark':
                    require(p['sam_body'] == proposals[tag]['sam_body'], 'operator_override_disguised_as_Spark')
                bound[tag] = p; result['order_checks'] += 1
            elif kind == 'reading_observed':
                require(cancelled is None and publication is not None and 'faulted' in bound and observed is None, 'reading_after_withdrawal_or_before_binding')
                check_file(root, p['photo'])
                observed = p; result['measurements'] += 1; result['order_checks'] += 1
            elif kind == 'reading_scored':
                require(observed is not None and scored is None, 'score_before_reading_or_duplicate')
                require(score_reading(frozen, observed) == p, 'reading_score_not_deterministic')
                scored = p; result['order_checks'] += 1
            elif kind == 'operator_reading_cancelled':
                require(cancelled is None and 'faulted' in diagnoses and
                        diagnoses['faulted']['agent_report']['verdict'] == 'structure_supported' and
                        requested is not None and frozen is not None and publication is not None and
                        observed is None and scored is None, 'unqualified_reading_withdrawal')
                catalog = json.loads((root/'reading-catalog.json').read_text())
                require(digest(catalog) == p['catalog_sha256'] == frozen['catalog_sha256'] and
                        len(catalog['explanations']) == 1 and
                        [x['id'] for x in catalog['explanations']] == p['verified_terminal_survivors'] and
                        p['requested_component'] == requested['component'] and
                        p['operator_reading_performed'] is False and
                        p['reading_forecast_exercised'] is False and
                        p['original_request_and_forecast_preserved'] is True and
                        p['timing'] == 'post_diagnosis_workflow_correction_after_results_known',
                        'misrepresented_cancelled_reading')
                cancelled = p; result['order_checks'] += 1
            elif kind == 'specimen_seal_opened':
                require((scored is not None or cancelled is not None) and revealed is None,
                        'reveal_before_score_or_withdrawal_or_duplicate')
                if cancelled is not None:
                    require(p['after_reading_score'] is False and p['after_reading_cancellation'] is True,
                            'withdrawal_misreported_as_reading_score')
                require(digest(p['assembly']) == p['sealed_sha256'], 'seal_hash_mismatch')
                prior = [e['payload'] for e in events[:event['sequence']] if e['kind'] == 'specimen_assembly_sealed' and e['payload']['state'] == 'faulted']
                require(len(prior) == 1 and prior[0]['sha256'] == p['sealed_sha256'], 'seal_was_not_precommitted')
                revealed = p; result['order_checks'] += 1
            elif kind == 'operator_restoration_confirmed':
                require(revealed is not None and restored is None and p['USB_off'] is True
                        and p['restored_intended_design'] is True and (p['reading_isolation_reconnected'] is True or
                        (cancelled is not None and p.get('reading_isolation_not_required') is True
                         and p['reading_isolation_reconnected'] is False)),
                        'restoration_before_reveal_or_unconfirmed')
                restored = p; result['order_checks'] += 1
            elif kind == 'run_completed':
                if cancelled is not None:
                    require(registered and revealed and restored and 'restored' in diagnoses and
                            observed is None and scored is None and
                            p['reading_performed'] is False and p['reading_forecast_exercised'] is False and
                            p['reading_outcome'] == 'not_performed_no_discriminating_numeric_reading' and
                            p['restored_verdict'] == diagnoses['restored']['agent_report']['verdict'] and
                            p['restored_caption'] == ('No mismatch in the tests Spark chose'
                                if p['restored_verdict'] == 'consistent' else None) and
                            p['operator_restored_and_rerun_consistent'] == (p['restored_verdict'] == 'consistent') and
                            p['native_diagnostic_repair_claim_overwritten'] is False and
                            p['post_diagnosis_workflow_correction'] is True,
                            'cancelled_reading_misreported_in_summary')
                else:
                    require(registered and scored and revealed and restored and 'restored' in diagnoses
                            and ('restored' in bound or waived is not None), 'incomplete_reading_pair')
                    if waived is not None:
                        require(p['both_state_photos_recorded'] is False and
                                p['restored_photo_not_repeated'] is True,
                                'waived_photo_reported_as_new_photo')
                    require(p['reading_outcome'] == scored['outcome'] and p['restored_verdict'] == diagnoses['restored']['agent_report']['verdict'],
                            'pair_summary_mismatch')
            elif ('forecast' in kind or 'prediction' in kind) and kind.endswith('_frozen'):
                raise ValueError('unsupported_frozen_prediction_kind')
        require(registered is not None, 'missing_reading_pair_registration')
        result['passed'] = True
    except (ValueError, OSError, UnicodeError, KeyError, TypeError, IndexError, AttributeError, OverflowError, RecursionError) as exc:
        result['error'] = re.sub(r'[^A-Za-z0-9_.:+-]', '_', str(exc))[:180] or type(exc).__name__
    return result


def runtime():
    root=Path(__file__).resolve().parents[2]
    sys.path.insert(0,str(root))
    from scripts import reading_experiment
    return reading_experiment


def restoration(record,report_file):
    old=runtime();log=old.open_pair(record,['awaiting_restoration_confirmation'])
    report=json.loads(Path(report_file).read_text())
    require(report.get('USB_off') is True and report.get('external_fault_removed') is True
            and report.get('mini_board_unchanged') is True and bool(report.get('operator_statement')),
            'actual_external_restoration_report_required')
    events=old.decode_events(log.file.read_bytes(),require_terminal=False)
    require(any(e['kind']=='operator_reading_cancelled' for e in events),'reading_not_cancelled')
    log.add('operator_restoration_confirmed',{'confirmed_by':'operator','USB_off':True,
        'restored_intended_design':True,'reading_isolation_reconnected':False,
        'reading_isolation_not_required':True,'new_diagnosis_context_required':True,
        'operator_statement':report['operator_statement'],'external_fault_removed':'Actual E30-E25 diode',
        'retained':'Mini R1/R2, D23-D25 REF extension, IN and instrument wiring; C30-A55 load absent.'})
    old.state(log,'awaiting_restored_setup')


def finish(record):
    old=runtime();log=old.open_pair(record,['awaiting_restored_photo'])
    events=old.decode_events(log.file.read_bytes(),require_terminal=False)
    require(any(e['kind']=='operator_reading_cancelled' for e in events),'reading_not_cancelled')
    require(not any(e['kind'] in ('reading_observed','reading_scored') for e in events),'unexpected_reading')
    verdict=log.control['restored_verdict']
    result={'schema':'benchmate.terminal_pair_reading_withdrawn.v1','cohort':old.COHORT,
        'source':'physical','official':True,'counted':True,'case_id':log.control['case_id'],'blind_test':False,
        'faulted_diagnosis':log.control['faulted_diagnosis'],
        'restored_diagnosis':log.control['restored_diagnosis'],
        'reading_outcome':'not_performed_no_discriminating_numeric_reading',
        'reading_performed':False,'reading_forecast_exercised':False,
        'reading_request_and_forecast_preserved':True,'reading_selection_Spark_requests_spent':1,
        'post_diagnosis_workflow_correction':True,'restored_verdict':verdict,
        'restored_caption':'No mismatch in the tests Spark chose' if verdict=='consistent' else None,
        'operator_restored_and_rerun_consistent':verdict=='consistent',
        'native_diagnostic_repair_claim_overwritten':False,'both_state_photos_recorded':False,
        'photo_scope':'Uploaded private documentary image; not used for diagnosis or reading score.'}
    old.save(log.path/'result.json',result);log.add('run_completed',result)
    old.update_index(log.path.name,status='completed',reading_outcome=result['reading_outcome'],restored_verdict=verdict)
    print(json.dumps({'record':str(log.path),**result}),flush=True)


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);s=p.add_subparsers(dest='action',required=True)
    a=s.add_parser('restoration');a.add_argument('record');a.add_argument('--operator-report',required=True)
    a=s.add_parser('finish');a.add_argument('record')
    a=s.add_parser('verify');a.add_argument('record');a.add_argument('--expected-head')
    args=p.parse_args(argv)
    if args.action=='restoration':restoration(args.record,args.operator_report);return 0
    if args.action=='finish':finish(args.record);return 0
    result=verify_pair(args.record,args.expected_head);print(legacy.format_result(result));return 0 if result['passed'] else 1


if __name__=='__main__':raise SystemExit(main())
