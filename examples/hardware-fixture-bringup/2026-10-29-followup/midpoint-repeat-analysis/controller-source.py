"""Two explicit additional DC blocks to check tails seen in the first valid block."""
from pathlib import Path
import json
import numpy as np
from serial.tools import list_ports
from benchmate.records import Recorder,read_events
from benchmate.instrument import InstrumentConfig,acquire_block

first=Path('runs/hardware-minima-corrected-midpoint/20261029T021311-bfd1fefbf3')
prior=read_events(first)[-1]['payload']
boot=prior['boot_id'];config=InstrumentConfig(vref_v=4.86,ref_v=1.63)
log=Recorder('runs/hardware-minima-midpoint-repeat',mode='two_DC_repeats_for_outlier_assessment')
(log.path/'controller-source.py').write_bytes(Path(__file__).read_bytes())
log.add('configuration',{'prior_accepted_block':prior['capture_record'],'expected_boot_id':boot,
 'reason':'First accepted 512-frame block had tails beyond several within-block standard deviations; assess persistence without deleting samples.',
 'repeat_count':2,'kind':'hold','target_v':1.63,'samples_per_block':512,'period_us':2000,
 'fixture_revision':'A4 direct fixed buffered REF, A1-A3 series 1k, no DUT',
 'calibration_performed':False,'automatic_recovery_or_rearm':False})
print(json.dumps({'record':str(log.path),'stage':'start'}),flush=True)
try:
    records=[prior['capture_record']]
    for index in range(2):
        ports=[p for p in list_ports.comports() if (p.vid,p.pid,p.serial_number)==(9025,105,'3612211F36323632E4B233334B572F52')]
        if len(ports)!=1:raise RuntimeError('Expected Minima absent/ambiguous')
        path,result=acquire_block(ports[0].device,config,output='runs/hardware-minima-capture',expected_boot_id=boot,
                                  kind='hold',hold_v=1.63,samples=512,period_us=2000)
        records.append(str(path));log.add('repeat_completed',{'index':index+1,'record':str(path),'result':result})
        print(json.dumps({'stage':'repeat_completed','index':index+1,'record':str(path)}),flush=True)
    summaries=[]
    for path in records:
        block=next(e['payload'] for e in read_events(path) if e['kind']=='raw_capture')
        a=np.array(block['rows']);x=a[:,2:6].astype(float);channels={}
        for i in range(4):
            z=x[:,i];med=float(np.median(z));sd=float(z.std(ddof=1));dev=np.abs(z-z.mean())
            channels[f'A{i+1}']={'mean_counts':float(z.mean()),'std_counts':sd,'median_counts':med,
                'MAD_counts':float(np.median(np.abs(z-med))),'max_abs_deviation_counts':float(dev.max()),
                'nominal_mean_v':float(z.mean()*4.86/16383),'nominal_std_mV':sd*4.86/16383*1000,
                'nominal_max_deviation_mV':float(dev.max()*4.86/16383*1000),
                'count_beyond_5_within_block_sd':int(np.sum(dev>5*sd)),'percentiles_counts':np.percentile(z,[0,1,50,99,100]).tolist()}
        summaries.append({'record':path,'channels':channels,'pairwise_correlation':np.corrcoef(x.T).tolist(),
            'frame_interval_us_min':int(np.diff(a[:,0]).min()),'frame_interval_us_max':int(np.diff(a[:,0]).max()),
            'overruns':block['overruns'],'ADC_states_before':block['adc_sample_states_readback_before'],
            'ADC_states_after':block['adc_sample_states_readback_after']})
    report={'blocks':summaries,'scope':'Descriptive diagnostic statistics; no trimming, denoising, frozen noise model or calibration acceptance.'}
    (log.path/'analysis.json').write_text(json.dumps(report,indent=2)+'\n')
    log.add('diagnostic_analysis',report)
    log.add('run_completed',{'additional_blocks':2,'additional_frames':1024,'boot_id':boot,
        'records':records,'output_state':'parked at code 1373, nominal REF 1.63 V','calibration_performed':False})
    print(json.dumps({'record':str(log.path),'stage':'completed','analysis':report}),flush=True)
except (Exception,KeyboardInterrupt) as exc:
    log.add('run_failed',{'error':str(exc) or type(exc).__name__,'automatic_recovery_or_rearm':False})
    print(json.dumps({'record':str(log.path),'stage':'failed','error':str(exc)}),flush=True)
    raise SystemExit(1)
