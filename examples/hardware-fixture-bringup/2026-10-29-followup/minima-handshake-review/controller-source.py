from pathlib import Path
from datetime import datetime,timezone
import json,time,serial
from serial.tools import list_ports
from benchmate.records import Recorder
log=Recorder('runs/hardware-minima-handshake-review',mode='read_only_PING_after_failed_handshake')
(log.path/'controller-source.py').write_bytes(Path(__file__).read_bytes())
expected='7dd3b19411ed4ecda7e4f286c8ce45f5'
log.add('scope',{'previous_failed_capture':'runs/hardware-minima-capture/20261029T022839-baeb98283f','expected_previous_boot_id':expected,'commands_allowed':['PING'],'no_ARM_CAPTURE_STOP_upload_or_reset':True,'measurement_retry':False})
def snapshot(stage):
    ports=[{'device':p.device,'vid':p.vid,'pid':p.pid,'serial':p.serial_number} for p in list_ports.comports() if p.vid==9025]
    log.add(stage,{'arduino_ports':ports});return ports
try:
    ports=snapshot('USB_before')
    matches=[p for p in ports if (p['vid'],p['pid'],p['serial'])==(9025,105,'3612211F36323632E4B233334B572F52')]
    if len(matches)!=1:raise RuntimeError('Minima absent or ambiguous')
    with serial.Serial(matches[0]['device'],115200,timeout=5,write_timeout=2) as board:
        time.sleep(2)
        existing=board.read(board.in_waiting)
        log.add('before_PING',{'queued_bytes':len(existing),'raw_text':existing.decode('utf-8',errors='replace')})
        board.write(b'PING\n');log.add('command_sent',{'command':'PING'})
        raw=board.readline()
        log.add('response',{'bytes_received':len(raw),'raw_text':raw.decode('utf-8',errors='replace')})
        if not raw:raise RuntimeError('No PING response within 5 seconds')
        p=json.loads(raw)
        if p.get('type')!='pong':raise RuntimeError('Not a PONG')
        log.add('run_completed',{'response':p,'same_as_previous_boot':p.get('boot_id')==expected,'stimulus_command_sent':False})
        print(json.dumps({'record':str(log.path),'result':p,'same_boot':p.get('boot_id')==expected}),flush=True)
except Exception as exc:
    snapshot('USB_after_failure')
    log.add('run_failed',{'error':str(exc),'boot_continuity_established':False,'stimulus_command_sent':False,'automatic_retry':False})
    print(json.dumps({'record':str(log.path),'error':str(exc)}),flush=True)
    raise SystemExit(1)
