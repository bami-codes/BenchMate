"""Confirmed input pull-down: fresh boot, explicit REF, one raw midpoint block.

No upload, automatic recovery, high stimulus, or long monitoring. All commands
use one serial connection; an incomplete stage ends the attempt.
"""
from pathlib import Path
from dataclasses import asdict
import hashlib
import json
import time
import numpy as np
import serial
from serial.tools import list_ports
from benchmate.records import Recorder
from benchmate.instrument import (BootContinuity, InstrumentConfig,
                                 capture_command, receive_response, validate_block)

PREVIOUS_BOOT = 'e522aadc799575eae297808f4df573c8'
config = InstrumentConfig(vref_v=4.88, ref_v=1.631)
log = Recorder('runs/hardware-minima-pulldown-startup', mode='new_boot_REF_setup_and_raw_midpoint_gross_checks')
for source, name in [(Path(__file__), 'controller-source.py'),
                     (Path('src/benchmate/instrument.py'), 'host-instrument.py')]:
    (log.path / name).write_bytes(source.read_bytes())
log.add('operator_power_report', {
    'verbatim': 'USB 연결 완료 / 전원 4.88V / REF 1.631V / B13 0.003V. 추가로 45열 구동 출력 0.002V',
    'supply_v': 4.88, 'REF_v': 1.631, 'undriven_input_B13_v': 0.003,
    'undriven_driver_D45_v': 0.002,
    'requested_ranges': {'supply': 'DC 20 V', 'REF_and_input': 'DC 2 V'},
    'reference': 'retained blue-rail GND post',
    'input_pulldown': {'holes': ['B13', 'E16'], 'isolated_reported_ohms': 100800,
                       'installation_report': 'runs/hardware-minima-input-pulldown/20261029T090925-d8e6d36e63'},
    'same_cable_port_and_other_wiring_retained_per_instruction': True,
    'DUT_absent_calibration_jumpers_retained': True,
    'scope': 'One operator-reported startup; no proof of USB fault cure or repeated-startup reliability.',
})
log.add('configuration', {
    'configuration': asdict(config), 'previous_boot_id': PREVIOUS_BOOT,
    'ref_code': config.ref_code, 'maximum_jump_code': config.max_jump,
    'samples': 512, 'period_us': 2000, 'single_serial_connection': True,
    'predeclared_gross_checks': {
        'mean_delta_from_reported_REF_v_max': 0.100,
        'all_sample_delta_from_reported_REF_v_max': 0.150,
        'channel_mean_spread_v_max': 0.050,
        'raw_rail_limits_exclusive': [16, 16367],
        'scope': 'Provisional wiring/saturation guards using nominal ADC volts, not calibration acceptance.',
    },
    'DMM_before_ARM_values_not_paired_to_midpoint_ADC': True,
    'fresh_midpoint_DMM_required_for_calibration_pair': True,
    'firmware_sha256': hashlib.sha256(Path('firmware/instrument/instrument.ino').read_bytes()).hexdigest(),
    'firmware_upload_requested': False, 'automatic_retry_or_rearm': False,
})
print(json.dumps({'record': str(log.path), 'stage': 'preflight'}), flush=True)
guard = BootContinuity()
stage = 'preflight'

def check_ping(packet, *, armed):
    guard.check(packet)
    if (packet.get('type') != 'pong' or packet.get('armed') is not armed or
            packet.get('dc_hold_supported') is not True or
            packet.get('adc_sample_state_channels') != [0, 1, 2, 21] or
            packet.get('adc_sample_states_readback') != [255] * 4):
        raise ValueError('Unexpected instrument or active ADC state')
    expected_ref = config.ref_code if armed else 0
    if packet.get('current_code') != expected_ref or packet.get('ref_code') != expected_ref:
        raise ValueError('Unexpected held or REF code')
    if armed and packet.get('max_jump_code') != config.max_jump:
        raise ValueError('Unexpected armed limits')

try:
    ports = [p for p in list_ports.comports() if (p.vid, p.pid, p.serial_number) ==
             (9025, 105, '3612211F36323632E4B233334B572F52')]
    log.add('USB_preflight', {'matching_ports': [p.device for p in ports]})
    if len(ports) != 1:
        raise RuntimeError('Expected Minima absent or ambiguous')
    with serial.Serial(ports[0].device, 115200, timeout=5, write_timeout=2) as board:
        time.sleep(2)
        board.reset_input_buffer()
        stage = 'startup_PING'
        board.write(b'PING\n')
        startup = receive_response(board, log, stage)
        check_ping(startup, armed=False)
        if guard.boot_id == PREVIOUS_BOOT:
            raise ValueError('New boot not established after reported USB disconnection')
        print(json.dumps({'stage': 'new_unarmed_boot_verified', 'boot_id': guard.boot_id}), flush=True)
        stage = 'explicit_REF_ARM'
        board.timeout = 15
        request = config.arm_command(guard.boot_id)
        log.add('serial_command', {'request': request.decode().strip()})
        board.write(request)
        packet = receive_response(board, log, 'ARM_response')
        guard.check(packet)
        if packet.get('type') != 'armed':
            raise ValueError('ARM not acknowledged')
        board.write(b'PING\n')
        check_ping(receive_response(board, log, 'post_ARM_PING'), armed=True)
        stage = 'midpoint_capture'
        request = capture_command(config, boot_id=guard.boot_id, kind='hold',
                                  hold_v=config.ref_v, samples=512, period_us=2000)
        log.add('serial_command', {'request': request.decode().strip()})
        board.timeout = 30
        board.write(request)
        block = receive_response(board, log, 'raw_capture')
        guard.check(block)
        validate_block(block, expected_command=request)
        if block.get('parked_ref_code') != config.ref_code:
            raise ValueError('Capture did not report REF parking')
        board.timeout = 5
        board.write(b'PING\n')
        check_ping(receive_response(board, log, 'post_capture_PING'), armed=True)
        stage = 'gross_voltage_checks'
        rows = np.asarray(block['rows'], dtype=np.int64)
        counts = rows[:, 2:6]
        volts = counts * config.vref_v / 16383
        means = volts.mean(axis=0)
        channels = {name: {
            'mean_counts': float(counts[:, i].mean()),
            'std_counts': float(counts[:, i].std(ddof=1)),
            'min_counts': int(counts[:, i].min()), 'max_counts': int(counts[:, i].max()),
            'nominal_mean_v': float(means[i]),
        } for i, name in enumerate(block['channels'])}
        checks = {
            'raw_not_at_rails': bool(((counts > 16) & (counts < 16367)).all()),
            'all_means_near_REF': bool((np.abs(means - config.ref_v) <= 0.100).all()),
            'all_samples_near_REF': bool((np.abs(volts - config.ref_v) <= 0.150).all()),
            'channel_mean_spread_within_50mV': bool(np.ptp(means) <= 0.050),
        }
        result = {'boot_id': guard.boot_id, 'held_code': config.ref_code,
                  'configuration': asdict(config), 'channels': channels, 'gross_checks': checks,
                  'samples': len(rows), 'frame_interval_us_min': int(np.diff(rows[:, 0]).min()),
                  'frame_interval_us_max': int(np.diff(rows[:, 0]).max()), 'overruns': block['overruns'],
                  'calibration_performed': False, 'fresh_midpoint_DMM_pending': True,
                  'nominal_volts_are_not_calibrated': True, 'all_samples_retained': True}
        (log.path / 'analysis.json').write_text(json.dumps(result, indent=2) + '\n')
        log.add('midpoint_gross_check_analysis', result)
        if not all(checks.values()):
            raise ValueError('Midpoint wiring/saturation guard failed; no further stimulus')
    log.add('run_completed', {**result, 'output_remains_at_REF_code': True,
                             'serial_connection_now_closed': True, 'USB_fault_cure_established': False})
    print(json.dumps({'record': str(log.path), 'stage': 'completed', **result}), flush=True)
except (Exception, KeyboardInterrupt) as exc:
    log.add('run_failed', {'stage': stage, 'error': str(exc) or type(exc).__name__,
                          'accepted_calibration_pairs': 0, 'automatic_retry_or_rearm': False,
                          'output_state_now_confirmed': False})
    print(json.dumps({'record': str(log.path), 'stage': 'failed',
                      'error': str(exc) or type(exc).__name__}), flush=True)
    raise SystemExit(1)
