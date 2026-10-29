"""Preserve the operator's board-node voltage comparison and check PING once."""
from pathlib import Path
import json,time,serial
from serial.tools import list_ports
from benchmate.records import Recorder
log=Recorder('runs/hardware-minima-sda-check',mode='operator_voltage_report_and_read_only_status_check')
(log.path/'controller-source.py').write_bytes(Path(__file__).read_bytes())
previous='7dd3b19411ed4ecda7e4f286c8ce45f5'
log.add('operator_report',{'raw_user_report':'D50 1.633V, SDA 1.633V','D50_v':1.633,'board_SDA_v':1.633,'meter_range':'DC 2 V per instruction','reference':'upper-left blue Arduino-GND rail','display_resolution_v':0.001,'accuracy_established':False,'sequential_not_simultaneous':True,'instruction_to_leave_USB_wiring_RESET_unchanged':True,'contact_times':'not recorded','scope':'No displayed breadboard-to-board node difference at this check; does not establish zero resistance or ADC calibration.'})
log.add('scope',{'commands_allowed':['PING'],'stimulus_or_reset_or_upload_planned':False,'previous_boot_id':previous,'automatic_capture_retry':False,'next_if_still_unresponsive':'request operator single RESET; do not re-arm automatically'})
def snapshot(stage):
    found=[{'port':p.device,'vid':p.vid,'pid':p.pid,'serial':p.serial_number} for p in list_ports.comports() if p.vid==9025]
    log.add(stage,{'arduino_ports':found});return found
try:
    ports=snapshot('USB_before')
    matches=[p for p in ports if (p['vid'],p['pid'],p['serial'])==(9025,105,'3612211F36323632E4B233334B572F52')]
    if len(matches)!=1:raise RuntimeError('Expected Minima absent or ambiguous')
    with serial.Serial(matches[0]['port'],115200,timeout=5,write_timeout=2) as board:
        time.sleep(2)
        queued=board.read(board.in_waiting)
        log.add('queued_input',{'bytes_received':len(queued),'raw_text':queued.decode('utf-8',errors='replace')})
        board.write(b'PING\n');log.add('command_sent',{'command':'PING'})
        raw=board.readline();log.add('response',{'bytes_received':len(raw),'raw_text':raw.decode('utf-8',errors='replace')})
        if not raw:raise RuntimeError('No PING response within 5 seconds')
        pong=json.loads(raw)
        if pong.get('type')!='pong':raise RuntimeError('Not a PONG')
    snapshot('USB_after')
    result={'response':pong,'same_as_previous_boot':pong.get('boot_id')==previous,'stimulus_command_sent':False,'calibration_performed':False}
    log.add('run_completed',result);print(json.dumps({'record':str(log.path),'result':result}),flush=True)
except Exception as exc:
    snapshot('USB_after_failure')
    log.add('run_failed',{'error':str(exc),'boot_continuity_established':False,'stimulus_command_sent':False,'accepted_samples':0,'automatic_retry_or_rearm':False})
    print(json.dumps({'record':str(log.path),'error':str(exc)}),flush=True)
    raise SystemExit(1)
