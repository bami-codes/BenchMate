"""Offline forecast for the known B1 with its measured output load.

This uses the known assembly resistance; it is not blind identification.
No loaded ADC data is available to this preparation script.
"""
from pathlib import Path
from dataclasses import asdict
import hashlib,json
import numpy as np
from benchmate.records import Recorder,read_events
from benchmate.instrument import InstrumentConfig,capture_command

base=Path('examples/hardware-b1-bringup/2026-10-29')
fit_path=base/'step-analysis/analysis.json'
profile_path=base/'first-step/provisional-calibration.json'
assert read_events(base/'step-analysis')[-1]['kind']=='run_completed'
fit=json.loads(fit_path.read_text());profile=json.loads(profile_path.read_text())
config=InstrumentConfig(vref_v=4.87,ref_v=1.627)
samples=512;period_us=500;step_index=samples//10
shape_request=capture_command(config,boot_id='1'*32,kind='step',samples=samples,period_us=period_us,amplitude_v=.2)
amplitude=int(shape_request.split()[5]);gain=9990/(9990+9990)
tau=fit['primary_fit']['tau_s']*gain
supply_ratio=config.vref_v/profile['nominal_supply_conversion_v']
actuator=profile['DAC_to_driver_path']
# The calibrated DAC slope is adjusted by the newly reported rail ratio;
# its fitted voltage offset is retained as a fixed offset. This is an
# explicit engineering approximation, not a new calibration fit.
driver_slope=actuator['gain_v_per_code']*supply_ratio
driver_offset=actuator['offset_v']
low_code=config.ref_code-amplitude;high_code=config.ref_code+amplitude
input_low=driver_slope*low_code+driver_offset
input_high=driver_slope*high_code+driver_offset
output_low=config.ref_v+gain*(input_low-config.ref_v)
output_high=config.ref_v+gain*(input_high-config.ref_v)
times=(np.arange(samples)*period_us+105)*1e-6
relative=times-step_index*period_us*1e-6
pred=output_low+(output_high-output_low)*(-np.expm1(-np.maximum(relative,0)/tau))
codes=np.where(np.arange(samples)<step_index,low_code,high_code)
# Map ADC data with the frozen affine map and an explicit reported-rail
# scale. No gain or offset may be estimated using this loaded capture.
scaled_maps={name:{'gain_v_per_count':c['gain_v_per_count']*supply_ratio,
                   'offset_v':c['offset_v']*supply_ratio} for name,c in profile['channels'].items()}
p={'scope':'Known B1 loaded engineering prediction; assembly R is used, not a blind diagnosis',
   'configuration':asdict(config),'previous_boot_id':'83af0e480fe8ae23aac6df290aebdfbc',
   'operator_power_report':'USB / 전원 4.87V / REF 1.627V',
   'hookup_record':'runs/hardware-b1-load-confirmed/20261029T122424-19773c5e0e',
   'load_resistor_ohm':9990,'known_B1_series_resistance_ohm':9990,
   'truth_resistance_used_in_prediction':True,'unloaded_fitted_tau_s':fit['primary_fit']['tau_s'],
   'predicted_loaded_tau_s':tau,'predicted_divider_gain_relative_to_REF':gain,
   'component_reference_loaded_tau_s':.00491508,'component_C_not_used_in_main_prediction':True,
   'kind':'step','samples':samples,'period_us':period_us,'step_index':step_index,'amplitude_v':.2,
   'code_low_high':[low_code,high_code],'expected_DAC_codes':codes.tolist(),
   'nominal_A2_time_s':times.tolist(),'nominal_A2_step_relative_time_s':relative.tolist(),
   'A2_read_completion_offset_us_assumed':105,'predicted_A2_v':pred.tolist(),
   'predicted_input_plateaus_v':[input_low,input_high],'predicted_output_plateaus_v':[output_low,output_high],
   'actuator':{'source':str(profile_path),'driver_v_per_code':driver_slope,'driver_offset_v':driver_offset},
   'voltage_conversion':{'formula':'scaled_gain * counts + scaled_offset',
                         'reported_supply_ratio':supply_ratio,'channels':scaled_maps,
                         'source_profile_modified':False,
                         'assumption':'Whole affine ADC map scales with reported supply; fixed-voltage residuals and DMM uncertainty remain uncalibrated'},
   'source_hashes':{str(fit_path):hashlib.sha256(fit_path.read_bytes()).hexdigest(),str(profile_path):hashlib.sha256(profile_path.read_bytes()).hexdigest()},
   'engineering_limits':{'whole_trace_RMS_mV_max':9,'each_region_RMS_mV_max':9,'max_prediction_time_error_us':25,'DAC_code_error_max':0},
   'regions_ms':[['pre_step',None,0],['0_to_5ms',0,5],['5_to_20ms',5,20],['20_to_80ms',20,80],['after_80ms',80,None]],
   'limits_basis':'Existing developmental 3 x 3 mV allowance; not a calibrated statistical test or pointwise error bound',
   'no_loaded_parameter_offset_or_phase_refit_for_prediction_score':True,
   'guard_limits':{'REF_mean_delta_v_max':.100,'REF_any_sample_delta_v_max':.150,'REF_channel_mean_spread_v_max':.050,
                   'step_signal_delta_from_REF_v_max':.350,'step_A4_delta_from_REF_v_max':.150,'raw_rail_limits_exclusive':[16,16367]},
   'known_passive_loaded_RC_startup_exception':True,'boot_and_ARM_ramp_excluded_from_experiment_data':True,
   'REF_guard_data_not_used_to_change_prediction':True,
   'limitations':['R/load readings are known engineering setup facts, not inferred values.',
                  'Unloaded effective tau is scaled using the ideal loaded RC equation.',
                  'Actuator map and ADC supply scaling are provisional; REF is the reported DMM value.',
                  'Buffer bias current, load-dependent offsets and dynamic REF changes are not fitted away.',
                  'A4 has no accepted gain calibration; full D2 and hardware diagnosis remain incomplete.']}
assert 2*amplitude<=config.max_jump and np.isfinite(pred).all()
log=Recorder('runs/hardware-b1-loaded-prediction',mode='pre_observation_known_B1_loaded_step_forecast')
(log.path/'controller-source.py').write_bytes(Path(__file__).read_bytes())
(log.path/'provisional-calibration.json').write_bytes(profile_path.read_bytes())
(log.path/'prediction.json').write_text(json.dumps(p,indent=2)+'\n')
digest=hashlib.sha256((log.path/'prediction.json').read_bytes()).hexdigest()
log.add('operator_power_report',{'verbatim':p['operator_power_report'],'supply_v':4.87,'REF_v':1.627,
 'requested_ranges':{'supply':'DC 20 V','REF':'DC 2 V'},'jumper14_retained_per_instruction':True})
log.add('prediction_frozen',{'file':'prediction.json','sha256':digest,'loaded_ADC_observation_acquired':False,
                            'predicted_loaded_tau_s':tau,'divider_gain':gain,'known_series_R_used':True,
                            'engineering_limits':p['engineering_limits'],'supply_ratio_applied_before_observation':supply_ratio})
log.add('run_completed',{'hardware_IO':False,'loaded_ADC_observation_pending':True,'prediction_sha256':digest})
print(json.dumps({'record':str(log.path),'predicted_tau_ms':tau*1000,'input_plateaus_v':p['predicted_input_plateaus_v'],
                  'output_plateaus_v':p['predicted_output_plateaus_v'],'ref_code':config.ref_code,'prediction_sha256':digest}))
