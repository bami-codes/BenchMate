"""Freeze both D01 voltage forecasts before powered loaded ADC acquisition."""
from pathlib import Path
from dataclasses import asdict
import hashlib,json
import numpy as np
from benchmate.records import Recorder,read_events
from benchmate.instrument import InstrumentConfig,capture_command
feature_path=Path('examples/hardware-d01-bringup/2026-10-29/load-alternatives/predictions.json')
feature_events=read_events(feature_path.parent)
f=json.loads(feature_path.read_text())
assert hashlib.sha256(feature_path.read_bytes()).hexdigest()==feature_events[1]['payload']['prediction_sha256']
profile_path=Path('examples/hardware-fixture-bringup/2026-10-29-followup/minima-three-point-analysis/provisional-calibration.json')
profile=json.loads(profile_path.read_text());config=InstrumentConfig(vref_v=4.89,ref_v=1.635)
n=512;period=500;index=n//10
request=capture_command(config,boot_id='1'*32,kind='step',samples=n,period_us=period,amplitude_v=.2)
amp=int(request.split()[5]);ratio=config.vref_v/profile['nominal_supply_conversion_v']
actuator=profile['DAC_to_driver_path'];slope=actuator['gain_v_per_code']*ratio;offset=actuator['offset_v']
codes=np.where(np.arange(n)<index,config.ref_code-amp,config.ref_code+amp)
u0=slope*(config.ref_code-amp)+offset;u1=slope*(config.ref_code+amp)+offset
t=(np.arange(n)*period+105)*1e-6;relative=t-index*period*1e-6
models={}
for name,h in f['hypotheses'].items():
 point=h['illustrative_point'];g=point['gain'];tau=point['loaded_tau_s']
 y0=config.ref_v+g*(u0-config.ref_v);y1=config.ref_v+g*(u1-config.ref_v)
 curve=y0+(y1-y0)*(-np.expm1(-np.maximum(relative,0)/tau))
 models[name]={'conditional_point':point,'conditional_ranges':{k:h[k] for k in ['gain_range','loaded_tau_range_s']},'predicted_output_plateaus_v':[y0,y1],'predicted_A2_v':curve.tolist()}
maps={ch:{'gain_v_per_count':c['gain_v_per_count']*ratio,'offset_v':c['offset_v']*ratio} for ch,c in profile['channels'].items()}
p={'scope':'Two frozen representative repair-model voltage forecasts; conditional discrimination, not posterior probabilities or full-family verification',
'configuration':asdict(config),'previous_boot_id':'a09aa39f4755ba059967f31ac9221cd3','operator_power_report':'D50 1.635 / D45 1.645 / C9 1.635; last supply 4.89V retained, not remeasured', 'stationary_DMM_record':'runs/hardware-d01-reference-recheck/20261029T140511-b5b1cdcec9', 'same_boot_retry':True, 'old_held_ref_code':1381, 'first_attempt_preserved':'runs/hardware-d01-loaded-step/20261029T135226-9d6e39c67e','hookup_record':'runs/hardware-d01-load-confirmed/20261029T134809-e1c0f5f6ef','load_resistor_ohm':f['load_ohm'],'specimen_component_truth_used':False,'kind':'step','samples':n,'period_us':period,'amplitude_v':.2,'step_index':index,'expected_DAC_codes':codes.tolist(),'nominal_A2_time_s':t.tolist(),'nominal_A2_step_relative_time_s':relative.tolist(),'predicted_input_plateaus_v':[u0,u1],'models':models,'actuator':{'driver_v_per_code':slope,'driver_offset_v':offset,'method':'Prior calibrated DAC slope scaled with reported supply; offset retained, as in preceding B1 load check'},'voltage_conversion':{'reported_supply_ratio':ratio,'channels':maps,'assumption':'Entire affine ADC map scaled by reported supply, unchanged from preceding B1 loaded check; provisional only'},'engineering_limits':{'whole_trace_RMS_mV_max':9,'each_region_RMS_mV_max':9,'max_prediction_time_error_us':25,'DAC_code_error_max':0},'regions_ms':[['pre_step',None,0],['0_to_5ms',0,5],['5_to_20ms',5,20],['20_to_80ms',20,80],['after_80ms',80,None]],'limit_basis':'Existing development 3 x 3 mV engineering allowance; not calibrated statistical confidence','no_loaded_parameter_offset_phase_or_prediction_refit':True,'REF_guard_not_used_to_modify_predictions':True,'known_passive_loaded_RC_startup_exception':True,'boot_and_ARM_ramp_excluded':True,'A4_based_DAC_change_applied':False,'source_hashes':{str(path):hashlib.sha256(path.read_bytes()).hexdigest() for path in [feature_path,profile_path]},'limitations':['Only declared representative points receive voltage-prediction scores; prior ranges are not a posterior or full-family test.','Assembly component truth is excluded; nominal design and measured intervention load are declared knowledge.','Supply scaling, buffered output path, REF stability and DMM accuracy remain provisional.','A4 gain remains uncalibrated; no exact physical centering or absolute accuracy is claimed.','No Spark call, final holdout evaluation or full D2 acceptance.']}
assert 2*amp<=config.max_jump
log=Recorder('runs/hardware-d01-loaded-prediction',mode='development_retry_two_new_forecasts_after_stationary_REF_report')
for path,name in [(Path(__file__),'controller-source.py'),(feature_path,'conditional-feature-predictions.json'),(profile_path,'provisional-calibration.json')]: (log.path/name).write_bytes(path.read_bytes())
(log.path/'prediction.json').write_text(json.dumps(p,indent=2)+'\n');digest=hashlib.sha256((log.path/'prediction.json').read_bytes()).hexdigest()
log.add('operator_power_report',{'verbatim':p['operator_power_report'],'supply_v':4.89,'REF_v':1.635,'measured_before_new_DAC_command':True,'supply_remeasured_now':False})
log.add('prediction_frozen',{'sha256':digest,'models':list(models),'engineering_limits':p['engineering_limits'],'specimen_component_truth_used':False,'loaded_ADC_observation_acquired':False,'A4_control_proposal_not_applied':True})
log.add('run_completed',{'hardware_IO':False,'loaded_ADC_pending':True,'prediction_sha256':digest})
Path('runs/d01-retry-prediction-path.txt').write_text(str(log.path/'prediction.json')+'\n')
print(json.dumps({'record':str(log.path),'ref_code':config.ref_code,'input_plateaus_v':[u0,u1],'models':{name:{k:v for k,v in model.items() if k!='predicted_A2_v'} for name,model in models.items()},'sha256':digest}))
