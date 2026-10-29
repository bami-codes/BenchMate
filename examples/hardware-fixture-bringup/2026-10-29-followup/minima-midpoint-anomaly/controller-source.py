"""Record unexpected operator midpoint voltages and issue one PING only."""
from pathlib import Path
import json,time,serial
from serial.tools import list_ports
from benchmate.records import Recorder
from benchmate.instrument import response_identity
prior='runs/hardware-minima-dc-hold/20261029T061032-da350f724b'
expected='cd496fa1aa18dcb15bae7d05553fe560'
log=Recorder('runs/hardware-minima-midpoint-anomaly',mode='unexpected_DMM_report_PING_only_no_stimulus')
(log.path/'controller-source.py').write_bytes(Path(__file__).read_bytes())
log.add('operator_report',{'raw_user_report':'35/40/45가 3.28V로 포화됐어','D35_D40_D45_reported_v':[3.28,3.28,3.28],'D50_v':None,'actual_meter_range':'not reconfirmed; preceding instruction specified DC 2 V','saturation':'operator description; physical cause not established','reference_per_instruction':'upper-left blue Arduino-GND rail','prior_hold_record':prior,'expected_nominal_target_v':1.633,'expected_code':1368,'expected_boot_id':expected})
log.add('plan_stopped',{'high_point_not_commanded':True,'ADC_capture_not_requested':True,'calibration_fit_not_performed':True,'allowed_commands':['PING'],'next_required':'localize unexpected voltage with independent DMM checks; do not assume a cause or resume sweep'})
def snapshot(stage):
    ports=[{'port':p.device,'vid':p.vid,'pid':p.pid,'serial':p.serial_number} for p in list_ports.comports() if p.vid==9025]
    log.add(stage,{'arduino_ports':ports});return ports
try:
    matches=[p for p in snapshot('USB_before') if (p['vid'],p['pid'],p['serial'])==(9025,105,'3612211F36323632E4B233334B572F52')]
    if len(matches)!=1:raise RuntimeError('Expected Minima absent or ambiguous')
    with serial.Serial(matches[0]['port'],115200,timeout=5,write_timeout=2) as board:
        time.sleep(2)
        pending=board.read(board.in_waiting);log.add('queued_input',{'bytes_received':len(pending),'raw_text':pending.decode('utf-8',errors='replace')})
        board.write(b'PING\n');log.add('command_sent',{'command':'PING'})
        raw=board.readline();log.add('response_raw',{'bytes_received':len(raw),'raw_text':raw.decode('utf-8',errors='replace')})
        if not raw:raise RuntimeError('No PING response within 5 seconds')
        packet=json.loads(raw);boot,uptime=response_identity(packet)
        if packet.get('type')!='pong':raise RuntimeError('Not a PONG')
    snapshot('USB_after')
    result={'response':packet,'same_boot':boot==expected,'expected_code_reported':packet.get('current_code')==1368,'nominal_code_voltage_with_earlier_supply_v':packet.get('current_code',0)*4.89/4095,'physical_voltage_verified':False,'stimulus_command_sent':False,'ADC_capture_requested':False,'anomaly_unresolved':True}
    log.add('run_completed',result);print(json.dumps({'record':str(log.path),'result':result}),flush=True)
except Exception as exc:
    snapshot('USB_after_failure');log.add('run_failed',{'error':str(exc),'stimulus_command_sent':False,'ADC_capture_requested':False,'automatic_retry_or_rearm':False,'anomaly_unresolved':True})
    print(json.dumps({'record':str(log.path),'error':str(exc)}),flush=True);raise SystemExit(1)
