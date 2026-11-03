#!/usr/bin/env python3
"""Frozen reading-assisted experiments. Staged CLI; no implicit paid or serial IO."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT/'src')]
from scripts import official_passive_A3_v2 as preserved
from benchmate.reading_rules import digest, make_forecast, score_reading
from benchmate.records import Recorder, decode_events, canonical, read_events

COHORT = 'reading-assisted-v1'
PUBLIC = Path('examples/reading-cohort/2026-11-03')
POLICY = Path('docs/2026-11-03-reading-cohort-policy.json')
RULES = Path('docs/2026-11-03-reading-rules.json')
FREEZE = PUBLIC/'freeze/manifest.json'
INDEX = PUBLIC/'index.json'
BUDGET = ROOT/'.private/reading-cohort-api-budget.json'
MODEL_BUDGET = ROOT/'.private/official-api-budget.json'
ACTIVE_STAGE_STARTED = False
EXTRA = ('scripts/reading_experiment.py', 'src/benchmate/reading_rules.py',
         'src/benchmate/reading_catalog.py', 'src/benchmate/reading_transport.py',
         'src/benchmate/reading_photo.py', 'src/benchmate/reading_verify.py',
         'src/benchmate/__main__.py', str(POLICY), str(RULES),
         'docs/2026-11-03-reading-experiment-protocol.md', 'scripts/photo_raw.py')
save = preserved.base.save
git = preserved.base.git


def sha(file):
    return hashlib.sha256(Path(file).read_bytes()).hexdigest()


def freeze():
    p = preserved.prepare(json.loads((ROOT/'examples/reviewed-designs/2026-11-03-pilot/design-01.json').read_text()))
    from benchmate.photo_v2.pipeline import SOURCES
    sources = dict(p['official_source_sha256'])
    for name in set(EXTRA) | set(SOURCES):
        sources[name] = sha(ROOT/name)
    output = ROOT/FREEZE
    output.parent.mkdir(parents=True, exist_ok=False)
    manifest = {'schema': 'benchmate.reading_cohort_freeze.v1', 'cohort': COHORT,
        'source_sha256': sources, 'policy_sha256': digest(json.loads((ROOT/POLICY).read_text())),
        'rules_sha256': digest(json.loads((ROOT/RULES).read_text())),
        'new_physical_runs': 0, 'new_paid_calls': 0,
        'case01_known_to_developers': True, 'blind_test': False}
    save(output, manifest)
    for name in sources:
        target = output.parent/'source'/name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((ROOT/name).read_bytes())
    print(json.dumps({'frozen': str(FREEZE), 'sources': len(sources), 'API_calls': 0, 'hardware_commands': 0}))


def check_freeze():
    manifest = json.loads((ROOT/FREEZE).read_text())
    for name, expected in manifest['source_sha256'].items():
        if sha(ROOT/name) != expected:
            raise ValueError('Frozen source changed: '+name)
    return manifest


def committed(file):
    relative = str(Path(file).relative_to(ROOT)) if Path(file).is_absolute() else str(file)
    if git('show', 'HEAD:'+relative).encode() != (ROOT/relative).read_bytes().rstrip(b'\n'):
        raise ValueError('Required artifact is not committed: '+relative)
    head = git('rev-parse', 'HEAD')
    if git('ls-remote', 'origin', 'refs/heads/main').split()[0] != head:
        raise ValueError('Remote publication receipt missing.')
    return head


def index():
    return json.loads((ROOT/INDEX).read_text()) if (ROOT/INDEX).exists() else {
        'schema': 'benchmate.reading_cohort_index.v1', 'cohort': COHORT,
        'policy_sha256': digest(json.loads((ROOT/POLICY).read_text())), 'attempts': []}


def update_index(run, **changes):
    data = index()
    next(a for a in data['attempts'] if a['run_id'] == run).update(changes)
    save(ROOT/INDEX, data)


def state(log, phase, **data):
    old = getattr(log, 'control', {})
    log.control = {**old, **data, 'phase': phase}
    log.add('cohort_state', log.control)
    save(log.path/'state.json', log.control)
    print(json.dumps({'record': str(log.path), 'phase': phase}), flush=True)


def open_pair(path, phases):
    check_freeze()
    path = Path(path).resolve()
    if not path.is_relative_to((ROOT/'runs/reading-cohort').resolve()):
        raise ValueError('Use a local reading-cohort run folder.')
    events = decode_events((path/'events.jsonl').read_bytes(), require_terminal=False, include_hash=True)
    if events[-1]['kind'] in ('run_completed', 'run_failed'):
        raise ValueError('Terminal attempt; no automatic retry or rewriting.')
    control = next(e['payload'] for e in reversed(events) if e['kind'] == 'cohort_state')
    if control['phase'] not in phases:
        raise ValueError('Stage unavailable: '+control['phase'])
    # The preserved official runner only reopens its single pre-run state;
    # this staged parent resumes from its verified hash-chain head instead.
    log = Recorder.__new__(Recorder)
    log.path = path; log.file = path/'events.jsonl'
    log.previous = events[-1]['sha256']; log.sequence = len(events)
    log.control = control
    return log


def start_stage(log, stage, execute):
    global ACTIVE_STAGE_STARTED
    if execute is not True:
        raise ValueError('Explicit --execute required for paid/hardware stages.')
    committed(FREEZE)
    committed(PUBLIC/'registrations'/f'{log.path.name}.json')
    with (log.path/(stage+'-started.json')).open('x') as f:
        json.dump({'one_attempt': True, 'no_automatic_retry': True}, f)
    ACTIVE_STAGE_STARTED = True


def linked(log, run, kind):
    run = Path(run)
    relative = str(run.relative_to(log.path))
    events = decode_events((run/'events.jsonl').read_bytes(), include_hash=True)
    value = {'file': relative+'/events.jsonl', 'sha256': sha(run/'events.jsonl'),
             'head_sha256': events[-1]['sha256'], 'kind': kind}
    log.add('child_record_bound', value)
    return value


def publish(log, document, label):
    check_freeze()
    if git('branch', '--show-current') != 'main' or git('diff', '--cached', '--name-only'):
        raise ValueError('Clean index on main required before publication.')
    if git('remote', 'get-url', 'origin') != 'https://github.com/bami-codes/BenchMate.git':
        raise ValueError('Unexpected publication destination.')
    relative = PUBLIC/'predictions'/log.path.name/(label+'.json')
    target = ROOT/relative; target.parent.mkdir(parents=True, exist_ok=True)
    raw = canonical(document)+b'\n'
    if preserved.base.redact(raw.decode(), preserved.base.load_keys(ROOT/'.env')) != raw.decode():
        raise ValueError('Prediction secret scan failed.')
    with target.open('xb') as f:
        f.write(raw)
    git('add', '--', str(relative))
    if git('diff', '--cached', '--name-only') != str(relative):
        raise ValueError('Unexpected staged artifact.')
    git('diff', '--cached', '--check')
    git('commit', '-m', 'Freeze reading-cohort prediction before its observation')
    commit = git('rev-parse', 'HEAD'); git('push', 'origin', 'HEAD:main')
    if git('ls-remote', 'origin', 'refs/heads/main').split()[0] != commit:
        raise ValueError('Remote publication not confirmed; observation blocked.')
    return {'sha256': digest(document), 'published': True, 'remote': True, 'commit': commit,
            'url': f'https://github.com/bami-codes/BenchMate/blob/{commit}/{relative}'}


def begin(args):
    manifest = check_freeze(); commit = committed(FREEZE)
    policy = json.loads((ROOT/POLICY).read_text()); data = index()
    if data['policy_sha256'] != digest(policy) or args.case not in policy['case_order']:
        raise ValueError('Cohort policy mismatch.')
    previous = [a for a in data['attempts'] if a['case_id'] == args.case]
    if any(a['status'] not in ('completed', 'failed') for a in previous):
        raise ValueError('An attempt is already active.')
    for case in policy['case_order'][:policy['case_order'].index(args.case)]:
        if not any(a['case_id'] == case and a['status'] == 'completed' for a in data['attempts']):
            raise ValueError('Earlier required case pair is incomplete.')
    if args.case == '06':
        raise ValueError('Active physical path remains disabled pending separate DC qualification.')
    from benchmate.known_design import sanitize_image
    clean, info = sanitize_image(Path(args.schematic).read_bytes())
    log = Recorder(ROOT/'runs/reading-cohort', mode=COHORT)
    (log.path/'schematic.png').write_bytes(clean)
    registration = {'schema': 'benchmate.reading_pair_registration.v1', 'cohort': COHORT,
        'case_id': args.case, 'run_id': log.path.name, 'attempt': len(previous)+1,
        'official': True, 'counted': True, 'selected_first_attempt': not previous,
        'freeze_sha256': digest(manifest), 'freeze_commit': commit, 'schematic': info,
        'policy_sha256': digest(policy), 'blind_test': False,
        'known_case_development': args.case == '01', 'paid_calls_before_assignment': 0,
        'stimuli_before_assignment': 0}
    save(log.path/'registration.json', registration)
    save(ROOT/PUBLIC/'registrations'/f'{log.path.name}.json', registration)
    log.add('reading_pair_registered', registration)
    state(log, 'awaiting_schematic_intake', case_id=args.case)
    data['attempts'].append({'run_id': log.path.name, 'case_id': args.case,
        'attempt': len(previous)+1, 'status': 'registered', 'counted': True,
        'selected_first_attempt': not previous})
    save(ROOT/INDEX, data)


def intake(args):
    log = open_pair(args.record, ['awaiting_schematic_intake'])
    start_stage(log, 'intake', args.execute)
    from benchmate.netlist_intake import extract
    from benchmate.image_archive import verify_clean_png
    raw = (log.path/'schematic.png').read_bytes()
    run, result = extract(raw, verify_clean_png(raw), output=log.path/'schematic-intake',
        env_path=ROOT/'.env', budget_path=BUDGET)
    linked(log, run, 'schematic_intake')
    if result['status'] == 'failed':
        raise ValueError('Schematic intake failed; no automatic retry.')
    save(log.path/'schematic-result.json', result)
    state(log, 'awaiting_design_confirmation', schematic_intake=str(run.relative_to(log.path)))
    print(json.dumps(result['candidate']), flush=True)


def confirm_design(args):
    log = open_pair(args.record, ['awaiting_design_confirmation'])
    from benchmate.netlist_intake import reviewed
    from benchmate.netlist_diagnosis.design import CONFIRMATION
    result = json.loads((log.path/'schematic-result.json').read_text())
    design = reviewed(result, source_sha256=sha(log.path/'schematic.png'),
        confirmation=CONFIRMATION, note='Operator confirmed this fresh schematic transcription; no assembly value supplied.')
    save(log.path/'reviewed-design.json', design)
    log.add('intended_design_operator_confirmed', {'reviewed_design': design, 'confirmed_by': 'operator'})
    state(log, 'awaiting_faulted_setup')


def prepare(args):
    log = open_pair(args.record, ['awaiting_faulted_setup', 'awaiting_restored_setup'])
    design = json.loads((log.path/'reviewed-design.json').read_text())
    output = log.path/'prepared'
    output.mkdir(exist_ok=False)
    protocol = preserved.prepare(design)
    protocol.update(cohort_plan_id=COHORT, official_source_sha256=check_freeze()['source_sha256'],
        selection_policy_sha256=digest(json.loads((ROOT/POLICY).read_text())))
    save(output/'reviewed-design.json', design); save(output/'protocol.json', protocol)
    pilot = log.path/'probe-prepared'; pilot.mkdir()
    from benchmate.passive_pilot import prepare as probe_prepare
    save(pilot/'reviewed-design.json', design); save(pilot/'protocol.json', probe_prepare(design))
    log.add('pair_protocol_prepared', {'sha256': digest(protocol), 'hardware_commands': 0, 'paid_calls': 0})
    print(json.dumps({'prepared': str(output), 'probe_prepared': str(pilot)}))


def diagnose(args):
    faulted = args.state == 'faulted'
    log = open_pair(args.record, ['awaiting_faulted_setup'] if faulted else ['awaiting_restored_setup'])
    start_stage(log, args.state+'-diagnosis', args.execute)
    d = json.loads((log.path/'reviewed-design.json').read_text())
    protocol = json.loads((log.path/'prepared/protocol.json').read_text())
    if protocol['official_source_sha256'] != check_freeze()['source_sha256']:
        raise ValueError('Prepared source manifest differs from freeze.')
    initial = json.loads(Path(args.initial_report).read_text())
    assembly = json.loads(Path(args.assembly_record).read_text())
    preserved.base.validate_assembly(d, initial, assembly)
    preflight_events = read_events(args.preflight_run)
    preflight = preflight_events[-1]['payload']
    previous = preserved.validate_boot_id(args.previous_boot_id)
    if (preflight_events[-1]['kind'] != 'run_completed' or preflight.get('commands') != ['PING']
            or preflight.get('armed') is not False or preflight.get('stimuli') != 0
            or preserved.validate_boot_id(preflight['boot_id']) == previous):
        raise ValueError('Fresh unarmed PING-only preflight required before diagnosis.')
    save(log.path/(args.state+'-assembly-local-only.json'), assembly)
    log.add('specimen_assembly_sealed', {'state': args.state, 'sha256': digest(assembly), 'transmitted_to_model': False})
    child = Recorder(log.path/('diagnosis-'+args.state), mode='reading_cohort_physical_diagnosis')
    save(child.path/'protocol.json', protocol); save(child.path/'reviewed-design.json', d)
    child.add('reading_cohort_diagnosis_bound', {'cohort': COHORT, 'source': 'physical',
        'parent_run': log.path.name, 'state': args.state, 'guard_version': preserved.VERSION,
        'official': True, 'counted': True, 'protocol_sha256': digest(protocol)})
    log.add('diagnosis_started', {'state': args.state, 'record': str(child.path.relative_to(log.path))})
    model = None
    try:
        from serial.tools import list_ports
        ports = [p for p in list_ports.comports() if (p.vid, p.pid, p.serial_number) == tuple(protocol['USB_identity'])]
        if len(ports) != 1:
            raise ValueError('Expected Minima absent or ambiguous; no serial or paid request opened.')
        bench = preserved.SettledBench(protocol, child, lambda f: preserved.base.intervention(child, d, f),
            design=d, initial_report=initial, approved=True, previous_boot_id=previous,
            preflight_boot_id=preflight['boot_id'])
        def publish_prediction(frozen, expected):
            if digest(frozen) != expected:
                raise ValueError('Diagnostic forecast hash mismatch.')
            save(child.path/'predictions-frozen.json', frozen)
            return publish(child, frozen, 'terminal')
        session = preserved.Session(bench, child, d, publish_prediction)
        model = preserved.OfficialModel(prompt=preserved.PROMPT, tools=session.tools,
            log=child, effort='medium', env_path=ROOT/'.env', budget_path=MODEL_BUDGET, max_requests=8)
        result = model.sanitize({**preserved.base.drive_agent(session, model), **model.metadata()})
        save(child.path/'result.json', result); child.add('run_completed', result)
        linked(log, child.path, 'terminal_diagnosis')
        log.add('diagnosis_finished', {'state': args.state, 'record': str(child.path.relative_to(log.path)),
            'agent_report': result['agent_report'], 'http_requests': result['http_requests'],
            'output_at_REF': True, 'boot_id': bench.boot_id})
        if faulted:
            if not session.verification or not session.verification['survivors']:
                raise ValueError('No verified explanation; reading discrimination is unavailable.')
            from benchmate.reading_catalog import build_catalog
            rules = json.loads((ROOT/RULES).read_text())
            catalog = build_catalog(d, session.frozen, session.verification, session.training,
                nominal_tolerance=rules['nominal_tolerance_fraction'])
            save(log.path/'reading-catalog.json', catalog)
            log.add('reading_catalog_generated', {'sha256': digest(catalog), 'training_only_intervals': True})
            state(log, 'awaiting_reading_selection', faulted_diagnosis=str(child.path.relative_to(log.path)), last_boot=bench.boot_id)
        else:
            state(log, 'awaiting_restored_photo', restored_diagnosis=str(child.path.relative_to(log.path)),
                  restored_verdict=result['agent_report']['verdict'], last_boot=bench.boot_id)
    except (Exception, KeyboardInterrupt) as exc:
        events = decode_events(child.file.read_bytes(), require_terminal=False)
        if events[-1]['kind'] not in ('run_completed', 'run_failed'):
            child.add('run_failed', {'error': str(exc) if isinstance(exc, (ValueError, RuntimeError)) else type(exc).__name__,
                'automatic_retry': False, **(model.metadata() if model else {})})
            linked(log, child.path, 'terminal_diagnosis_failed')
        raise
    finally:
        if model:
            model.close()


def select_reading(args):
    log = open_pair(args.record, ['awaiting_reading_selection'])
    start_stage(log, 'reading-selection', args.execute)
    from benchmate.agent import function_tool
    from benchmate.reading_transport import call
    catalog = json.loads((log.path/'reading-catalog.json').read_text())
    brief = {'intended_components': catalog['components'], 'explanations': [
        {k: v for k, v in e.items() if k not in ('model',)} for e in catalog['explanations']]}
    prompt = '''You have completed terminal measurements and reserved checks.
Choose ONE intended component and ONE quantity for an operator reading that
best distinguishes the surviving bounded explanations. You choose, not the
runner. Explain which ambiguity it addresses. You have no photograph, operator
reading, assembly truth, case name, or previous-run evidence. Sources are chosen
by the operator after forecasts are frozen. Markings describe a printed nominal
value, NOT the actual electrical value; a damaged part can retain its old label.
An isolated power-off DMM resistance reading measures actual resistance. A
marking observation may leave explanations unresolved. Do not claim uniqueness
from lowest residual. Return request_reading once, concise English reason.'''
    tool = function_tool('request_reading', 'Choose one component/quantity before its reading or photo is received.', {
        'component': {'type': 'string', 'enum': list(catalog['components'])},
        'quantity': {'type': 'string', 'enum': ['resistance', 'capacitance']}, 'reason': {'type': 'string'}})
    run, result = call([{'type': 'input_text', 'text': prompt+'\n'+json.dumps(brief)}],
        tool=tool, output=log.path/'reading-selection', budget=BUDGET)
    linked(log, run, 'reading_selection')
    args_out = result['arguments']
    if not isinstance(args_out, dict) or set(args_out) != {'component', 'quantity', 'reason'}:
        raise ValueError('Invalid reading choice retained; no retry.')
    request = {**args_out, 'chosen_by': 'muse_spark'}
    rules = json.loads((ROOT/RULES).read_text())
    forecast = make_forecast(request, catalog, rules)
    log.add('reading_requested', request)
    save(log.path/'reading-forecast.json', forecast)
    log.add('reading_forecast_frozen', {**forecast, 'sha256': digest(forecast)})
    receipt = publish(log, forecast, 'reading')
    log.add('reading_forecast_publication', receipt)
    state(log, 'awaiting_faulted_photo', requested_component=request['component'],
          reading_forecast_sha256=digest(forecast))
    print(json.dumps({'request': request, 'forecast': forecast, 'publication': receipt}), flush=True)


def photo_prepare(args):
    log = open_pair(args.record, ['awaiting_faulted_photo', 'awaiting_restored_photo'])
    tag = 'faulted' if log.control['phase'] == 'awaiting_faulted_photo' else 'restored'
    if not args.new_capture_confirmed:
        raise ValueError('New actual-state photo capture attestation required; never reuse case1 pixels.')
    from benchmate.reading_photo import prepare as prepare_photo
    out = log.path/('photo-'+tag)/'prepared'
    plan = prepare_photo(args.image, out, check_freeze()['source_sha256'], digest(check_freeze()))
    old_policy = json.loads((ROOT/'examples/photo-v2/2026-11-03/frozen-v2-final/policy.json').read_text())
    if plan['input']['sha256'] in old_policy['source_development_images'] or plan['full']['sha256'] in old_policy['source_development_images']:
        raise ValueError('Known development photograph cannot be reused as a new actual-state capture.')
    log.add('board_photo_received', {'state': tag, 'file': str((out/'input.png').relative_to(log.path)),
        'sha256': plan['input']['sha256'], 'new_capture_operator_confirmed': True,
        'artifacts': [{'file': str((out/n).relative_to(log.path)), 'sha256': sha(out/n)}
                      for n in ('input.png', 'clean-full.png', 'plan.json')],
        'blind_test': False, 'surface_value_reading_enabled': False})
    state(log, 'awaiting_'+tag+'_segmentation', current_photo=tag)


def segment(args):
    log = open_pair(args.record, ['awaiting_faulted_segmentation', 'awaiting_restored_segmentation'])
    tag = log.control['current_photo']; start_stage(log, tag+'-SAM', args.execute)
    from benchmate.reading_photo import segment as do_segment
    p = log.path/('photo-'+tag)/'prepared'; result = do_segment(p, BUDGET)
    sam = json.loads((p/'sam-outcomes.json').read_text())[0]
    linked(log, p/sam['run'], 'SAM_localization')
    log.add('sam_localization_finished', {'state': tag, 'requests': result['requests'], 'status': result['status']})
    state(log, 'awaiting_'+tag+'_decode')


def decode(args):
    log = open_pair(args.record, ['awaiting_faulted_decode', 'awaiting_restored_decode'])
    tag = log.control['current_photo']
    from benchmate.reading_photo import decode as do_decode
    d = log.path/('photo-'+tag)
    result = do_decode(d/'prepared', d/'decoded')
    log.add('bodies_decoded', {'state': tag, 'manifest': str((d/'decoded/body-manifest.json').relative_to(log.path)),
        'sha256': sha(d/'decoded/body-manifest.json'), 'bodies': [c['id'] for c in result['components']],
        'artifacts': [{'file': str(f.relative_to(log.path)), 'sha256': sha(f)}
                      for f in sorted((d/'decoded').rglob('*')) if f.is_file()],
        'SAM_native_preserved': True, 'surface_reads': 0})
    state(log, 'awaiting_'+tag+'_binding')


def bind(args):
    log = open_pair(args.record, ['awaiting_faulted_binding', 'awaiting_restored_binding'])
    tag = log.control['current_photo']; start_stage(log, tag+'-body-binding', args.execute)
    from benchmate.reading_photo import binding_request
    run, proposal = binding_request(log.path/('photo-'+tag)/'decoded', log.path/'schematic.png',
        log.control['requested_component'], BUDGET, log.path/('photo-'+tag)/'binding')
    linked(log, run, 'body_binding')
    log.add('body_binding_proposed', {'state': tag, **proposal})
    save(log.path/('photo-'+tag)/'binding-proposal.json', proposal)
    state(log, 'awaiting_'+tag+'_body_confirmation')
    print(json.dumps(proposal), flush=True)


def confirm_body(args):
    log = open_pair(args.record, ['awaiting_faulted_body_confirmation', 'awaiting_restored_body_confirmation'])
    tag = log.control['current_photo']; d = log.path/('photo-'+tag)
    proposal = json.loads((d/'binding-proposal.json').read_text())
    if args.accept and proposal['sam_body'] is not None and not args.operator_body:
        binding = {**proposal, 'operator_confirmed': True}
    elif not args.accept and args.operator_body:
        bodies = json.loads((d/'decoded/body-manifest.json').read_text())['components']
        selected = next((b for b in bodies if b['id'] == args.operator_body), None)
        if selected is None:
            raise ValueError('Operator must select an existing retained body; no invented SAM mask.')
        binding = {**proposal, 'sam_body': selected['id'], 'chosen_by': 'operator',
            'reason': 'Operator assigned after Spark could not identify or operator rejected its proposed correspondence.',
            'operator_confirmed': True, 'localizer': selected['localizer']}
    else:
        raise ValueError('Confirm the actual proposal or explicitly assign an existing body.')
    log.add('body_binding', {'state': tag, **binding})
    save(d/'body-binding.json', binding)
    state(log, 'awaiting_reading_observation' if tag == 'faulted' else 'awaiting_pair_completion')


def observe(args):
    log = open_pair(args.record, ['awaiting_reading_observation'])
    from benchmate.known_design import sanitize_image
    supplied = json.loads(Path(args.observation).read_text())
    clean, _ = sanitize_image(Path(args.evidence).read_bytes())
    file = log.path/'reading-evidence.png'
    with file.open('xb') as f:
        f.write(clean)
    observation = {**supplied, 'photo': {'file': 'reading-evidence.png', 'sha256': sha(file)}}
    forecast = json.loads((log.path/'reading-forecast.json').read_text())
    scored = score_reading(forecast, observation)
    log.add('reading_observed', observation)
    log.add('reading_scored', scored)
    save(log.path/'reading-observation.json', observation); save(log.path/'reading-score.json', scored)
    state(log, 'awaiting_reveal', reading_outcome=scored['outcome'])
    print(json.dumps(scored), flush=True)


def reveal(args):
    log = open_pair(args.record, ['awaiting_reveal'])
    assembly = json.loads((log.path/'faulted-assembly-local-only.json').read_text())
    log.add('specimen_seal_opened', {'state': 'faulted', 'sealed_sha256': digest(assembly), 'assembly': assembly,
        'after_reading_score': True, 'transmitted_to_diagnosis': False})
    state(log, 'awaiting_restoration_confirmation')


def restoration(args):
    log = open_pair(args.record, ['awaiting_restoration_confirmation'])
    if not args.power_off_restored_confirmed:
        raise ValueError('Actual operator power-off restoration confirmation required.')
    log.add('operator_restoration_confirmed', {'confirmed_by': 'operator', 'USB_off': True,
        'restored_intended_design': True, 'reading_isolation_reconnected': True,
        'new_diagnosis_context_required': True})
    state(log, 'awaiting_restored_setup')


def finish(args):
    log = open_pair(args.record, ['awaiting_pair_completion'])
    result = {'cohort': COHORT, 'source': 'physical', 'official': True, 'counted': True,
        'case_id': log.control['case_id'], 'blind_test': False,
        'faulted_diagnosis': log.control['faulted_diagnosis'],
        'restored_diagnosis': log.control['restored_diagnosis'],
        'reading_outcome': log.control['reading_outcome'], 'restored_verdict': log.control['restored_verdict'],
        'restored_caption': 'No mismatch in the tests Spark chose' if log.control['restored_verdict'] == 'consistent' else None,
        'operator_restored_and_rerun_consistent': log.control['restored_verdict'] == 'consistent',
        'native_diagnostic_repair_claim_overwritten': False, 'both_state_photos_recorded': True}
    save(log.path/'result.json', result); log.add('run_completed', result)
    update_index(log.path.name, status='completed', reading_outcome=result['reading_outcome'],
                 restored_verdict=result['restored_verdict'])
    print(json.dumps({'record': str(log.path), **result}), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('freeze')
    p = sub.add_parser('begin'); p.add_argument('--case', required=True); p.add_argument('--schematic', required=True)
    commands = ('intake', 'confirm-design', 'prepare', 'diagnose', 'select-reading', 'photo-prepare',
                'segment', 'decode', 'bind', 'confirm-body', 'observe', 'reveal', 'restoration', 'finish')
    ps = {}
    for command in commands:
        p = sub.add_parser(command); p.add_argument('--record', required=True); ps[command] = p
    for command in ('intake', 'diagnose', 'select-reading', 'segment', 'bind'):
        ps[command].add_argument('--execute', action='store_true')
    p = ps['diagnose']; p.add_argument('--state', choices=['faulted', 'restored'], required=True)
    for name in ('initial-report', 'assembly-record', 'previous-boot-id', 'preflight-run'):
        p.add_argument('--'+name, required=True)
    ps['photo-prepare'].add_argument('--image', required=True)
    ps['photo-prepare'].add_argument('--new-capture-confirmed', action='store_true')
    ps['confirm-body'].add_argument('--accept', action='store_true')
    ps['confirm-body'].add_argument('--operator-body')
    ps['observe'].add_argument('--observation', required=True); ps['observe'].add_argument('--evidence', required=True)
    ps['restoration'].add_argument('--power-off-restored-confirmed', action='store_true')
    args = parser.parse_args()
    actions = {'freeze': lambda _: freeze(), 'begin': begin, 'intake': intake, 'confirm-design': confirm_design,
        'prepare': prepare, 'diagnose': diagnose, 'select-reading': select_reading, 'photo-prepare': photo_prepare,
        'segment': segment, 'decode': decode, 'bind': bind, 'confirm-body': confirm_body, 'observe': observe,
        'reveal': reveal, 'restoration': restoration, 'finish': finish}
    try:
        actions[args.command](args)
    except (Exception, KeyboardInterrupt) as exc:
        # Every paid/hardware failure is terminal; manual data-entry mistakes
        # before a paid stage are rejected without inventing an observation.
        if ACTIVE_STAGE_STARTED and args.command in ('intake', 'diagnose', 'select-reading', 'segment', 'bind'):
            try:
                log = open_pair(args.record, [p for p in (
                    'awaiting_schematic_intake', 'awaiting_faulted_setup', 'awaiting_restored_setup',
                    'awaiting_reading_selection', 'awaiting_faulted_segmentation', 'awaiting_restored_segmentation',
                    'awaiting_faulted_binding', 'awaiting_restored_binding')])
                linked_files = {e['payload']['file'] for e in decode_events(log.file.read_bytes(), require_terminal=False)
                                if e['kind'] == 'child_record_bound'}
                for child in sorted(log.path.rglob('events.jsonl')):
                    if child == log.file or str(child.relative_to(log.path)) in linked_files:
                        continue
                    try:
                        linked(log, child.parent, 'failed_stage_retained')
                    except ValueError:
                        pass
                log.add('run_failed', {'stage': args.command,
                    'error': str(exc) if isinstance(exc, (ValueError, RuntimeError)) else type(exc).__name__,
                    'automatic_retry': False})
                update_index(log.path.name, status='failed', failed_stage=args.command)
            except Exception:
                pass
        raise


if __name__ == '__main__':
    main()
