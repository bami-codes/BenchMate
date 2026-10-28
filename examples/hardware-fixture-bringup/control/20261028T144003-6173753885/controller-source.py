"""Supervised fixture DC hold only. No ADC capture, reset or automatic recovery."""
import argparse
import hashlib
import json
from pathlib import Path
import time

import serial
from serial.tools import list_ports

from benchmate.dac_loopback import LEVEL_CODES, validate_state
from benchmate.records import Recorder


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', required=True)
    parser.add_argument('--previous-mv', type=int, choices=LEVEL_CODES, required=True)
    parser.add_argument('--level-mv', type=int, choices=LEVEL_CODES, required=True)
    args = parser.parse_args()
    if abs(args.level_mv - args.previous_mv) > 1000:
        parser.error('A supervised nominal change must not exceed 1000 mV')
    log = Recorder('runs/hardware-fixture-dc', mode='fixture_driver_manual_dc_hold')
    source = Path(__file__).read_bytes()
    (log.path / 'controller-source.py').write_bytes(source)
    attempted = False

    def present():
        return any(p.device == args.port and p.vid == 9025 and p.pid == 4098
                   and p.serial_number == '68EE8F6B2D68' for p in list_ports.comports())

    def exchange(board, command, kind, level):
        log.add('serial_command', {'ascii': command})
        board.write((command + '\n').encode('ascii'))
        board.flush()
        raw = board.read_until(b'\n', size=8192)
        log.add('serial_response_raw', {'ascii': raw.decode('ascii', errors='backslashreplace')})
        packet = json.loads(raw)
        validate_state(packet, kind, level)
        if kind == 'pong' and (packet.get('adc_bits') != 14 or packet.get('dac_bits') != 12):
            raise ValueError('Unexpected converter resolution')
        return packet

    log.add('fixture_configuration', {
        'port': args.port, 'previous_nominal_mv': args.previous_mv,
        'target_nominal_mv': args.level_mv, 'requested_dac_code': LEVEL_CODES[args.level_mv],
        'source_sha256': hashlib.sha256(source).hexdigest(),
        'connections': 'Arduino 5V/GND/A0 to LM358 fixture; no DUT or ADC leads',
        'driver_pulldown_ohm_operator_display': 999,
        'boot_id_available': False, 'adc_capture': False,
        'automatic_recovery': False, 'actual_voltage_requires_operator_DMM': True})
    print(json.dumps({'record': str(log.path), 'state': 'preflight'}), flush=True)
    try:
        if not present():
            raise RuntimeError('Expected original board absent; no new output command sent')
        with serial.Serial(args.port, 115200, timeout=3, write_timeout=2) as board:
            time.sleep(2)
            board.reset_input_buffer()
            exchange(board, 'PING', 'pong', args.previous_mv)
            attempted = True
            exchange(board, f'HOLD {args.level_mv}', 'holding', args.level_mv)
            time.sleep(0.5)
            exchange(board, 'PING', 'pong', args.level_mv)
        start = time.monotonic()
        for index in range(16):
            time.sleep(max(0, start + index - time.monotonic()))
            seen = present()
            log.add('post_hold_usb_sample', {
                'index': index, 'elapsed_s': time.monotonic() - start,
                'usb_device_present': seen, 'serial_port_closed': True})
            if not seen:
                raise RuntimeError('USB disappeared after HOLD; output may remain driven')
        with serial.Serial(args.port, 115200, timeout=3, write_timeout=2) as board:
            time.sleep(2)
            board.reset_input_buffer()
            exchange(board, 'PING', 'pong', args.level_mv)
        result = {'target_nominal_mv': args.level_mv, 'dac_code': LEVEL_CODES[args.level_mv],
                  'post_close_state_verified': True, 'output_remains_driven': True,
                  'dmm_reading_pending': True, 'calibration_performed': False,
                  'scope': 'Short command/state check, not a long-term USB reliability test'}
        log.add('run_completed', result)
        print(json.dumps({'record': str(log.path), 'state': 'completed', **result}), flush=True)
    except (Exception, KeyboardInterrupt) as exc:
        result = {'error': str(exc) or type(exc).__name__, 'hold_attempted': attempted,
                  'output_may_remain_driven': True, 'automatic_recovery': False}
        log.add('run_failed', result)
        print(json.dumps({'record': str(log.path), 'state': 'failed', **result}), flush=True)
        raise SystemExit(1)


if __name__ == '__main__':
    main()
