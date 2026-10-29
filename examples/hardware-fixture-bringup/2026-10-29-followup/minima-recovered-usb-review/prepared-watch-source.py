"""After confirmed RESET, keep one serial connection and REF output for 10 minutes."""
from pathlib import Path
import argparse
import hashlib
import json
import time
import serial
from serial.tools import list_ports
from benchmate.records import Recorder
from benchmate.instrument import BootContinuity, InstrumentConfig, receive_response

parser = argparse.ArgumentParser()
parser.add_argument('--confirmation', required=True)
args = parser.parse_args()
confirmation = json.loads(Path(args.confirmation).read_text())
assert confirmation['operator_single_RESET_confirmed'] is True
assert confirmation['USB_wiring_firmware_unchanged'] is True
assert confirmation['previous_boot_id'] == 'b4ab5f3bf78ec9374ac381996885027b'
config = InstrumentConfig(vref_v=4.86, ref_v=1.62)
log = Recorder('runs/hardware-minima-persistent-ref-watch', mode='single_open_REF_and_periodic_PING_diagnostic')
for source, name in [(Path(__file__), 'controller-source.py'), (Path('src/benchmate/instrument.py'), 'host-instrument.py')]:
    (log.path / name).write_bytes(source.read_bytes())
log.add('operator_RESET_confirmation', confirmation)
log.add('configuration', {
    'supply_v': 4.86, 'REF_target_v': 1.62, 'ref_code': config.ref_code,
    'supply_basis': 'Latest operator power report; no USB or fixture change during requested RESET',
    'duration_seconds': 600, 'PING_interval_seconds': 2,
    'one_serial_open': True, 'output_after_ARM_unchanged': True,
    'no_ADC_capture': True, 'automatic_retry_or_rearm': False,
    'firmware_sha256': hashlib.sha256(Path('firmware/instrument/instrument.ino').read_bytes()).hexdigest(),
    'scope': 'Continuous-open plus periodic-status comparison; not proof of a specific USB fault cause or calibrated voltage.',
})
print(json.dumps({'record': str(log.path), 'stage': 'preflight'}), flush=True)
guard = BootContinuity()
successes = 0
try:
    ports = [p for p in list_ports.comports() if (p.vid, p.pid, p.serial_number) ==
             (9025, 105, '3612211F36323632E4B233334B572F52')]
    log.add('USB_preflight', {'matching_ports': [p.device for p in ports]})
    if len(ports) != 1:
        raise RuntimeError('Expected Minima absent or ambiguous')
    with serial.Serial(ports[0].device, 115200, timeout=5, write_timeout=2) as board:
        time.sleep(2)
        board.reset_input_buffer()
        board.write(b'PING\n')
        packet = receive_response(board, log, 'startup_PING')
        guard.check(packet)
        if guard.boot_id == confirmation['previous_boot_id']:
            raise ValueError('New boot not established after confirmed RESET')
        if (packet.get('type') != 'pong' or packet.get('armed') is not False or
                packet.get('current_code') != 0 or packet.get('ref_code') != 0 or
                packet.get('dc_hold_supported') is not True or
                packet.get('adc_sample_state_channels') != [0, 1, 2, 21] or
                packet.get('adc_sample_states_readback') != [255] * 4):
            raise ValueError('Expected unarmed instrument startup state')
        request = config.arm_command(guard.boot_id)
        log.add('explicit_ARM_command', {'request': request.decode().strip()})
        board.write(request)
        packet = receive_response(board, log, 'ARM_response')
        guard.check(packet)
        if packet.get('type') != 'armed':
            raise ValueError('ARM not acknowledged')
        start = time.monotonic()
        deadline = start + 600
        next_progress = 0
        while True:
            board.write(b'PING\n')
            packet = receive_response(board, log, 'held_REF_PING')
            guard.check(packet)
            if (packet.get('type') != 'pong' or packet.get('armed') is not True or
                    packet.get('ref_code') != config.ref_code or
                    packet.get('current_code') != config.ref_code or
                    packet.get('max_jump_code') != config.max_jump or
                    packet.get('adc_sample_state_channels') != [0, 1, 2, 21] or
                    packet.get('adc_sample_states_readback') != [255] * 4):
                raise ValueError('Held REF state changed')
            successes += 1
            elapsed = time.monotonic() - start
            if elapsed >= next_progress:
                print(json.dumps({'stage': 'watching', 'elapsed_seconds': round(elapsed, 2),
                                  'successful_PINGs': successes, 'boot_id': guard.boot_id,
                                  'held_code': config.ref_code}), flush=True)
                next_progress += 40
            if time.monotonic() >= deadline:
                break
            time.sleep(max(0, min(2, deadline - time.monotonic())))
    result = {'duration_seconds': round(time.monotonic() - start, 3),
              'successful_PINGs': successes, 'boot_id': guard.boot_id,
              'held_code_at_final_check': config.ref_code,
              'output_remains_driven': True, 'serial_connection_now_closed': True,
              'ADC_capture_requested': False, 'calibration_performed': False,
              'fault_cause_established': False}
    log.add('run_completed', result)
    print(json.dumps({'record': str(log.path), 'stage': 'completed', **result}), flush=True)
except (Exception, KeyboardInterrupt) as exc:
    log.add('run_failed', {'error': str(exc) or type(exc).__name__,
                          'successful_PINGs_before_failure': successes,
                          'output_state_now_confirmed': False,
                          'automatic_retry_or_rearm': False, 'ADC_capture_requested': False})
    print(json.dumps({'record': str(log.path), 'stage': 'failed', 'error': str(exc)}), flush=True)
    raise SystemExit(1)
