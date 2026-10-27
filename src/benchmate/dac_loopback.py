"""One explicit bare-board DC point at a time; output stays held for the DMM."""
import argparse
import json
import statistics
import time
import serial
from .hardware import validate_capture
from .records import Recorder

PROTOCOL = "benchmate-dac-loopback-v1"
LEVEL_CODES = {600: 501, 1100: 919, 1600: 1337, 2100: 1755, 2600: 2173}
NOMINAL_SUPPLY_MV = 4900


def validate_state(packet, kind, level_mv=None):
    if packet.get('protocol') != PROTOCOL or packet.get('type') != kind:
        raise ValueError('Unexpected loopback firmware response')
    if packet.get('nominal_supply_mv') != NOMINAL_SUPPLY_MV or packet.get('calibrated') is not False:
        raise ValueError('Unexpected nominal reference or calibration claim')
    if level_mv is not None:
        if (packet.get('dac_enabled') is not True or
                packet.get('nominal_level_mv') != level_mv or
                packet.get('dac_code') != LEVEL_CODES[level_mv]):
            raise ValueError('DAC state does not match the requested DC point')


def validate_loopback_capture(packet, level_mv):
    validate_state(packet, 'capture', level_mv)
    validate_capture(packet, protocol=PROTOCOL)
    if (packet.get('dac_bits') != 12 or len(packet['samples']) != 64 or
            packet.get('timestamp_semantics') != 'analogRead_completion_us'):
        raise ValueError('Unexpected loopback block or timing semantics')
    return packet


def acquire_point(port, level_mv, *, output='runs/hardware-dac-loopback'):
    if type(level_mv) is not int or level_mv not in LEVEL_CODES:
        raise ValueError('Select one of the five predefined nominal DC levels')
    log = Recorder(output, mode='hardware_uncalibrated_dc_loopback')
    log.add('loopback_configuration', {
        'nominal_level_mv': level_mv, 'requested_dac_code': LEVEL_CODES[level_mv],
        'nominal_supply_mv': NOMINAL_SUPPLY_MV,
        'wiring_requirement': 'A0 feeds A1–A4 through separate 1k resistors; no rail tie or DUT.',
        'scope': 'Combined DAC/ADC functional check. Nominal levels are not measured volts.',
        'output_lifetime': 'A0 remains driven at this point after capture; unplug USB before rewiring.'})
    try:
        with serial.Serial(port, 115200, timeout=5, write_timeout=2) as board:
            time.sleep(2)
            board.reset_input_buffer()
            board.write(b'PING\n')
            pong = json.loads(board.readline())
            log.add('firmware_handshake', pong)
            validate_state(pong, 'pong')
            if pong.get('adc_bits') != 14 or pong.get('dac_bits') != 12:
                raise ValueError('Unexpected converter resolution')
            board.write(f'HOLD {level_mv}\n'.encode())
            held = json.loads(board.readline())
            log.add('dac_hold_response', held)
            validate_state(held, 'holding', level_mv)
            board.write(b'CAPTURE\n')
            raw = board.read_until(b'\n', size=65536)
            packet = json.loads(raw)
            log.add('raw_capture', packet)  # Preserve rejected packets, too.
            validate_loopback_capture(packet, level_mv)
            channels = {}
            for i, name in enumerate(packet['channels']):
                values = [s['raw'][i] for s in packet['samples']]
                channels[name] = {'min': min(values), 'max': max(values),
                                  'mean': statistics.mean(values),
                                  'sample_sd': statistics.stdev(values)}
            result = {'source': 'hardware_uncalibrated', 'samples_per_channel': 64,
                      'nominal_level_mv': level_mv, 'dac_code': LEVEL_CODES[level_mv],
                      'raw_counts_by_channel': channels, 'diagnosis_performed': False,
                      'stimulus_generated': True, 'output_remains_driven': True,
                      'dmm_reading_v': None, 'calibration_performed': False}
            log.add('run_completed', result)
            return log.path, result
    except Exception as exc:
        log.add('run_failed', {'error': str(exc) if isinstance(exc, ValueError) else type(exc).__name__,
                              'output_may_remain_driven': True})
        raise RuntimeError(f'Loopback point failed ({type(exc).__name__}); record: {log.path}. '
                           'A0 may still be driven; unplug USB before rewiring.') from None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', required=True)
    parser.add_argument('--level-mv', type=int, choices=tuple(LEVEL_CODES), required=True)
    parser.add_argument('--output', default='runs/hardware-dac-loopback')
    args = parser.parse_args()
    path, result = acquire_point(args.port, args.level_mv, output=args.output)
    print(json.dumps({'run': str(path), **result}, indent=2))


if __name__ == '__main__':
    main()
