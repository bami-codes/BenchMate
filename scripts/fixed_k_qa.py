#!/usr/bin/env python3
"""No-provider, no-rewire, two-phase fixed-k reference reproducibility QA."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import time

import numpy as np
import serial
from serial.tools import list_ports

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from benchmate.instrument import BootContinuity
from benchmate.netlist_diagnosis.menu import MENU,RESERVED
from benchmate.physical_bench import PhysicalBench
from benchmate.records import Recorder
from benchmate.ref_reproducibility import POLICY,digest,evaluate,fit,fault_checks
from benchmate.reproducibility_bench import ReproducibilityCaptureMixin

TRAIN_NAMES=['unloaded_step_small','unloaded_sine_1hz_large','unloaded_step_large',
             'unloaded_sine_1hz_small','unloaded_sine_5hz_small']
TRAIN_SEQUENCE=TRAIN_NAMES+list(reversed(TRAIN_NAMES))
NEW_SOURCES=['src/benchmate/ref_reproducibility.py','src/benchmate/reproducibility_bench.py',
             'src/benchmate/reproducibility_session.py','scripts/fixed_k_qa.py','scripts/fixed_k_pilot.py',
             'docs/2026-11-03-fixed-k-repro-amendment.md']


def save(path,value):
    tmp=path.with_suffix(path.suffix+'.tmp');tmp.write_text(json.dumps(value,indent=2,allow_nan=False)+'\n');tmp.replace(path)
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def waveform(s):return {k:v for k,v in s.items() if k!='load_ohm'}


def validate_sources(plan):
    for n,h in plan['sources'].items():
        if sha(ROOT/n)!=h:raise ValueError('Pinned source changed: '+n)
    if sha(ROOT/'docs/2026-11-02-passive-pilot-amendment.md')!=plan['protocol']['amendment_sha256']:
        raise ValueError('Original hardware amendment changed')
    if plan['policy']!=POLICY or plan['train_sequence']!=TRAIN_SEQUENCE or plan['reserved']!=RESERVED:
        raise ValueError('Fixed QA plan changed')


class QABench(ReproducibilityCaptureMixin,PhysicalBench):
    qa_training_only=True


def receipt_check(receipt,candidate):
    if (receipt.get('published') is not True or receipt.get('remote') is not True
        or receipt.get('candidate_sha256')!=digest(candidate)
        or not re.fullmatch('[0-9a-f]{40}',receipt.get('commit',''))
        or not receipt.get('public_path','').startswith('examples/fixed-k-repro/')):
        raise ValueError('Remote freeze receipt required before validation')
    raw=subprocess.check_output(['git','show',receipt['commit']+':'+receipt['public_path']],cwd=ROOT)
    if digest(json.loads(raw))!=digest(candidate):raise ValueError('Committed candidate mismatch')


def main():
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='command',required=True)
    q=sub.add_parser('plan');q.add_argument('--prepared',required=True);q.add_argument('--expected-unarmed-boot',required=True);q.add_argument('--output',required=True)
    q=sub.add_parser('train');q.add_argument('--plan',required=True);q.add_argument('--authorization',required=True);q.add_argument('--output',required=True);q.add_argument('--execute',action='store_true')
    q=sub.add_parser('validate');q.add_argument('--state',required=True);q.add_argument('--freeze-receipt',required=True);q.add_argument('--execute',action='store_true')
    a=p.parse_args()
    if a.command=='plan':
        protocol=json.loads((Path(a.prepared)/'protocol.json').read_text());sources=dict(protocol['pilot_source_sha256'])
        sources.update({n:sha(ROOT/n) for n in NEW_SOURCES})
        plan={'schema':'benchmate.fixed-k-ref-QA-plan.v1','protocol':protocol,'policy':POLICY,'sources':sources,
            'expected_unarmed_boot':a.expected_unarmed_boot,'train_sequence':TRAIN_SEQUENCE,'reserved':RESERVED,
            'scope':'Current design-01 and unchanged unloaded fixture; other loads are not qualified',
            'initial_HOLDs':3,'post_wave_HOLD_each':True,'validation_pre_HOLD':True,'maximum_blocks':28,
            'paid_requests':0,'firmware_upload':False,'manual_DMM_readings':False,'rewiring':False,
            'software_fault_injection_only':True,'OUT_used_for_k_fit':False,'automatic_retry':False,
            'candidate_remote_freeze_before_validation':True,'old_failures_reclassified':False}
        validate_sources(plan);out=Path(a.output);out.mkdir(parents=True,exist_ok=False);save(out/'plan.json',plan)
        print(json.dumps({'plan':str(out/'plan.json'),'hardware_commands':0,'paid_requests':0}));return
    if not a.execute:raise ValueError('Explicit authorized --execute required')
    if a.command=='train':
        plan=json.loads(Path(a.plan).read_text());auth=json.loads(Path(a.authorization).read_text())
        if auth.get('fixed_k_QA_authorized') is not True or not auth.get('verbatim'):
            raise ValueError('Explicit unchanged-wiring fixed-k QA authorization required')
        root=Path(a.output);root.mkdir(parents=True,exist_ok=False)
        state={'plan':plan,'authorization':auth,'status':'training_pending','boot_id':plan['expected_unarmed_boot']}
        save(root/'state.json',state);save(root/'plan.json',plan);save(root/'authorization.json',auth)
    else:
        root=Path(a.state).parent;state=json.loads(Path(a.state).read_text());plan=state['plan']
        if state['status']!='training_complete':raise ValueError('Training is not complete or QA already attempted')
        candidate=json.loads((root/'candidate.json').read_text())
        if digest(candidate)!=state['candidate_sha256']:raise ValueError('Candidate changed after fit')
        receipt=json.loads(Path(a.freeze_receipt).read_text());receipt_check(receipt,candidate)
        state['status']='validation_pending';save(root/'state.json',state);save(root/'freeze-receipt.json',receipt)
    validate_sources(plan)
    log=Recorder(root/'stages',mode='fixed_k_ref_QA_'+a.command+'_no_LLM_not_diagnosis')
    log.add('fixed_k_QA_plan',{'plan_sha256':digest(plan),'policy':POLICY,'paid_requests':0})
    if a.command=='train':
        for n in plan['sources']:
            target=root/'source'/n;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes((ROOT/n).read_bytes())
    bench=QABench(plan['protocol'],log,lambda *a:None,initial_report=state['authorization'],previous_boot_id=state['boot_id'])
    bench.last_confirmed_park=False
    try:
        ports=[x for x in list_ports.comports() if (x.vid,x.pid,x.serial_number)==tuple(plan['protocol']['USB_identity'])]
        if len(ports)!=1:raise ValueError('Expected Minima absent or ambiguous; no port opened')
        continuity=BootContinuity(state['boot_id'])
        with serial.Serial(ports[0].device,115200,timeout=5,write_timeout=2) as board:
            time.sleep(2);board.reset_input_buffer()
            if a.command=='train':
                bench._ping(board,continuity,'fixed_k_QA_initial_unarmed_PING',False)
                ack=bench._request(board,continuity,bench.config.arm_command(continuity.boot_id),'fixed_k_QA_ARM',15)
                if ack.get('type')!='armed':raise ValueError('ARM not acknowledged')
                bench._ping(board,continuity,'fixed_k_QA_armed_PING',True)
                bench.last_confirmed_park=True
                for i in range(3):bench._hold(board,continuity,f'origin_{i+1}')
                for i,name in enumerate(TRAIN_SEQUENCE,1):
                    s=waveform(MENU[name]);rows=bench._capture(board,continuity,f'train_{i}_{name}',s)
                    bench._waveform_checks(rows,s);bench._hold(board,continuity,f'train_{i}_return')
                bench._ping(board,continuity,'fixed_k_QA_training_final_PING',True)
                outcome=fit(bench.repro_blocks,bench.repro_origin,bench.config.vref_v)
                save(root/'training-data.json',bench.repro_blocks);save(root/'training-fit.json',outcome)
                if not outcome['passed']:raise ValueError(outcome['reason'])
                candidate=outcome['candidate']
                faults=fault_checks(bench.repro_blocks,bench.repro_origin,bench.config,bench.p['guard_limits'],candidate['fixed_k'])
                save(root/'software-fault-checks.json',faults)
                if not faults['passed']:raise ValueError('Software fault injection check failed')
                save(root/'candidate.json',candidate)
                state.update(status='training_complete',boot_id=continuity.boot_id,
                    candidate_sha256=digest(candidate),training_data_sha256=digest(bench.repro_blocks),
                    reference_means=bench.reference_means,origin=bench.repro_origin,
                    software_faults_passed=True,output_at_REF_confirmed=True)
                result={'stage':'candidate_ready_for_remote_freeze','fixed_k':candidate['fixed_k'],
                    'feasible_training_interval':candidate['feasible_training_interval'],
                    'candidate_sha256':digest(candidate),'fault_injection':faults,
                    'training_blocks':len(bench.repro_blocks),'reserved_captures':0,'qualified':False}
            else:
                if digest(json.loads((root/'training-data.json').read_text()))!=state['training_data_sha256']:
                    raise ValueError('Training data changed')
                bench.reference_means=state['reference_means']
                bench.repro_blocks=json.loads((root/'training-data.json').read_text())
                bench.repro_origin=state['origin']
                bench.raw_hold_means=[r['means'] for r in bench.reference_means if r['hold']]
                bench.fixed_model=candidate;bench.qa_training_only=False
                bench._ping(board,continuity,'fixed_k_QA_validation_initial_PING',True)
                bench.last_confirmed_park=True
                bench._hold(board,continuity,'validation_pre_HOLD')
                for i,spec in enumerate(RESERVED,1):
                    s=waveform(spec);rows=bench._capture(board,continuity,f'validation_{i}',s)
                    bench._waveform_checks(rows,s);bench._hold(board,continuity,f'validation_{i}_return')
                bench._ping(board,continuity,'fixed_k_QA_validation_final_PING',True)
                check=evaluate(bench.repro_blocks,bench.repro_origin,bench.config.vref_v,candidate['fixed_k'])
                if not check['passed']:raise ValueError('Fixed candidate validation failed')
                qualification={'schema':'benchmate.fixed-k-ref-qualification.v1','passed':True,
                    'source':'physical_instrument_QA','validation_refit':False,
                    'candidate_sha256':digest(candidate),'plan_sha256':digest(plan),
                    'qualified_fixtures':['unloaded'],'tested_design_scope':'Current design-01 only; per-run guards still required',
                    'fault_injection_passed':True,'validation_check':check,'source_sha256':plan['sources'],
                    'freeze_receipt':receipt,'physical_REF_stability_established':False,
                    'OUT_used_for_fit_or_acceptance':False,'legacy_failures_reclassified':False}
                save(root/'qualification.json',qualification);save(root/'all-QA-data.json',bench.repro_blocks)
                state.update(status='passed',qualification_sha256=digest(qualification),output_at_REF_confirmed=True)
                result={'stage':'QA_passed','qualified_fixtures':['unloaded'],'fixed_k':candidate['fixed_k'],
                    'qualification_sha256':digest(qualification),'total_blocks':len(bench.repro_blocks),
                    'validation_refit':False,'physical_REF_stability_established':False}
        save(root/'state.json',state)
        result.update(record=str(log.path),root=str(root),paid_requests=0,output_at_REF_confirmed=True)
        save(log.path/'result.json',result);log.add('run_completed',result);print(json.dumps(result),flush=True)
    except (Exception,KeyboardInterrupt) as exc:
        if hasattr(bench,'repro_blocks'):save(root/('partial-'+a.command+'-data.json'),bench.repro_blocks)
        state.update(status='failed',failed_phase=a.command,automatic_retry=False)
        save(root/'state.json',state)
        result={'stage':'QA_failed','phase':a.command,'error':str(exc) if isinstance(exc,ValueError) else type(exc).__name__,
            'capture_attempts':bench.capture_attempts,'frames':bench.frames,'paid_requests':0,
            'output_at_REF_confirmed':bench.last_confirmed_park,'no_retry':True,'root':str(root)}
        save(log.path/'result.json',result);log.add('run_failed',result);print(json.dumps(result),flush=True);raise SystemExit(1)


if __name__=='__main__':main()
