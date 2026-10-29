"""Record physical midpoint recovery; verify same boot, then hold the low DC point."""
from pathlib import Path
import json
import time
import serial
from serial.tools import list_ports
from benchmate.records import Recorder, read_events
from benchmate.instrument import BootContinuity, InstrumentConfig, set_dc_level

recovery = Path('runs/hardware-minima-driver-power-reapplication/20261029T072055-53145320d9')
prior = read_events(recovery)[-1]
assert prior['kind'] == 'run_completed'
boot = prior['payload']['boot_id']
config = InstrumentConfig(vref_v=4.86, ref_v=1.62)
log = Recorder('runs/hardware-minima-recovered-driver-low', mode='operator_midpoint_recovery_then_guarded_low_DC')
for source, name in [(Path(__file__), 'controller-source.py'), (Path('src/benchmate/instrument.py'), 'host-instrument.py')]:
    (log.path / name).write_bytes(source.read_bytes())
log.add('operator_midpoint_report', {
    'raw_report': '4개 다 1.62V',
    'contacts_order': ['U1_actual_pin_5_E13', 'U1_actual_pin_6_E12', 'U1_actual_pin_7_E11', 'D50_REF'],
    'voltage_displays_v': [1.62, 1.62, 1.62, 1.62],
    'meter_range': 'DC 20 V per instruction',
    'reference': 'retained blue-rail GND post',
    'sequential_not_simultaneous': True,
    'scope': 'Midpoint follower agreement at displayed resolution after power reapplication; no proven latch mechanism, offset accuracy or all-range recovery.',
    'prior_ARM_record': prior['payload']['ARM_record'],
})
log.add('configuration', {
    'expected_boot_id': boot, 'expected_prior_code': config.ref_code,
    'supply_conversion_v': config.vref_v, 'REF_target_v': config.ref_v,
    'low_target_v': 0.62, 'DUT_absent_and_wiring_unchanged': True,
    'no_new_ARM_or_firmware_change': True, 'ADC_capture_requested': False,
})
print(json.dumps({'record': str(log.path), 'stage': 'preflight'}), flush=True)
try:
    ports = [p for p in list_ports.comports() if (p.vid, p.pid, p.serial_number) ==
             (9025, 105, '3612211F36323632E4B233334B572F52')]
    log.add('USB_preflight', {'matching_ports': [p.device for p in ports]})
    if len(ports) != 1:
        raise RuntimeError('Expected Minima absent or ambiguous')
    port = ports[0].device
    guard = BootContinuity(boot)
    with serial.Serial(port, 115200, timeout=5, write_timeout=2) as board:
        time.sleep(2)
        board.reset_input_buffer()
        board.write(b'PING\n')
        log.add('serial_command', {'command': 'PING'})
        raw = board.readline()
        log.add('serial_response_raw', {'raw_text': raw.decode('utf-8', errors='replace')})
        if not raw.endswith(b'\n'):
            raise ValueError('Incomplete PING before low-point command')
        packet = json.loads(raw)
        guard.check(packet)
        if (packet.get('type') != 'pong' or packet.get('armed') is not True or
                packet.get('current_code') != config.ref_code or
                packet.get('ref_code') != config.ref_code or
                packet.get('max_jump_code') != config.max_jump or
                packet.get('dc_hold_supported') is not True):
            raise ValueError('Expected held midpoint state not confirmed')
        log.add('same_boot_midpoint_state_verified', packet)
    path, result = set_dc_level(port, config, hold_v=0.62,
                               expected_boot_id=boot, output='runs/hardware-minima-dc-hold')
    log.add('low_DC_hold_completed', {'record': str(path), 'result': result})
    log.add('run_completed', {
        'boot_id': boot, 'DC_hold_record': str(path),
        'held_code': result['held_code'], 'nominal_target_v': 0.62,
        'midpoint_physical_following_reported': True,
        'low_DMM_readings_pending': True, 'ADC_block_acquired': False,
        'calibration_performed': False, 'earlier_fault_cause_established': False,
    })
    print(json.dumps({'record': str(log.path), 'stage': 'completed', 'hold_record': str(path),
                      'boot_id': boot, 'held_code': result['held_code']}), flush=True)
except (Exception, KeyboardInterrupt) as exc:
    log.add('run_failed', {'error': str(exc) or type(exc).__name__,
                          'automatic_retry_or_rearm': False, 'calibration_performed': False})
    print(json.dumps({'record': str(log.path), 'stage': 'failed', 'error': str(exc)}), flush=True)
    raise SystemExit(1)
