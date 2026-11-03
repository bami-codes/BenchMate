#!/usr/bin/env python3
"""One prospective A3-primary waveform QA on the known already armed boot."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
import numpy as np
import serial
from serial.tools import list_ports
from benchmate.a3_ref_guard import A3GuardMixin, VERSION
from benchmate.instrument import BootContinuity, validate_boot_id
from benchmate.physical_bench import PhysicalBench
from benchmate.records import Recorder

spec = importlib.util.spec_from_file_location('preserved_original_QA', ROOT / 'experiments/original_guard_qa.py')
original = importlib.util.module_from_spec(spec); spec.loader.exec_module(original)


class Bench(A3GuardMixin, PhysicalBench):
    pass


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path, value):
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')


def check(bench, board, expected_boot):
    continuity = BootContinuity(validate_boot_id(expected_boot))
    bench._ping(board, continuity, 'A3_QA_observed_armed_PING', True)
    bench.log.add('QA_startup_wait_started', {'minimum_s': 10., 'ARM_during_wait': False})
    start = time.monotonic(); bench.sleep(10.)
    if time.monotonic() - start < 10.:
        raise ValueError('Startup wait too short; no capture.')
    bench.log.add('QA_startup_wait_completed', {'elapsed_monotonic_s': time.monotonic()-start})
    return original.check(bench, board, expected_boot)


def main():
    p = argparse.ArgumentParser(description=__doc__); sub = p.add_subparsers(dest='command', required=True)
    a = sub.add_parser('plan'); a.add_argument('--prepared', required=True)
    a.add_argument('--expected-armed-boot', required=True); a.add_argument('--output', required=True)
    a = sub.add_parser('run'); a.add_argument('--plan', required=True)
    a.add_argument('--authorization', required=True); a.add_argument('--output', required=True)
    a.add_argument('--execute', action='store_true'); args = p.parse_args()
    if args.command == 'plan':
        protocol = json.loads((Path(args.prepared) / 'protocol.json').read_text())
        sources = dict(protocol['official_source_sha256'])
        for name in ('src/benchmate/a3_ref_guard.py', 'experiments/a3_reference_qa.py',
                     'experiments/original_guard_qa.py', 'docs/2026-11-03-A3-REF-amendment.md'):
            sources[name] = sha(ROOT / name)
        plan = {'schema': 'benchmate.A3_REF_QA.v1', 'baseline_protocol': protocol,
                'effective_guard_version': VERSION, 'primary_REF_channel': 'A3',
                'A4_role': 'record_and_report_only', 'sources': sources,
                'expected_armed_boot': validate_boot_id(args.expected_armed_boot),
                'waves': original.WAVES, 'blocks_max': 17, 'frames_max': 8704,
                'serial_commands_max': 37, 'ARM_max': 0, 'startup_wait_s': 10.,
                'scope': 'Current unloaded design-01; existing wiring and firmware unchanged',
                'SPARK_requests': 0, 'k_correction': False, 'OUT_used_for_fitting': False,
                'F01_F02_failures_preserved': True}
        out = Path(args.output); out.mkdir(parents=True, exist_ok=False)
        save(out / 'plan.json', plan)
        print(json.dumps({'plan': str(out / 'plan.json'), 'hardware_commands': 0, 'SPARK_requests': 0})); return
    if not args.execute:
        raise ValueError('Explicit authorized --execute required.')
    plan = json.loads(Path(args.plan).read_text()); auth = json.loads(Path(args.authorization).read_text())
    if auth.get('A3_primary_QA_selected') is not True or auth.get('wiring_unchanged') is not True:
        raise ValueError('Operator A3 guard choice and unchanged wiring required.')
    if plan['waves'] != original.WAVES or plan['effective_guard_version'] != VERSION:
        raise ValueError('Pinned guard or waveforms changed.')
    for name, digest in plan['sources'].items():
        if sha(ROOT / name) != digest:
            raise ValueError('Pinned source changed: ' + name)
    out = Path(args.output); out.mkdir(parents=True, exist_ok=False)
    save(out / 'plan.json', plan); save(out / 'authorization.json', auth)
    for name in ('src/benchmate/a3_ref_guard.py', 'experiments/a3_reference_qa.py',
                 'experiments/original_guard_qa.py', 'docs/2026-11-03-A3-REF-amendment.md'):
        target = out / 'source' / name; target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((ROOT / name).read_bytes())
    log = Recorder(out / 'stages', mode='A3_primary_REF_QA_no_model_not_diagnosis')
    log.add('A3_primary_QA_plan', plan)
    bench = Bench(plan['baseline_protocol'], log, lambda *a: None, initial_report=auth,
                  previous_boot_id=plan['expected_armed_boot'])
    try:
        ports = [x for x in list_ports.comports()
                 if (x.vid, x.pid, x.serial_number) == tuple(plan['baseline_protocol']['USB_identity'])]
        if len(ports) != 1:
            raise ValueError('Expected Minima absent or ambiguous; no serial opened.')
        with serial.Serial(ports[0].device, 115200, timeout=5, write_timeout=2) as board:
            time.sleep(2); board.reset_input_buffer()
            boot = check(bench, board, plan['expected_armed_boot'])
        means = np.asarray([r['means'] for r in bench.reference_means])
        result = {'passed': True, 'guard_version': VERSION, 'primary_REF_channel': 'A3',
                  'A4_role': 'record_and_report_only', 'blocks': bench.capture_attempts,
                  'frames': bench.frames, 'raw_block_mean_spans_mV': (np.ptp(means, axis=0)*1000).tolist(),
                  'boot_id': boot, 'output_at_REF_confirmed': True, 'SPARK_requests': 0,
                  'scope': plan['scope'], 'k_correction': False, 'OUT_used_for_fitting': False}
        guards = [json.loads(line)['payload'] for line in log.file.read_text().splitlines()
                  if json.loads(line)['kind'] == 'physical_electrical_guard']
        result['A4_auxiliary_warning_blocks'] = sum(
            not all(g['A4_auxiliary'][k] for k in ('rails_ok', 'REF_envelope_ok', 'block_mean_span_3mV_ok'))
            for g in guards)
        save(out / 'result.json', result); log.add('run_completed', result)
    except (Exception, KeyboardInterrupt) as exc:
        result = {'passed': False, 'error': str(exc) if isinstance(exc, ValueError) else type(exc).__name__,
                  'guard_version': VERSION, 'blocks': bench.capture_attempts, 'frames': bench.frames,
                  'SPARK_requests': 0, 'automatic_retry': False, 'output_at_REF_confirmed': False}
        save(out / 'result.json', result); log.add('run_failed', result)
        print(json.dumps({'record': str(log.path), **result}), flush=True); raise SystemExit(1)
    print(json.dumps({'record': str(log.path), **result}), flush=True)


if __name__ == '__main__':
    main()
