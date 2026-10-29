"""Keep the confirmed DC level's serial connection active during a DMM reading.

PING-only: never ARM, DC, CAPTURE, RESET, or retry. Create STOP in the printed
record directory to close cleanly before any other serial controller runs.
"""
from pathlib import Path
import argparse
import json
import time
import serial
from serial.tools import list_ports
from benchmate.records import Recorder, read_events
from benchmate.instrument import BootContinuity, InstrumentConfig, receive_response

parser = argparse.ArgumentParser()
parser.add_argument('--hold-record', required=True)
args = parser.parse_args()
events = read_events(args.hold_record)
last = events[-1]
assert last['kind'] == 'run_completed'
held = last['payload']
config = InstrumentConfig(**next(e['payload']['configuration'] for e in events
                                if e['kind'] == 'DC_configuration'))
boot, code = held['boot_id'], held['held_code']
guard = BootContinuity(boot)
log = Recorder('runs/hardware-minima-held-level-watch', mode='PING_only_hold_watch_during_operator_measurement')
(log.path / 'controller-source.py').write_bytes(Path(__file__).read_bytes())
(log.path / 'host-instrument.py').write_bytes(Path('src/benchmate/instrument.py').read_bytes())
log.add('configuration', {
    'prior_hold_record': args.hold_record, 'boot_id': boot, 'held_code': code,
    'ref_code': config.ref_code, 'max_jump': config.max_jump,
    'PING_interval_seconds': 2, 'maximum_duration_seconds': 1800,
    'no_stimulus_or_capture_commands': True,
    'stop_control': 'Create STOP in this record directory; no other serial process until terminal event.',
})
print(json.dumps({'record': str(log.path), 'stage': 'preflight'}), flush=True)
count = 0
start = time.monotonic()
try:
    ports = [p for p in list_ports.comports() if (p.vid, p.pid, p.serial_number) ==
             (9025, 105, '3612211F36323632E4B233334B572F52')]
    log.add('USB_preflight', {'matching_ports': [p.device for p in ports]})
    if len(ports) != 1:
        raise RuntimeError('Expected Minima absent or ambiguous')
    with serial.Serial(ports[0].device, 115200, timeout=5, write_timeout=2) as board:
        time.sleep(2)
        board.reset_input_buffer()
        next_progress = 0
        while True:
            board.write(b'PING\n')
            packet = receive_response(board, log, 'held_level_PING')
            guard.check(packet)
            if (packet.get('type') != 'pong' or packet.get('armed') is not True or
                    packet.get('current_code') != code or packet.get('ref_code') != config.ref_code or
                    packet.get('max_jump_code') != config.max_jump):
                raise ValueError('Held level no longer matches the DMM point')
            count += 1
            elapsed = time.monotonic() - start
            if elapsed >= next_progress:
                print(json.dumps({'stage': 'watching', 'elapsed_seconds': round(elapsed, 2),
                                  'successful_PINGs': count, 'held_code': code}), flush=True)
                next_progress += 40
            if (log.path / 'STOP').exists():
                stop_reason = 'explicit_host_stop_after_final_successful_PING'
                break
            if elapsed >= 1800:
                stop_reason = 'maximum_duration_reached'
                break
            time.sleep(2)
    result = {'boot_id': boot, 'held_code_at_final_check': code,
              'successful_PINGs': count, 'duration_seconds': time.monotonic() - start,
              'stop_reason': stop_reason, 'serial_connection_now_closed': True,
              'output_remains_driven': True, 'ADC_capture_requested': False,
              'calibration_performed': False}
    log.add('run_completed', result)
    print(json.dumps({'record': str(log.path), 'stage': 'completed', **result}), flush=True)
except (Exception, KeyboardInterrupt) as exc:
    log.add('run_failed', {'error': str(exc) or type(exc).__name__,
                          'successful_PINGs_before_failure': count,
                          'DMM_pair_continuity_unconfirmed': True,
                          'automatic_retry_or_rearm': False})
    print(json.dumps({'record': str(log.path), 'stage': 'failed', 'error': str(exc)}), flush=True)
    raise SystemExit(1)
