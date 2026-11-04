"""Versioned W1 path reading and v3 photo stage around frozen diagnostics.

No diagnostic scheduler or electrical guard is changed. Stage sources are
published before the first follow-up model call or operator observation.
"""
import argparse
from copy import deepcopy
import json
from pathlib import Path
import shutil
import sys

from .records import decode_events
from .reading_rules import digest, make_forecast, score_reading, validate_forecast
from .reading_candidates_v3 import parse as parse_candidates

ROOT = Path(__file__).resolve().parents[2]
NOTE = 'docs/2026-11-04-wire-path-observable.md'
SOURCES = ('src/benchmate/reading_wire_stage.py', 'src/benchmate/reading_wire_catalog.py',
           'src/benchmate/reading_candidates_v3.py', 'tests/test_reading_wire_catalog.py',
           'tests/test_reading_wire_stage.py', NOTE)
ACTIVE = False


def runtime():
    sys.path.insert(0, str(ROOT))
    from scripts import reading_experiment
    return reading_experiment


def opened(record, phases):
    r = runtime()
    log = r.open_pair(record, phases)
    scope = json.loads((log.path / 'wire-stage-scope.json').read_text())
    for name, h in scope['source_sha256'].items():
        if r.sha(ROOT / name) != h:
            raise ValueError('Frozen wire-stage source changed: ' + name)
    return r, log, scope


def qualify(record):
    r = runtime()
    log = r.open_pair(record, ['awaiting_reading_selection'])
    if (log.path / 'wire-stage-scope.json').exists():
        raise ValueError('Wire stage already qualified; no overwrite.')
    original = json.loads((log.path / 'reading-catalog.json').read_text())
    design = json.loads((log.path / 'reviewed-design.json').read_text())
    child = log.path / log.control['faulted_diagnosis']
    events = decode_events((child / 'events.jsonl').read_bytes())
    training = [e['payload'] for e in events if e['kind'] == 'netlist_observation' and e['payload']['purpose'] == 'training']
    frozen = json.loads((child / 'predictions-frozen.json').read_text())
    result = json.loads((child / 'result.json').read_text())
    from .reading_wire_catalog import extend
    catalog = extend(original, design, frozen, result['verification'], training)
    if catalog is None:
        raise ValueError('No qualified literal series-wire replacement; do not invent a W1 reading.')
    r.save(log.path / 'wire-reading-catalog.json', catalog)
    scope = {'schema': 'benchmate.wire_path_reading_stage.v1',
        'source_sha256': {n: r.sha(ROOT / n) for n in SOURCES},
        'catalog_sha256': digest(catalog), 'parent_catalog_sha256': digest(original),
        'after_terminal_diagnosis': True, 'before_reading_selection': True,
        'before_photo_or_operator_reading': True, 'measurement_isolation': catalog['wire_reading_setup'],
        'candidate_binding_version': 'candidate-kind-set-v3', 'restored_extra_reading': False,
        'external_repair_unchanged_mini_photo_not_repeated': True,
        'public_manifest': str(r.PUBLIC / 'wire-qualifications' / log.path.name / 'scope.json')}
    r.save(log.path / 'wire-stage-scope.json', scope)
    r.save(ROOT / scope['public_manifest'], scope)
    r.save((ROOT / scope['public_manifest']).parent / 'catalog.json', catalog)
    for name in SOURCES:
        target = log.path / 'wire-stage-source' / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, target)
    log.add('wire_stage_qualified', {'file': 'wire-stage-scope.json',
        'sha256': r.sha(log.path / 'wire-stage-scope.json'), 'catalog_file': 'wire-reading-catalog.json',
        'catalog_sha256': r.sha(log.path / 'wire-reading-catalog.json'),
        'public_manifest': scope['public_manifest'], 'before_operator_observation': True})
    r.state(log, 'awaiting_wire_reading_selection')
    print(json.dumps({'scope': scope['public_manifest'], 'operator_reading_received': False, 'paid_calls': 0}))


def paid(r, log, scope, stage, execute):
    global ACTIVE
    r.committed(ROOT / scope['public_manifest'])
    r.start_stage(log, stage, execute)
    ACTIVE = True


def select(record, execute):
    r, log, scope = opened(record, ['awaiting_wire_reading_selection'])
    paid(r, log, scope, 'wire-reading-selection', execute)
    catalog = json.loads((log.path / 'wire-reading-catalog.json').read_text())
    from .agent import function_tool
    from .reading_transport import call
    prompt = '''Choose ONE intended component and quantity for a useful operator reading.
You choose the target, not the runner. The verified terminal model does not identify
where its series resistance resides. The supplied catalog contains bounded physical
placements, not truth. Prefer a reading whose explanation intervals differ; do not
request an unrelated fixed-value branch when its intervals are identical.
W physical_kind means a wire/path, with resistance as the numeric observable, not
a capacitor. Its reading keeps the path and contacts installed and disconnects all
three mini-board leads from the fixture; the DMM probes its free IN/OUT lead ends.
The operator chooses the source after forecasts are published. Markings do not
measure resistance and cannot distinguish an unconstrained printed nominal.
No photograph, operator value, assembly truth or earlier-case data is supplied.
Call request_reading once with a concise English reason.'''
    brief = {'components': catalog['components'], 'measurement_setup': catalog['wire_reading_setup'],
             'explanations': [{k: v for k, v in e.items() if k != 'model'} for e in catalog['explanations']]}
    tool = function_tool('request_reading', 'Choose one useful component/quantity before its reading.', {
        'component': {'type': 'string', 'enum': list(catalog['components'])},
        'quantity': {'type': 'string', 'enum': ['resistance', 'capacitance']}, 'reason': {'type': 'string'}})
    child, result = call([{'type': 'input_text', 'text': prompt + '\n' + json.dumps(brief)}],
                        tool=tool, output=log.path / 'wire-reading-selection', budget=r.BUDGET)
    r.linked(log, child, 'wire_reading_selection')
    args = result['arguments']
    if not isinstance(args, dict) or set(args) != {'component', 'quantity', 'reason'}:
        raise ValueError('Invalid reading choice; no retry.')
    request = {**args, 'chosen_by': 'muse_spark'}
    forecast = make_forecast(request, catalog, json.loads((ROOT / r.RULES).read_text()))
    ranges = [(x['low'], x['high']) for x in forecast['forecasts'] if x['source'] == 'operator_dmm']
    if len(set(ranges)) < 2:
        raise ValueError('Chosen reading cannot distinguish declared placements; do not spend an operator reading.')
    r.save(log.path / 'wire-reading-forecast.json', forecast)
    log.add('reading_requested', request)
    log.add('wire_reading_forecast_frozen', {'file': 'wire-reading-forecast.json',
        'sha256': r.sha(log.path / 'wire-reading-forecast.json'), 'forecast_sha256': digest(forecast)})
    publication = r.publish(log, forecast, 'wire-reading')
    log.add('wire_reading_forecast_publication', publication)
    r.state(log, 'awaiting_faulted_photo', requested_component=request['component'],
            reading_forecast_sha256=digest(forecast))
    print(json.dumps({'request': request, 'forecast': forecast, 'publication': publication}))


def bind(record, execute):
    r, log, scope = opened(record, ['awaiting_faulted_binding'])
    paid(r, log, scope, 'faulted-candidate-binding-v3', execute)
    from .reading_candidates_v3 import request as body_request
    from .reading_transport import call
    content, tool, ids, inventory = body_request(log.path, log.control['requested_component'])
    intended = json.loads((log.path / 'reviewed-design.json').read_text())
    content[0]['text'] += ('\nOperator-reviewed intended connections, including the name W1 for '
                          'the visible direct IN-OUT wire:\n' + json.dumps(intended['elements']))
    log.add('candidate_request_inputs_frozen', {'inputs': inventory, 'tool': tool,
        'intended_design_sha256': digest(intended), 'operator_values_supplied': False})
    child, result = call(content, tool=tool, output=log.path / 'photo-faulted/candidates-v3', budget=r.BUDGET)
    r.linked(log, child, 'body_candidates_v3')
    receipt = parse_candidates(result['arguments'], ids)
    proposal = {'state': 'faulted', 'component': log.control['requested_component'],
                'chosen_by': 'muse_spark', 'operator_confirmed': False,
                'surface_values_read': False, **receipt}
    r.save(log.path / 'photo-faulted/candidate-proposal.json', proposal)
    log.add('body_candidates_proposed', proposal)
    r.state(log, 'awaiting_wire_path_confirmation')
    print(json.dumps(proposal))


def confirm_path(record, report_file):
    r, log, _ = opened(record, ['awaiting_wire_path_confirmation'])
    report = json.loads(Path(report_file).read_text())
    if (report.get('mini_IN_OUT_ports_identified') is not True
            or type(report.get('accept_model_candidates')) is not bool
            or not isinstance(report.get('operator_verbatim'), str) or not report['operator_verbatim'].strip()):
        raise ValueError('Actual operator port/candidate confirmation required.')
    proposal = json.loads((log.path / 'photo-faulted/candidate-proposal.json').read_text())
    ids = [c['sam_body'] for c in proposal['candidate_bodies']] if report['accept_model_candidates'] else report.get('operator_candidate_ids', [])
    manifest = json.loads((log.path / 'photo-faulted/decoded/body-manifest.json').read_text())
    known = {c['id'] for c in manifest['components']}
    if not isinstance(ids, list) or len(set(ids)) != len(ids) or any(i not in known for i in ids):
        raise ValueError('Only existing body IDs may be confirmed; an empty unassigned set is allowed.')
    value = {'component': log.control['requested_component'], 'candidate_ids': ids,
        'candidate_chosen_by': 'muse_spark' if report['accept_model_candidates'] else 'operator',
        'candidate_operator_confirmed': report['accept_model_candidates'],
        'path_ports_identified_by': 'operator', 'mini_IN_OUT_ports_identified': True,
        'operator_verbatim': report['operator_verbatim'],
        'scope': 'Candidate bodies and the isolated mini-board port pair; no numeric value or unique body identity asserted.'}
    r.save(log.path / 'wire-path-confirmation.json', value)
    log.add('wire_path_confirmed', value)
    r.state(log, 'awaiting_wire_observation')


def observe(record, report_file, evidence=None):
    r, log, _ = opened(record, ['awaiting_wire_observation'])
    report = json.loads(Path(report_file).read_text())
    isolation = report['isolation']
    expected = {'USB_off': True, 'all_three_fixture_leads_disconnected': True,
                'W1_installed': True, 'R_C_installed': True, 'discharge_wait_completed': True,
                'DMM_across_free_IN_OUT_lead_ends': True}
    if isolation != expected:
        raise ValueError('Confirm whole-board isolation with W1/contacts retained, not a removed-wire-only reading.')
    from .known_design import sanitize_image
    raw, _ = sanitize_image(Path(evidence).read_bytes()) if evidence else ((log.path / 'photo-faulted/prepared/input.png').read_bytes(), None)
    image = log.path / 'reading-evidence.png'
    import hashlib
    observation = {**report['reading'], 'photo': {'file': 'reading-evidence.png',
                   'sha256': hashlib.sha256(raw).hexdigest()}}
    forecast = json.loads((log.path / 'wire-reading-forecast.json').read_text())
    score = score_reading(forecast, observation)
    with image.open('xb') as f:
        f.write(raw)
    log.add('wire_path_isolation_confirmed', {'setup': isolation, 'operator_verbatim': report['operator_verbatim'],
        'evidence_scope': 'operator supplied reading photograph' if evidence else 'existing board context only; numeric value is operator report, not image authentication'})
    log.add('reading_observed', observation)
    log.add('wire_reading_scored', score)
    r.save(log.path / 'wire-reading-observation.json', observation)
    r.save(log.path / 'wire-reading-score.json', score)
    r.state(log, 'awaiting_reveal' if score['outcome'] == 'one_explanation_remains' else 'awaiting_wire_reading_decision',
            reading_outcome=score['outcome'])
    print(json.dumps(score))


def close(record, report_file):
    r, log, _ = opened(record, ['awaiting_restored_photo'])
    report = json.loads(Path(report_file).read_text())
    if (report.get('mini_components_and_layout_unchanged') is not True
            or report.get('only_external_fault_removed') is not True
            or not isinstance(report.get('operator_statement'), str) or not report['operator_statement'].strip()):
        raise ValueError('Confirm actual unchanged mini board and external-only restoration.')
    scored = json.loads((log.path / 'wire-reading-score.json').read_text())
    if len(scored['fits']) != 1 or not scored['fits'][0].startswith('external_path:'):
        raise ValueError('This external-only photo waiver requires the supported external-path alternative.')
    photo = log.path / 'photo-faulted/prepared/input.png'
    log.add('restored_photo_not_repeated', {'reason': 'unchanged_mini_board_external_restoration',
        'operator_report': report, 'original_capture_sha256': r.sha(photo),
        'new_restored_photo': False, 'image_relabelled_as_restored': False,
        'new_SAM_requests': 0, 'new_binding_requests': 0})
    result = {'schema': 'benchmate.wire_path_pair_result.v1', 'case_id': log.control['case_id'],
        'source': 'physical', 'cohort': r.COHORT, 'blind_test': False,
        'faulted_diagnosis': log.control['faulted_diagnosis'], 'restored_diagnosis': log.control['restored_diagnosis'],
        'reading_outcome': log.control['reading_outcome'], 'restored_verdict': log.control['restored_verdict'],
        'restored_caption': 'No mismatch in the tests Spark chose' if log.control['restored_verdict'] == 'consistent' else None,
        'operator_restored_and_rerun_consistent': log.control['restored_verdict'] == 'consistent',
        'native_diagnostic_repair_claim_overwritten': False, 'original_fault_photo_retained': True,
        'restored_photo_not_repeated': True, 'SAM_identifies_component_values': False}
    r.save(log.path / 'result.json', result)
    log.add('run_completed', result)
    r.update_index(log.path.name, status='completed', reading_outcome=result['reading_outcome'],
                   restored_verdict=result['restored_verdict'], completion_method='qualified_wire_path_reading_candidate_v3_external_repair')
    print(json.dumps(result))


def verify(record):
    """Keyless stdlib integrity, bound decisions and recorded-order audit."""
    from .reading_verify import chain, check_file, require, legacy
    import re
    root = Path(record)
    answer = {'passed': False, 'events': 0, 'forecasts': 0, 'measurements': 0,
              'order_checks': 0, 'prediction_files': 0, 'error': None}
    try:
        events = chain(root / 'events.jsonl')
        answer.update(events=len(events), head_sha256=events[-1]['sha256'], run_status=events[-1]['kind'])
        registration = scope = catalog = request = forecast = publication = proposal = path = isolation = observed = score = seal = restored = waiver = None
        photos = {}; decoded = {}; children = {}; diagnoses = {}; choices = {}; binding_ids = None
        for event in events:
            k, p = event['kind'], event['payload']
            if k == 'reading_pair_registered':
                require(registration is None, 'duplicate_registration')
                registration = p
            elif k == 'case05_workflow_scope_frozen':
                require(not children and not diagnoses, 'setup_scope_after_intake')
                value = json.loads(check_file(root, p).read_text())
                for n, h in value['source_sha256'].items():
                    require(runtime_free_sha(ROOT / n) == h, 'setup_source_changed')
            elif k == 'child_record_bound':
                f = check_file(root, p)
                require(p['file'] not in children, 'duplicate_child')
                child = chain(f, p['head_sha256'])
                children[p['file']] = child
                answer['events'] += len(child)
                if p['kind'].startswith('terminal_diagnosis'):
                    result = legacy.verify_run(f, expected_head=p['head_sha256'])
                    require(result['passed'], 'diagnostic_child_' + str(result.get('error')))
                    for name in ('forecasts', 'measurements', 'order_checks', 'prediction_files'):
                        answer[name] += result[name]
                elif p['kind'] in ('wire_reading_selection', 'body_candidates_v3'):
                    require(child[-1]['kind'] == 'run_completed' and child[-1]['payload']['requests'] == 1, 'incomplete_single_request')
                    choices[p['kind']] = child[-1]['payload']['arguments']
                    if p['kind'] == 'body_candidates_v3':
                        tool = next(x['payload']['tool'] for x in child if x['kind'] == 'model_request_frozen')
                        binding_ids = tool['parameters']['properties']['candidate_bodies']['items']['properties']['sam_body']['enum']
            elif k == 'diagnosis_finished':
                child = children[p['record'] + '/events.jsonl']
                require(child[-1]['payload']['agent_report'] == p['agent_report'], 'report_mismatch')
                if p['state'] == 'restored': require(restored is not None, 'restored_before_operator')
                require(p['state'] not in diagnoses, 'duplicate_diagnosis')
                diagnoses[p['state']] = p
            elif k == 'wire_stage_qualified':
                require(scope is None and 'faulted' in diagnoses and request is None, 'qualification_order')
                scope = json.loads(check_file(root, p).read_text())
                catalog_file = check_file(root, {'file': p['catalog_file'], 'sha256': p['catalog_sha256']})
                catalog = json.loads(catalog_file.read_text())
                require(digest(catalog) == scope['catalog_sha256'], 'catalog_hash')
                require(catalog['reserved_OUT_used_for_intervals'] == 0, 'reserved_output_profile')
                for n, h in scope['source_sha256'].items():
                    require(runtime_free_sha(ROOT / n) == h, 'wire_source_changed')
                answer['order_checks'] += 1
            elif k == 'reading_requested':
                require(scope is not None and request is None, 'request_order')
                require({**choices['wire_reading_selection'], 'chosen_by': 'muse_spark'} == p, 'request_not_Spark')
                request = p
            elif k == 'wire_reading_forecast_frozen':
                require(request is not None and forecast is None and not photos, 'forecast_order')
                forecast = validate_forecast(json.loads(check_file(root, p).read_text()))
                rules = json.loads((ROOT / 'docs/2026-11-03-reading-rules.json').read_text())
                require(forecast == make_forecast(request, catalog, rules), 'forecast_not_from_catalog')
                require(digest(forecast) == p['forecast_sha256'], 'forecast_hash')
                answer['forecasts'] += 1; answer['prediction_files'] += 1
            elif k == 'wire_reading_forecast_publication':
                require(forecast is not None and publication is None and p['sha256'] == digest(forecast)
                        and p['published'] and p['remote'] and re.fullmatch('[0-9a-f]{40}', p['commit']), 'publication_order')
                publication = p; answer['order_checks'] += 1
            elif k == 'board_photo_received':
                require(publication is not None and p['state'] not in photos, 'photo_order')
                check_file(root, p)
                for item in p['artifacts']: check_file(root, item)
                photos[p['state']] = p
            elif k == 'bodies_decoded':
                require(p['state'] in photos and p['state'] not in decoded, 'decode_order')
                check_file(root, {'file': p['manifest'], 'sha256': p['sha256']})
                for item in p['artifacts']: check_file(root, item)
                decoded[p['state']] = p
            elif k == 'candidate_request_inputs_frozen':
                require('faulted' in decoded, 'candidate_inputs_before_decode')
                for name, h in p['inputs'].items():
                    rel = name.split(registration['run_id'] + '/', 1)[1]
                    check_file(root, {'file': rel, 'sha256': h})
            elif k == 'body_candidates_proposed':
                require('faulted' in decoded and proposal is None and p['component'] == request['component'], 'candidate_order')
                require(set(binding_ids) <= set(decoded['faulted']['bodies']), 'unretained_candidate_id')
                receipt = parse_candidates(choices['body_candidates_v3'], binding_ids)
                require(all(p[n] == v for n, v in receipt.items()) and p['chosen_by'] == 'muse_spark'
                        and p['surface_values_read'] is False, 'candidate_not_bound_to_model')
                proposal = p
            elif k == 'wire_path_confirmed':
                require(proposal is not None and path is None and p['mini_IN_OUT_ports_identified'], 'path_confirmation_order')
                if p['candidate_chosen_by'] == 'muse_spark':
                    require(p['candidate_ids'] == [c['sam_body'] for c in proposal['candidate_bodies']], 'operator_override_as_Spark')
                else: require(p['candidate_chosen_by'] == 'operator', 'path_assigner')
                require(set(p['candidate_ids']) <= set(decoded['faulted']['bodies']), 'unknown_confirmed_body')
                path = p; answer['order_checks'] += 1
            elif k == 'wire_path_isolation_confirmed':
                require(path is not None and isolation is None and all(v is True for v in p['setup'].values()), 'isolation_order')
                require(set(p['setup']) == {'USB_off', 'all_three_fixture_leads_disconnected', 'W1_installed', 'R_C_installed', 'discharge_wait_completed', 'DMM_across_free_IN_OUT_lead_ends'}, 'isolation_scope')
                isolation = p
            elif k == 'reading_observed':
                require(isolation is not None and observed is None and publication is not None, 'observation_order')
                check_file(root, p['photo']); observed = p
                answer['measurements'] += 1; answer['order_checks'] += 1
            elif k == 'wire_reading_scored':
                require(observed is not None and score is None and p == score_reading(forecast, observed), 'nondeterministic_score')
                score = p
            elif k == 'specimen_seal_opened':
                require(score is not None and score['outcome'] == 'one_explanation_remains' and seal is None, 'seal_order')
                prior = [x['payload'] for x in events[:event['sequence']] if x['kind'] == 'specimen_assembly_sealed' and x['payload']['state'] == 'faulted']
                require(len(prior) == 1 and digest(p['assembly']) == p['sealed_sha256'] == prior[0]['sha256'], 'assembly_seal_mismatch')
                seal = p; answer['order_checks'] += 1
            elif k == 'operator_restoration_confirmed':
                require(seal is not None and restored is None and p['USB_off'] and p['restored_intended_design'] and p['reading_isolation_reconnected'], 'restoration_order')
                restored = p
            elif k == 'restored_photo_not_repeated':
                require('restored' in diagnoses and waiver is None and p['operator_report']['mini_components_and_layout_unchanged']
                        and p['operator_report']['only_external_fault_removed'] and not p['new_restored_photo']
                        and not p['image_relabelled_as_restored'] and p['original_capture_sha256'] == photos['faulted']['sha256']
                        and len(score['fits']) == 1 and score['fits'][0].startswith('external_path:'), 'photo_waiver')
                waiver = p
            elif k == 'run_completed':
                require(registration and scope and score and seal and restored and waiver and 'restored' in diagnoses, 'incomplete_wire_pair')
                require(p['reading_outcome'] == score['outcome'] and p['restored_verdict'] == diagnoses['restored']['agent_report']['verdict'], 'summary_mismatch')
        require(registration is not None, 'missing_registration')
        answer['passed'] = True
    except (ValueError, OSError, KeyError, TypeError, IndexError, AttributeError, StopIteration) as exc:
        answer['error'] = str(exc)[:200]
    return answer


def runtime_free_sha(path):
    import hashlib
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('action', choices=['qualify', 'select', 'bind', 'confirm-path', 'observe', 'close', 'verify'])
    p.add_argument('record')
    p.add_argument('--execute', action='store_true')
    p.add_argument('--report')
    p.add_argument('--evidence')
    args = p.parse_args()
    if args.action == 'verify':
        result = verify(args.record)
        print(('PASS ' if result['passed'] else 'FAIL ') + json.dumps(result) + ' scope=internal_integrity+recorded_order creation_time=unproven')
        raise SystemExit(0 if result['passed'] else 1)
    try:
        if args.action == 'qualify': qualify(args.record)
        elif args.action == 'select': select(args.record, args.execute)
        elif args.action == 'bind': bind(args.record, args.execute)
        elif args.action == 'confirm-path': confirm_path(args.record, args.report)
        elif args.action == 'observe': observe(args.record, args.report, args.evidence)
        elif args.action == 'close': close(args.record, args.report)
    except (Exception, KeyboardInterrupt) as exc:
        if ACTIVE:
            r = runtime()
            phase = json.loads((Path(args.record) / 'state.json').read_text())['phase']
            log = r.open_pair(args.record, [phase])
            linked = {x['payload']['file'] for x in decode_events(log.file.read_bytes(), require_terminal=False) if x['kind'] == 'child_record_bound'}
            for f in sorted(log.path.rglob('events.jsonl')):
                if f != log.file and str(f.relative_to(log.path)) not in linked:
                    r.linked(log, f.parent, 'failed_stage_retained')
            log.add('run_failed', {'stage': args.action, 'automatic_retry': False, 'error_type': type(exc).__name__})
            r.update_index(log.path.name, status='failed', failed_stage=args.action)
        raise


if __name__ == '__main__':
    main()
