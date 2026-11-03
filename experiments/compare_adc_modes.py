#!/usr/bin/env python3
"""Explicit ADC maintenance comparison, never diagnosis, calibration or scoring.

Raw ADC-QA packets are logged unchanged. An explicit metadata adapter reuses
the frozen v2 row/boot/electrical validation; ordinary v2 tools reject this FW.
Only 3 mV reference failures are retained rather than ending this comparison.
Other bounds, timing, communication and ADC faults stop without retry.
"""
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
from benchmate.instrument import BootContinuity, validate_boot_id, receive_response, capture_command
from benchmate.physical_bench import PhysicalBench
from benchmate.records import Recorder

PROTOCOL='benchmate-instrument-adcqa-v1'
MODES=[0,1,2,0]
EXTRA=['experiments/compare_adc_modes.py','firmware/instrument_adcqa/instrument_adcqa.ino',
       'firmware/instrument_adcqa/adc_qa.h','firmware/instrument_adcqa/boot_identity.h',
       'docs/2026-11-03-adc-mode-comparison.md']


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def save(path,value):path.write_text(json.dumps(value,indent=2,allow_nan=False)+'\n')


def validation_view(packet,mode):
    if (packet.get('protocol')!=PROTOCOL or packet.get('adc_qa_mode')!=mode
        or packet.get('adc_qa_failed') is not False
        or packet.get('adc_qa_single_channel') is not (mode!=0)
        or packet.get('adc_qa_discard_per_channel')!=(1 if mode==2 else 0)):
        raise ValueError('Unexpected ADC QA firmware, mode or failed ADC; no next action')
    result={**packet,'protocol':'benchmate-instrument-v2'}
    if packet.get('type')=='capture':
        if packet.get('timestamp_semantics')!='adc_read_completion_us':
            raise ValueError('Unexpected ADC QA timing semantics')
        # Same stored completion offsets/row layout; not sampling apertures.
        result['timestamp_semantics']='analogRead_completion_us'
    return result


class QALog(Recorder):
    def __init__(self,*a,**k):self.last_guard=None;self.guards=[];super().__init__(*a,**k)
    def add(self,kind,payload):
        if kind=='physical_electrical_guard':self.last_guard=payload;self.guards.append(payload)
        return super().add(kind,payload)


class QABench(PhysicalBench):
    def __init__(self,*a,**k):super().__init__(*a,**k);self.mode=0;self.last_raw=None
    def _request(self,board,continuity,command,label,timeout=5):
        self.log.add('serial_command',{'request':command.decode().strip(),'label':label})
        board.timeout=timeout
        if board.write(command)!=len(command):raise ValueError('Incomplete write; no retry')
        raw=receive_response(board,self.log,label);view=validation_view(raw,self.mode)
        continuity.check(view)
        if raw.get('type')=='capture':self.last_raw=raw
        return view
    def qa_capture(self,board,continuity,label,settings):
        try:rows=self._capture(board,continuity,label,settings)
        except ValueError as exc:
            guard=self.log.last_guard or {};failed={k for k,v in guard.get('checks',{}).items() if not v}
            allowed={'A4_block_mean_span','stationary_path_mean_span'}
            if (str(exc)!='Electrical/reference guard failed; no next stimulus'
                or guard.get('label')!=label or not failed or not failed<=allowed):raise
            self.log.add('QA_reference_failure_retained',{'label':label,'failed_checks':sorted(failed),
                'threshold_mV':3.,'diagnosis_use_allowed':False,'planned_mode_comparison_only':True})
            rows=np.asarray(self.last_raw['rows'])
        if settings['kind']=='step':
            n=settings['samples'];period=settings['period_us']
            amplitude=int(capture_command(self.config,boot_id=continuity.boot_id,**settings).split()[5])
            expected=np.full(n,self.config.ref_code+amplitude)
            expected[:n//10]=self.config.ref_code-amplitude
            checks={'frame_schedule':bool((abs(rows[:,0]-np.arange(n)*period)<=25).all()),
                    'read_completion_within_frame':bool((rows[:,6:10]<period).all()),
                    'DAC_codes':bool((rows[:,1]==expected).all())}
            self.log.add('ADC_QA_timing_and_code',{'label':label,'checks':checks,
                'read_completion_us_median':np.median(rows[:,6:10],axis=0).tolist()})
            if not all(checks.values()):raise ValueError('ADC QA timing/code check failed')
        return rows


def main():
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='command',required=True)
    q=sub.add_parser('plan');q.add_argument('--prepared',required=True);q.add_argument('--binary',required=True)
    q.add_argument('--rollback-binary',required=True);q.add_argument('--output',required=True)
    q=sub.add_parser('execute');q.add_argument('--plan',required=True);q.add_argument('--authorization',required=True)
    q.add_argument('--previous-boot-id',required=True);q.add_argument('--output',required=True);q.add_argument('--execute',action='store_true')
    a=p.parse_args()
    if a.command=='plan':
        protocol=json.loads((Path(a.prepared)/'protocol.json').read_text())
        sources=dict(protocol['pilot_source_sha256']);sources.update({n:sha(ROOT/n) for n in EXTRA})
        for n,h in sources.items():
            if sha(ROOT/n)!=h:raise ValueError('Pinned source changed: '+n)
        plan={'schema':'benchmate.adc-mode-QA.v1','protocol':protocol,'sources':sources,
              'binary_path':a.binary,'binary_sha256':sha(a.binary),'mode_sequence':MODES,
              'rollback_binary_path':a.rollback_binary,'rollback_binary_sha256':sha(a.rollback_binary),
              'planned_uploads_including_original_restore':2,
              'per_mode':['center_HOLD_1','center_HOLD_2','center_HOLD_3','step_0.2V','return_HOLD','step_0.5V','return_HOLD'],
              'step_period_us':500,'hold_period_us':2000,'samples':512,'reference_limit_mV':3.,
              'reference_failure_recorded_and_comparison_continues':True,'other_guard_failure_stops':True,
              'paid_requests':0,'diagnosis_use_allowed':False,'automatic_retry_or_rearm':False,
              'firmware_upload_authorization_required':True,'drive_authorization_required':True}
        out=Path(a.output);out.mkdir(parents=True,exist_ok=False);save(out/'plan.json',plan)
        print(json.dumps({'plan':str(out/'plan.json'),'hardware_commands':0,'paid_requests':0}));return
    if not a.execute:raise ValueError('Explicit authorized --execute required')
    plan=json.loads(Path(a.plan).read_text());auth=json.loads(Path(a.authorization).read_text())
    if auth.get('ADC_QA_upload_and_drive_authorized') is not True or not auth.get('verbatim'):
        raise ValueError('Explicit approval for separate firmware and automatic mode QA required')
    if plan['mode_sequence']!=MODES:raise ValueError('Fixed comparison sequence changed')
    for n,h in plan['sources'].items():
        if sha(ROOT/n)!=h:raise ValueError('Pinned source changed: '+n)
    if sha(plan['binary_path'])!=plan['binary_sha256']:raise ValueError('Compiled binary changed')
    if sha(plan['rollback_binary_path'])!=plan['rollback_binary_sha256']:raise ValueError('Original restore binary changed')
    if sha(ROOT/'docs/2026-11-02-passive-pilot-amendment.md')!=plan['protocol']['amendment_sha256']:
        raise ValueError('Original hardware amendment changed')
    validate_boot_id(a.previous_boot_id)
    log=QALog(a.output,mode='automatic_ADC_mode_comparison_no_LLM_not_diagnosis')
    save(log.path/'plan.json',plan);save(log.path/'authorization.json',auth)
    for n in plan['sources']:
        target=log.path/'source'/n;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes((ROOT/n).read_bytes())
    log.add('ADC_QA_plan_frozen',plan)
    bench=QABench(plan['protocol'],log,lambda *a:None,initial_report=auth,previous_boot_id=a.previous_boot_id)
    summaries=[]
    try:
        ports=[x for x in list_ports.comports() if (x.vid,x.pid,x.serial_number)==tuple(plan['protocol']['USB_identity'])]
        if len(ports)!=1:raise ValueError('Expected Minima absent or ambiguous')
        with serial.Serial(ports[0].device,115200,timeout=5,write_timeout=2) as board:
            time.sleep(2);board.reset_input_buffer();continuity=BootContinuity()
            bench._ping(board,continuity,'ADC_QA_initial_PING',False)
            if continuity.boot_id==a.previous_boot_id:raise ValueError('New firmware boot not established')
            ack=bench._request(board,continuity,bench.config.arm_command(continuity.boot_id),'ADC_QA_ARM',15)
            if ack.get('type')!='armed':raise ValueError('ARM not acknowledged')
            for cycle,mode in enumerate(MODES,1):
                bench.mode=mode;bench.reference_means=[]
                guard_start=len(log.guards)
                ack=bench._request(board,continuity,f'QA_MODE {continuity.boot_id} {mode}\n'.encode(),'ADC_QA_mode')
                if ack.get('type')!='adc_qa_mode':raise ValueError('Mode not acknowledged')
                bench._ping(board,continuity,'ADC_QA_mode_PING',True)
                hold={'kind':'hold','hold_v':bench.config.ref_v,'samples':512,'period_us':2000}
                for j in range(3):bench.qa_capture(board,continuity,f'cycle{cycle}_mode{mode}_center{j+1}',hold)
                for amplitude in (.2,.5):
                    settings={'kind':'step','samples':512,'period_us':500,'amplitude_v':amplitude}
                    bench.qa_capture(board,continuity,f'cycle{cycle}_mode{mode}_step{amplitude}',settings)
                    bench.qa_capture(board,continuity,f'cycle{cycle}_mode{mode}_return{amplitude}',hold)
                means=np.asarray([x['means'] for x in bench.reference_means])
                failures=[{'label':g['label'],'failed_checks':[k for k,v in g['checks'].items() if not v]}
                          for g in log.guards[guard_start:] if not all(g['checks'].values())]
                summary={'cycle':cycle,'mode':mode,'means':bench.reference_means,
                         'A3_block_span_mV':float(np.ptp(means[:,2])*1000),
                         'A4_block_span_mV':float(np.ptp(means[:,3])*1000),
                         'reference_3mV_failure':bool(failures),'reference_failures':failures,
                         'diagnosis_use_allowed':False}
                summaries.append(summary);log.add('ADC_QA_mode_complete',summary)
            bench.mode=0
            bench._ping(board,continuity,'ADC_QA_final_PING',True)
        result={'comparison_completed':True,'summaries':summaries,'paid_requests':0,
                'last_confirmed_code':bench.config.ref_code,'not_diagnosis_or_calibration':True}
        save(log.path/'result.json',result);log.add('run_completed',result)
    except (Exception,KeyboardInterrupt) as exc:
        result={'comparison_completed':False,'error':str(exc) if isinstance(exc,ValueError) else type(exc).__name__,
                'summaries':summaries,'paid_requests':0,'no_retry_or_rearm':True,'output_state_confirmed':False}
        save(log.path/'result.json',result);log.add('run_failed',result)
        print(json.dumps({'record':str(log.path),**result}),flush=True);raise SystemExit(1)
    print(json.dumps({'record':str(log.path),**result}),flush=True)


if __name__=='__main__':main()
