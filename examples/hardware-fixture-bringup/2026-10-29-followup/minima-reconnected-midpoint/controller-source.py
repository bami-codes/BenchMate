"""Explicit re-arm after operator USB reconnection, then one midpoint block."""
from pathlib import Path
import hashlib,json,numpy as np
from serial.tools import list_ports
from benchmate.records import Recorder,read_events
from benchmate.instrument import InstrumentConfig,acquire_block,response_identity
status_path=Path('runs/hardware-minima-sda-check/20261029T054628-fcf7911b05')
status=read_events(status_path)[-1]
assert status['kind']=='run_completed'
pong=status['payload']['response'];boot,_=response_identity(pong)
assert pong['armed'] is False
config=InstrumentConfig(vref_v=4.86,ref_v=1.63)
log=Recorder('runs/hardware-minima-reconnected-midpoint',mode='explicit_rearm_after_operator_USB_reconnection')
for src,name in [(Path(__file__),'controller-source.py'),(Path('src/benchmate/instrument.py'),'host-instrument.py'),(Path('firmware/instrument/instrument.ino'),'instrument.ino')]:
    (log.path/name).write_bytes(src.read_bytes())
log.add('operator_report',{'raw_user_report':'USB를 다시 연결했어','USB_reconnection_reported':True,'exact_reconnection_time':'not supplied','DMM_before_or_after_reconnection':'not supplied','prior_D50_SDA_report_v':[1.633,1.633],'reconnection_consistent_with_new_boot':True,'prior_unresponsive_root_cause_established':False})
log.add('configuration',{'read_only_status_record':str(status_path),'expected_boot_id':boot,'supply_conversion_v':4.86,'supply_source':'Earlier measured supply; not freshly remeasured','target_v':1.63,'ref_code':config.ref_code,'fixture_state':'Previously confirmed A4 direct fixed REF, A1-A3 1k series, no DUT, calibration jumpers unchanged in session','kind':'hold','samples':512,'period_us':2000,'source_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in log.path.iterdir() if p.name!='events.jsonl'},'scope':'One new-boot diagnostic block; not a calibration fit or uninterrupted continuation of prior boot'})
print(json.dumps({'record':str(log.path),'stage':'preflight'}),flush=True)
try:
    uploaded=Path('runs/hardware-minima-adc-fix/20261029T021205-69b721fd5f/instrument.ino')
    assert uploaded.read_bytes()==(log.path/'instrument.ino').read_bytes(),'Source changed since upload'
    found=[p for p in list_ports.comports() if (p.vid,p.pid,p.serial_number)==(9025,105,'3612211F36323632E4B233334B572F52')]
    log.add('USB_preflight',{'matching_ports':[p.device for p in found]})
    if len(found)!=1:raise RuntimeError('Expected Minima absent or ambiguous')
    arm_path,arm=acquire_block(found[0].device,config,output='runs/hardware-minima-capture',arm_only=True,expected_boot_id=boot)
    log.add('explicit_ARM_completed',{'record':str(arm_path),'result':arm})
    print(json.dumps({'stage':'armed','ref_code':config.ref_code}),flush=True)
    path,result=acquire_block(found[0].device,config,output='runs/hardware-minima-capture',expected_boot_id=boot,kind='hold',hold_v=1.63,samples=512,period_us=2000)
    log.add('capture_record',{'record':str(path),'result':result})
    block=next(e['payload'] for e in read_events(path) if e['kind']=='raw_capture')
    rows=np.asarray(block['rows']);channels={}
    for i,name in enumerate(block['channels']):
        x=rows[:,i+2].astype(float);mean=x.mean();sd=x.std(ddof=1)
        channels[name]={'mean_counts':float(mean),'std_counts':float(sd),'nominal_mean_v':float(mean*4.86/16383),'nominal_std_mV':float(sd*4.86/16383*1000),'nominal_max_deviation_mV':float(np.max(np.abs(x-mean))*4.86/16383*1000),'min_counts':int(x.min()),'max_counts':int(x.max())}
    analysis={'source':'hardware_uncalibrated','raw_capture_record':str(path),'accepted_frames':len(rows),'channels':channels,'frame_interval_us_min':int(np.diff(rows[:,0]).min()),'frame_interval_us_max':int(np.diff(rows[:,0]).max()),'overruns':block['overruns'],'ADC_states_before':block['adc_sample_states_readback_before'],'ADC_states_after':block['adc_sample_states_readback_after'],'limits':['Conversion uses earlier 4.86 V supply, not freshly measured.','DMM and ADC were not simultaneous; no ADC error or fit is calculated.','No trimming; this block does not establish long-duration communication reliability.']}
    (log.path/'analysis.json').write_text(json.dumps(analysis,indent=2)+'\n')
    log.add('raw_midpoint_analysis',analysis)
    log.add('run_completed',{'arm_record':str(arm_path),'capture_record':str(path),'boot_id':boot,'accepted_frames':len(rows),'parked_ref_code':config.ref_code,'calibration_performed':False})
    print(json.dumps({'record':str(log.path),'stage':'completed','analysis':analysis}),flush=True)
except (Exception,KeyboardInterrupt) as exc:
    log.add('run_failed',{'error':str(exc) or type(exc).__name__,'automatic_retry_or_rearm':False,'calibration_performed':False})
    print(json.dumps({'record':str(log.path),'stage':'failed','error':str(exc)}),flush=True)
    raise SystemExit(1)
