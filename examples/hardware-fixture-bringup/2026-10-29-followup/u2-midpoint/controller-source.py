"""First U2 gross DC check after operator-confirmed fresh power-on; no capture."""
import hashlib
import json
from pathlib import Path
import time
import serial
from serial.tools import list_ports
from benchmate.dac_loopback import validate_state
from benchmate.records import Recorder


def main():
    port = '/dev/cu.usbmodem68EE8F6B2D682'
    log = Recorder('runs/hardware-fixture-buffer', mode='u2_first_midpoint_hold')
    source = Path(__file__).read_bytes()
    (log.path / 'controller-source.py').write_bytes(source)
    hold_attempted = False

    def present():
        return any(p.device == port and p.vid == 9025 and p.pid == 4098
                   and p.serial_number == '68EE8F6B2D68' for p in list_ports.comports())

    def exchange(board, command, kind, level=None):
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

    log.add('operator_power_report', {
        'raw_user_report': '확인했어 / 4.88V / 1.62V',
        'source': 'Operator report, not host-acquired voltages',
        'orientation_and_lead_clearance_requested_check_confirmed': True,
        'supply_v': 4.88, 'REF_J10_v': 1.62, 'meter_mode': 'DC 20V per instruction',
        'reference': 'Upper-left blue Arduino GND rail',
        'same_cable_port_and_jumpers_11_14_15': 'Retained per instruction',
        'powered_U2_follower_outputs_verified': False})
    log.add('configuration', {
        'port': port, 'source_sha256': hashlib.sha256(source).hexdigest(),
        'dut_connected': False, 'A1_A4_series_resistors_connected': True,
        'A5_connected': False, 'calibration_IN_OUT_bridge': True,
        'shunt_bypass': True, 'auxiliary_input_parked_at_REF': True,
        'target_nominal_mv': 1600, 'target_dac_code': 1337,
        'firmware': 'benchmate-dac-loopback-v1', 'boot_id_available': False,
        'required_initial_state': 'Fresh boot: DAC disabled, code 0, nominal level 0',
        'adc_capture': False, 'automatic_recovery': False})
    print(json.dumps({'record': str(log.path), 'state': 'preflight'}), flush=True)
    try:
        if not present():
            raise RuntimeError('Expected original USB board absent; no HOLD sent')
        with serial.Serial(port, 115200, timeout=3, write_timeout=2) as board:
            time.sleep(2)
            board.reset_input_buffer()
            initial = exchange(board, 'PING', 'pong')
            if initial.get('dac_enabled') is not False or initial.get('dac_code') != 0 or initial.get('nominal_level_mv') != 0:
                raise ValueError('Expected fresh disabled state; output left unchanged')
            hold_attempted = True
            exchange(board, 'HOLD 1600', 'holding', 1600)
            time.sleep(0.5)
            exchange(board, 'PING', 'pong', 1600)
        start = time.monotonic()
        for index in range(16):
            time.sleep(max(0, start + index - time.monotonic()))
            seen = present()
            log.add('post_hold_usb_sample', {'index': index, 'elapsed_s': time.monotonic()-start,
                                            'usb_device_present': seen, 'serial_port_closed': True})
            if not seen:
                raise RuntimeError('USB lost after HOLD; output may remain driven')
        with serial.Serial(port, 115200, timeout=3, write_timeout=2) as board:
            time.sleep(2)
            board.reset_input_buffer()
            exchange(board, 'PING', 'pong', 1600)
        result = {'nominal_level_mv': 1600, 'dac_code': 1337,
                  'post_reopen_state_verified': True, 'output_remains_driven': True,
                  'DMM_buffer_readings_pending': True, 'adc_capture_performed': False,
                  'calibration_performed': False}
        log.add('run_completed', result)
        print(json.dumps({'record': str(log.path), 'state': 'completed', **result}), flush=True)
    except (Exception, KeyboardInterrupt) as exc:
        result = {'error': str(exc) or type(exc).__name__, 'hold_attempted': hold_attempted,
                  'output_may_remain_driven': hold_attempted, 'automatic_recovery': False}
        log.add('run_failed', result)
        print(json.dumps({'record': str(log.path), 'state': 'failed', **result}), flush=True)
        raise SystemExit(1)


if __name__ == '__main__':
    main()
