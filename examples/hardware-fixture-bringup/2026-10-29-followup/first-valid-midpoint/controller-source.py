"""Explicit arm and one raw HOLD block after the confirmed A4 fixture correction."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
from serial.tools import list_ports
from benchmate.records import Recorder, read_events
from benchmate.instrument import InstrumentConfig, acquire_block


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--upload-run',required=True)
    parser.add_argument('--confirmation',required=True)
    args=parser.parse_args()
    upload=read_events(args.upload_run)
    if upload[-1]['kind']!='run_completed' or upload[-1]['payload'].get('active_ADC_states')!=[255]*4:
        raise ValueError('Need completed fixed-firmware upload/PING run')
    config_entry=next(e['payload'] for e in upload if e['kind']=='configuration')
    firmware=Path('firmware/instrument/instrument.ino')
    if hashlib.sha256(firmware.read_bytes()).hexdigest()!=config_entry['sources_sha256']['instrument.ino']:
        raise ValueError('Working firmware differs from recorded upload')
    confirmation=json.loads(Path(args.confirmation).read_text())
    if not all(confirmation.get(k) is True for k in ('D50_G50_jumper_installed','A4_wire_reconnected','D50_G50_continuity','USB_reconnected','DUT_absent')):
        raise ValueError('Missing physical configuration confirmation')
    config=InstrumentConfig(vref_v=confirmation['supply_v'],ref_v=confirmation['D50_v'])
    boot=upload[-1]['payload']['boot_id']
    log=Recorder('runs/hardware-minima-corrected-midpoint',mode='fixed_REF_sense_and_active_ADC_state_first_hold')
    for src,name in [(Path(__file__),'controller-source.py'),(firmware,'instrument.ino'),
                     (Path('src/benchmate/instrument.py'),'host-instrument.py')]:
        (log.path/name).write_bytes(src.read_bytes())
    log.add('configuration',{'operator_confirmation':confirmation,'upload_run':args.upload_run,
        'expected_boot_id':boot,'output_target_v':config.ref_v,'supply_conversion_v':config.vref_v,
        'settings':{'samples':512,'period_us':2000,'kind':'hold'},
        'DMM_scope':'Supply and fixed REF measured before upload; driven A1-A3 nodes not independently remeasured at this new target yet.',
        'scope':'Raw uncalibrated midpoint block, not completed gain/offset or AR(1) calibration.',
        'source_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in log.path.iterdir() if p.name!='events.jsonl'}})
    print(json.dumps({'record':str(log.path),'stage':'preflight'}),flush=True)
    try:
        found=[p for p in list_ports.comports() if (p.vid,p.pid,p.serial_number)==(9025,105,'3612211F36323632E4B233334B572F52')]
        log.add('USB_preflight',{'matching_ports':[p.device for p in found]})
        if len(found)!=1: raise RuntimeError('Expected Minima identity absent or ambiguous')
        arm_path,arm=acquire_block(found[0].device,config,output='runs/hardware-minima-capture',arm_only=True,expected_boot_id=boot)
        log.add('explicit_ARM_completed',{'record':str(arm_path),'result':arm,
                                       'meaning':'Firmware state, not independently measured output voltage'})
        print(json.dumps({'stage':'armed','ref_code':config.ref_code,'boot_id':boot}),flush=True)
        capture_path,result=acquire_block(found[0].device,config,output='runs/hardware-minima-capture',expected_boot_id=boot,
                                           kind='hold',hold_v=config.ref_v,samples=512,period_us=2000)
        log.add('capture_record',{'record':str(capture_path),'result':result})
        block=next(e['payload'] for e in read_events(capture_path) if e['kind']=='raw_capture')
        rows=np.array(block['rows'],dtype=np.int64);x=rows[:,2:6];offsets=rows[:,6:10];dt=np.diff(rows[:,0])
        channels={}
        for i,name in enumerate(block['channels']):
            z=x[:,i].astype(float);demean=z-z.mean()
            denom=float(np.dot(demean,demean))
            channels[name]={'mean_counts':float(z.mean()),'sample_std_counts':float(z.std(ddof=1)),
                'min_counts':int(z.min()),'max_counts':int(z.max()),
                'nominal_mean_v':float(z.mean()*config.vref_v/16383),
                'nominal_sample_std_mV':float(z.std(ddof=1)*config.vref_v/16383*1000),
                'within_block_lag1_estimate':float(np.dot(demean[:-1],demean[1:])/denom) if denom else None,
                'read_completion_offset_us':{'min':int(offsets[:,i].min()),'max':int(offsets[:,i].max()),'mean':float(offsets[:,i].mean())}}
        analysis={'source':'hardware_uncalibrated','samples_per_channel':len(rows),'raw_capture_record':str(capture_path),
            'period_us_requested':2000,'frame_interval_us':{'min':int(dt.min()),'max':int(dt.max()),'mean':float(dt.mean()),'std':float(dt.std(ddof=1))},
            'max_start_lateness_us':block['max_start_lateness_us'],'overruns':block['overruns'],
            'ADC_channel_mapping':block['adc_sample_state_channels'],
            'ADC_states_before':block['adc_sample_states_readback_before'],'ADC_states_after':block['adc_sample_states_readback_after'],
            'channels':channels,
            'limitations':['Voltages use reported 4.86 V / ideal full-scale 16383, no calibrated channel correction.',
                'Single approximately 1 s block; within-block lag1 is descriptive, not a frozen noise model.',
                'Read-completion times are not calibrated sample apertures.',
                'No multi-point linearity, frequency response, long-duration stability, or DUT diagnosis established.']}
        (log.path/'analysis.json').write_text(json.dumps(analysis,indent=2)+'\n')
        log.add('raw_midpoint_analysis',analysis)
        log.add('run_completed',{'capture_record':str(capture_path),'arm_record':str(arm_path),'accepted_frames':len(rows),
            'channels':4,'boot_id':boot,'calibration_performed':False,'output_remains_driven':True,'parked_ref_code':config.ref_code})
        print(json.dumps({'record':str(log.path),'stage':'completed','analysis':analysis}),flush=True)
    except (Exception,KeyboardInterrupt) as exc:
        log.add('run_failed',{'error':str(exc) or type(exc).__name__,'automatic_retry_or_rearm':False,'calibration_performed':False})
        print(json.dumps({'record':str(log.path),'stage':'failed','error':str(exc) or type(exc).__name__}),flush=True)
        raise SystemExit(1)


if __name__=='__main__': main()
