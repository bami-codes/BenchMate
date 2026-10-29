"""One raw four-channel HOLD block after operator midpoint DMM confirmation."""
import hashlib
import json
from pathlib import Path
import numpy as np
from serial.tools import list_ports
from benchmate.records import Recorder, read_events
from benchmate.instrument import InstrumentConfig, acquire_block


def main():
    previous=Path('runs/hardware-minima-fixture/20261029T013558-074fdc0481')
    prior=read_events(previous)[-1]['payload']
    expected_boot=prior['boot_id']
    config=InstrumentConfig(vref_v=4.88,ref_v=1.62)
    settings={'kind':'hold','hold_v':1.62,'samples':512,'period_us':2000}
    log=Recorder('runs/hardware-minima-midpoint',mode='operator_DMM_and_first_fixture_ADC_block')
    (log.path/'controller-source.py').write_bytes(Path(__file__).read_bytes())
    log.add('operator_confirmation',{
        'raw_user_report':'1.61 / 1.61 / 1.61 / 1.62 이렇게나와 minima야',
        'board':'UNO R4 Minima','serial_number':'3612211F36323632E4B233334B572F52',
        'readings_v':{'D35_IN':1.61,'D40_OUT_buffer':1.61,'D45_drive':1.61,'D50_REF':1.62},
        'meter':'ANENG DM950; DC 20 V per instruction','voltage_reference':'Arduino GND',
        'sequential_not_simultaneous':True,'meter_display_resolution_v':0.01,
        'meter_accuracy_established':False,'transients':'not reported; absence is not independently established',
        'prior_supply_v':4.88,'prior_REF_v':1.62,'prior_control_run':str(previous),
        'fixture':'U1/U2, A1-A4 each through series 1k; calibration bridge IN-OUT; shunt bypass; auxiliary parked REF; no DUT',
        'expected_boot_id':expected_boot,'settings':settings,
        'source_sha256':{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in
            [Path(__file__),Path('src/benchmate/instrument.py'),Path('firmware/instrument/instrument.ino')]},
        'scope':'Raw uncalibrated midpoint acquisition; not gain/offset or noise-model calibration'})
    print(json.dumps({'record':str(log.path),'stage':'preflight'}),flush=True)
    try:
        found=[p for p in list_ports.comports() if (p.vid,p.pid,p.serial_number)==(9025,105,'3612211F36323632E4B233334B572F52')]
        log.add('USB_preflight',{'matching_ports':[p.device for p in found]})
        if len(found)!=1: raise RuntimeError('Expected Minima identity absent or ambiguous')
        path,result=acquire_block(found[0].device,config,output='runs/hardware-minima-capture',
                                  expected_boot_id=expected_boot,**settings)
        log.add('acquisition_record',{'path':str(path),'result':result})
        events=read_events(path)
        block=next(x['payload'] for x in events if x['kind']=='raw_capture')
        rows=np.array(block['rows'],dtype=np.int64)
        counts=rows[:,2:6];offsets=rows[:,6:10];dt=np.diff(rows[:,0])
        channels={}
        for i,name in enumerate(block['channels']):
            x=counts[:,i].astype(float);z=x-x.mean()
            lag=float(np.dot(z[:-1],z[1:])/np.dot(z,z)) if np.dot(z,z)>0 else None
            channels[name]={'mean_counts':float(x.mean()),'sample_std_counts':float(x.std(ddof=1)),
                'min_counts':int(x.min()),'max_counts':int(x.max()),
                'nominal_mean_v':float(x.mean()*config.vref_v/16383),
                'nominal_sample_std_mV':float(x.std(ddof=1)*config.vref_v/16383*1000),
                'within_block_lag1_estimate':lag,
                'read_completion_offset_us_mean':float(offsets[:,i].mean()),
                'read_completion_offset_us_min':int(offsets[:,i].min()),
                'read_completion_offset_us_max':int(offsets[:,i].max())}
        differences={}
        for a,b in [(1,0),(2,0),(3,2)]:
            d=counts[:,a]-counts[:,b]
            differences[f'A{a+1}_minus_A{b+1}']={'mean_counts':float(d.mean()),'std_counts':float(d.std(ddof=1)),
                'nominal_mean_mV':float(d.mean()*config.vref_v/16383*1000)}
        analysis={'source':'hardware_uncalibrated','capture_record':str(path),'samples_per_channel':len(rows),
            'requested_period_us':2000,'frame_interval_us':{'min':int(dt.min()),'max':int(dt.max()),
                'mean':float(dt.mean()),'std':float(dt.std(ddof=1))},
            'max_start_lateness_us':block['max_start_lateness_us'],'overruns':block['overruns'],
            'adc_sampling_state_readback':block['adc_sample_states_readback_min'],
            'channels':channels,'paired_DC_differences':differences,
            'interpretation_limits':['Voltage conversions use operator 4.88 V and ideal 16383 full scale; no channel correction.',
                'Single ~1 s block; lag1 estimates are descriptive, not a frozen AR(1) noise model.',
                'Read-completion offsets are not calibrated sampling apertures.',
                'DMM displays and ADC acquisition are sequential; DMM resolution is not accuracy.',
                'No DAC/ADC individual linearity, long-duration reliability or circuit diagnosis established.']}
        (log.path/'analysis.json').write_text(json.dumps(analysis,indent=2)+'\n')
        log.add('midpoint_analysis',analysis)
        log.add('run_completed',{'raw_capture':str(path),'accepted_frames':len(rows),'channels':4,
            'boot_id':expected_boot,'DMM_readings_recorded':True,'calibration_performed':False,
            'output_state':'Capture parks back at armed REF code 1359','automatic_retry':False})
        print(json.dumps({'record':str(log.path),'stage':'completed','capture':result,'analysis':analysis}),flush=True)
    except (Exception,KeyboardInterrupt) as exc:
        log.add('run_failed',{'error':str(exc) or type(exc).__name__,'automatic_retry_or_rearm':False,
                             'calibration_performed':False})
        print(json.dumps({'record':str(log.path),'stage':'failed','error':str(exc) or type(exc).__name__}),flush=True)
        raise SystemExit(1)


if __name__=='__main__': main()
