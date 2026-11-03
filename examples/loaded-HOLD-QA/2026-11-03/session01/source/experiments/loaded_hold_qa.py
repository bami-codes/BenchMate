#!/usr/bin/env python3
"""One bounded, loaded HOLD-only maintenance QA; not an official diagnosis."""
import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
import numpy as np
import serial
from serial.tools import list_ports
from benchmate.instrument import BootContinuity, validate_boot_id
from benchmate.physical_bench import PhysicalBench
from benchmate.records import Recorder

COUNT = 12
CONFIRMATION = ('I retained the loaded wiring with E30–A55 installed, kept the specimen '
                'and remaining instrument wiring unchanged, removed probes, and reconnected '
                'the same USB port after power off.')
NOTE = 'docs/2026-11-03-loaded-HOLD-QA-plan.md'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path, value):
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')


def check(bench, board, previous_boot):
    continuity = BootContinuity()
    bench._ping(board, continuity, 'loaded_QA_unarmed_PING', False)
    if continuity.boot_id == validate_boot_id(previous_boot):
        raise ValueError('New USB-off boot required; no ARM.')
    packet = bench._request(board, continuity, bench.config.arm_command(continuity.boot_id), 'loaded_QA_ARM', 15)
    if packet.get('type') != 'armed':
        raise ValueError('ARM not acknowledged; no HOLD.')
    bench._ping(board, continuity, 'loaded_QA_armed_PING', True)
    for index in range(COUNT):
        bench._hold(board, continuity, 'loaded_QA_HOLD_' + str(index + 1))
    bench._ping(board, continuity, 'loaded_QA_final_PING', True)
    return continuity.boot_id


def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest='command', required=True)
    a = sub.add_parser('plan')
    a.add_argument('--prepared', required=True)
    a.add_argument('--previous-boot-id', required=True)
    a.add_argument('--output', required=True)
    a = sub.add_parser('run')
    a.add_argument('--plan', required=True)
    a.add_argument('--operator-report', required=True)
    a.add_argument('--output', required=True)
    a.add_argument('--execute', action='store_true')
    args = p.parse_args()
    if args.command == 'plan':
        protocol = json.loads((Path(args.prepared) / 'protocol.json').read_text())
        sources = deepcopy(protocol['official_source_sha256'])
        for name in ('experiments/loaded_hold_qa.py', NOTE):
            sources[name] = sha(ROOT / name)
        plan = {'schema': 'benchmate.loaded_HOLD_QA.v1', 'protocol': protocol,
                'sources': sources, 'previous_boot_id': validate_boot_id(args.previous_boot_id),
                'HOLD_blocks_max': COUNT, 'frames_max': COUNT * 512,
                'serial_commands_max': 28, 'ARM_max': 1, 'CAPTURE_max': COUNT,
                'allowed_waveform': 'HOLD at REF only', 'SPARK_requests': 0,
                'diagnostic_training': False, 'counted_as_official_diagnosis': False,
                'k_correction': False, 'original_guards_unchanged': True,
                'automatic_retry': False, 'firmware_upload': False,
                'operator_confirmation': CONFIRMATION}
        for name, digest in sources.items():
            if sha(ROOT / name) != digest:
                raise ValueError('Source changed before plan: ' + name)
        out = Path(args.output)
        out.mkdir(parents=True, exist_ok=False)
        save(out / 'plan.json', plan)
        print(json.dumps({'plan': str(out / 'plan.json'), 'HOLD_blocks_max': COUNT,
                          'hardware_commands': 0, 'SPARK_requests': 0})); return
    if not args.execute:
        raise ValueError('Explicit --execute after operator choice required.')
    plan = json.loads(Path(args.plan).read_text())
    report = json.loads(Path(args.operator_report).read_text())
    if (report.get('verbatim') != CONFIRMATION or report.get('USB_off_wiring_confirmed') is not True
            or report.get('USB_connected') is not True or report.get('loaded_HOLD_QA_selected') is not True):
        raise ValueError('Exact loaded wiring confirmation and explicit QA choice required.')
    if plan['HOLD_blocks_max'] != COUNT or plan['operator_confirmation'] != CONFIRMATION:
        raise ValueError('Fixed QA plan changed.')
    for name, digest in plan['sources'].items():
        if sha(ROOT / name) != digest:
            raise ValueError('Source changed: ' + name)
    root = Path(args.output)
    root.mkdir(parents=True, exist_ok=False)
    save(root / 'plan.json', plan)
    save(root / 'operator-report.json', report)
    log = Recorder(root / 'stages', mode='loaded_HOLD_only_QA_not_diagnosis')
    log.add('loaded_HOLD_QA_plan', plan)
    bench = PhysicalBench(plan['protocol'], log, lambda *a: None,
                          initial_report=report, previous_boot_id=plan['previous_boot_id'])
    try:
        ports = [x for x in list_ports.comports()
                 if (x.vid, x.pid, x.serial_number) == tuple(plan['protocol']['USB_identity'])]
        if len(ports) != 1:
            raise ValueError('Expected Minima absent or ambiguous; no serial opened.')
        with serial.Serial(ports[0].device, 115200, timeout=5, write_timeout=2) as board:
            time.sleep(2)
            board.reset_input_buffer()
            boot = check(bench, board, plan['previous_boot_id'])
        means = np.array([x['means'] for x in bench.reference_means])
        result = {'passed': True, 'blocks': bench.capture_attempts, 'frames': bench.frames,
                  'raw_channel_block_mean_spans_mV': (np.ptp(means, axis=0) * 1000).tolist(),
                  'boot_id': boot, 'output_at_REF_confirmed': True,
                  'scope': 'Loaded constant-HOLD repeatability on this boot; no waveform/model validation',
                  'k_correction': False, 'SPARK_requests': 0,
                  'official_01_F01_failure_preserved': True}
        save(root / 'result.json', result)
        log.add('run_completed', result)
    except (Exception, KeyboardInterrupt) as exc:
        result = {'passed': False, 'error': str(exc) if isinstance(exc, ValueError) else type(exc).__name__,
                  'blocks': bench.capture_attempts, 'frames': bench.frames,
                  'output_at_REF_confirmed': False, 'SPARK_requests': 0,
                  'automatic_retry': False, 'official_01_F01_failure_preserved': True}
        save(root / 'result.json', result)
        log.add('run_failed', result)
        print(json.dumps({'record': str(log.path), **result}), flush=True)
        raise SystemExit(1)
    print(json.dumps({'record': str(log.path), **result}), flush=True)


if __name__ == '__main__':
    main()
