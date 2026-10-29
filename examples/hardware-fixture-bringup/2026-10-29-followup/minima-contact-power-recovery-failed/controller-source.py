"""Confirm post-contact cold boot and explicitly restore only REF; no capture."""
from pathlib import Path
import json,time,hashlib,serial
from serial.tools import list_ports
from benchmate.records import Recorder,read_events
from benchmate.instrument import BootContinuity,InstrumentConfig,acquire_block
previous='cd496fa1aa18dcb15bae7d05553fe560';config=InstrumentConfig(vref_v=4.88,ref_v=1.63)
log=Recorder('runs/hardware-minima-probe-recovery',mode='post_contact_fresh_power_REF_and_explicit_rearm_no_capture')
for src,name in [(Path(__file__),'controller-source.py'),(Path('src/benchmate/instrument.py'),'host-instrument.py')]:
    (log.path/name).write_bytes(src.read_bytes())
log.add('operator_report',{'raw_user_report':'파랑 레일 기둥은 그대로 사용중이라 괜찮아. 빨강 레일 기둥 제거 완료 / 4.88V / 1.63V','actual_ground_probe':'Original blue-rail GND post retained; J27 relocation not performed','red_plus5V_probe_post_removed':True,'earlier_both_posts_removed_description':'Superseded by the explicit retained-blue-post clarification; earlier record remains unchanged.','prior_USB_off_and_no_persistent_rail_tone_reported':True,'USB_reconnected_per_power_reading_instruction':True,'supply_v':4.88,'REF_v':1.63,'meter_range':'DC 20 V per instruction','scope':'Fresh power/REF display, not driver/DAC recovery or calibrated accuracy'})
log.add('configuration',{'previous_boot_id':previous,'supply_conversion_v':4.88,'REF_target_v':1.63,'expected_code_after_ARM':config.ref_code,'DUT_absent_and_calibration_wiring_retained':True,'ARM_only_after_new_unarmed_boot_verified':True,'ADC_capture_requested':False,'high_point_not_requested':True})
print(json.dumps({'record':str(log.path),'stage':'preflight'}),flush=True)
try:
    ports=[p for p in list_ports.comports() if (p.vid,p.pid,p.serial_number)==(9025,105,'3612211F36323632E4B233334B572F52')]
    log.add('USB_preflight',{'matching_ports':[p.device for p in ports]})
    if len(ports)!=1:raise RuntimeError('Expected Minima absent or ambiguous')
    port=ports[0].device;guard=BootContinuity()
    for cycle in range(2):
        with serial.Serial(port,115200,timeout=5,write_timeout=2) as board:
            time.sleep(2);board.reset_input_buffer();board.write(b'PING\n')
            log.add('serial_command',{'cycle':cycle,'command':'PING'})
            raw=board.readline();log.add('serial_response_raw',{'cycle':cycle,'raw_text':raw.decode('utf-8',errors='replace')})
            if not raw.endswith(b'\n'):raise ValueError('Incomplete PING')
            packet=json.loads(raw);guard.check(packet)
            if guard.boot_id==previous:raise ValueError('Fresh boot not established after reported USB disconnection')
            if packet.get('type')!='pong' or packet.get('armed') is not False or packet.get('current_code')!=0 or packet.get('ref_code')!=0 or packet.get('dc_hold_supported') is not True:
                raise ValueError('Expected unarmed DC-capable startup state')
            if packet.get('adc_sample_state_channels')!=[0,1,2,21] or packet.get('adc_sample_states_readback')!=[255]*4:
                raise ValueError('Unexpected active ADC settings')
            log.add('fresh_unarmed_PING_verified',packet)
    print(json.dumps({'stage':'fresh_boot_verified','boot_id':guard.boot_id}),flush=True)
    arm_path,result=acquire_block(port,config,output='runs/hardware-minima-capture',arm_only=True,expected_boot_id=guard.boot_id)
    log.add('explicit_ARM_completed',{'record':str(arm_path),'result':result})
    post=next(e['payload'] for e in read_events(arm_path) if e['kind']=='firmware_postcheck')
    if post.get('current_code')!=config.ref_code:raise ValueError('Post-ARM output code not confirmed')
    log.add('run_completed',{'boot_id':guard.boot_id,'new_boot_verified':True,'ARM_record':str(arm_path),'held_code':config.ref_code,'nominal_target_v':1.63,'ADC_capture_requested':False,'driver_and_DAC_DMM_recovery_pending':True,'calibration_performed':False,'sweep_not_resumed':True})
    print(json.dumps({'record':str(log.path),'stage':'completed','boot_id':guard.boot_id,'held_code':config.ref_code}),flush=True)
except (Exception,KeyboardInterrupt) as exc:
    log.add('run_failed',{'error':str(exc) or type(exc).__name__,'automatic_retry_or_rearm':False,'ADC_capture_requested':False,'calibration_performed':False})
    print(json.dumps({'record':str(log.path),'stage':'failed','error':str(exc)}),flush=True);raise SystemExit(1)
