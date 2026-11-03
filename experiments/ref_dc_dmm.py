#!/usr/bin/env python3
"""Bounded retained-DUT DC/DMM QA. No provider, firmware upload or model fitting.

start establishes C. Each advance records three DMM readings, captures HOLD at
the same level (firmware parks REF), then holds the next planned DC level.
Serial is closed while the operator reads. Every reopen verifies boot and code.
Reference spans above 3 mV remain qualification failures, not diagnostic passes.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import sys
import time

import numpy as np
import serial
from serial.tools import list_ports

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from benchmate.instrument import InstrumentConfig, BootContinuity, capture_command, dc_hold_command, receive_response, validate_block
from benchmate.records import Recorder, canonical

SEQUENCE = ['C','L','C','H','C','C','H','C','L','C']


def sha(value): return hashlib.sha256(value).hexdigest()
def save(path, value):
    tmp = path.with_suffix(path.suffix+'.tmp')
    tmp.write_text(json.dumps(value, indent=2, allow_nan=False)+'\n'); tmp.replace(path)


def levels(config):
    return {'C': config.ref_v, 'L': config.ref_v-.5, 'H': config.ref_v+.5}


def readings(values):
    if len(values) != 3: raise ValueError('Exactly three displayed DMM readings required')
    result = [float(x) for x in values]
    if any(not math.isfinite(x) or not .5 <= x <= 2.8 for x in result):
        raise ValueError('DMM readings are outside the retained REF check range')
    return result


def validate_sources(state):
    for name, expected in state['source_sha256'].items():
        if sha((ROOT/name).read_bytes()) != expected: raise ValueError('Pinned source changed: '+name)
    if sha((ROOT/'docs/2026-11-02-passive-pilot-amendment.md').read_bytes()) != state['protocol']['amendment_sha256']:
        raise ValueError('Hardware amendment changed')


def span_summary(samples):
    if not samples: return {}
    a = np.asarray([x['ADC_means_nominal_v'] for x in samples])
    spans = {f'A{i+1}': float(np.ptp(a[:, i])*1000) for i in (2, 3)}
    return {'REF_block_mean_span_mV': spans, 'existing_limit_mV': 3.,
            'A4_within_existing_3mV_limit': spans['A4'] <= 3.,
            'diagnosis_use_allowed': False, 'scope': 'Instrument QA only; no rejected trial is reclassified.'}


class Device:
    def __init__(self, board, log, config, *, boot=None):
        self.board, self.log, self.config = board, log, config
        self.continuity = BootContinuity(boot)
    def request(self, command, name, timeout=10):
        self.log.add('serial_command', {'request': command.decode().strip(), 'label': name})
        self.board.timeout = timeout
        if self.board.write(command) != len(command): raise ValueError('Incomplete write; no retry')
        p = receive_response(self.board, self.log, name); self.continuity.check(p); return p
    def ping(self, code, *, armed=True):
        p = self.request(b'PING\n', 'DC_QA_PING')
        if (p.get('type') != 'pong' or p.get('armed') is not armed or p.get('current_code') != code
                or p.get('ref_code') != (self.config.ref_code if armed else 0)
                or p.get('dc_hold_supported') is not True
                or p.get('adc_sample_state_channels') != [0,1,2,21]
                or p.get('adc_sample_states_readback') != [255]*4
                or (armed and p.get('max_jump_code') != self.config.max_jump)):
            raise ValueError('Unexpected boot, firmware or held output; no re-arm')
        return p
    def dc(self, label):
        if label not in levels(self.config): raise ValueError('Only the fixed C/L/H levels are available')
        command = dc_hold_command(self.config, boot_id=self.continuity.boot_id, hold_v=levels(self.config)[label])
        code = int(command.split()[2]); p = self.request(command, 'DC_QA_held', 40)
        if p.get('type') != 'dc_held' or p.get('held_code') != code: raise ValueError('DC not acknowledged')
        self.ping(code); time.sleep(5)
        return code
    def sample(self, label, protocol):
        command = capture_command(self.config, boot_id=self.continuity.boot_id, kind='hold',
                                  hold_v=levels(self.config)[label], samples=512, period_us=2000)
        p = self.request(command, 'DC_QA_raw_HOLD', 30); validate_block(p, expected_command=command)
        if p.get('parked_ref_code') != self.config.ref_code: raise ValueError('REF park not reported')
        self.ping(self.config.ref_code)
        a = np.asarray(p['rows']); v = a[:,2:6]*self.config.vref_v/16383
        g = protocol['guard_limits']
        checks = {'raw_rails': bool(((a[:,2:6]>16)&(a[:,2:6]<16367)).all()),
                  'IN_OUT_envelope': bool((abs(v[:,:2]-self.config.ref_v)<=g['signal_envelope_v']).all()),
                  'REF_envelope': bool((abs(v[:,2:4]-self.config.ref_v)<=g['A4_envelope_v']).all()),
                  'held_DAC_code': bool((a[:,1]==int(command.split()[5])).all())}
        self.log.add('DC_QA_electrical_bounds', {'checks': checks, 'means_nominal_v': v.mean(axis=0).tolist()})
        if not all(checks.values()): raise ValueError('Electrical bound failed; no next DC level')
        return v.mean(axis=0).tolist()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest='command', required=True)
    q = sub.add_parser('plan'); q.add_argument('--prepared', required=True); q.add_argument('--output', required=True)
    q = sub.add_parser('start'); q.add_argument('--plan', required=True); q.add_argument('--operator-report', required=True)
    q.add_argument('--output', required=True); q.add_argument('--execute', action='store_true')
    q = sub.add_parser('advance'); q.add_argument('--state', required=True); q.add_argument('--readings', nargs=3, required=True)
    q.add_argument('--execute', action='store_true')
    args = p.parse_args()
    if args.command == 'plan':
        protocol = json.loads((Path(args.prepared)/'protocol.json').read_text())
        sources = dict(protocol['pilot_source_sha256']); own = str(Path(__file__).resolve().relative_to(ROOT))
        sources[own] = sha(Path(__file__).read_bytes()); c = InstrumentConfig(**protocol['configuration'])
        plan = {'schema':'benchmate.retained_DUT_DC_QA.v1','protocol':protocol,'source_sha256':sources,
                'sequence':SEQUENCE,'levels_v':levels(c), 'paid_requests':0,'firmware_upload':False,
                'scope':'Retained passive design-01 DUT, unloaded. A3 REF via A23, A4 REF via I50. Not diagnosis or holdout.',
                'DMM_before_ADC_capture_at_same_held_level':True,'simultaneous_DMM_ADC_claim':False,
                'reference_limit_mV':3.,'reference_qualification_failure_is_recorded':True,
                'QA_collects_planned_levels_within_electrical_bounds_even_if_reference_unqualified':True,
                'no_automatic_retry_or_rearm':True,'codes':{k:int(dc_hold_command(c,boot_id='1'*32,hold_v=v).split()[2]) for k,v in levels(c).items()}}
        validate_sources(plan); out=Path(args.output); out.mkdir(parents=True,exist_ok=False); save(out/'plan.json',plan)
        print(json.dumps({'plan':str(out/'plan.json'),'codes':plan['codes'],'hardware_commands':0,'paid_requests':0})); return
    if not args.execute: raise ValueError('Explicit user-authorized --execute required')
    if args.command == 'start':
        state=json.loads(Path(args.plan).read_text()); validate_sources(state)
        report=json.loads(Path(args.operator_report).read_text())
        if (report.get('operator_confirmed') is not True or report.get('USB_off_then_reconnected') is not True
                or report.get('DUT_retained_unloaded_A3REF') is not True or report.get('DMM_range')!='DC2V'):
            raise ValueError('Confirmed retained-DUT setup and DMM range required')
        root=Path(args.output); root.mkdir(parents=True,exist_ok=False); state_path=root/'state.json'
        save(root/'plan.json',state); save(root/'operator-report.json',report)
        state.update(index=0,samples=[],pending=True,stopped=False,completed=False,operator_report=report)
    else:
        state_path=Path(args.state); root=state_path.parent; state=json.loads(state_path.read_text())
        validate_sources(state); values=readings(args.readings)
        if state.get('pending') or state.get('stopped') or state.get('completed'):
            raise ValueError('Session is stopped, completed or has an unresolved prior operation')
        state['pending']=True
    save(state_path,state)
    log=Recorder(root/'stages',mode='retained_DUT_persistent_DC_DMM_QA_no_LLM')
    log.add('DC_QA_plan',{'plan_sha256':sha(canonical({k:v for k,v in state.items() if k not in ('samples','pending')})),
                        'scope':state['scope'],'reference_limit_mV':3.,'paid_requests':0})
    config=InstrumentConfig(**state['protocol']['configuration'])
    try:
        ports=[x for x in list_ports.comports() if (x.vid,x.pid,x.serial_number)==tuple(state['protocol']['USB_identity'])]
        if len(ports)!=1: raise ValueError('Expected Minima absent or ambiguous; no port opened')
        with serial.Serial(ports[0].device,115200,timeout=10,write_timeout=2) as board:
            time.sleep(2); board.reset_input_buffer(); dev=Device(board,log,config,boot=state.get('boot_id'))
            if args.command=='start':
                dev.ping(0,armed=False)
                ack=dev.request(config.arm_command(dev.continuity.boot_id),'DC_QA_ARM',15)
                if ack.get('type')!='armed': raise ValueError('ARM not acknowledged')
                dev.ping(config.ref_code); state['boot_id']=dev.continuity.boot_id
                for name in state['source_sha256']:
                    target=root/'source'/name; target.parent.mkdir(parents=True,exist_ok=True); target.write_bytes((ROOT/name).read_bytes())
            else:
                label=state['sequence'][state['index']]; dev.ping(state['held_code'])
                log.add('operator_DMM_readings',{'level':label,'display_strings':args.readings,'readings_v':values,
                        'DMM_range':'DC2V','point':'D50 vs blue GND','requested_spacing_s':2,'spacing_not_independently_measured':True})
                means=dev.sample(label,state['protocol'])
                state['samples'].append({'level':label,'DMM_display_strings':args.readings,'DMM_v':values,
                       'ADC_means_nominal_v':means,'DMM_precedes_ADC_at_same_level':True,'stage':str(log.path)})
                state['index']+=1
            if state['index']<len(state['sequence']):
                label=state['sequence'][state['index']]; state['held_code']=dev.dc(label)
                result={'stage':'awaiting_DMM','level':label,'index':state['index']+1,
                        'nominal_drive_v':levels(config)[label],'held_code':state['held_code'],'output_remains_held':True}
            else:
                dev.ping(config.ref_code); state['held_code']=config.ref_code; state['completed']=True
                result={'stage':'completed','output_at_REF':True,'samples':state['samples']}
        state.update(pending=False,last_stage=str(log.path)); save(state_path,state)
        result.update(state=str(state_path),record=str(log.path),paid_requests=0,reference_summary=span_summary(state['samples']))
        save(log.path/'result.json',result); log.add('run_completed',result); print(json.dumps(result),flush=True)
    except (Exception,KeyboardInterrupt) as exc:
        state.update(stopped=True,pending=False);save(state_path,state)
        result={'stage':'failed','error':str(exc) if isinstance(exc,ValueError) else type(exc).__name__,
                'output_state_confirmed':False,'no_retry_or_rearm':True,'paid_requests':0,'state':str(state_path)}
        save(log.path/'result.json',result);log.add('run_failed',result);print(json.dumps(result),flush=True)
        raise SystemExit(1)


if __name__=='__main__':main()
