"""Freeze conditional loaded gains and time constants from unloaded observations.

This is not Bayesian posterior inference. It reads a fitted unloaded response,
explicit nominal design/prior ranges, and the measured fixture-load value only.
"""
from pathlib import Path
import hashlib,json
import numpy as np
from benchmate.records import Recorder,read_events
source=Path('runs/hardware-d01-unloaded-analysis/20261029T134032-a9f66c03d3')
assert read_events(source)[-1]['kind']=='run_completed'
a=json.loads((source/'analysis.json').read_text());tau=a['primary_fit']['tau_s'];load=9990.
ranges={'nominal_R_changed_C':{'R':[9500.,10500.],'C':[1.5e-6,2.5e-6]},'changed_R_nominal_C':{'R':[15000.,25000.],'C':[.9e-6,1.1e-6]}}
points={'nominal_R_changed_C':10000.,'changed_R_nominal_C':tau/1e-6};hypotheses={}
for name,p in ranges.items():
 lo=max(p['R'][0],tau/p['C'][1]);hi=min(p['R'][1],tau/p['C'][0]);assert lo<=hi
 gmin=load/(hi+load);gmax=load/(lo+load);r=points[name];g=load/(r+load)
 hypotheses[name]={'prior_ranges':p,'R_range_on_fitted_tau_ridge_ohm':[lo,hi], 'gain_range':[gmin,gmax],'loaded_tau_range_s':[tau*gmin,tau*gmax], 'illustrative_point':{'R_ohm':r,'C_f':tau/r,'gain':g,'loaded_tau_s':tau*g}}
t=np.linspace(0,.12,241)
result={'scope':'Frozen conditional RC feature predictions before any D01 loaded observation; no posterior probabilities or calibrated intervals','unloaded_analysis_record':str(source),'unloaded_analysis_sha256':hashlib.sha256((source/'analysis.json').read_bytes()).hexdigest(),'unloaded_tau_s':tau,'load_ohm':load,'load_is_instrument_intervention_not_specimen_truth':True,'declared_design':a['declared_design'],'prior_source':'docs/preregistration.md development revision, repair R/C ranges','formulas':{'gain':'Rload / (R + Rload)','loaded_tau':'unloaded_tau * gain'},'hypotheses':hypotheses,'normalized_step_time_s':t.tolist(),'normalized_OUT_response_per_unit_IN_step':{name:(h['illustrative_point']['gain']*(-np.expm1(-t/h['illustrative_point']['loaded_tau_s']))).tolist() for name,h in hypotheses.items()},'unloaded_fit_output_levels':{k:a['primary_fit'][k] for k in ['low_output_v','high_output_v']},'full_voltage_forecast_pending_fresh_supply_REF':True,'no_new_observation_to_select_or_refit_hypotheses':True,'specimen_measured_R_C_or_assembly_truth_used':False,'posterior_integration_performed':False,'limits':['Ranges condition on a point tau fit; they omit noise, calibration and model uncertainty.','The two point examples are not separate R/C estimates or evidence weights.','Fresh supply/REF may configure voltage commands before ADC; they cannot select a fault.','A full voltage forecast and engineering gates must be recorded before loaded acquisition.','No full D2 acceptance or automated Spark diagnosis.']}
log=Recorder('runs/hardware-d01-load-alternatives',mode='pre_observation_conditional_loaded_features')
(log.path/'controller-source.py').write_bytes(Path(__file__).read_bytes());(log.path/'predictions.json').write_text(json.dumps(result,indent=2)+'\n')
log.add('loaded_alternatives_frozen',{'prediction_sha256':hashlib.sha256((log.path/'predictions.json').read_bytes()).hexdigest(),'hypotheses':hypotheses,'no_D01_loaded_observation':True,'specimen_truth_used':False,'posterior_integration_performed':False})
log.add('run_completed',{'hardware_IO':False,'loaded_observation_pending':True,'voltage_forecast_pending':True})
print(json.dumps({'record':str(log.path),'hypotheses':hypotheses}))
