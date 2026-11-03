#!/usr/bin/env python3
"""One fixed, guarded QA after replacement of the existing board-GND lead.

No provider, firmware upload, fitting, retries or relaxed thresholds.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import time

import serial
from serial.tools import list_ports

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from benchmate.instrument import BootContinuity,validate_boot_id
from benchmate.physical_bench import PhysicalBench
from benchmate.records import Recorder


def confirmed(report):
    flags=['USB_off_wiring_confirmed','USB_connected','only_existing_Arduino_GND_lead_replaced','new_lead_continuity_checked','unloaded_DUT_retained']
    if any(report.get(k) is not True for k in flags) or not report.get('verbatim'):
        raise ValueError('Confirmed USB-off replacement of only the existing Arduino-GND lead required')
    if report.get('contacts')!=['Arduino GND','same existing blue GND rail contact']:
        raise ValueError('GND lead endpoint report does not match plan')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--plan',required=True);p.add_argument('--report',required=True)
    p.add_argument('--previous-boot-id',required=True);p.add_argument('--output',required=True)
    p.add_argument('--execute',action='store_true');a=p.parse_args()
    if not a.execute:raise ValueError('Explicit user-authorized --execute required')
    plan=json.loads(Path(a.plan).read_text());report=json.loads(Path(a.report).read_text());confirmed(report)
    validate_boot_id(a.previous_boot_id)
    if a.previous_boot_id!=plan['previous_boot_id']:raise ValueError('Previous boot does not match frozen maintenance plan')
    for n,h in plan['sources'].items():
        if hashlib.sha256((ROOT/n).read_bytes()).hexdigest()!=h:raise ValueError('Pinned source changed: '+n)
    protocol=plan['protocol']
    if hashlib.sha256((ROOT/'docs/2026-11-02-passive-pilot-amendment.md').read_bytes()).hexdigest()!=protocol['amendment_sha256']:
        raise ValueError('Original amendment changed')
    log=Recorder(a.output,mode='ground_return_lead_maintenance_QA_no_LLM_not_diagnosis')
    def save(n,v):(log.path/n).write_text(json.dumps(v,indent=2)+'\n')
    save('plan.json',plan);save('operator-report.json',report)
    for n in plan['sources']:
        target=log.path/'source'/n;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes((ROOT/n).read_bytes())
    log.add('ground_QA_plan',plan)
    bench=PhysicalBench(protocol,log,lambda *a:None,initial_report=report,previous_boot_id=a.previous_boot_id)
    try:
        ports=[x for x in list_ports.comports() if (x.vid,x.pid,x.serial_number)==tuple(protocol['USB_identity'])]
        if len(ports)!=1:raise ValueError('Expected Minima absent or ambiguous')
        with serial.Serial(ports[0].device,115200,timeout=5,write_timeout=2) as board:
            time.sleep(2);board.reset_input_buffer();continuity=BootContinuity()
            bench._ping(board,continuity,'ground_QA_initial_PING',False)
            if continuity.boot_id==a.previous_boot_id:raise ValueError('New boot not established after reported maintenance')
            ack=bench._request(board,continuity,bench.config.arm_command(continuity.boot_id),'ground_QA_ARM',15)
            if ack.get('type')!='armed':raise ValueError('ARM not acknowledged')
            for i in range(3):bench._hold(board,continuity,f'ground_QA_center_{i+1}')
            for name,amplitude in [('small',.2),('large',.5)]:
                settings={'kind':'step','samples':512,'period_us':500,'amplitude_v':amplitude}
                rows=bench._capture(board,continuity,'ground_QA_'+name,settings)
                bench._waveform_checks(rows,settings);bench._hold(board,continuity,'ground_QA_'+name+'_return')
            bench._ping(board,continuity,'ground_QA_final_PING',True)
        result={'passed':True,'paid_requests':0,'boot_id':continuity.boot_id,'output_at_REF_confirmed':True,
                'capture_attempts':bench.capture_attempts,'frames':bench.frames,'means_v':bench.reference_means,'not_diagnosis_or_holdout':True}
        save('result.json',result);log.add('run_completed',result)
    except (Exception,KeyboardInterrupt) as exc:
        result={'passed':False,'error':str(exc) if isinstance(exc,ValueError) else type(exc).__name__,
                'paid_requests':0,'capture_attempts':bench.capture_attempts,'frames':bench.frames,
                'means_v':bench.reference_means,'no_retry_or_rearm':True,'output_state_confirmed':False}
        save('result.json',result);log.add('run_failed',result)
        print(json.dumps({'record':str(log.path),**result}),flush=True);raise SystemExit(1)
    print(json.dumps({'record':str(log.path),**result}),flush=True)


if __name__=='__main__':main()
