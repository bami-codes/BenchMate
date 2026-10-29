"""Pair one reported DMM point with a same-boot ADC block, then set the next level."""
from pathlib import Path
import argparse,hashlib,json,numpy as np
from serial.tools import list_ports
from benchmate.records import Recorder,read_events
from benchmate.instrument import InstrumentConfig,acquire_block,set_dc_level
p=argparse.ArgumentParser();p.add_argument('--confirmation',required=True);args=p.parse_args()
c=json.loads(Path(args.confirmation).read_text());held_events=read_events(c['prior_hold_record']);held=held_events[-1]
assert held['kind']=='run_completed'
held=held['payload'];boot=held['boot_id'];code=held['held_code']
config_data=next(e['payload']['configuration'] for e in held_events
                 if e['kind'] in ('DC_configuration','configuration') and 'configuration' in e['payload'])
target=held.get('nominal_target_v',config_data['ref_v'])
config=InstrumentConfig(**config_data);dmm=c['dmm_nodes_v'];assert len(dmm)==4 and all(type(v) in (float,int) and 0<=v<=config.vref_v for v in dmm)
log=Recorder('runs/hardware-minima-dc-point',mode='single_DC_point_DMM_then_ADC_no_calibration_fit')
for src,name in [(Path(__file__),'controller-source.py'),(Path('src/benchmate/instrument.py'),'host-instrument.py')]:
    (log.path/name).write_bytes(src.read_bytes())
log.add('operator_report',c)
log.add('configuration',{'expected_boot_id':boot,'prior_held_code':code,'nominal_target_v':target,'configuration':config_data,'samples':512,'period_us':2000,'source_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in log.path.iterdir() if p.name!='events.jsonl'},'scope':'Sequential DMM and ADC, no per-channel fit; A4 remains fixed REF, not a swept channel'})
print(json.dumps({'record':str(log.path),'stage':'preflight','point':c['point']}),flush=True)
try:
    ports=[p for p in list_ports.comports() if (p.vid,p.pid,p.serial_number)==(9025,105,'3612211F36323632E4B233334B572F52')]
    log.add('USB_preflight',{'matching_ports':[p.device for p in ports]})
    if len(ports)!=1:raise RuntimeError('Expected Minima absent or ambiguous')
    capture_path,result=acquire_block(ports[0].device,config,output='runs/hardware-minima-capture',expected_boot_id=boot,kind='hold',hold_v=target,samples=512,period_us=2000)
    log.add('capture_record',{'record':str(capture_path),'result':result})
    ce=read_events(capture_path);before=next(e['payload'] for e in ce if e['kind']=='firmware_handshake')
    if before.get('current_code')!=code:raise ValueError('Capture is raw-valid but prior held code differs; DMM pair is invalid')
    block=next(e['payload'] for e in ce if e['kind']=='raw_capture');rows=np.asarray(block['rows']);channels={}
    for i,name in enumerate(block['channels']):
        x=rows[:,i+2].astype(float);v=float(x.mean()*config.vref_v/16383)
        channels[name]={'mean_counts':float(x.mean()),'std_counts':float(x.std(ddof=1)),'min_counts':int(x.min()),'max_counts':int(x.max()),'nominal_mean_v':v,'DMM_v':dmm[i],'sequential_nominal_ADC_minus_DMM_mV':(v-dmm[i])*1000,'nominal_std_mV':float(x.std(ddof=1)*config.vref_v/16383*1000),'max_abs_deviation_counts':float(np.max(np.abs(x-x.mean())))}
    analysis={'point':c['point'],'raw_capture_record':str(capture_path),'samples_per_channel':len(rows),'boot_id':boot,'held_code_before_capture':before['current_code'],'channels':channels,'frame_interval_us_min':int(np.diff(rows[:,0]).min()),'frame_interval_us_max':int(np.diff(rows[:,0]).max()),'overruns':block['overruns'],'ADC_states_before':block['adc_sample_states_readback_before'],'ADC_states_after':block['adc_sample_states_readback_after'],'limits':['Sequential DMM report then ADC; not simultaneous, DMM accuracy not established.',f'Nominal volts use the recorded {config.vref_v:g} V supply display, not an independently frozen gain.','A4 is fixed REF; no A4 multi-point gain calibration.','No trimming or calibration acceptance from this block.']}
    (log.path/'analysis.json').write_text(json.dumps(analysis,indent=2)+'\n');log.add('raw_point_analysis',analysis)
    print(json.dumps({'stage':'captured','analysis':analysis}),flush=True)
    next_record=None;next_result=None
    if c.get('next_target_v') is not None:
        next_path,next_result=set_dc_level(ports[0].device,config,hold_v=c['next_target_v'],expected_boot_id=boot,output='runs/hardware-minima-dc-hold')
        next_record=str(next_path);log.add('next_DC_hold_completed',{'record':next_record,'result':next_result})
    log.add('run_completed',{'capture_record':str(capture_path),'accepted_frames':len(rows),'boot_id':boot,'next_hold_record':next_record,'next_hold_result':next_result,'calibration_performed':False})
    print(json.dumps({'record':str(log.path),'stage':'completed','next_hold_record':next_record,'next_hold_result':next_result}),flush=True)
except (Exception,KeyboardInterrupt) as exc:
    log.add('run_failed',{'error':str(exc) or type(exc).__name__,'automatic_retry_or_rearm':False,'calibration_performed':False})
    print(json.dumps({'record':str(log.path),'stage':'failed','error':str(exc)}),flush=True);raise SystemExit(1)
