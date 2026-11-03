#!/usr/bin/env python3
"""Versioned fixed-k conditional diagnosis using the existing Spark tool loop."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import time
import uuid
import serial
from serial.tools import list_ports

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from benchmate.agent import drive_agent
from benchmate.config import load_keys, redact
from benchmate.instrument import validate_boot_id, receive_response, BootContinuity
from benchmate.netlist_diagnosis.design import checked, digest
from benchmate.netlist_diagnosis.physical import operator_report
from benchmate.reproducibility_bench import FixedKPhysicalNetlistBench as PhysicalNetlistBench, validate_qualification
from benchmate.reproducibility_session import Session, PROMPT
from benchmate.ref_reproducibility import POLICY
from benchmate.passive_pilot import INSTRUMENT, prepare as base_prepare, source_hashes as base_source_hashes
import hashlib
from benchmate.providers import MetaToolSession
from benchmate.records import Recorder, canonical



EXTRA_SOURCES = ['src/benchmate/ref_reproducibility.py', 'src/benchmate/reproducibility_bench.py',
                 'src/benchmate/reproducibility_session.py', 'scripts/fixed_k_qa.py',
                 'scripts/fixed_k_pilot.py', 'docs/2026-11-03-fixed-k-repro-amendment.md']

def source_hashes():
    values = base_source_hashes()
    values.update({n: hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in EXTRA_SOURCES})
    return values


def prepare(design, candidate, qualification, cohort):
    validate_qualification(candidate, qualification)
    if qualification.get('source_sha256') != source_hashes():
        raise ValueError('Exact QA-qualified source manifest required')
    for n, h in qualification.get('source_sha256', {}).items():
        if hashlib.sha256((ROOT/n).read_bytes()).hexdigest() != h:
            raise ValueError('QA-qualified source changed: '+n)
    if cohort not in ('pilot', 'evaluation'): raise ValueError('Explicit cohort required')
    p = base_prepare(design)
    p.update(pilot=cohort=='pilot', excluded_from_evaluation=cohort=='pilot',
             pilot_runtime_version='fixed-k-conditional-v1', pilot_source_sha256=source_hashes())
    p['reference_reproducibility'] = {'policy': POLICY, 'candidate_sha256': digest(candidate),
        'qualification_sha256': digest(qualification), 'qualified_fixtures': qualification['qualified_fixtures'],
        'physical_REF_stability_established': False, 'IN_OUT_corrected': False}
    p['reference_scope'] += ' Fixed input-linked REF reproducibility mode, not proof of physical REF stability.'
    p['api_plan']['prompt'] = PROMPT
    return p


def save(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False)+'\n')


def publish(log, protocol, frozen, sha):
    if digest(frozen) != sha or source_hashes() != protocol['pilot_source_sha256']:
        raise ValueError('Forecast/source hash mismatch')
    def git(*args):
        return subprocess.check_output(['git', *args], cwd=ROOT, text=True, stderr=subprocess.STDOUT).strip()
    if git('branch', '--show-current') != 'main' or git('diff', '--cached', '--name-only'):
        raise ValueError('Clean index on main required before publication')
    if git('remote', 'get-url', 'origin') != 'https://github.com/bami-codes/BenchMate.git':
        raise ValueError('Unexpected publication destination')
    envelope = {'pilot': protocol['pilot'], 'excluded_from_evaluation': protocol['excluded_from_evaluation'],
                'reference_reproducibility': protocol['reference_reproducibility'], 'prediction_sha256': sha,
                'protocol_sha256': digest(protocol), 'source_sha256': protocol['pilot_source_sha256'],
                'instrument': INSTRUMENT, 'prediction': frozen}
    raw = canonical(envelope)+b'\n'
    if redact(raw.decode(), load_keys(ROOT/'.env')) != raw.decode():
        raise ValueError('Secret scan failed')
    relative = Path('examples/fixed-k-pilot-freezes')/log.path.name/'predictions.json'
    target = ROOT/relative; target.parent.mkdir(parents=True, exist_ok=False)
    target.write_bytes(raw)
    git('add', '--', str(relative))
    if git('diff', '--cached', '--name-only') != str(relative):
        raise ValueError('Unexpected staged file')
    git('diff', '--cached', '--check')
    git('commit', '-m', 'Freeze fixed-k conditional predictions before reserved measurements')
    commit = git('rev-parse', 'HEAD'); git('push', 'origin', 'HEAD:main')
    if git('ls-remote', 'origin', 'refs/heads/main').split()[0] != commit:
        raise ValueError('Remote publication receipt not established')
    return {'sha256': sha, 'published': True, 'remote': True, 'commit': commit,
            'url': f'https://github.com/bami-codes/BenchMate/blob/{commit}/{relative}'}


def intervention(log, design, fixture):
    request_id = uuid.uuid4().hex
    choice = 'connect_output_load' if fixture == 'output_load' else 'remove_output_load'
    instruction = ('Disconnect USB and wait for the power LED to go out. '
        + ('Connect' if fixture == 'output_load' else 'Remove')
        + ' only the large-board E30–A55 OUT-load jumper. Keep A55–C35 absent, '
        'the B28–B35 1 kohm resistor, B50–B23, D55–D60 load and C23–A60 REF return, '
        'and all specimen wiring unchanged. Remove probes and reconnect the same USB port.')
    response = log.path/f'operator-response-{request_id}.json'
    request = {'request_id': request_id, 'fixture': fixture, 'choice': choice,
               'instruction': instruction, 'response_file': str(response),
               'fixed_response': operator_report(choice, fixture=fixture, design_sha256=digest(design))}
    save(log.path/'operator-request.json', request)
    log.add('operator_action_requested', request)
    print(json.dumps({'stage': 'awaiting_operator', 'request': request}), flush=True)
    deadline = time.monotonic()+1800
    while not response.exists():
        if time.monotonic() > deadline:
            raise ValueError('Operator timeout; no implied confirmation')
        time.sleep(.25)
    value = json.loads(response.read_text())
    if value.get('request_id') != request_id or value.get('report') != request['fixed_response']:
        raise ValueError('Exact pending English choice required')
    return value['report']


def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest='command', required=True)
    a = sub.add_parser('prepare'); a.add_argument('--reviewed-design', required=True); a.add_argument('--output', required=True)
    a.add_argument('--candidate', required=True); a.add_argument('--qualification', required=True)
    a.add_argument('--cohort', choices=['pilot','evaluation'], default='pilot')
    a = sub.add_parser('probe'); a.add_argument('--prepared', required=True); a.add_argument('--execute', action='store_true')
    a.add_argument('--output', default=str(ROOT/'runs/passive-pilot-probe'))
    a = sub.add_parser('run'); a.add_argument('--prepared', required=True); a.add_argument('--initial-report', required=True)
    a.add_argument('--assembly-record', required=True)
    a.add_argument('--previous-boot-id', required=True); a.add_argument('--execute', action='store_true')
    a.add_argument('--output', default=str(ROOT/'runs/fixed-k-conditional'))
    args = p.parse_args()
    if args.command == 'prepare':
        design = checked(json.loads(Path(args.reviewed_design).read_text()))
        if design['operator_review_simulated']:
            raise ValueError('Real image review required')
        candidate = json.loads(Path(args.candidate).read_text()); qualification = json.loads(Path(args.qualification).read_text())
        protocol = prepare(design, candidate, qualification, args.cohort)
        out = Path(args.output); out.mkdir(parents=True, exist_ok=False)
        save(out/'candidate.json', candidate); save(out/'qualification.json', qualification)
        save(out/'reviewed-design.json', design); save(out/'protocol.json', protocol)
        print(json.dumps({'prepared': str(out), 'paid_calls': 0, 'hardware_commands': 0})); return
    if not args.execute:
        raise ValueError('Physical and paid execution needs explicit --execute after user authorization')
    directory = Path(args.prepared)
    design = checked(json.loads((directory/'reviewed-design.json').read_text()))
    protocol = json.loads((directory/'protocol.json').read_text())
    candidate = json.loads((directory/'candidate.json').read_text()); qualification = json.loads((directory/'qualification.json').read_text())
    cohort = 'pilot' if protocol['pilot'] else 'evaluation'
    if protocol != prepare(design, candidate, qualification, cohort):
        raise ValueError('Prepared protocol, sources or amendment changed')
    if args.command == 'probe':
        log = Recorder(args.output, mode='physical_passive_pilot_PING_only')
        try:
            ports = [p for p in list_ports.comports() if (p.vid, p.pid, p.serial_number) == tuple(protocol['USB_identity'])]
            if len(ports) != 1:
                raise ValueError('Expected Minima absent or ambiguous; no port opened')
            continuity = BootContinuity()
            with serial.Serial(ports[0].device, 115200, timeout=5, write_timeout=2) as board:
                time.sleep(2); board.reset_input_buffer()
                log.add('serial_command', {'request': 'PING', 'purpose': 'Read boot and firmware; no ARM or stimulus'})
                if board.write(b'PING\n') != 5:
                    raise ValueError('Incomplete PING write; no retry')
                packet = receive_response(board, log, 'preflight_PING')
                continuity.check(packet)
            if (packet.get('type') != 'pong' or packet.get('armed') is not False
                    or packet.get('current_code') != 0 or packet.get('ref_code') != 0
                    or packet.get('dc_hold_supported') is not True
                    or packet.get('adc_sample_state_channels') != [0, 1, 2, 21]
                    or packet.get('adc_sample_states_readback') != [255]*4):
                raise ValueError('Expected unarmed v2 firmware after confirmed USB-off setup; no re-arm')
            result = {'boot_id': continuity.boot_id, 'armed': False, 'commands': ['PING'], 'stimuli': 0}
            save(log.path/'result.json', result); log.add('run_completed', result)
            print(json.dumps({'record': str(log.path), **result})); return
        except (Exception, KeyboardInterrupt) as exc:
            log.add('run_failed', {'error': str(exc) if isinstance(exc, ValueError) else type(exc).__name__, 'automatic_retry': False})
            raise
    initial = json.loads(Path(args.initial_report).read_text())
    expected = operator_report('initial_unloaded', fixture='unloaded', design_sha256=digest(design))
    if initial != expected:
        raise ValueError('Exact initial unloaded English report required')
    assembly = json.loads(Path(args.assembly_record).read_text())
    if (assembly.get('schema') != 'benchmate.operator_assembly_record.v1'
            or assembly.get('operator_confirmed') is not True
            or assembly.get('reviewed_design_sha256') != digest(design)
            or assembly.get('instrument_series_ohm') != 1000.
            or assembly.get('USB_off_wiring_confirmed') is not True
            or not isinstance(assembly.get('specimen_truth'), list) or not assembly['specimen_truth']):
        raise ValueError('Matching confirmed local assembly truth and common 1 kohm instrument record required')
    validate_boot_id(args.previous_boot_id)
    ports = [p for p in list_ports.comports() if (p.vid, p.pid, p.serial_number) == tuple(protocol['USB_identity'])]
    if len(ports) != 1:
        raise ValueError('Expected Minima absent or ambiguous; no paid call or port opened')
    log = Recorder(args.output, mode='spark_fixed_k_conditional_'+cohort)
    save(log.path/'protocol.json', protocol); save(log.path/'reviewed-design.json', design)
    save(log.path/'initial-operator-report.json', initial)
    save(log.path/'operator-assembly-local-only.json', assembly)
    log.add('operator_assembly_record_local_only', {'sha256': digest(assembly), 'transmitted_to_model': False})
    for name in protocol['pilot_source_sha256']:
        target = log.path/'source'/name; target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((ROOT/name).read_bytes())
    log.add('pilot_protocol_frozen', {'protocol_sha256': digest(protocol), 'instrument': INSTRUMENT,
            'source_sha256': protocol['pilot_source_sha256'], 'specimen_truth_transmitted': False,
            'pilot': protocol['pilot'], 'excluded_from_evaluation': protocol['excluded_from_evaluation']})
    bench = PhysicalNetlistBench(protocol, log, lambda f: intervention(log, design, f),
                design=design, initial_report=initial, previous_boot_id=args.previous_boot_id, approved=True, candidate=candidate, qualification=qualification)
    model = None
    print(json.dumps({'stage': 'started', 'record': str(log.path)}), flush=True)
    try:
        # The only training-order selector is the actual model, never a script.
        session = Session(bench, log, design, lambda f, s: publish(log, protocol, f, s))
        model = MetaToolSession(prompt=PROMPT, tools=session.tools, log=log, effort='medium',
                    env_path=ROOT/'.env', budget_path=ROOT/'.private/api-budget.json', max_requests=8)
        result = model.sanitize({**drive_agent(session, model), **model.metadata(),
                                'pilot': protocol['pilot'], 'excluded_from_evaluation': protocol['excluded_from_evaluation']})
        save(log.path/'result.json', result); log.add('run_completed', result)
        print(json.dumps({'stage': 'completed', 'record': str(log.path),
                          'report': result['agent_report'], 'http_requests': result['http_requests']}), flush=True)
    except (Exception, KeyboardInterrupt) as exc:
        result = {'error': str(exc) if isinstance(exc, (ValueError, RuntimeError)) else type(exc).__name__,
                  'instrument': bench.metadata(), 'automatic_retry': False,
                  **(model.metadata() if model else {})}
        if model: result = model.sanitize(result)
        save(log.path/'result.json', result); log.add('run_failed', result)
        print(json.dumps({'stage': 'failed', 'record': str(log.path), **result}), flush=True)
        raise SystemExit(1)
    finally:
        if model: model.close()


if __name__ == '__main__':
    main()
