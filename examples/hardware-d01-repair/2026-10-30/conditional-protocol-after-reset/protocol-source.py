"""Prospective revision after an absolute-voltage failure, not a rescore."""
from pathlib import Path
import json,hashlib,sys
ROOT=Path('/Users/bami/Documents/metaai');sys.path.insert(0,str(ROOT/'src'))
from benchmate.records import Recorder,read_events
old=ROOT/'examples/hardware-d01-repair/2026-10-30/attempt1-capture/prediction.json'
p=json.loads(old.read_text())
for w in p['waveforms']:
    for m in w['predictions'].values():m.pop('predicted_A2_v')
p['scope']='Prospective measured-IN-conditioned incremental repair response. Does not validate absolute voltage, REF/A2 offset calibration or full D2.'
p['previous_boot_id']='965280fa5627e569080ee7e6fb95d326'
p['operator_RESET_report']='reset 완료'
p['startup_policy']='Explicit operator RESET with USB/wiring unchanged, same known passive repaired RC and load. Require a new unarmed boot and one explicit REF ARM. Retain last supply estimate and command code; stationary raw REF/path guards must pass before scored stimuli. Not a general boot-continuation calibration policy.'
p['preceding_attempt']='runs/hardware-d01-repair-conditional-capture/20261029T154955-695b8dca47'
p['preceding_attempt_status']='PING received zero bytes; zero capture attempts, no ARM or stimulus; preserved.'
p['operator_post_failure_DMM_report']='REF 1.635 / 구동−REF −0.010'
p['operator_power_report']='Supply 4.89 V retained from first repair attempt; later stationary DMM REF 1.635 V and DRIVE-REF -0.010 V. Command reference remains encoded as 1.637 V/code 1371; it is not a new physical REF measurement.'
p['all_predictions_saved_before_post_repair_ADC']=False
p['model_algorithm_and_initialization_policy_frozen_before_new_capture']=True
p['conditional_waveforms_computed_after_measured_IN_available']=True
p['scored_OUT_never_input_to_predictor']=True
p['pre_stimulus_origin']={'blocks':3,'frames_per_block':512,'period_us':2000,
    'rule':'Freeze A1 and A2 means from three separate stationary HOLD blocks before either scored waveform. Use these only as input/output origins, never to fit gain/tau.',
    'stationary_path_mean_span_mV_max':3,
    'step_initial_state':'Equilibrium of measured pre-step IN mean; no scored OUT used.',
    'sine_initial_state':'Periodic solution of the first complete measured IN cycle, representing preceding firmware warmup; no scored OUT used.'}
p['reference_policy']='REF is assumed stationary within the existing 3 mV A4 mean-span guard; no uncalibrated raw A4 correction is injected into the prediction.'
p['decision']='Both fixed repaired-model incremental waveform checks must pass whole/regional 9 mV limits; unchanged model must fail the step check. This validates incremental dynamics only; original absolute-voltage failures stay failed.'
p['guard_captures']={'count':5,'samples':512,'period_us':2000,'positions':['baseline 1','baseline 2','baseline 3','between waveforms','after sine']}
p['original_failure_preserved']=str(old.parent.relative_to(ROOT))
p['protocol_revision_after_observed_failure']=True
p['development_replay_not_independent_verification']={'original_input_minus_actuator_mean_mV':{'step':.3002389292704015,'sine':.2887418078189371},
    'old_data_incremental_replay_RMS_mV':{'repair_step':2.2792646319919188,'repair_sine':2.9619589803097948,'unchanged_step':11.54421494260154,'unchanged_sine':11.8501864308651},
    'original_scores_unchanged':True}
p['predictor_sha256']=hashlib.sha256((ROOT/'src/benchmate/measured_input.py').read_bytes()).hexdigest()
p['capture_controller_sha256']=hashlib.sha256(Path('/private/tmp/benchmate-capture-conditional-repair-after-reset.py').read_bytes()).hexdigest()
p['predictor_validation']='9 tests passed: independent closed-form step with actual level offset/jitter; exact periodic sample-and-hold sine including first sample; later input drift; invalid data/timing.'
log=Recorder(ROOT/'runs/hardware-d01-repair-conditional-protocol',mode='prospective_incremental_protocol_after_absolute_failure')
for src,name in [(Path(__file__),'protocol-source.py'),(ROOT/'src/benchmate/measured_input.py','measured-input-predictor.py'),
                 (Path('/private/tmp/benchmate-capture-conditional-repair-after-reset.py'),'capture-controller.py'),
                 (old.parent/'provisional-calibration.json','provisional-calibration.json')]:
    (log.path/name).write_bytes(src.read_bytes())
(log.path/'protocol.json').write_text(json.dumps(p,ensure_ascii=False,indent=2)+'\n')
sha=hashlib.sha256((log.path/'protocol.json').read_bytes()).hexdigest()
log.add('stationary_DMM_report',{'verbatim':p['operator_post_failure_DMM_report'],'sequential_report_not_simultaneous_with_prior_capture':True})
log.add('conditional_protocol_frozen',{'sha256':sha,'no_new_hardware_IO':True,'predictor_sha256':p['predictor_sha256'],
    'gain_tau_unchanged_from_pre_repair_model':True,'scored_A2_not_used_for_model_or_origin':True,
    'absolute_voltage_validation_not_claimed':True})
log.add('run_completed',{'hardware_IO':False,'protocol_sha256':sha,'prospective_baseline_and_checks_pending':True})
(ROOT/'runs/d01-repair-conditional-plan-path.txt').write_text(str(log.path/'protocol.json')+'\n')
assert read_events(log.path)[-1]['kind']=='run_completed'
print(json.dumps({'record':str(log.path),'protocol_sha256':sha,'scored_waveforms':2,'separate_baseline_blocks':3,'same_boot_code':1371,'hardware_IO':False}))
