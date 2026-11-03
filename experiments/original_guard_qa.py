#!/usr/bin/env python3
"""Uncorrected original-guard QA on the explicitly unchanged, already armed boot."""
from copy import deepcopy
import argparse
import hashlib
import json
from pathlib import Path
import sys
import time

import numpy as np
import serial
from serial.tools import list_ports

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from benchmate.instrument import BootContinuity,validate_boot_id
from benchmate.netlist_diagnosis.menu import MENU,RESERVED
from benchmate.physical_bench import PhysicalBench
from benchmate.records import Recorder

NAMES=['unloaded_step_small','unloaded_sine_1hz_large','unloaded_step_large',
       'unloaded_sine_1hz_small','unloaded_sine_5hz_small']
WAVES=[{'label':n,'settings':deepcopy(MENU[n])} for n in NAMES]+[
    {'label':f'validation_{i+1}','settings':deepcopy(s)} for i,s in enumerate(RESERVED)]
NOTE='docs/2026-11-03-original-guard-QA-plan.md'


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,v):p.write_text(json.dumps(v,indent=2,allow_nan=False)+'\n')


def check(bench,board,expected_boot):
    # No ARM, DC, reset, fit or adaptive retry. Unexpected state stops at PING.
    continuity=BootContinuity(validate_boot_id(expected_boot))
    bench._ping(board,continuity,'original_guard_initial_armed_PING',True)
    for i in range(3):bench._hold(board,continuity,f'original_guard_origin_{i+1}')
    for item in WAVES:
        settings={k:v for k,v in item['settings'].items() if k!='load_ohm'}
        rows=bench._capture(board,continuity,'original_guard_'+item['label'],settings)
        bench._waveform_checks(rows,settings)
        bench._hold(board,continuity,'original_guard_'+item['label']+'_return')
    bench._ping(board,continuity,'original_guard_final_PING',True)
    return continuity.boot_id


def main():
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='command',required=True)
    q=sub.add_parser('plan');q.add_argument('--prepared',required=True);q.add_argument('--expected-armed-boot',required=True);q.add_argument('--output',required=True)
    q=sub.add_parser('run');q.add_argument('--plan',required=True);q.add_argument('--authorization',required=True);q.add_argument('--output',required=True);q.add_argument('--execute',action='store_true')
    a=p.parse_args()
    if a.command=='plan':
        protocol=json.loads((Path(a.prepared)/'protocol.json').read_text());sources=dict(protocol['pilot_source_sha256'])
        for n in ('experiments/original_guard_qa.py',NOTE):sources[n]=sha(ROOT/n)
        plan={'schema':'benchmate.original-guard-QA.v1','protocol':protocol,'sources':sources,
            'expected_armed_boot':validate_boot_id(a.expected_armed_boot),'waves':WAVES,
            'initial_HOLDs':3,'return_HOLD_each':True,'maximum_blocks':17,'maximum_frames':8704,
            'k_fitted':False,'k_correction':False,'sample_RMS_threshold_added':False,
            'original_guards_unchanged':True,'scope':'Unloaded design-01 after only existing GND lead replacement; no parallel lead',
            'new_paid_requests':0,'firmware_upload':False,'rewiring':False,'manual_DMM':False,
            'automatic_retry_or_rearm':False,'previous_failures_reclassified':False}
        for n,h in sources.items():
            if sha(ROOT/n)!=h:raise ValueError('Pinned source changed: '+n)
        out=Path(a.output);out.mkdir(parents=True,exist_ok=False);save(out/'plan.json',plan)
        print(json.dumps({'plan':str(out/'plan.json'),'hardware_commands':0,'paid_requests':0}));return
    if not a.execute:raise ValueError('Explicit authorized --execute required')
    plan=json.loads(Path(a.plan).read_text());auth=json.loads(Path(a.authorization).read_text())
    if auth.get('original_uncorrected_QA_authorized') is not True or not auth.get('verbatim'):
        raise ValueError('Explicit original uncorrected QA authorization required')
    if plan['waves']!=WAVES:raise ValueError('Fixed waveforms changed')
    for n,h in plan['sources'].items():
        if sha(ROOT/n)!=h:raise ValueError('Pinned source changed: '+n)
    if sha(ROOT/'docs/2026-11-02-passive-pilot-amendment.md')!=plan['protocol']['amendment_sha256']:
        raise ValueError('Original hardware amendment changed')
    root=Path(a.output);root.mkdir(parents=True,exist_ok=False)
    save(root/'plan.json',plan);save(root/'authorization.json',auth)
    for n in plan['sources']:
        target=root/'source'/n;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes((ROOT/n).read_bytes())
    log=Recorder(root/'stages',mode='uncorrected_original_guard_QA_no_LLM_not_diagnosis')
    log.add('original_guard_QA_plan',plan)
    bench=PhysicalBench(plan['protocol'],log,lambda *a:None,initial_report=auth,previous_boot_id=plan['expected_armed_boot'])
    try:
        ports=[x for x in list_ports.comports() if (x.vid,x.pid,x.serial_number)==tuple(plan['protocol']['USB_identity'])]
        if len(ports)!=1:raise ValueError('Expected Minima absent or ambiguous')
        with serial.Serial(ports[0].device,115200,timeout=5,write_timeout=2) as board:
            time.sleep(2);board.reset_input_buffer();boot=check(bench,board,plan['expected_armed_boot'])
        means=np.asarray([x['means'] for x in bench.reference_means])
        result={'passed':True,'reference_guard':'original raw A4 block mean span <=3 mV',
            'raw_A3_block_mean_span_mV':float(np.ptp(means[:,2])*1000),
            'raw_A4_block_mean_span_mV':float(np.ptp(means[:,3])*1000),
            'frames':bench.frames,'capture_attempts':bench.capture_attempts,'means_v':bench.reference_means,
            'qualified_scope':'Current unloaded design-01; per-run guards remain required',
            'k_fitted':False,'k_correction':False,'physical_REF_stability_independently_established':False,
            'OUT_model_fitting_or_diagnostic_verification':False,'raw_OUT_safety_checks_retained':True,
            'boot_id':boot,'output_at_REF_confirmed':True,'paid_requests':0}
        save(root/'result.json',result);log.add('run_completed',result)
    except (Exception,KeyboardInterrupt) as exc:
        result={'passed':False,'error':str(exc) if isinstance(exc,ValueError) else type(exc).__name__,
            'frames':bench.frames,'capture_attempts':bench.capture_attempts,'means_v':bench.reference_means,
            'no_retry_or_rearm':True,'output_state_confirmed':False,'paid_requests':0}
        save(root/'result.json',result);log.add('run_failed',result)
        print(json.dumps({'record':str(log.path),**result}),flush=True);raise SystemExit(1)
    print(json.dumps({'root':str(root),'record':str(log.path),'passed':True,
        'raw_A3_span_mV':result['raw_A3_block_mean_span_mV'],'raw_A4_span_mV':result['raw_A4_block_mean_span_mV'],
        'frames':bench.frames,'k_correction':False,'output_at_REF_confirmed':True,'paid_requests':0}),flush=True)


if __name__=='__main__':main()
