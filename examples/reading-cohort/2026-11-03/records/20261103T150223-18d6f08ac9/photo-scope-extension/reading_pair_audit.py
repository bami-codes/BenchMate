"""Additive pair audit: unchanged frozen reading audit plus prospective photo scope.

Copied from the preserved reading_verify.verify_pair; only an explicit,
before-intake declared external-restoration photo waiver is added. Original
sources and all diagnostic/reading score rules remain unchanged.
"""
import json
from pathlib import Path
import re
from .reading_verify import chain, check_file, require, legacy
from .reading_rules import digest, validate_forecast, score_reading

PHOTO_RULE = 'No repeat for unchanged mini-board configuration after external repair; original image keeps original capture state'

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
        workflow = waived = None
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
                    for key in ('forecasts', 'measurements', 'order_checks', 'prediction_files'):
                        result[key] += c[key]
                elif p['kind'] == 'reading_selection':
                    child_reading_choice = children[-1]['payload'].get('arguments')
                elif p['kind'] == 'body_binding':
                    child_binding_choice = children[-1]['payload'].get('arguments')
            elif kind == 'diagnosis_finished':
                require(p['state'] not in diagnoses, 'duplicate_diagnosis')
                require(p['record']+'/events.jsonl' in child_files, 'unbound_diagnosis_record')
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
                require(publication is not None and 'faulted' in bound and observed is None, 'reading_before_publication_or_binding_or_duplicate')
                check_file(root, p['photo'])
                observed = p; result['measurements'] += 1; result['order_checks'] += 1
            elif kind == 'reading_scored':
                require(observed is not None and scored is None, 'score_before_reading_or_duplicate')
                require(score_reading(frozen, observed) == p, 'reading_score_not_deterministic')
                scored = p; result['order_checks'] += 1
            elif kind == 'specimen_seal_opened':
                require(scored is not None and revealed is None, 'reveal_before_score_or_duplicate')
                require(digest(p['assembly']) == p['sealed_sha256'], 'seal_hash_mismatch')
                prior = [e['payload'] for e in events[:event['sequence']] if e['kind'] == 'specimen_assembly_sealed' and e['payload']['state'] == 'faulted']
                require(len(prior) == 1 and prior[0]['sha256'] == p['sealed_sha256'], 'seal_was_not_precommitted')
                revealed = p; result['order_checks'] += 1
            elif kind == 'operator_restoration_confirmed':
                require(revealed is not None and restored is None and p['USB_off'] is True
                        and p['restored_intended_design'] is True and p['reading_isolation_reconnected'] is True,
                        'restoration_before_reveal_or_unconfirmed')
                restored = p; result['order_checks'] += 1
            elif kind == 'run_completed':
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
