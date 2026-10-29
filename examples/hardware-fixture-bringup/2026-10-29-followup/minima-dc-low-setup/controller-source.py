"""Explicit ARM and first low DC calibration level; no ADC block yet."""
from pathlib import Path
import json,hashlib
from serial.tools import list_ports
from benchmate.records import Recorder,read_events
from benchmate.instrument import InstrumentConfig,acquire_block,set_dc_level
upload=Path('runs/hardware-minima-dc-upload/20261029T060304-97be44864a');events=read_events(upload);last=events[-1]
assert last['kind']=='run_completed' and last['payload']['dc_hold_supported'] is True and last['payload']['armed'] is False
assert (upload/'instrument.ino').read_bytes()==Path('firmware/instrument/instrument.ino').read_bytes()
boot=last['payload']['boot_id'];config=InstrumentConfig(vref_v=4.89,ref_v=1.633)
log=Recorder('runs/hardware-minima-dc-calibration',mode='first_persistent_low_point_setup_no_ADC_block')
for src,name in [(Path(__file__),'controller-source.py'),(Path('src/benchmate/instrument.py'),'host-instrument.py')]:
    (log.path/name).write_bytes(src.read_bytes())
log.add('configuration',{'upload_record':str(upload),'expected_boot_id':boot,'supply_v':4.89,'supply_basis':'Latest operator DC 20 V display before manual DFU upload','REF_target_v':1.633,'DC_target_v':.633,'fixture_state':'Confirmed calibration bridge and shunt bypass remain; A1-A3 through 1k, A4 directly to fixed buffered REF; no DUT','ADC_capture_requested':False,'scope':'Persistent low point for upcoming DMM report, not a calibration fit'})
print(json.dumps({'record':str(log.path),'stage':'preflight'}),flush=True)
try:
    ports=[p for p in list_ports.comports() if (p.vid,p.pid,p.serial_number)==(9025,105,'3612211F36323632E4B233334B572F52')]
    log.add('USB_preflight',{'matching_ports':[p.device for p in ports]})
    if len(ports)!=1:raise RuntimeError('Expected Minima absent or ambiguous')
    arm_path,arm=acquire_block(ports[0].device,config,output='runs/hardware-minima-capture',arm_only=True,expected_boot_id=boot)
    log.add('explicit_ARM_completed',{'record':str(arm_path),'result':arm})
    print(json.dumps({'stage':'armed','ref_code':config.ref_code,'boot_id':boot}),flush=True)
    hold_path,hold=set_dc_level(ports[0].device,config,hold_v=.633,expected_boot_id=boot,output='runs/hardware-minima-dc-hold')
    log.add('DC_hold_completed',{'record':str(hold_path),'result':hold})
    log.add('run_completed',{'arm_record':str(arm_path),'DC_hold_record':str(hold_path),'boot_id':boot,'held_code':hold['held_code'],'nominal_target_v':.633,'DMM_readings_pending':True,'ADC_block_acquired':False,'calibration_performed':False})
    print(json.dumps({'record':str(log.path),'stage':'completed','held_code':hold['held_code'],'boot_id':boot}),flush=True)
except (Exception,KeyboardInterrupt) as exc:
    log.add('run_failed',{'error':str(exc) or type(exc).__name__,'automatic_retry_or_rearm':False,'calibration_performed':False})
    print(json.dumps({'record':str(log.path),'stage':'failed','error':str(exc)}),flush=True);raise SystemExit(1)
