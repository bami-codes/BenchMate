"""Record the operator's finer DC displays and acquire one same-setting comparison block."""
from pathlib import Path
import json
import numpy as np
from serial.tools import list_ports
from benchmate.records import Recorder,read_events
from benchmate.instrument import InstrumentConfig,acquire_block

boot='7dd3b19411ed4ecda7e4f286c8ce45f5'
config=InstrumentConfig(vref_v=4.86,ref_v=1.63)
dmm={'A1':1.631,'A2':1.630,'A3':1.631,'A4':1.629}
log=Recorder('runs/hardware-minima-precise-midpoint',mode='operator_DC_2V_report_and_current_ADC_comparison')
(log.path/'controller-source.py').write_bytes(Path(__file__).read_bytes())
log.add('operator_report',{'raw_user_report':'1.631/1.630 / 1.631/1.629이렇게고 1번칩 3번핀도 1.629',
    'D35_D40_D45_D50_v':list(dmm.values()),'U1_pin3_divider_v':1.629,
    'meter':'ANENG DM950, DC 2 V range per instruction','reference':'Arduino GND',
    'display_resolution_v':0.001,'accuracy_established':False,'sequential_not_simultaneous':True,
    'exact_contact_times':'not recorded','same_output_and_wiring_per_instruction':True,
    'supply_conversion_v':4.86,'supply_conversion_source':'earlier DC 20 V supply display, not freshly measured',
    'DAC_setting':1373,'expected_boot_id':boot,'fixture_revision':'A4 direct buffered REF; A1-A3 through 1k; no DUT'})
print(json.dumps({'record':str(log.path),'stage':'preflight'}),flush=True)
try:
    ports=[p for p in list_ports.comports() if (p.vid,p.pid,p.serial_number)==(9025,105,'3612211F36323632E4B233334B572F52')]
    log.add('USB_preflight',{'matching_ports':[p.device for p in ports]})
    if len(ports)!=1:raise RuntimeError('Expected Minima absent/ambiguous')
    path,result=acquire_block(ports[0].device,config,output='runs/hardware-minima-capture',expected_boot_id=boot,
                              kind='hold',hold_v=1.63,samples=512,period_us=2000)
    log.add('capture_record',{'path':str(path),'result':result})
    block=next(e['payload'] for e in read_events(path) if e['kind']=='raw_capture')
    a=np.asarray(block['rows']);counts=a[:,2:6].astype(float);means=counts.mean(axis=0);std=counts.std(axis=0,ddof=1)
    channels={}
    for i,name in enumerate(block['channels']):
        channels[name]={'mean_counts':float(means[i]),'std_counts':float(std[i]),'nominal_ADC_v':float(means[i]*4.86/16383),
            'operator_DMM_v':dmm[name],'nominal_ADC_minus_DMM_mV':float((means[i]*4.86/16383-dmm[name])*1000),
            'supply_implied_by_zero_offset_ideal_ADC_v':float(dmm[name]*16383/means[i])}
    delta={'nominal_ADC_A4_minus_A3_mV':float((means[3]-means[2])*4.86/16383*1000),
           'DMM_A4_minus_A3_mV':(dmm['A4']-dmm['A3'])*1000}
    analysis={'channels':channels,'relative_comparison':delta,
              'scope':'Sequential one-point comparison; cannot distinguish channel offset, gain, lead drop, dynamic/temporal change or DMM accuracy. No fit or gain correction applied.',
              'accepted_frames':len(a),'calibration_performed':False}
    (log.path/'analysis.json').write_text(json.dumps(analysis,indent=2)+'\n')
    log.add('one_point_comparison',analysis)
    log.add('run_completed',{'capture_record':str(path),'accepted_frames':len(a),'boot_id':boot,
                            'output_remains_at_code':1373,'calibration_performed':False})
    print(json.dumps({'record':str(log.path),'stage':'completed','analysis':analysis}),flush=True)
except (Exception,KeyboardInterrupt) as exc:
    log.add('run_failed',{'error':str(exc) or type(exc).__name__,'automatic_retry_or_rearm':False})
    print(json.dumps({'record':str(log.path),'stage':'failed','error':str(exc)}),flush=True)
    raise SystemExit(1)
