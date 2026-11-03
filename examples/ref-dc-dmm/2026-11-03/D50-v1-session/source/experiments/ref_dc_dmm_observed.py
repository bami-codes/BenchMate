#!/usr/bin/env python3
"""Continue the frozen DC QA while preserving reported DMM ranges as ranges.

No fabricated readings, new levels, provider calls, firmware or threshold changes.
The original recorder remains pinned and supplies all serial and guard logic.
"""
import argparse
import json
import math
from pathlib import Path
import time

import ref_dc_dmm as qa

OWN = 'experiments/ref_dc_dmm_observed.py'
NOTE = 'docs/2026-11-03-ref-dc-dmm-observation-amendment.md'


def observation(value):
    kind = value.get('kind')
    strings = value.get('display_strings', [])
    if kind not in ('displayed_range', 'three_readings'):
        raise ValueError('An observed range or three actual readings are required')
    if len(strings) != (2 if kind == 'displayed_range' else 3):
        raise ValueError('Wrong number of reported values')
    volts = [float(x) for x in strings]
    if any(not math.isfinite(x) or not .5 <= x <= 2.8 for x in volts):
        raise ValueError('DMM observation outside retained REF check range')
    if kind == 'displayed_range' and volts[0] > volts[1]:
        raise ValueError('Reversed range')
    if not value.get('operator_reply_original'):
        raise ValueError('Preserve the actual operator reply')
    return {**value, 'volts': volts, 'range_v': [min(volts), max(volts)],
            'individual_readings_known': kind == 'three_readings',
            'spacing_independently_verified': False, 'DMM_range': 'DC2V',
            'point': 'D50 vs blue GND'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    subs = parser.add_subparsers(dest='command', required=True)
    p = subs.add_parser('bind'); p.add_argument('--state', required=True)
    p = subs.add_parser('advance'); p.add_argument('--state', required=True)
    p.add_argument('--observation', required=True); p.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    state_path = Path(args.state); root = state_path.parent
    state = json.loads(state_path.read_text()); qa.validate_sources(state)
    if state.get('pending') or state.get('stopped') or state.get('completed'):
        raise ValueError('Pending, stopped or completed session; no operation')
    if args.command == 'bind':
        if state['index'] != 0 or state['samples'] or state.get('observation_extension'):
            raise ValueError('Extension must be fixed before the first ADC/DMM pair')
        receipt = {'schema': 'benchmate.DMM_range_reporting_extension.v1',
                   'prior_state_sha256': qa.sha(state_path.read_bytes()),
                   'original_plan_sha256': qa.sha((root/'plan.json').read_bytes()),
                   'adopted_after_first_operator_range_report': True,
                   'hardware_commands': 0, 'paid_requests': 0,
                   'levels_sequence_firmware_thresholds_unchanged': True,
                   'new_sources': {n: qa.sha((qa.ROOT/n).read_bytes()) for n in (OWN, NOTE)}}
        qa.save(root/'state-before-observation-extension.json', state)
        state['source_sha256'].update(receipt['new_sources'])
        state['observation_extension'] = receipt
        qa.save(root/'observation-extension.json', receipt)
        for name in receipt['new_sources']:
            target = root/'source'/name; target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes((qa.ROOT/name).read_bytes())
        qa.save(state_path, state); print(json.dumps(receipt)); return
    if not args.execute or not state.get('observation_extension'):
        raise ValueError('Bound extension and authorized --execute required')
    for name in (OWN, NOTE):
        if state['source_sha256'].get(name) != qa.sha((qa.ROOT/name).read_bytes()):
            raise ValueError('Unpinned observation extension')
    observed = observation(json.loads(Path(args.observation).read_text()))
    state['pending'] = True; qa.save(state_path, state)
    log = qa.Recorder(root/'stages', mode='retained_DUT_DC_DMM_QA_reported_observation_no_LLM')
    log.add('DC_QA_observation_extension', state['observation_extension'])
    config = qa.InstrumentConfig(**state['protocol']['configuration'])
    try:
        ports = [p for p in qa.list_ports.comports()
                 if (p.vid, p.pid, p.serial_number) == tuple(state['protocol']['USB_identity'])]
        if len(ports) != 1: raise ValueError('Expected Minima absent or ambiguous; no port opened')
        with qa.serial.Serial(ports[0].device, 115200, timeout=10, write_timeout=2) as board:
            time.sleep(2); board.reset_input_buffer()
            dev = qa.Device(board, log, config, boot=state['boot_id'])
            label = state['sequence'][state['index']]; dev.ping(state['held_code'])
            log.add('operator_DMM_observation', {'level': label, **observed})
            means = dev.sample(label, state['protocol'])
            state['samples'].append({'level': label, 'DMM_observation': observed,
                'ADC_means_nominal_v': means, 'DMM_precedes_ADC_at_same_level': True,
                'simultaneous_measurement': False, 'stage': str(log.path)})
            state['index'] += 1
            if state['index'] < len(state['sequence']):
                label = state['sequence'][state['index']]; state['held_code'] = dev.dc(label)
                result = {'stage': 'awaiting_DMM', 'level': label, 'index': state['index']+1,
                    'nominal_drive_v': qa.levels(config)[label], 'held_code': state['held_code'],
                    'output_remains_held': True}
            else:
                dev.ping(config.ref_code); state['held_code'] = config.ref_code
                state['completed'] = True
                result = {'stage': 'completed', 'output_at_REF': True}
        state.update(pending=False, last_stage=str(log.path)); qa.save(state_path, state)
        result.update(state=str(state_path), record=str(log.path), paid_requests=0,
                      last_sample=state['samples'][-1], reference_summary=qa.span_summary(state['samples']))
        qa.save(log.path/'result.json', result); log.add('run_completed', result)
        print(json.dumps(result), flush=True)
    except (Exception, KeyboardInterrupt) as exc:
        state.update(stopped=True, pending=False); qa.save(state_path, state)
        result = {'stage': 'failed', 'error': str(exc) if isinstance(exc, ValueError) else type(exc).__name__,
                  'output_state_confirmed': False, 'no_retry_or_rearm': True, 'paid_requests': 0,
                  'state': str(state_path)}
        qa.save(log.path/'result.json', result); log.add('run_failed', result)
        print(json.dumps(result), flush=True); raise SystemExit(1)


if __name__ == '__main__': main()
