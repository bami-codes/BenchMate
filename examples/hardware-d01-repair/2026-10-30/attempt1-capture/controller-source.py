"""Two fixed physical-repair checks. No refit, retry, firmware upload or A4 servo."""
from pathlib import Path
import sys,json,hashlib,time
import numpy as np
import serial
from serial.tools import list_ports
ROOT=Path('/Users/bami/Documents/metaai')
sys.path.insert(0,str(ROOT/'src'))
from benchmate.records import Recorder,read_events
from benchmate.instrument import InstrumentConfig,BootContinuity,capture_command,receive_response,validate_block

def main():
    prediction_path=Path((ROOT/'runs/d01-repair-voltage-path.txt').read_text().strip())
    source_events=read_events(prediction_path.parent)
    freeze=next(e['payload'] for e in source_events if e['kind']=='both_predictions_frozen')
    digest=hashlib.sha256(prediction_path.read_bytes()).hexdigest()
    assert digest==freeze['sha256']
    p=json.loads(prediction_path.read_text())
    model=ROOT/p['model_plan']
    assert hashlib.sha256(model.read_bytes()).hexdigest()==p['model_plan_sha256']
    config=InstrumentConfig(**p['configuration']);limits=p['engineering_limits'];guard_limits=p['guard_limits']
    log=Recorder(ROOT/'runs/hardware-d01-repair-capture',mode='two_frozen_physical_repair_checks_with_manual_REF_no_automatic_tracking')
    for path,name in [(Path(__file__),'controller-source.py'),(prediction_path,'prediction.json'),
                      (prediction_path.parent/'provisional-calibration.json','provisional-calibration.json'),
                      (ROOT/'src/benchmate/instrument.py','host-instrument.py')]:
        (log.path/name).write_bytes(path.read_bytes())
    log.add('predeclared_repair_check',{'prediction_sha256':digest,'model_plan_sha256':p['model_plan_sha256'],
        'operator_removal_report':p['operator_removal_report'],'operator_power_report':p['operator_power_report'],
        'guard_limits':guard_limits,'engineering_limits':limits,'guard_blocks':3,'verification_blocks':2,
        'all_attempts_retained':True,'automatic_retry_or_rearm':False,'known_passive_RC_startup_exception':True,
        'startup_and_ARM_ramp_excluded':True,'automatic_A4_tracking':False,'full_D2_accepted':False})
    continuity=BootContinuity();stage='preflight';reference_means=[];scores={};capture_count=0

    def request(board,command,kind,timeout=5):
        log.add('serial_command',{'request':command.decode().strip()})
        board.timeout=timeout
        if board.write(command)!=len(command):raise RuntimeError('Incomplete write; no retry')
        packet=receive_response(board,log,kind);continuity.check(packet)
        return packet

    def ping(board,kind,armed):
        packet=request(board,b'PING\n',kind)
        code=config.ref_code if armed else 0
        if (packet.get('type')!='pong' or packet.get('armed') is not armed
            or packet.get('current_code')!=code or packet.get('ref_code')!=code
            or packet.get('dc_hold_supported') is not True
            or packet.get('adc_sample_state_channels')!=[0,1,2,21]
            or packet.get('adc_sample_states_readback')!=[255]*4
            or (armed and packet.get('max_jump_code')!=config.max_jump)):
            raise ValueError('Unexpected firmware or output state; no re-arm')
        return packet

    def capture(board,label,settings):
        nonlocal capture_count
        command=capture_command(config,boot_id=continuity.boot_id,**settings)
        capture_count+=1
        block=request(board,command,label+'_raw_capture',30)
        validate_block(block,expected_command=command)
        if block.get('parked_ref_code')!=config.ref_code:raise ValueError('REF park not reported')
        ping(board,label+'_postcheck',True)
        rows=np.asarray(block['rows']);nominal=rows[:,2:6]*config.vref_v/16383
        mean_ref=float(nominal[:,3].mean());reference_means.append({'label':label,'nominal_A4_mean_v':mean_ref})
        return block,rows,nominal

    def electrical_checks(rows,volts,is_hold):
        checks={'raw_not_at_rails':bool(((rows[:,2:6]>16)&(rows[:,2:6]<16367)).all()),
                'A4_envelope':bool((abs(volts[:,3]-config.ref_v)<=guard_limits['A4_envelope_v']).all()),
                'A4_block_mean_stability':float(np.ptp([r['nominal_A4_mean_v'] for r in reference_means]))*1000<=limits['reference_guard_A4_block_mean_span_mV_max']}
        if is_hold:
            means=volts.mean(axis=0)
            checks.update(REF_means_near_meter=bool((abs(means-config.ref_v)<=guard_limits['REF_mean_delta_v_max']).all()),
                REF_all_samples_near_meter=bool((abs(volts-config.ref_v)<=guard_limits['REF_any_sample_delta_v_max']).all()),
                REF_channel_mean_spread=float(np.ptp(means))<=guard_limits['REF_channel_mean_spread_v_max'])
        else: checks['signal_envelope']=bool((abs(volts[:,:3]-config.ref_v)<=guard_limits['signal_envelope_v']).all())
        return checks

    def hold(board,label):
        block,rows,volts=capture(board,label,{'kind':'hold','hold_v':config.ref_v,'samples':512,'period_us':2000})
        checks=electrical_checks(rows,volts,True)
        log.add('reference_guard',{'label':label,'mean_counts':rows[:,2:6].mean(axis=0).tolist(),
            'nominal_mean_v':volts.mean(axis=0).tolist(),'checks':checks,'overruns':block['overruns']})
        if not all(checks.values()):raise ValueError('Reference guard failed; no next stimulus')
        print(json.dumps({'stage':label+'_passed','nominal_means_v':volts.mean(axis=0).tolist()}),flush=True)

    def score(waveform,rows):
        setting=waveform['settings'];kind=setting['kind'];nominal_t=np.asarray(waveform['nominal_A2_time_s'])
        a2=p['voltage_conversion']['channels']['A2']
        y=rows[:,3]*a2['gain_v_per_count']+a2['offset_v']
        time_error=float(np.max(abs((rows[:,0]+rows[:,7])*1e-6-nominal_t)))*1e6
        code_error=int(np.max(abs(rows[:,1]-np.asarray(waveform['expected_DAC_codes']))))
        masks=[]
        if kind=='step':
            relative=nominal_t-(setting['samples']//10)*setting['period_us']*1e-6
            for name,lo,hi in limits['step_regions_ms']:
                mask=np.ones(len(rows),dtype=bool)
                if lo is not None:mask&=relative>=lo/1000
                if hi is not None:mask&=relative<hi/1000
                masks.append((name,mask))
        else:
            phase=np.floor((nominal_t*setting['frequency_hz']%1)*limits['sine_phase_bins']).astype(int)
            masks=[('phase_'+str(i),phase==i) for i in range(limits['sine_phase_bins'])]
        result={}
        for name,prediction in waveform['predictions'].items():
            residual=y-np.asarray(prediction['predicted_A2_v'])
            regions=[{'name':label,'samples':int(mask.sum()),'RMS_mV':float(np.sqrt(np.mean(residual[mask]**2)))*1000,
                      'max_abs_mV':float(np.max(abs(residual[mask])))*1000} for label,mask in masks]
            rms=float(np.sqrt(np.mean(residual**2)))*1000
            checks={'whole_RMS':rms<=limits['whole_trace_RMS_mV_max'],
                    'all_regional_RMS':all(r['RMS_mV']<=limits['each_step_region_or_sine_phase_bin_RMS_mV_max'] for r in regions),
                    'timing':time_error<=limits['max_prediction_time_error_us'],
                    'DAC_codes':code_error<=limits[kind+'_DAC_code_error_max']}
            result[name]={'RMS_mV':rms,'mean_residual_mV':float(residual.mean())*1000,
                          'max_abs_residual_mV':float(np.max(abs(residual)))*1000,'regions':regions,
                          'checks':checks,'passed':all(checks.values()),'refitted_samples':0}
        return {'models':result,'max_time_error_us':time_error,'max_DAC_code_error':code_error}

    try:
        ports=[p for p in list_ports.comports() if (p.vid,p.pid,p.serial_number)==(9025,105,'3612211F36323632E4B233334B572F52')]
        log.add('USB_preflight',{'matching_ports':[p.device for p in ports]})
        if len(ports)!=1:raise ValueError('Expected Minima absent or ambiguous')
        with serial.Serial(ports[0].device,115200,timeout=5,write_timeout=2) as board:
            time.sleep(2);board.reset_input_buffer()
            stage='fresh_boot_PING';ping(board,stage,False)
            if continuity.boot_id==p['previous_boot_id']:raise ValueError('Expected fresh boot after capacitor removal')
            stage='explicit_REF_ARM';arm=request(board,config.arm_command(continuity.boot_id),'ARM_response',15)
            if arm.get('type')!='armed':raise ValueError('ARM not acknowledged')
            ping(board,'post_ARM_PING',True)
            stage='reference_before_step';hold(board,stage)
            for i,waveform in enumerate(p['waveforms']):
                kind=waveform['settings']['kind'];stage=kind+'_verification'
                block,rows,volts=capture(board,kind,waveform['settings'])
                score_result=score(waveform,rows)
                checks=electrical_checks(rows,volts,False)
                score_result['electrical_guards']=checks
                score_result['frame_interval_us_range']=[int(np.diff(rows[:,0]).min()),int(np.diff(rows[:,0]).max())]
                scores[kind]=score_result
                log.add('frozen_prediction_comparison',{'kind':kind,**score_result})
                (log.path/(kind+'-comparison.json')).write_text(json.dumps(score_result,indent=2)+'\n')
                print(json.dumps({'stage':kind+'_scored','models':{k:{'RMS_mV':v['RMS_mV'],'passed':v['passed']} for k,v in score_result['models'].items()},'electrical_guards':checks}),flush=True)
                if not all(checks.values()):raise ValueError('Electrical/reference guard failed; no next stimulus')
                stage='reference_between' if i==0 else 'reference_after_sine';hold(board,stage)
            ping(board,'final_PING',True)
        model_pass=all(v['models']['repair_to_declared_nominal_C']['passed'] for v in scores.values())
        counterfactual_failed=not scores['step']['models']['no_repair_counterfactual']['passed']
        result={'boot_id':continuity.boot_id,'configuration':p['configuration'],'output_parked_ref_code':config.ref_code,
                'prediction_sha256':digest,'scores':scores,'reference_block_means':reference_means,
                'A4_mean_span_mV':float(np.ptp([r['nominal_A4_mean_v'] for r in reference_means]))*1000,
                'capture_attempts':capture_count,'total_frames':capture_count*512,'verification_frames':1024,'guard_frames':1536,
                'both_repair_waveforms_passed':model_pass,'no_repair_step_failed':counterfactual_failed,
                'repair_engineering_check_passed':model_pass and counterfactual_failed,
                'post_repair_samples_used_for_refit':0,'automatic_A4_tracking':False,'full_D2_accepted':False,'Spark_invoked':False,
                'scope':p['scope']}
        (log.path/'result.json').write_text(json.dumps(result,indent=2)+'\n')
        log.add('run_completed',result)
        (ROOT/'runs/d01-repair-capture-path.txt').write_text(str(log.path)+'\n')
        print(json.dumps({'record':str(log.path),'stage':'completed','repair_engineering_check_passed':result['repair_engineering_check_passed'],'A4_mean_span_mV':result['A4_mean_span_mV'],'boot_id':continuity.boot_id,'held_code':config.ref_code}),flush=True)
    except (Exception,KeyboardInterrupt) as exc:
        log.add('run_failed',{'stage':stage,'error':str(exc) or type(exc).__name__,'capture_attempts':capture_count,
            'completed_scores':scores,'reference_block_means':reference_means,'repair_accepted':False,
            'automatic_retry_or_rearm':False,'output_state_now_confirmed':False})
        print(json.dumps({'record':str(log.path),'stage':'failed','failed_at':stage,'error':str(exc) or type(exc).__name__}),flush=True)
        raise SystemExit(1)

if __name__=='__main__':main()
