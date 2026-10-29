"""Upload the non-driving bring-up sketch to the identified USB-only spare."""
import hashlib
import json
from pathlib import Path
import subprocess
import time

import serial
from serial.tools import list_ports
from benchmate.records import Recorder


def main():
    identity = '3612211F36323632E4B233334B572F52'
    log = Recorder('runs/hardware-minima-bringup', mode='usb_only_upload_and_ping')
    build = Path('.arduino/build-minima-usb-check')
    sketch = Path('firmware/bringup/bringup.ino')
    script = Path(__file__).read_bytes()
    (log.path/'controller-source.py').write_bytes(script)
    (log.path/'bringup.ino').write_bytes(sketch.read_bytes())
    upload_started = False

    def ports():
        return [p for p in list_ports.comports()
                if p.vid == 9025 and p.pid == 105 and p.serial_number == identity]

    def ping(port, label):
        found = ports()
        if len(found) != 1 or found[0].device != port:
            raise RuntimeError('Expected Minima USB identity absent or port changed')
        with serial.Serial(port, 115200, timeout=3, write_timeout=2) as board:
            time.sleep(2)
            board.reset_input_buffer()
            log.add('serial_command', {'ascii': 'PING', 'label': label})
            board.write(b'PING\n'); board.flush()
            raw = board.read_until(b'\n', size=8192)
            log.add('serial_response_raw', {'ascii': raw.decode('ascii', errors='backslashreplace')})
            packet = json.loads(raw)
            expected = {'protocol': 'benchmate-bringup-v1', 'type': 'pong',
                        'adc_bits': 14, 'dac_enabled': False, 'calibrated': False}
            if packet != expected:
                raise ValueError('Unexpected bring-up PING state')

    log.add('operator_configuration', {
        'raw_user_report': '예비 보드 USB만 연결 완료',
        'fixture_attached': False, 'same_cable_and_Mac_port': 'Per instruction',
        'original_WiFi_fixture_leads': 'Seven leads retained; original USB unplugged per instruction',
        'FQBN': 'arduino:renesas_uno:minima', 'serial_number': identity,
        'firmware_source_sha256': hashlib.sha256(sketch.read_bytes()).hexdigest(),
        'binary_sha256': hashlib.sha256((build/'bringup.ino.bin').read_bytes()).hexdigest(),
        'controller_sha256': hashlib.sha256(script).hexdigest(),
        'compile_result': {'flash_bytes': 40208, 'static_ram_bytes': 5512},
        'DAC_drive_requested': False, 'ADC_capture_requested': False,
        'closed_port_observation_s': 60, 'boot_ID_available': False,
        'scope': 'USB-only identification/basic communication; not same-fixture reliability or calibration'})
    print(json.dumps({'record': str(log.path), 'state': 'preflight'}), flush=True)
    try:
        found = ports()
        if len(found) != 1:
            raise RuntimeError('Expected single spare Minima identity before upload')
        options = json.loads((build/'build.options.json').read_text())
        if options['fqbn'] != 'arduino:renesas_uno:minima':
            raise ValueError('Wrong build target')
        command = ['sh', 'scripts/arduino.sh', 'upload', '--fqbn', options['fqbn'],
                   '--port', found[0].device, '--input-dir', str(build), str(sketch.parent)]
        log.add('upload_started', {'command': command})
        upload_started = True
        result = subprocess.run(command, capture_output=True, text=True, timeout=60)
        (log.path/'upload.log').write_text(result.stdout + result.stderr)
        log.add('upload_result', {'returncode': result.returncode, 'file': 'upload.log'})
        print(json.dumps({'state': 'upload_finished', 'returncode': result.returncode}), flush=True)
        if result.returncode:
            raise RuntimeError('Upload failed; not retried')
        # Upload intentionally re-enumerates the target; wait once for application USB.
        deadline = time.monotonic() + 20
        while True:
            found = ports()
            if len(found) == 1: break
            if time.monotonic() >= deadline:
                raise RuntimeError('Minima application USB did not return after upload')
            time.sleep(0.5)
        port = found[0].device
        log.add('application_USB', {'port': port, 'serial_number': identity})
        for cycle in range(3):
            ping(port, f'open_close_{cycle+1}')
            log.add('open_close_cycle_passed', {'cycle': cycle+1})
            time.sleep(1)
        start = time.monotonic()
        for index in range(61):
            time.sleep(max(0, start + index - time.monotonic()))
            found = ports()
            seen = len(found) == 1 and found[0].device == port
            log.add('passive_USB_sample', {'index': index, 'elapsed_s': time.monotonic()-start,
                                           'expected_device_present': seen, 'serial_closed': True})
            if not seen: raise RuntimeError('USB disappeared during closed-port interval')
            if index % 20 == 0:
                print(json.dumps({'state': 'USB_watch', 'elapsed_s': index, 'present': True}), flush=True)
        ping(port, 'after_closed_port_interval')
        result = {'port': port, 'upload_completed': True, 'open_close_cycles_passed': 3,
                  'closed_port_USB_samples_present': 61, 'final_PING_verified': True,
                  'DAC_drive_requested': False, 'ADC_capture_requested': False,
                  'same_fixture_test_performed': False, 'cause_identified': False}
        log.add('run_completed', result)
        print(json.dumps({'record': str(log.path), 'state': 'completed', **result}), flush=True)
    except (Exception, KeyboardInterrupt) as exc:
        result = {'error': str(exc) or type(exc).__name__, 'upload_started': upload_started,
                  'automatic_recovery': False, 'DAC_drive_requested': False}
        log.add('run_failed', result)
        print(json.dumps({'record': str(log.path), 'state': 'failed', **result}), flush=True)
        raise SystemExit(1)


if __name__ == '__main__':
    main()
