"""Upload/PING the active-channel ADC-state fix after confirmed REF wiring. No ARM or CAPTURE."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import time
import serial
from serial.tools import list_ports
from benchmate.records import Recorder
from benchmate.instrument import BootContinuity

IDENTITY = '3612211F36323632E4B233334B572F52'
BUILD = Path('.arduino/build-minima-adc-check')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dfu-mode', action='store_true')
    parser.add_argument('--confirmation', required=True)
    args = parser.parse_args()
    confirmation=json.loads(Path(args.confirmation).read_text())
    for field in ('D50_G50_jumper_installed','A4_wire_reconnected','D50_G50_continuity','USB_reconnected','DUT_absent'):
        if confirmation.get(field) is not True: raise ValueError('Missing fixture confirmation: '+field)
    if not 4<=confirmation['supply_v']<=5.5 or abs(confirmation['D50_v']-confirmation['G50_v'])>.03:
        raise ValueError('Unexpected supply or REF-node mismatch')
    log = Recorder('runs/hardware-minima-adc-fix', mode='fixture_connected_ADC_state_fix_upload_and_PING')
    log.add('operator_configuration', confirmation)
    continuity = BootContinuity()
    for source in [Path(__file__), Path('firmware/instrument/instrument.ino'),
                   Path('firmware/instrument/boot_identity.h'), Path('runs/minima-adc-check-compile.log')]:
        dest = 'controller-source.py' if source == Path(__file__) else source.name
        (log.path/dest).write_bytes(source.read_bytes())
    log.add('configuration', {
        'fixture_attached': True,
        'operator_basis': 'Explicit fixture correction and DMM confirmation file',
        'serial_number': IDENTITY, 'fqbn': 'arduino:renesas_uno:minima',
        'expected_start_mode': 'manual_DFU' if args.dfu_mode else 'instrument_v2_application',
        'binary_sha256': hashlib.sha256((BUILD/'instrument.ino.bin').read_bytes()).hexdigest(),
        'sources_sha256': {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                           for p in log.path.iterdir() if p.name != 'events.jsonl'},
        'output_commands_requested': False, 'ADC_capture_requested': False,
        'physical_reset_test_performed': False, 'fixture_connected_during_USB_observation': True, 'same_fixture_long_term_stability_established': False})
    print(json.dumps({'record': str(log.path), 'stage': 'preflight'}), flush=True)

    def ports():
        return [p for p in list_ports.comports()
                if (p.vid, p.pid, p.serial_number) == (9025,105,IDENTITY)]

    def ping(port, label):
        found = ports()
        if len(found) != 1 or found[0].device != port:
            raise RuntimeError('Minima identity/port disappeared or changed')
        with serial.Serial(port,115200,timeout=3,write_timeout=2) as board:
            time.sleep(2)
            board.reset_input_buffer()
            log.add('serial_command', {'ascii': 'PING', 'label': label})
            board.write(b'PING\n'); board.flush()
            raw = board.read_until(b'\n',size=8192)
            log.add('serial_response_raw', {'ascii': raw.decode('ascii',errors='backslashreplace')})
            if not raw.endswith(b'\n'): raise ValueError('Truncated or absent PING response')
            packet = json.loads(raw)
            continuity.check(packet)
            if (packet.get('type') != 'pong' or packet.get('armed') is not False or
                packet.get('calibrated') is not False or packet.get('adc_bits') != 14 or
                packet.get('dac_bits') != 12 or packet.get('ref_code') != 0):
                raise ValueError('Unexpected instrument v2 unarmed state')
            if packet.get('adc_sample_state_channels') != [0,1,2,21] or packet.get('adc_sample_states_readback') != [255]*4:
                raise ValueError('Active ADC state readback not all 255')
            log.add('unarmed_PING_verified', packet)
            return packet

    try:
        options = json.loads((BUILD/'build.options.json').read_text())
        if options['fqbn'] != 'arduino:renesas_uno:minima': raise ValueError('Wrong target build')
        command = ['sh','scripts/arduino.sh','upload','--fqbn',options['fqbn']]
        if args.dfu_mode:
            query = subprocess.run([
                '.arduino/data/packages/arduino/tools/dfu-util/0.11.0-arduino5/dfu-util',
                '--device','2341:0369','--list'],capture_output=True,text=True,timeout=10)
            log.add('DFU_preflight', {'stdout':query.stdout,'stderr':query.stderr,'returncode':query.returncode})
            targets = [s for s in query.stdout.splitlines() if 'Found DFU:' in s]
            if query.returncode or not targets or any(f'serial="{IDENTITY}"' not in s for s in targets):
                raise RuntimeError('Expected identified spare in accessible DFU')
        else:
            found = ports()
            log.add('USB_preflight', {'matching_ports':[p.device for p in found]})
            if len(found) != 1: raise RuntimeError('Expected one identified spare application port')
            command += ['--port',found[0].device]
        command += ['--input-dir',str(BUILD),'firmware/instrument']
        log.add('upload_started', {'command':command})
        result = subprocess.run(command,capture_output=True,text=True,timeout=60)
        (log.path/'upload.log').write_text(result.stdout+result.stderr)
        log.add('upload_result', {'returncode':result.returncode,'file':'upload.log'})
        print(json.dumps({'stage':'upload_finished','returncode':result.returncode}),flush=True)
        if result.returncode: raise RuntimeError('Upload failed; no automatic retry')
        deadline=time.monotonic()+20
        while True:
            found=ports()
            if len(found)==1: break
            if time.monotonic()>=deadline: raise RuntimeError('Application USB did not return after upload')
            time.sleep(.5)
        port=found[0].device
        log.add('application_USB', {'port':port,'serial_number':IDENTITY})
        packets=[]
        for cycle in range(3):
            packets.append(ping(port,f'open_close_{cycle+1}'))
            time.sleep(1)
        start=time.monotonic()
        for index in range(31):
            time.sleep(max(0,start+index-time.monotonic()))
            found=ports()
            present=len(found)==1 and found[0].device==port
            log.add('passive_USB_sample', {'index':index,'elapsed_s':time.monotonic()-start,
                                         'present':present,'serial_closed':True})
            if not present: raise RuntimeError('USB disappeared with serial closed')
            if index%15==0: print(json.dumps({'stage':'USB_watch','elapsed_s':index}),flush=True)
        packets.append(ping(port,'after_closed_port_interval'))
        if packets[-1]['uptime_ms'] <= packets[0]['uptime_ms']:
            raise ValueError('Uptime did not advance')
        summary={'upload_completed':True,'port':port,'boot_id':continuity.boot_id,
                 'boot_id_ready':True,'PINGs_verified':len(packets),
                 'uptime_ms_first':packets[0]['uptime_ms'],'uptime_ms_last':packets[-1]['uptime_ms'],
                 'closed_port_USB_samples_present':31,'same_boot_across_port_cycles':True,
                 'armed':False,'active_ADC_states':[255]*4,'output_commands_requested':False,'ADC_capture_requested':False,
                 'physical_reset_test_performed':False,'fixture_connected_during_USB_observation':True,'long_duration_stability_established':False}
        log.add('run_completed',summary)
        print(json.dumps({'record':str(log.path),'stage':'completed',**summary}),flush=True)
    except (Exception, KeyboardInterrupt) as exc:
        result={'error':str(exc) or type(exc).__name__,'automatic_retry':False,
                'output_commands_requested':False,'ADC_capture_requested':False}
        log.add('run_failed',result)
        print(json.dumps({'record':str(log.path),'stage':'failed',**result}),flush=True)
        raise SystemExit(1)


if __name__=='__main__': main()
