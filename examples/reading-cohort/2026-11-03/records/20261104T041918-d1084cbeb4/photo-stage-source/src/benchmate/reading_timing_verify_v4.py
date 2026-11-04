"""Fresh-clone, stdlib-only verification of reading pairs and legacy runs."""
import argparse
import hashlib
import json
from pathlib import Path
import re

from . import verify as legacy
from .records import canonical
from .reading_rules import digest, validate_forecast, score_reading
from .reading_candidates_v3 import parse as parse_candidates

ROOT = Path(__file__).resolve().parents[2]


def require(ok, message):
    if not ok:
        raise ValueError(message)


def file_in(root, name):
    p = Path(name)
    require(not p.is_absolute() and '..' not in p.parts, 'unsafe_artifact_path')
    file = (root/p).resolve()
    require(file.is_relative_to(root.resolve()), 'artifact_outside_record')
    return file


def check_file(root, item):
    file = file_in(root, item['file'])
    require(hashlib.sha256(file.read_bytes()).hexdigest() == item['sha256'], 'artifact_hash_mismatch')
    return file


def chain(file, expected_head=None):
    events = []; head = '0'*64
    for line in Path(file).read_text().splitlines():
        e = json.loads(line, object_pairs_hook=legacy._object, parse_constant=legacy._constant)
        require(isinstance(e, dict) and set(e) == {'sequence', 'timestamp', 'kind', 'payload', 'previous_sha256', 'sha256'}, 'invalid_event_fields')
        require(type(e['sequence']) is int and e['sequence'] == len(events), 'event_sequence_mismatch')
        require(e['previous_sha256'] == head, 'previous_sha256_mismatch')
        require(digest({k: v for k, v in e.items() if k != 'sha256'}) == e['sha256'], 'event_sha256_mismatch')
        require(not events or events[-1]['kind'] not in ('run_completed', 'run_failed'), 'event_after_terminal')
        require(events or e['kind'] == 'run_started', 'missing_run_started')
        events.append(e); head = e['sha256']
    require(events and events[-1]['kind'] in ('run_completed', 'run_failed'), 'missing_terminal_event')
    if expected_head is not None:
        require(head == expected_head, 'expected_head_mismatch')
    return events


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
        candidate_choice = candidate_ids = None
        timing_scope = photo_scope = restored_scope = restored_documentary = None
        ports_sha = None
        for event in events:
            kind, p = event['kind'], event['payload']
            if kind == 'reading_pair_registered':
                require(registered is None and p['cohort'] == 'reading-assisted-v1', 'duplicate_or_unknown_registration')
                registered = p
            elif kind in ('case03_workflow_scope_frozen', 'reading_timing_backend_qualified', 'photo_candidate_stage_qualified'):
                scope = json.loads(check_file(root,p).read_text())
                for name,h in scope['source_sha256'].items():
                    require(hashlib.sha256(file_in(ROOT,name).read_bytes()).hexdigest()==h,'qualified_stage_source_changed')
                if kind=='case03_workflow_scope_frozen':
                    require(hashlib.sha256(file_in(ROOT,scope['timing_qualification']).read_bytes()).hexdigest()==scope['timing_qualification_sha256'],'common_timing_qualification_hash')
                if kind=='reading_timing_backend_qualified':timing_scope=scope
                if kind=='photo_candidate_stage_qualified':
                    require(not photos and observed is None,'photo_stage_qualified_after_photo_or_value')
                    photo_scope=scope
            elif kind=='pair_protocol_prepared':
                require(digest(json.loads((root/'prepared/protocol.json').read_text()))==p['sha256'],'prepared_protocol_hash')
            elif kind=='intended_design_operator_confirmed':
                require(json.loads((root/'reviewed-design.json').read_text())==p['reviewed_design'],'reviewed_design_artifact')
            elif kind=='operator_photo_ports_confirmed':
                check_file(root,p);ports_sha=p['sha256']
            elif kind == 'child_record_bound':
                file = check_file(root, p)
                require(p['file'] not in child_files, 'duplicate_child_record')
                child_files.add(p['file'])
                children = chain(file, p['head_sha256']); result['events'] += len(children)
                if p['kind'].startswith('terminal_diagnosis'):
                    c = legacy.verify_run(file, expected_head=p['head_sha256'])
                    require(c['passed'], 'child_diagnosis_'+str(c['error']))
                    if children[-1]['kind']=='run_completed':
                        require(any(e['kind']=='channel_timing_model_bound' and e['payload']['version']=='frame-anchored-channel-timing-v4' for e in children),'diagnosis_missing_v4_backend')
                    for key in ('forecasts', 'measurements', 'order_checks', 'prediction_files'):
                        result[key] += c[key]
                elif p['kind'] == 'reading_selection':
                    child_reading_choice = children[-1]['payload'].get('arguments')
                elif p['kind']=='body_candidates_v3':
                    require(children[-1]['kind']=='run_completed' and children[-1]['payload']['requests']==1,'candidate_child_incomplete')
                    candidate_choice=children[-1]['payload']['arguments']
                    tool=next(e['payload']['tool'] for e in children if e['kind']=='model_request_frozen')
                    candidate_ids=tool['parameters']['properties']['candidate_bodies']['items']['properties']['sam_body']['enum']
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
            elif kind=='candidate_request_inputs_frozen':
                require(photo_scope is not None and 'faulted' in decoded,'candidate_inputs_before_qualified_decode')
                for name,h in p['inputs'].items():
                    rel=name.split(registered['run_id']+'/',1)[1]
                    check_file(root,{'file':rel,'sha256':h})
                require(p['operator_ports_sha256']==ports_sha and p['operator_values_supplied'] is False,'candidate_port_or_value_context')
            elif kind=='body_candidates_proposed':
                tag=p['state'];require(tag=='faulted' and tag in decoded and tag not in proposals,'candidate_proposal_order')
                require(candidate_choice is not None and set(candidate_ids)<=set(decoded[tag]['bodies']),'candidate_ids_not_retained')
                receipt=parse_candidates(candidate_choice,candidate_ids)
                require(all(p[k]==v for k,v in receipt.items()) and p['chosen_by']=='muse_spark' and p['surface_values_read'] is False,'candidate_not_bound_to_raw_model')
                proposals[tag]=p
            elif kind=='restored_photo_scope_declared':
                require('restored' in diagnoses and diagnoses['restored']['agent_report']['verdict']=='consistent' and 'restored' not in photos and restored_scope is None,'restored_scope_after_photo_or_inconsistent')
                check_file(root,p)
                require(p['Spark_binding_requests']==0 and p['operator_value_requests']==0 and p['component_identity_claimed'] is False,'restored_scope_identity_claim')
                restored_scope=p
            elif kind=='restored_documentary_completed':
                require(restored_scope is not None and 'restored' in decoded and restored_documentary is None,'restored_documentary_before_scope_or_decode')
                check_file(root,{'file':p['manifest'],'sha256':p['sha256']})
                require(p['SAM_role']=='documentary_display_only' and p['Spark_binding_requests']==0 and p['operator_value_requests']==0 and p['component_identity_claimed'] is False,'documentary_fabricated_binding')
                require(photos['faulted']['sha256']!=photos['restored']['sha256'],'changed_board_photo_reused')
                restored_documentary=p
            elif kind == 'body_binding_proposed':
                require(p['state'] in decoded and p['state'] not in proposals, 'body_proposal_before_decode_or_duplicate')
                require(p['chosen_by'] == 'muse_spark', 'invalid_body_proposer')
                require(child_binding_choice == {k: p[k] for k in ('sam_body', 'reason')},
                        'body_proposal_not_bound_to_Spark_choice')
                child_binding_choice = None
                proposals[p['state']] = p
            elif kind == 'body_binding':
                tag = p['state']
                require(tag=='faulted' and photo_scope is not None and proposals[tag]['mapping_status']=='unique' and p['binding_version']=='candidate-kind-set-v3' and p['chosen_by']=='muse_spark', 'ambiguous_reference_or_operator_truth_label')
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
                        and 'restored' in decoded and restored_documentary is not None and timing_scope is not None and photo_scope is not None, 'incomplete_reading_pair')
                require(json.loads((root/'result.json').read_text())==p,'terminal_result_artifact')
                require(p['reading_outcome'] == scored['outcome'] and p['restored_verdict'] == diagnoses['restored']['agent_report']['verdict'],
                        'pair_summary_mismatch')
            elif ('forecast' in kind or 'prediction' in kind) and kind.endswith('_frozen'):
                raise ValueError('unsupported_frozen_prediction_kind')
        require(registered is not None, 'missing_reading_pair_registration')
        result['passed'] = True
    except (ValueError, OSError, UnicodeError, KeyError, TypeError, IndexError, AttributeError, OverflowError, RecursionError, StopIteration) as exc:
        result['error'] = re.sub(r'[^A-Za-z0-9_.:+-]', '_', str(exc))[:180] or type(exc).__name__
    return result


def verify_run(path, *, expected_head=None):
    # Dispatch without importing numpy, scipy, PIL, providers or serial.
    try:
        path = Path(path); file = path/'events.jsonl' if path.is_dir() else path
        if any(json.loads(line).get('kind') == 'reading_pair_registered' for line in file.read_text().splitlines()):
            return verify_pair(path, expected_head)
    except (OSError, ValueError, TypeError, AttributeError):
        pass
    return legacy.verify_run(path, expected_head=expected_head)


def main(argv=None):
    p = argparse.ArgumentParser(prog='python -m benchmate.reading_timing_verify_v4')
    p.add_argument('path'); p.add_argument('--expected-head')
    args = p.parse_args(argv)
    result = verify_run(args.path, expected_head=args.expected_head)
    print(legacy.format_result(result))
    return 0 if result['passed'] else 1
