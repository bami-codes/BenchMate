#!/usr/bin/env python3
"""Fixed instrument QA after D50--G50 bridge replacement; no provider or fitting.

Original PhysicalBench guards stop at the first failure. The sequence is an
instrument test, never a Spark-selected diagnosis or reserved validation run.
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
from benchmate.physical_bench import PhysicalBench
from benchmate.records import Recorder


def check(bench, board, previous_boot):
    validate_boot_id(previous_boot)
    continuity = BootContinuity()
    bench._ping(board, continuity, 'bridge_QA_initial_PING', False)
    if continuity.boot_id == previous_boot:
        raise ValueError('New boot required after USB-off bridge replacement')
    ack = bench._request(board, continuity, bench.config.arm_command(continuity.boot_id), 'bridge_QA_ARM', 15)
    if ack.get('type') != 'armed': raise ValueError('ARM not acknowledged; no retry')
    bench.boot_id = continuity.boot_id
    bench._ping(board, continuity, 'bridge_QA_armed_PING', True)
    for i in range(3): bench._hold(board, continuity, f'bridge_QA_center_{i+1}')
    for name, amplitude in [('small', .2), ('large', .5)]:
        settings = {'kind':'step','samples':512,'period_us':500,'amplitude_v':amplitude}
        rows = bench._capture(board, continuity, 'bridge_QA_'+name+'_step', settings)
        bench._waveform_checks(rows, settings)
        bench._hold(board, continuity, 'bridge_QA_'+name+'_return_REF')
    bench._ping(board, continuity, 'bridge_QA_final_PING', True)
    return continuity.boot_id


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--prepared', required=True); p.add_argument('--report', required=True)
    p.add_argument('--previous-boot-id', required=True); p.add_argument('--output', required=True)
    p.add_argument('--execute', action='store_true'); args = p.parse_args()
    if not args.execute: raise ValueError('Explicit authorized --execute required')
    protocol = json.loads((Path(args.prepared)/'protocol.json').read_text())
    report = json.loads(Path(args.report).read_text())
    for flag in ('USB_off_wiring_confirmed','USB_connected','only_D50_G50_replaced','new_jumper_continuity_checked'):
        if report.get(flag) is not True: raise ValueError('Operator confirmation missing: '+flag)
    if report.get('new_jumper_contacts') != ['D50','G50'] or not report.get('verbatim'):
        raise ValueError('Exact bridge replacement report required')
    validate_boot_id(args.previous_boot_id)
    sources = dict(protocol['pilot_source_sha256'])
    for name, expected in sources.items():
        if hashlib.sha256((ROOT/name).read_bytes()).hexdigest() != expected:
            raise ValueError('Pinned source changed: '+name)
    if hashlib.sha256((ROOT/'docs/2026-11-02-passive-pilot-amendment.md').read_bytes()).hexdigest() != protocol['amendment_sha256']:
        raise ValueError('Hardware amendment changed')
    own = str(Path(__file__).resolve().relative_to(ROOT)); sources[own] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    log = Recorder(args.output, mode='physical_REF_bridge_repair_QA_not_diagnosis_no_LLM')
    def save(name, value): (log.path/name).write_text(json.dumps(value,indent=2)+'\n')
    save('protocol.json',protocol); save('operator-report.json',report); save('source-manifest.json',sources)
    for name in sources:
        target = log.path/'source'/name; target.parent.mkdir(parents=True,exist_ok=True)
        target.write_bytes((ROOT/name).read_bytes())
    log.add('bridge_QA_plan', {'center_HOLD_blocks':3,'steps_V':[.2,.5],
        'step_samples':512,'step_period_us':500,'post_step_HOLD_each':True,
        'guard_thresholds_changed':False,'first_guard_failure_stops':True,'paid_requests':0,
        'firmware_upload':False,'fitting':False,'not_a_diagnosis_or_holdout':True})
    def no_rewire(*a,**k): raise ValueError('No rewiring during this fixed QA')
    bench = PhysicalBench(protocol,log,no_rewire,initial_report=report,previous_boot_id=args.previous_boot_id)
    try:
        ports = [x for x in list_ports.comports() if (x.vid,x.pid,x.serial_number)==tuple(protocol['USB_identity'])]
        if len(ports)!=1: raise ValueError('Expected Minima absent or ambiguous')
        with serial.Serial(ports[0].device,115200,timeout=5,write_timeout=2) as board:
            time.sleep(2); board.reset_input_buffer(); boot=check(bench,board,args.previous_boot_id)
        result={'passed':True,'boot_id':boot,'last_confirmed_code':bench.config.ref_code,'paid_requests':0,
                'capture_attempts':bench.capture_attempts,'frames':bench.frames,'means_v':bench.reference_means,
                'not_a_diagnosis_or_holdout':True,'output_at_REF_confirmed':True}
        save('result.json',result); log.add('run_completed',result)
    except (Exception,KeyboardInterrupt) as exc:
        result={'passed':False,'error':str(exc) if isinstance(exc,ValueError) else type(exc).__name__,
                'capture_attempts':bench.capture_attempts,'frames':bench.frames,'means_v':bench.reference_means,
                'paid_requests':0,'automatic_retry_or_rearm':False,'output_state_confirmed':False}
        save('result.json',result);log.add('run_failed',result)
        print(json.dumps({'record':str(log.path),**result}),flush=True);raise SystemExit(1)
    print(json.dumps({'record':str(log.path),**result}),flush=True)


if __name__=='__main__':main()
