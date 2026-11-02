#!/usr/bin/env python3
"""Isolated physical REF QA: one explicit ARM, ten fixed HOLD blocks, no LLM.

This is instrument maintenance, not a diagnosis, model fit or reserved test.
The preserved electrical/boot guards are used without changing their limits.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import time

import serial
from serial.tools import list_ports

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from benchmate.instrument import BootContinuity, validate_boot_id
from benchmate.netlist_diagnosis.design import checked, digest
from benchmate.passive_pilot import prepare, source_hashes
from benchmate.physical_bench import PhysicalBench
from benchmate.records import Recorder

BLOCKS = 10


def check_reference(bench, board, previous_boot):
    """Never retries or emits a STEP/SINE; a failed guard ends this check."""
    validate_boot_id(previous_boot)
    continuity = BootContinuity()
    bench._ping(board, continuity, 'reference_QA_initial_PING', False)
    if continuity.boot_id == previous_boot:
        raise ValueError('New boot required after reported USB-off maintenance')
    packet = bench._request(board, continuity, bench.config.arm_command(continuity.boot_id), 'reference_QA_ARM', 15)
    if packet.get('type') != 'armed':
        raise ValueError('ARM not acknowledged; no retry')
    bench._ping(board, continuity, 'reference_QA_armed_PING', True)
    bench.boot_id = continuity.boot_id
    for i in range(BLOCKS):
        bench._hold(board, continuity, f'reference_QA_HOLD_{i+1:02d}')
    bench._ping(board, continuity, 'reference_QA_final_PING', True)
    return continuity.boot_id


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--prepared', required=True)
    p.add_argument('--maintenance-report', required=True)
    p.add_argument('--previous-boot-id', required=True)
    p.add_argument('--output', required=True)
    p.add_argument('--execute', action='store_true')
    args = p.parse_args()
    if not args.execute:
        raise ValueError('User-authorized physical maintenance requires explicit --execute')
    directory = Path(args.prepared)
    design = checked(json.loads((directory/'reviewed-design.json').read_text()))
    protocol = json.loads((directory/'protocol.json').read_text())
    if protocol != prepare(design):
        raise ValueError('Frozen base protocol or sources changed')
    report = json.loads(Path(args.maintenance_report).read_text())
    if (report.get('operator_confirmed') is not True or report.get('USB_off_wiring_confirmed') is not True
            or report.get('USB_connected') is not True or report.get('spare_lead_continuity_checked') is not True
            or report.get('new_lead_contacts') != ['I50', 'Arduino A4']
            or report.get('specimen_or_instrument_values_changed') is not False):
        raise ValueError('Confirmed USB-off A4 lead replacement required')
    validate_boot_id(args.previous_boot_id)
    log = Recorder(args.output, mode='physical_reference_QA_HOLD_only_no_LLM')
    def save(name, value):
        (log.path/name).write_text(json.dumps(value, indent=2)+'\n')
    manifest = source_hashes()
    own = str(Path(__file__).resolve().relative_to(ROOT))
    manifest[own] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    save('protocol.json', protocol); save('maintenance-report.json', report)
    save('source-manifest.json', manifest)
    for name in manifest:
        target = log.path/'source'/name; target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((ROOT/name).read_bytes())
    log.add('reference_QA_plan', {'HOLD_blocks': BLOCKS, 'frames_per_block': 512,
            'period_us': 2000, 'target_code': 1376, 'paid_requests': 0,
            'STEP_or_SINE_commands': 0, 'diagnosis': False, 'source_sha256': manifest,
            'guard_thresholds_changed': False, 'operator_report_sha256': digest(report)})
    def no_rewire(*a, **k): raise ValueError('No wiring action is available during reference QA')
    bench = PhysicalBench(protocol, log, no_rewire, initial_report=report,
                          previous_boot_id=args.previous_boot_id)
    try:
        ports = [q for q in list_ports.comports() if (q.vid, q.pid, q.serial_number) == tuple(protocol['USB_identity'])]
        if len(ports) != 1:
            raise ValueError('Expected Minima absent or ambiguous; no port opened')
        with serial.Serial(ports[0].device, 115200, timeout=5, write_timeout=2) as board:
            time.sleep(2); board.reset_input_buffer()
            boot = check_reference(bench, board, args.previous_boot_id)
        result = {'passed': True, 'boot_id': boot, 'HOLD_blocks': BLOCKS,
                  'frames': bench.frames, 'means_v': bench.reference_means,
                  'last_confirmed_code': bench.config.ref_code, 'paid_requests': 0,
                  'STEP_or_SINE_commands': 0, 'not_a_diagnosis_or_holdout': True,
                  'new_USB_off_confirmation_required_before_frozen_pilot_CLI': True}
        save('result.json', result); log.add('run_completed', result)
        print(json.dumps({'record': str(log.path), **result}), flush=True)
    except (Exception, KeyboardInterrupt) as exc:
        result = {'passed': False, 'error': str(exc) if isinstance(exc, (ValueError, RuntimeError)) else type(exc).__name__,
                  'capture_attempts': bench.capture_attempts, 'frames': bench.frames,
                  'means_v': bench.reference_means, 'paid_requests': 0,
                  'automatic_retry': False, 'STEP_or_SINE_commands': 0}
        save('result.json', result); log.add('run_failed', result)
        print(json.dumps({'record': str(log.path), **result}), flush=True)
        raise SystemExit(1)


if __name__ == '__main__':
    main()
