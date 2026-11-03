"""One separately frozen, three-HOLD recovery QA. No model, no waveform retry."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import time

from .records import Recorder, canonical, decode_events
from .reading_rules import digest
from .reading_verify import verify_run, chain

ROOT = Path(__file__).resolve().parents[2]
BASE_FREEZE = 'examples/reading-cohort/2026-11-03/freeze/manifest.json'
NOTE = 'docs/2026-11-03-reading-recovery-protocol.md'
COUNT = 3
WAIT = 10.
CONFIRMATION = ('I checked the restored R1 input/output columns with USB off, retained the '
                'unloaded fixture and remaining instrument wiring, removed probes, and '
                'reconnected the same USB port. I selected one bounded HOLD-only recovery QA.')


def save(file, value):
    file = Path(file); file.parent.mkdir(parents=True, exist_ok=True)
    file.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False)+'\n')


def sha(file):
    return hashlib.sha256(Path(file).read_bytes()).hexdigest()


def original_sources():
    value = json.loads((ROOT/BASE_FREEZE).read_text())['source_sha256']
    for name, expected in value.items():
        if sha(ROOT/name) != expected:
            raise ValueError('Original reading pipeline changed: '+name)
    return value


def make_plan(failed_pair, previous_boot, output):
    from .instrument import validate_boot_id
    pair = Path(failed_pair).resolve(); audited = verify_run(pair)
    if not audited['passed'] or audited['run_status'] != 'run_failed':
        raise ValueError('Complete verified failed pair required; never reopen its chain.')
    protocol = json.loads((pair/'prepared/protocol.json').read_text())
    sources = dict(original_sources())
    for name in ('src/benchmate/reading_recovery.py', NOTE):
        sources[name] = sha(ROOT/name)
    plan = {'schema': 'benchmate.reading_recovery_QA.v1', 'failed_pair': str(pair),
        'failed_pair_head_sha256': audited['head_sha256'],
        'previous_boot_id': validate_boot_id(previous_boot),
        'protocol': protocol, 'protocol_sha256': digest(protocol),
        'design': json.loads((pair/'reviewed-design.json').read_text()),
        'source_sha256': sources, 'HOLD_blocks_max': COUNT, 'frames_max': COUNT*512,
        'ARM_max': 1, 'serial_commands_max': 11, 'startup_wait_s': WAIT,
        'allowed_waveform': 'HOLD at existing REF only; no step or sine',
        'SPARK_requests': 0, 'SAM_requests': 0, 'estimated_usd': 0.,
        'firmware_upload': False, 'k_correction': False,
        'electrical_guard': 'Existing A3 primary 3mV and trusted-channel guards, unchanged',
        'firmware_settling': 'Existing A2 window/clip/settling conditions, unchanged',
        'operator_confirmation': CONFIRMATION, 'automatic_retry': False,
        'counted_as_official_diagnosis': False,
        'scope': 'Restored unloaded HOLD repeatability on one new boot, not diagnostic waveform validation.'}
    out = Path(output); out.mkdir(parents=True, exist_ok=False)
    save(out/'plan.json', plan)
    for name in sources:
        target = out/'source'/name; target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((ROOT/name).read_bytes())
    return plan


def validate_plan(plan):
    if (plan['schema'] != 'benchmate.reading_recovery_QA.v1' or plan['HOLD_blocks_max'] != COUNT
            or plan['ARM_max'] != 1 or plan['startup_wait_s'] != WAIT
            or plan['operator_confirmation'] != CONFIRMATION
            or digest(plan['protocol']) != plan['protocol_sha256']):
        raise ValueError('Frozen recovery plan changed.')
    original_sources()
    for name, expected in plan['source_sha256'].items():
        if sha(ROOT/name) != expected:
            raise ValueError('Frozen recovery source changed: '+name)
    old = verify_run(plan['failed_pair'], expected_head=plan['failed_pair_head_sha256'])
    if not old['passed'] or old['run_status'] != 'run_failed':
        raise ValueError('Original failed record changed.')
    if json.loads((Path(plan['failed_pair'])/'prepared/protocol.json').read_text()) != plan['protocol']:
        raise ValueError('Recovery must retain the failed run measurement protocol.')


def check(bench, board, previous_boot, *, monotonic=time.monotonic):
    from .instrument import BootContinuity, validate_boot_id
    c = BootContinuity()
    bench._ping(board, c, 'recovery_unarmed_PING', False)
    if c.boot_id == validate_boot_id(previous_boot):
        raise ValueError('Fresh unarmed USB boot required; no ARM.')
    bench.log.add('recovery_USB_wait_started', {'boot_id': c.boot_id, 'minimum_s': WAIT})
    started = monotonic(); bench.sleep(WAIT)
    bench._ping(board, c, 'recovery_after_wait_PING', False)
    elapsed = monotonic()-started
    if elapsed < WAIT:
        raise ValueError('Ten-second wait not reached; no ARM.')
    bench.log.add('recovery_USB_wait_completed', {'boot_id': c.boot_id, 'elapsed_s': elapsed})
    reply = bench._request(board, c, bench.config.arm_command(c.boot_id), 'recovery_ARM', 15)
    if reply.get('type') != 'armed':
        raise ValueError('ARM not acknowledged; no capture.')
    bench._ping(board, c, 'recovery_armed_PING', True)
    bench.boot_id = c.boot_id
    for index in range(COUNT):
        # Propagate the first error immediately. No loop around a failed block.
        bench._hold(board, c, 'recovery_HOLD_'+str(index+1))
    bench._ping(board, c, 'recovery_final_PING', True)
    return c.boot_id


def check_publication(plan_file):
    relative = str(Path(plan_file).resolve().relative_to(ROOT))
    def git(*args):
        return subprocess.check_output(['git', *args], cwd=ROOT, text=True, stderr=subprocess.STDOUT).strip()
    if git('show', 'HEAD:'+relative).encode() != Path(plan_file).read_bytes().rstrip(b'\n'):
        raise ValueError('Recovery plan must be committed before execution.')
    if git('ls-remote', 'origin', 'refs/heads/main').split()[0] != git('rev-parse', 'HEAD'):
        raise ValueError('Recovery plan must be pushed before execution.')


def run(plan_file, report_file, output, execute):
    if not execute:
        raise ValueError('Explicit operator-selected --execute required.')
    plan = json.loads(Path(plan_file).read_text()); validate_plan(plan); check_publication(plan_file)
    report = json.loads(Path(report_file).read_text())
    if report != {'verbatim': CONFIRMATION, 'USB_off_wiring_confirmed': True,
                  'USB_connected': True, 'fixture': 'unloaded', 'recovery_QA_selected': True}:
        raise ValueError('Actual operator wiring/check/reconnect confirmation required.')
    with (Path(plan_file).parent/'execution-started.json').open('x') as f:
        json.dump({'one_attempt': True, 'automatic_retry': False}, f)
    # Imports are delayed; verification never imports serial, providers or keys.
    import serial
    import numpy as np
    from serial.tools import list_ports
    from .a3_ref_guard import A3GuardMixin, VERSION
    from .physical_bench import PhysicalBench
    class Bench(A3GuardMixin, PhysicalBench):
        pass
    log = Recorder(output, mode='restored_three_HOLD_recovery_QA_not_diagnosis')
    save(log.path/'plan.json', plan); save(log.path/'operator-report.json', report)
    log.add('recovery_HOLD_QA_plan', plan)
    bench = Bench(plan['protocol'], log, lambda *a: None, initial_report=report,
                  previous_boot_id=plan['previous_boot_id'])
    try:
        ports = [p for p in list_ports.comports() if (p.vid, p.pid, p.serial_number) == tuple(plan['protocol']['USB_identity'])]
        if len(ports) != 1:
            raise ValueError('Expected Minima absent or ambiguous; no serial opened.')
        with serial.Serial(ports[0].device, 115200, timeout=5, write_timeout=2) as board:
            bench.sleep(2); board.reset_input_buffer()
            boot = check(bench, board, plan['previous_boot_id'])
        means = np.asarray([x['means'] for x in bench.reference_means])
        result = {'passed': True, 'blocks': bench.capture_attempts, 'frames': bench.frames,
            'boot_id': boot, 'guard_version': VERSION, 'raw_mean_spans_mV': (np.ptp(means,axis=0)*1000).tolist(),
            'output_at_REF_confirmed': True, 'SPARK_requests': 0, 'SAM_requests': 0,
            'automatic_retry': False, 'diagnostic_waveforms': 0, 'scope': plan['scope']}
        save(log.path/'result.json', result); log.add('run_completed', result)
    except (Exception, KeyboardInterrupt) as exc:
        packets = decode_events(log.file.read_bytes(), require_terminal=False)
        firmware = next((e['payload'].get('message') for e in reversed(packets)
                         if isinstance(e['payload'], dict) and e['payload'].get('type') == 'error'), None)
        result = {'passed': False, 'error': str(exc) if isinstance(exc,(ValueError,RuntimeError)) else type(exc).__name__,
            'firmware_error': firmware, 'blocks_attempted': bench.capture_attempts, 'frames': bench.frames,
            'output_at_REF_confirmed': False, 'SPARK_requests': 0, 'SAM_requests': 0,
            'automatic_retry': False, 'diagnostic_waveforms': 0}
        save(log.path/'result.json', result); log.add('run_failed', result)
    print(json.dumps({'record': str(log.path), **result}), flush=True)
    return result['passed']


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__); sub = p.add_subparsers(dest='command', required=True)
    q = sub.add_parser('plan'); q.add_argument('--failed-pair',required=True)
    q.add_argument('--previous-boot-id',required=True); q.add_argument('--output',required=True)
    q = sub.add_parser('run'); q.add_argument('--plan',required=True); q.add_argument('--operator-report',required=True)
    q.add_argument('--output',required=True); q.add_argument('--execute',action='store_true')
    q = sub.add_parser('verify'); q.add_argument('record')
    a = p.parse_args(argv)
    if a.command == 'plan':
        plan = make_plan(a.failed_pair,a.previous_boot_id,a.output)
        print(json.dumps({'plan':str(Path(a.output)/'plan.json'),'HOLD_blocks_max':COUNT,'ARM_max':1,
                          'SPARK_requests':0,'SAM_requests':0,'hardware_commands':0})); return 0
    if a.command == 'run':
        return 0 if run(a.plan,a.operator_report,a.output,a.execute) else 1
    events = chain(Path(a.record)/'events.jsonl')
    print(f"PASS events={len(events)} run_status={events[-1]['kind']} scope=internal_integrity creation_time=unproven")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
