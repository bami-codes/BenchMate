"""Recompute a prior raw block using the later operator supply display; no IO."""
from pathlib import Path
import json,numpy as np
from benchmate.records import Recorder,read_events
source=Path('runs/hardware-minima-capture/20261029T054821-4327661a62')
events=read_events(source);assert events[-1]['kind']=='run_completed'
b=next(e['payload'] for e in events if e['kind']=='raw_capture');means=np.asarray(b['rows'])[:,2:6].mean(axis=0)
log=Recorder('runs/hardware-minima-supply-comparison',mode='offline_sequential_DMM_and_ADC_comparison')
(log.path/'controller-source.py').write_bytes(Path(__file__).read_bytes())
log.add('operator_report',{'raw_user_report':'4.89V / 1.636V / 1.633V','supply_v':4.89,'D45_v':1.636,'D50_v':1.633,'supply_meter_range':'DC 20 V','signal_meter_range':'DC 2 V','reference':'upper-left blue Arduino-GND rail','instruction_to_leave_USB_wiring_RESET_unchanged':True,'supply_display_resolution_v':0.01,'signal_display_resolution_v':0.001,'meter_accuracy_established':False,'sequential_not_simultaneous':True})
channels={}
for i,name in enumerate(b['channels']):
    v=float(means[i]*4.89/16383)
    entry={'mean_counts':float(means[i]),'nominal_v_using_old_4_86_supply':float(means[i]*4.86/16383),'nominal_v_using_later_4_89_supply':v}
    if name in ('A3','A4'):
        dmm={'A3':1.636,'A4':1.633}[name];entry.update({'operator_DMM_v':dmm,'sequential_ADC_minus_DMM_mV':(v-dmm)*1000})
    channels[name]=entry
analysis={'raw_capture_record':str(source),'capture_boot_id':b['boot_id'],'channels':channels,'assumptions':['ADC full-scale 16383 and later supply display 4.89 V; no channel gain/offset fit.','Later supply may differ from supply during capture; DMM readings are sequential.','Display agreement is not an accuracy bound.'],'calibration_performed':False,'hardware_commands_sent':False,'original_record_changed':False}
(log.path/'analysis.json').write_text(json.dumps(analysis,indent=2)+'\n');log.add('offline_comparison',analysis)
log.add('run_completed',{'raw_capture_record':str(source),'calibration_performed':False,'hardware_commands_sent':False})
print(json.dumps({'record':str(log.path),'analysis':analysis}),flush=True)
