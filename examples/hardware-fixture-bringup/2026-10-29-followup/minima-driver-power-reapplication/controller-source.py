"""Confirmed power reapplication: verify new unarmed boot, then explicitly ARM REF only."""
from pathlib import Path
import hashlib
import json
import time
import serial
from serial.tools import list_ports
from benchmate.records import Recorder, read_events
from benchmate.instrument import BootContinuity, InstrumentConfig, acquire_block

prior_recovery = 'runs/hardware-minima-probe-reset-recovery/20261029T064625-11722ff724'
previous_boot = read_events(prior_recovery)[-1]['payload']['boot_id']
config = InstrumentConfig(vref_v=4.86, ref_v=1.62)
log = Recorder('runs/hardware-minima-driver-power-reapplication', mode='confirmed_power_reapplication_guarded_REF_only')
for source, name in [(Path(__file__), 'controller-source.py'), (Path('src/benchmate/instrument.py'), 'host-instrument.py')]:
    (log.path / name).write_bytes(source.read_bytes())
log.add('operator_power_report', {
    'raw_report': '연결완료 / 4.86V / 1.62V',
    'supply_v': 4.86, 'REF_v': 1.62,
    'meter_range': 'DC 20 V per instruction',
    'reference': 'retained blue-rail GND post',
    'supply_contact': 'existing divider resistor A3-side lead',
    'REF_contact': 'D50 jumper',
    'USB_reconnection_confirmed': True,
    'same_cable_port_and_unchanged_wiring_ICs_per_instruction': True,
    'prior_direct_feedback_pin_beep_record': 'runs/hardware-minima-pin-feedback/20261029T071318-5fec08ea86',
    'prior_voltage_contacts': 'U1 actual pins 5 and 7; B13/A11 posts absent',
    'prior_voltage_values_v': [1.62, 3.4],
    'power_off_duration_not_measured': True,
})
log.add('configuration', {
    'previous_boot_id': previous_boot,
    'supply_conversion_v': config.vref_v, 'REF_target_v': config.ref_v,
    'expected_code_after_ARM': config.ref_code,
    'max_jump_code': config.max_jump,
    'DUT_absent_and_calibration_wiring_retained': True,
    'ARM_only_after_new_unarmed_boot_verified': True,
    'ADC_capture_requested': False, 'high_point_not_requested': True,
    'firmware_sha256': hashlib.sha256(Path('firmware/instrument/instrument.ino').read_bytes()).hexdigest(),
    'firmware_upload_requested': False,
})
print(json.dumps({'record': str(log.path), 'stage': 'preflight'}), flush=True)
try:
    ports = [p for p in list_ports.comports() if (p.vid, p.pid, p.serial_number) ==
             (9025, 105, '3612211F36323632E4B233334B572F52')]
    log.add('USB_preflight', {'matching_ports': [p.device for p in ports]})
    if len(ports) != 1:
        raise RuntimeError('Expected Minima absent or ambiguous')
    port = ports[0].device
    guard = BootContinuity()
    with serial.Serial(port, 115200, timeout=5, write_timeout=2) as board:
        time.sleep(2)
        board.reset_input_buffer()
        board.write(b'PING\n')
        log.add('serial_command', {'command': 'PING'})
        raw = board.readline()
        log.add('serial_response_raw', {'raw_text': raw.decode('utf-8', errors='replace')})
        if not raw.endswith(b'\n'):
            raise ValueError('Incomplete PING')
        packet = json.loads(raw)
        guard.check(packet)
        if guard.boot_id == previous_boot:
            raise ValueError('New boot not established after reported power reapplication')
        if (packet.get('type') != 'pong' or packet.get('armed') is not False or
                packet.get('current_code') != 0 or packet.get('ref_code') != 0 or
                packet.get('dc_hold_supported') is not True):
            raise ValueError('Expected unarmed DC-capable startup state')
        if (packet.get('adc_sample_state_channels') != [0, 1, 2, 21] or
                packet.get('adc_sample_states_readback') != [255] * 4):
            raise ValueError('Unexpected active ADC settings')
        log.add('fresh_unarmed_PING_verified', packet)
    print(json.dumps({'stage': 'fresh_boot_verified', 'boot_id': guard.boot_id}), flush=True)
    arm_path, result = acquire_block(port, config, output='runs/hardware-minima-capture',
                                    arm_only=True, expected_boot_id=guard.boot_id)
    log.add('explicit_ARM_completed', {'record': str(arm_path), 'result': result})
    post = next(e['payload'] for e in read_events(arm_path) if e['kind'] == 'firmware_postcheck')
    if post.get('current_code') != config.ref_code:
        raise ValueError('Post-ARM output code not confirmed')
    log.add('run_completed', {
        'boot_id': guard.boot_id, 'new_boot_verified': True,
        'ARM_record': str(arm_path), 'held_code': config.ref_code,
        'nominal_target_v': config.ref_v, 'ADC_capture_requested': False,
        'physical_driver_recovery_not_yet_verified': True,
        'calibration_performed': False, 'sweep_not_resumed': True,
    })
    print(json.dumps({'record': str(log.path), 'stage': 'completed',
                      'boot_id': guard.boot_id, 'held_code': config.ref_code}), flush=True)
except (Exception, KeyboardInterrupt) as exc:
    log.add('run_failed', {'error': str(exc) or type(exc).__name__,
                          'automatic_retry_or_rearm': False,
                          'ADC_capture_requested': False, 'calibration_performed': False})
    print(json.dumps({'record': str(log.path), 'stage': 'failed', 'error': str(exc)}), flush=True)
    raise SystemExit(1)
