#!/usr/bin/env python3
"""Prepare, preregister, then explicitly run one official passive diagnosis."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys
import time
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from serial.tools import list_ports
from benchmate.agent import drive_agent
from benchmate.config import load_keys, redact
from benchmate.instrument import validate_boot_id
from benchmate.netlist_diagnosis.design import checked, digest
from benchmate.netlist_diagnosis.physical import operator_report
from benchmate.official_passive import Bench, Session, OfficialModel, PROMPT, prepare, POLICY_FILE
from benchmate.records import Recorder, canonical, decode_events, read_events

INDEX = Path('examples/official-runs/2026-11-03/index.json')
BUDGET = ROOT / '.private/official-api-budget.json'


def save(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n')


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT, text=True, stderr=subprocess.STDOUT).strip()


def load_prepared(directory):
    directory = Path(directory)
    design = checked(json.loads((directory / 'reviewed-design.json').read_text()))
    protocol = json.loads((directory / 'protocol.json').read_text())
    if protocol != prepare(design):
        raise ValueError('Prepared official protocol, sources or selection policy changed.')
    return design, protocol


def validate_assembly(design, initial, assembly):
    if initial != operator_report('initial_unloaded', fixture='unloaded', design_sha256=digest(design)):
        raise ValueError('Exact initial unloaded operator report required.')
    if (assembly.get('schema') != 'benchmate.operator_assembly_record.v1'
            or assembly.get('operator_confirmed') is not True
            or assembly.get('reviewed_design_sha256') != digest(design)
            or assembly.get('instrument_series_ohm') != 1000.
            or assembly.get('USB_off_wiring_confirmed') is not True
            or not isinstance(assembly.get('specimen_truth'), list) or not assembly['specimen_truth']):
        raise ValueError('Matching confirmed local assembly required before official allocation.')


def registration(record):
    return json.loads((Path(record) / 'official-registration.json').read_text())


def index_for(policy):
    if (ROOT / INDEX).exists():
        index = json.loads((ROOT / INDEX).read_text())
        if index['selection_policy_sha256'] != digest(policy):
            raise ValueError('Official selection policy changed.')
        return index
    return {'schema': 'benchmate.official_run_index.v1', 'cohort_plan_id': policy['cohort_plan_id'],
            'selection_policy_sha256': digest(policy), 'cohort_activated': True,
            'primary_selection': 'first_started_attempt_regardless_of_outcome',
            'slots': [{**slot, 'counted': False} for slot in policy['ordered_slots']]}


def update_index(run_id, **changes):
    index = json.loads((ROOT / INDEX).read_text())
    entry = next(s for s in index['slots'] if s['run_id'] == run_id)
    entry.update(changes)
    save(ROOT / INDEX, index)


def register(args):
    design, protocol = load_prepared(args.prepared)
    initial = json.loads(Path(args.initial_report).read_text())
    assembly = json.loads(Path(args.assembly_record).read_text())
    validate_assembly(design, initial, assembly)
    previous = validate_boot_id(args.previous_boot_id)
    events = read_events(args.preflight_run)
    preflight = events[-1]['payload']
    if (events[-1]['kind'] != 'run_completed' or preflight.get('armed') is not False
            or preflight.get('commands') != ['PING'] or preflight.get('stimuli') != 0
            or validate_boot_id(preflight['boot_id']) == previous):
        raise ValueError('Completed unarmed PING preflight on a new operator-connected boot required.')
    policy = json.loads((ROOT / POLICY_FILE).read_text())
    index = index_for(policy)
    slot = next(s for s in index['slots'] if s['slot_id'] == args.slot)
    case = next(c for c in policy['cases'] if c['case_id'] == slot['case_id'])
    if slot['run_id'] is not None or case['reviewed_design_sha256'] != digest(design):
        raise ValueError('Primary slot already assigned, or reviewed design mismatch.')
    if any(s['status'] != 'completed' for s in index['slots'] if s['order'] < slot['order']):
        raise ValueError('Earlier required slot is incomplete; no automatic bypass.')
    log = Recorder(args.output, mode='spark_physical_official_passive')
    run_id = log.path.name
    public = Path('examples/official-runs/2026-11-03/registrations') / (run_id + '.json')
    bound = {'schema': 'benchmate.official_run_binding.v1', 'run_id': run_id,
             'slot_id': slot['slot_id'], 'case_id': slot['case_id'], 'state': slot['state'],
             'cohort_plan_id': policy['cohort_plan_id'], 'official': True, 'counted': True,
             'pilot': False, 'excluded_from_evaluation': False, 'source': 'physical',
             'actor': 'muse_spark', 'selection_policy_sha256': digest(policy),
             'reviewed_design_sha256': digest(design), 'protocol_sha256': digest(protocol),
             'source_sha256': protocol['official_source_sha256'],
             'source_commit': git('rev-parse', 'HEAD'),
             'assigned_utc': datetime.now(timezone.utc).isoformat(),
             'first_paid_request_already_sent': False, 'first_stimulus_already_sent': False,
             'run_started_event_sha256': log.previous, 'public_registration': str(public)}
    save(log.path / 'official-registration.json', bound)
    save(log.path / 'protocol.json', protocol)
    save(log.path / 'reviewed-design.json', design)
    save(log.path / 'initial-operator-report.json', initial)
    save(log.path / 'operator-assembly-local-only.json', assembly)
    save(log.path / 'preflight.json', {'record': str(args.preflight_run), 'previous_boot_id': previous,
                                     'observed_unarmed_boot_id': preflight['boot_id']})
    for name in protocol['official_source_sha256']:
        target = log.path / 'source' / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((ROOT / name).read_bytes())
    log.add('official_run_bound', bound)
    log.add('operator_assembly_record_local_only', {'sha256': digest(assembly), 'transmitted_to_model': False})
    log.add('official_protocol_frozen', {'protocol_sha256': digest(protocol),
            'source_sha256': protocol['official_source_sha256'], 'official': True,
            'pilot': False, 'excluded_from_evaluation': False, 'k_correction': False})
    save(ROOT / public, bound)
    slot.update(run_id=run_id, status='registered', counted=True,
                registration_file=str(public), protocol_sha256=digest(protocol))
    save(ROOT / INDEX, index)
    print(json.dumps({'record': str(log.path), 'slot': args.slot, 'registration': str(public),
                      'index': str(INDEX), 'paid_calls': 0, 'hardware_commands': 0}), flush=True)


def reopen(record):
    record = Path(record)
    events = decode_events((record / 'events.jsonl').read_bytes(), require_terminal=False, include_hash=True)
    if events[-1]['kind'] != 'official_protocol_frozen':
        raise ValueError('Run has already started execution or is not an official registration.')
    log = Recorder.__new__(Recorder)
    log.path, log.file = record, record / 'events.jsonl'
    log.previous, log.sequence = events[-1]['sha256'], len(events)
    return log


def publish(log, bound, protocol, frozen, sha):
    if digest(frozen) != sha or protocol != prepare(json.loads((log.path / 'reviewed-design.json').read_text())):
        raise ValueError('Forecast, protocol or source mismatch before publication.')
    if git('branch', '--show-current') != 'main' or git('diff', '--cached', '--name-only'):
        raise ValueError('Clean index on main required for prediction publication.')
    if git('remote', 'get-url', 'origin') != 'https://github.com/bami-codes/BenchMate.git':
        raise ValueError('Unexpected publication destination.')
    (log.path / 'predictions-frozen.json').write_bytes(canonical(frozen) + b'\n')
    envelope = {'schema': 'benchmate.official_prediction_envelope.v1',
                'official': True, 'pilot': False, 'excluded_from_evaluation': False,
                'run_id': bound['run_id'], 'slot_id': bound['slot_id'],
                'cohort_plan_id': bound['cohort_plan_id'], 'protocol_sha256': digest(protocol),
                'source_sha256': protocol['official_source_sha256'],
                'prediction_sha256': sha, 'prediction': frozen}
    raw = canonical(envelope) + b'\n'
    if redact(raw.decode(), load_keys(ROOT / '.env')) != raw.decode():
        raise ValueError('Prediction secret scan failed.')
    relative = Path('examples/official-freezes/2026-11-03') / log.path.name / 'predictions.json'
    target = ROOT / relative
    target.parent.mkdir(parents=True, exist_ok=False)
    target.write_bytes(raw)
    git('add', '--', str(relative))
    if git('diff', '--cached', '--name-only') != str(relative):
        raise ValueError('Unexpected staged file during prediction freeze.')
    git('diff', '--cached', '--check')
    git('commit', '-m', 'Freeze official prediction before reserved physical capture')
    commit = git('rev-parse', 'HEAD')
    git('push', 'origin', 'HEAD:main')
    if git('ls-remote', 'origin', 'refs/heads/main').split()[0] != commit:
        raise ValueError('Remote prediction receipt not confirmed; no reserved stimulus.')
    return {'sha256': sha, 'published': True, 'remote': True, 'commit': commit,
            'url': f'https://github.com/bami-codes/BenchMate/blob/{commit}/{relative}'}


def intervention(log, design, fixture):
    request_id = uuid.uuid4().hex
    choice = 'connect_output_load' if fixture == 'output_load' else 'remove_output_load'
    instruction = ('Disconnect USB and wait for the power LED to go out. '
        + ('Connect' if fixture == 'output_load' else 'Remove')
        + ' only the large-board E30–A55 OUT-load jumper. Keep A55–C35 absent, '
        'B28–B35 1 kohm, A23–A45, I50–A4, D50–G50, B50–B23, the renewed GND '
        'return and the specimen unchanged. Remove probes and reconnect the same USB port.')
    response = log.path / ('operator-response-' + request_id + '.json')
    request = {'request_id': request_id, 'fixture': fixture, 'choice': choice,
               'instruction': instruction, 'response_file': str(response),
               'fixed_response': operator_report(choice, fixture=fixture, design_sha256=digest(design))}
    save(log.path / 'operator-request.json', request)
    log.add('operator_action_requested', request)
    print(json.dumps({'stage': 'awaiting_operator', 'request': request}), flush=True)
    deadline = time.monotonic() + 1800
    while not response.exists():
        if time.monotonic() > deadline:
            raise ValueError('Operator timeout; no implied confirmation.')
        time.sleep(.25)
    value = json.loads(response.read_text())
    if value.get('request_id') != request_id or value.get('report') != request['fixed_response']:
        raise ValueError('Exact pending fixed English report required.')
    return value['report']


def run(args):
    if not args.execute:
        raise ValueError('Explicit --execute after user authorization required.')
    record = Path(args.record)
    bound = registration(record)
    design = checked(json.loads((record / 'reviewed-design.json').read_text()))
    protocol = json.loads((record / 'protocol.json').read_text())
    initial = json.loads((record / 'initial-operator-report.json').read_text())
    assembly = json.loads((record / 'operator-assembly-local-only.json').read_text())
    validate_assembly(design, initial, assembly)
    if protocol != prepare(design) or bound['protocol_sha256'] != digest(protocol):
        raise ValueError('Registered protocol/source changed; no model or hardware access.')
    published = json.loads(git('show', 'HEAD:' + bound['public_registration']))
    if published != bound or git('ls-remote', 'origin', 'refs/heads/main').split()[0] != git('rev-parse', 'HEAD'):
        raise ValueError('Run registration must be committed and pushed before execution.')
    index = json.loads((ROOT / INDEX).read_text())
    if not any(s['run_id'] == bound['run_id'] and s['status'] == 'registered' for s in index['slots']):
        raise ValueError('Primary official slot is not registered or has already executed.')
    ports = [p for p in list_ports.comports() if (p.vid, p.pid, p.serial_number) == tuple(protocol['USB_identity'])]
    if len(ports) != 1:
        raise ValueError('Expected Minima absent or ambiguous; no paid call or port opened.')
    log = reopen(record)
    with (record / 'execution-started.json').open('x') as f:
        json.dump({'attempt_started': True, 'registration': bound['public_registration']}, f)
    update_index(bound['run_id'], status='running')
    preflight = json.loads((record / 'preflight.json').read_text())
    bench = Bench(protocol, log, lambda fixture: intervention(log, design, fixture),
                  design=design, initial_report=initial, approved=True,
                  previous_boot_id=preflight['previous_boot_id'],
                  preflight_boot_id=preflight['observed_unarmed_boot_id'])
    model = None
    print(json.dumps({'stage': 'started', 'record': str(log.path), 'slot_id': bound['slot_id']}), flush=True)
    try:
        session = Session(bench, log, design, lambda f, s: publish(log, bound, protocol, f, s))
        model = OfficialModel(prompt=PROMPT, tools=session.tools, log=log, effort='medium',
                              env_path=ROOT / '.env', budget_path=BUDGET, max_requests=8)
        result = model.sanitize({**drive_agent(session, model), **model.metadata(), 'official_run': bound})
        save(record / 'result.json', result)
        log.add('run_completed', result)
        update_index(bound['run_id'], status='completed', verdict=result['agent_report']['verdict'])
        print(json.dumps({'stage': 'completed', 'record': str(log.path), 'slot_id': bound['slot_id'],
                          'report': result['agent_report'], 'http_requests': result['http_requests']}), flush=True)
    except (Exception, KeyboardInterrupt) as exc:
        result = {'error': str(exc) if isinstance(exc, (ValueError, RuntimeError)) else type(exc).__name__,
                  'instrument': bench.metadata(), 'automatic_retry': False, 'official_run': bound,
                  **(model.metadata() if model else {})}
        if model:
            result = model.sanitize(result)
        save(record / 'result.json', result)
        log.add('run_failed', result)
        update_index(bound['run_id'], status='failed', error=result['error'])
        print(json.dumps({'stage': 'failed', 'record': str(log.path), **result}), flush=True)
        raise SystemExit(1)
    finally:
        if model:
            model.close()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest='command', required=True)
    a = sub.add_parser('prepare')
    a.add_argument('--reviewed-design', required=True)
    a.add_argument('--output', required=True)
    a = sub.add_parser('register')
    for name in ('prepared', 'slot', 'initial-report', 'assembly-record', 'previous-boot-id', 'preflight-run'):
        a.add_argument('--' + name, required=True)
    a.add_argument('--output', default=str(ROOT / 'runs/official'))
    a = sub.add_parser('run')
    a.add_argument('--record', required=True)
    a.add_argument('--execute', action='store_true')
    args = p.parse_args()
    if args.command == 'prepare':
        design = checked(json.loads(Path(args.reviewed_design).read_text()))
        out = Path(args.output)
        out.mkdir(parents=True, exist_ok=False)
        save(out / 'reviewed-design.json', design)
        save(out / 'protocol.json', prepare(design))
        print(json.dumps({'prepared': str(out), 'paid_calls': 0, 'hardware_commands': 0}))
    elif args.command == 'register':
        register(args)
    else:
        run(args)


if __name__ == '__main__':
    main()
