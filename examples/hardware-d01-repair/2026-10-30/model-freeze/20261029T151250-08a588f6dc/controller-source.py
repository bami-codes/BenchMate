"""Freeze a conditional physical-repair model before operator intervention."""
from pathlib import Path
import sys,json,hashlib,math
root=Path('/Users/bami/Documents/metaai')
sys.path.insert(0,str(root/'src'))
from benchmate.records import Recorder,read_events

target=root/'examples/hardware-d01-repair/2026-10-30'
assert not target.exists(), 'A repair plan already exists; do not overwrite'
analysis_path=root/'examples/hardware-d01-bringup/2026-10-29/loaded-retry-analysis/analysis.json'
feature_path=root/'examples/hardware-d01-bringup/2026-10-29/load-alternatives/predictions.json'
profile_path=root/'examples/hardware-fixture-bringup/2026-10-29-followup/minima-three-point-analysis/provisional-calibration.json'
analysis=json.loads(analysis_path.read_text())
features=json.loads(feature_path.read_text())
observed=analysis['conditional_RC_estimate']
R=observed['R_ohm'];load=features['load_ohm'];C=features['declared_design']['C_f']
g=load/(R+load);tau=R*load/(R+load)*C
assert abs(g-observed['gain'])<1e-12
assert 0.004<tau<0.006 and 0.009<observed['tau_s']<0.012
times=[i*0.0005 for i in range(241)]
models={
    'repair_to_declared_nominal_C': {'R_ohm':R,'C_f':C,'gain':g,'loaded_tau_s':tau},
    'no_repair_counterfactual': {'R_ohm':R,'C_f':observed['C_f'],'gain':g,'loaded_tau_s':observed['tau_s']},
}
for model in models.values():
    model['output_change_per_unit_input_step']=[model['gain']*(-math.expm1(-t/model['loaded_tau_s'])) for t in times]
    wt=2*math.pi*5*model['loaded_tau_s']
    model['continuous_5Hz_gain']=model['gain']/math.sqrt(1+wt*wt)
    model['continuous_5Hz_phase_deg']=-math.degrees(math.atan(wt))

plan={
    'scope':'Conditional known-specimen physical repair engineering check; provisional calibration, not Spark diagnosis or final holdout',
    'training_source':str(analysis_path.relative_to(root)),
    'training_rule':'R and pre-repair C/tau from the saved pre-repair loaded response; repair C from declared nominal design only.',
    'measured_specimen_component_truth_used':False,
    'load_ohm':load,'models':models,'normalized_step_time_s':times,
    'settings':[
        {'kind':'step','amplitude_v':0.2,'samples':512,'period_us':500,'step_index':51},
        {'kind':'sine','frequency_hz':5,'amplitude_v':0.2,'samples':512,'period_us':2000,'settle_ms':1200,'warmup_frames':600},
    ],
    'voltage_forecast_policy':{
        'fresh_supply_and_REF_required_after_USB_reconnection':True,
        'both_full_voltage_predictions_saved_before_any_post_repair_ADC':True,
        'fixed_provisional_profile':str(profile_path.relative_to(root)),
        'conversion':'Retain preceding D01 supply-scaled affine ADC maps and DAC-driver slope with fixed driver offset.',
        'A2_nominal_read_completion_offset_us':105,
        'waveform':'Quantized commanded codes; exponential sample-and-hold propagation including sine warmup.',
        'repair_parameters_remain_frozen':True,'automatic_A4_tracking':False,
        'no_OUT_based_offset_gain_phase_or_model_adjustment':True,
    },
    'engineering_limits':{
        'whole_trace_RMS_mV_max':9,'each_step_region_or_sine_phase_bin_RMS_mV_max':9,
        'max_prediction_time_error_us':25,'step_DAC_code_error_max':0,'sine_DAC_code_error_max':1,
        'step_regions_ms':[['pre_step',None,0],['0_to_5ms',0,5],['5_to_20ms',5,20],['20_to_80ms',20,80],['after_80ms',80,None]],
        'sine_phase_bins':8,
        'reference_guard_A4_block_mean_span_mV_max':3,
        'basis':'Retained development 3 x 3mV waveform allowance and prior 3mV stability allowance; not calibrated uncertainty.',
    },
    'decision':'Both repaired-model waveforms must pass their whole/regional checks and no-repair counterfactual must fail at least the step check. Otherwise report the observed limits or unresolved repair effect, with no refit/retry hidden.',
    'all_samples_and_attempts_retained':True,'automatic_retry_or_rearm':False,
    'operator_intervention':{
        'power':'Disconnect USB and wait for power LED off before touching parts.',
        'remove_only':'Added capacitor on mini-board I8-I13, both legs.',
        'retain':'Original C1 D8-D13 and R1 B3-B8, E8-F8/E13-F13 bridges, all IN/OUT/RET leads, OUT load E30-A55/D55-D60/C23-A60, jumpers 11 and 14.',
        'confirm_before_power':'Both removed legs clear; original C1 retained; continuity D8-I8 and D13-I13; leave USB disconnected.',
    },
    'physical_repair_performed':False,'full_voltage_predictions_pending_fresh_power_report':True,
    'source_hashes':{str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [analysis_path,feature_path,profile_path]},
}
log=Recorder(target/'model-freeze',mode='physical_repair_response_model_frozen_before_capacitor_removal')
(log.path/'controller-source.py').write_bytes(Path(__file__).read_bytes())
(log.path/'plan.json').write_text(json.dumps(plan,indent=2)+'\n')
digest=hashlib.sha256((log.path/'plan.json').read_bytes()).hexdigest()
log.add('repair_model_frozen',{'plan_sha256':digest,'repair_gain':g,'repair_loaded_tau_s':tau,'pre_repair_loaded_tau_s':observed['tau_s'],'physical_removal_not_yet_requested':True,'hardware_IO':False})
log.add('run_completed',{'plan_sha256':digest,'physical_repair_pending':True,'full_voltage_predictions_pending':True,'hardware_IO':False})
assert read_events(log.path)[-1]['kind']=='run_completed'
(target/'README.md').write_text(f'''# D01 physical repair — pre-intervention prediction

Status: model frozen before requesting physical removal; **repair not performed**.

Using the earlier loaded-response estimate R = {R/1000:.5f} kohm and the
declared nominal repair capacitance 1 uF, with the same 9.99 kohm output load,
the predicted gain stays **{g:.5f}** while loaded tau changes from
**{observed['tau_s']*1000:.3f} ms to {tau*1000:.3f} ms**. Measured specimen
component values are not used. This is conditional on the one-state RC model
and provisional calibration, not a calibrated uncertainty statement.

The [frozen plan]({log.path.name if False else 'model-freeze/'+log.path.name}/plan.json)
contains both repaired and unchanged counterfactual response curves, settings,
whole/regional limits, and the exact operator intervention. Both full voltage
waveforms will be saved after fresh supply/REF readings and before either
post-repair acquisition. The model is already fixed; fresh power readings
configure the stimulus and conversion, never the circuit parameters.

First check: +/-0.2 V step, 512 frames at 500 us. Second check: 5 Hz sine,
+/-0.2 V, 512 frames at 2000 us after the existing warmup. No post-repair
fit, offset adjustment or phase alignment enters the frozen scores. Original
failures remain visible and automatic reference tracking remains disabled.

Plan SHA-256: `{digest}`.
''')
print(json.dumps({'plan':str(log.path/'plan.json'),'gain':g,'tau_before_ms':observed['tau_s']*1000,'tau_after_ms':tau*1000,'sha256':digest,'hardware_IO':False}))
