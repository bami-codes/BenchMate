"""One small-signal loopback check after provisional DC fitting; no retries."""
from pathlib import Path
import hashlib,json
import numpy as np
from serial.tools import list_ports
from benchmate.records import Recorder,read_events
from benchmate.instrument import InstrumentConfig,acquire_block

profile_path=Path('runs/hardware-minima-three-point-analysis/20261029T103049-22aa45da34/provisional-calibration.json')
profile=json.loads(profile_path.read_text())
boot='58d7c1c8418e4792edb4628854a46bb1'
config=InstrumentConfig(4.88,1.631)
log=Recorder('runs/hardware-minima-loopback-sine-check',mode='small_signal_fixture_consistency_not_full_calibration')
for source,name in [(Path(__file__),'controller-source.py'),(Path('src/benchmate/instrument.py'),'host-instrument.py'),(profile_path,'provisional-calibration.json')]:
    (log.path/name).write_bytes(source.read_bytes())
log.add('predeclared_check',{
    'boot_id':boot,'DUT_absent_calibration_bridge_and_shunt_bypass_retained':True,
    'frequency_hz':5,'nominal_amplitude_v':0.2,'samples':512,'period_us':2000,
    'profile_sha256':hashlib.sha256(profile_path.read_bytes()).hexdigest(),
    'reference':'Sinusoid fit to calibrated A3 driver, evaluated at each channel read-completion timestamp',
    'A1_A2_limits':{'RMS_vs_fitted_driver_mV_max':5,'fitted_amplitude_ratio_error_percent_max':1,'relative_phase_deg_max':2},
    'no_fit_changes_from_this_check':True,
    'scope':'One small-signal frequency, same fixture; not unknown-circuit inference, full band validation or A4 gain calibration.',
    'output_parks_at_REF_after_capture':True,'automatic_retry_or_rearm':False})
print(json.dumps({'record':str(log.path),'stage':'preflight'}),flush=True)
try:
    ports=[p for p in list_ports.comports() if (p.vid,p.pid,p.serial_number)==(9025,105,'3612211F36323632E4B233334B572F52')]
    log.add('USB_preflight',{'matching_ports':[p.device for p in ports]})
    if len(ports)!=1:raise RuntimeError('Expected Minima absent or ambiguous')
    cap,result=acquire_block(ports[0].device,config,output='runs/hardware-minima-capture',expected_boot_id=boot,kind='sine',frequency_hz=5,amplitude_v=.2,samples=512,period_us=2000)
    log.add('capture_record',{'record':str(cap),'result':result})
    events=read_events(cap);raw=next(e['payload'] for e in events if e['kind']=='raw_capture')
    rows=np.asarray(raw['rows']);channels={};signals={};fits={};times={}
    def design(t):return np.column_stack([np.sin(2*np.pi*5*t),np.cos(2*np.pi*5*t),np.ones(len(t))])
    for i,name in enumerate(['A1','A2','A3']):
        coeff=profile['channels'][name];v=rows[:,i+2]*coeff['gain_v_per_count']+coeff['offset_v'];t=(rows[:,0]+rows[:,i+6])*1e-6
        X=design(t);fit=np.linalg.lstsq(X,v,rcond=None)[0];res=v-X@fit
        signals[name]=v;times[name]=t;fits[name]=fit
        channels[name]={'fitted_amplitude_v':float(np.hypot(fit[0],fit[1])),'fitted_phase_rad':float(np.arctan2(fit[1],fit[0])),'fitted_offset_v':float(fit[2]),'own_sine_fit_RMS_mV':float(np.sqrt(np.mean(res**2))*1000),'max_abs_own_fit_residual_mV':float(np.max(np.abs(res))*1000)}
    comparisons={}
    for name in ['A1','A2']:
        rms=float(np.sqrt(np.mean((signals[name]-design(times[name])@fits['A3'])**2))*1000)
        ratio=channels[name]['fitted_amplitude_v']/channels['A3']['fitted_amplitude_v']
        phase=(channels[name]['fitted_phase_rad']-channels['A3']['fitted_phase_rad']+np.pi)%(2*np.pi)-np.pi
        comparisons[name]={'RMS_vs_fitted_driver_mV':rms,'fitted_amplitude_ratio':ratio,'relative_phase_deg':float(np.degrees(phase)),
                           'pass':bool(rms<=5 and abs(ratio-1)*100<=1 and abs(np.degrees(phase))<=2)}
    a={'capture_record':str(cap),'boot_id':boot,'channels':channels,'comparisons':comparisons,'all_checks_pass':all(c['pass'] for c in comparisons.values()),
       'overruns':raw['overruns'],'samples_per_channel':len(rows),'parked_ref_code':raw['parked_ref_code'],'profile_changed':False,
       'limits':['Read-completion timestamps, not calibrated sample apertures.','Reference sinusoid is fitted to driver data from this block; this is a relative path consistency test, not an independent absolute-voltage reference.','A4 and full-frequency-band validation remain incomplete.','All samples retained; RMS checks do not certify a Gaussian or AR(1) noise model.']}
    (log.path/'analysis.json').write_text(json.dumps(a,indent=2)+'\n');log.add('analysis',a)
    log.add('run_completed',{'raw_capture_completed':True,'fixture_check_passed':a['all_checks_pass'],'full_D2_calibration_accepted':False,'output_parked_ref_code':raw['parked_ref_code'],'boot_id':boot})
    print(json.dumps({'record':str(log.path),'stage':'completed','analysis':a}),flush=True)
except Exception as exc:
    log.add('run_failed',{'error':str(exc),'automatic_retry_or_rearm':False,'calibration_accepted':False})
    print(json.dumps({'record':str(log.path),'stage':'failed','error':str(exc)}),flush=True);raise SystemExit(1)
