"""One additional waveform against a saved prediction; no refit or retry."""
from pathlib import Path
import hashlib,json,time
import numpy as np
import serial
from serial.tools import list_ports
from benchmate.records import Recorder,read_events
from benchmate.instrument import InstrumentConfig,BootContinuity,capture_command,receive_response,validate_block

prediction_path=Path('runs/hardware-b1-step-analysis/20261029T114450-975a52b634/frozen-sine-prediction.json')
freeze_events=read_events(prediction_path.parent)
assert freeze_events[-1]['kind']=='run_completed'
freeze=next(e['payload'] for e in freeze_events if e['kind']=='sine_prediction_frozen')
assert hashlib.sha256(prediction_path.read_bytes()).hexdigest()==freeze['sha256']
p=json.loads(prediction_path.read_text())
profile_path=Path(p['source_step_record'])/'provisional-calibration.json'
assert hashlib.sha256(profile_path.read_bytes()).hexdigest()==p['provisional_profile_sha256']
profile=json.loads(profile_path.read_text());config=InstrumentConfig(**p['configuration'])
request=capture_command(config,boot_id=p['boot_id'],kind='sine',frequency_hz=p['frequency_hz'],amplitude_v=p['amplitude_v'],samples=p['samples'],period_us=p['period_us'])
assert request.decode().strip()==p['command']
log=Recorder('runs/hardware-b1-frozen-sine-check',mode='frozen_B1_engineering_forecast_new_waveform_no_refit')
for source,name in [(Path(__file__),'controller-source.py'),(prediction_path,'frozen-sine-prediction.json'),(profile_path,'provisional-calibration.json'),(Path('src/benchmate/instrument.py'),'host-instrument.py')]:
    (log.path/name).write_bytes(source.read_bytes())
log.add('frozen_prediction_reference',{'source':str(prediction_path),'sha256':freeze['sha256'],
    'limits':p['engineering_limits'],'no_refit':True,'automatic_retry_or_rearm':False,
    'known_passive_fixture_unchanged_per_instruction':True,'full_D2_acceptance_claimed':False})
print(json.dumps({'record':str(log.path),'stage':'preflight'}),flush=True)
guard=BootContinuity(p['boot_id']);stage='preflight'
def ping(board,kind):
    board.timeout=5;log.add('serial_command',{'request':'PING'});board.write(b'PING\n')
    packet=receive_response(board,log,kind);guard.check(packet)
    if (packet.get('type')!='pong' or packet.get('armed') is not True or
        packet.get('current_code')!=config.ref_code or packet.get('ref_code')!=config.ref_code or
        packet.get('max_jump_code')!=config.max_jump or
        packet.get('adc_sample_state_channels')!=[0,1,2,21] or packet.get('adc_sample_states_readback')!=[255]*4):
        raise ValueError('Unexpected instrument state; no automatic re-arm')
try:
    ports=[x for x in list_ports.comports() if (x.vid,x.pid,x.serial_number)==(9025,105,'3612211F36323632E4B233334B572F52')]
    log.add('USB_preflight',{'matching_ports':[x.device for x in ports]})
    if len(ports)!=1:raise RuntimeError('Expected Minima absent or ambiguous')
    with serial.Serial(ports[0].device,115200,timeout=5,write_timeout=2) as board:
        time.sleep(2);board.reset_input_buffer();stage='initial_PING';ping(board,stage)
        stage='sine_capture';log.add('serial_command',{'request':request.decode().strip()});board.timeout=30
        if board.write(request)!=len(request):raise RuntimeError('Incomplete write')
        block=receive_response(board,log,'sine_raw_capture');guard.check(block);validate_block(block,expected_command=request)
        if block.get('parked_ref_code')!=config.ref_code:raise ValueError('REF park not reported')
        stage='post_capture_PING';ping(board,stage)
    stage='frozen_prediction_comparison'
    rows=np.asarray(block['rows']);c=profile['channels']['A2']
    observed=rows[:,3]*c['gain_v_per_count']+c['offset_v']
    predicted=np.asarray(p['predicted_A2_v']);residual=observed-predicted
    actual_t=(rows[:,0]+rows[:,7])*1e-6;nominal_t=np.asarray(p['nominal_sample_time_s'])
    time_error_us=float(np.max(np.abs(actual_t-nominal_t))*1e6)
    code_error=int(np.max(np.abs(rows[:,1]-np.asarray(p['expected_DAC_codes']))))
    phase=np.floor((nominal_t*p['frequency_hz']%1)*p['fixed_phase_bins']).astype(int)
    bins=[{'bin':i,'samples':int((phase==i).sum()),'RMS_mV':float(np.sqrt(np.mean(residual[phase==i]**2))*1000)} for i in range(p['fixed_phase_bins'])]
    rms=float(np.sqrt(np.mean(residual**2))*1000);lim=p['engineering_limits']
    nominal=rows[:,2:6]*config.vref_v/16383
    checks={'all_sample_RMS':rms<=lim['all_sample_RMS_mV_max'],
            'all_phase_bins_RMS':all(x['RMS_mV']<=lim['each_phase_bin_RMS_mV_max'] for x in bins),
            'nominal_prediction_timing':time_error_us<=lim['sample_time_error_us_max'],
            'nominal_DAC_codes':code_error<=lim['DAC_code_difference_max'],
            'signal_envelope':bool((np.abs(nominal[:,:3]-config.ref_v)<=.350).all()),
            'REF_envelope':bool((np.abs(nominal[:,3]-config.ref_v)<=.150).all())}
    result={'boot_id':guard.boot_id,'samples':len(rows),'overruns':block['overruns'],
            'frame_interval_us_min':int(np.diff(rows[:,0]).min()),'frame_interval_us_max':int(np.diff(rows[:,0]).max()),
            'RMS_prediction_residual_mV':rms,'mean_prediction_residual_mV':float(np.mean(residual)*1000),
            'max_abs_prediction_residual_mV':float(np.max(abs(residual))*1000),
            'phase_bin_residuals':bins,'max_prediction_time_error_us':time_error_us,
            'max_DAC_code_difference':code_error,'checks':checks,'engineering_check_passed':all(checks.values()),
            'prediction_sha256':freeze['sha256'],'validation_samples_used_for_refit':0,
            'output_parked_ref_code':config.ref_code,'full_D2_accepted':False,
            'scope':p['scope'],'calibrated_statistical_significance_claimed':False}
    (log.path/'analysis.json').write_text(json.dumps(result,indent=2)+'\n')
    log.add('frozen_prediction_comparison',result)
    log.add('run_completed',{'raw_capture_valid':True,'engineering_check_passed':result['engineering_check_passed'],
                              'validation_refit':False,'output_parked_ref_code':config.ref_code,'full_D2_accepted':False})
    print(json.dumps({'record':str(log.path),'stage':'completed','analysis':result}),flush=True)
except (Exception,KeyboardInterrupt) as exc:
    log.add('run_failed',{'stage':stage,'error':str(exc) or type(exc).__name__,
                         'accepted_validation_samples':0,'automatic_retry_or_rearm':False,'output_state_now_confirmed':False})
    print(json.dumps({'record':str(log.path),'stage':'failed','error':str(exc) or type(exc).__name__}),flush=True)
    raise SystemExit(1)
