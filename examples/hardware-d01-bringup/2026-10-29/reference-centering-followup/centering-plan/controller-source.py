"""Offline local A3/A4 alignment and one bounded centering trial; no hardware I/O."""
from pathlib import Path
import hashlib,json,math
import numpy as np
from benchmate.records import Recorder,read_events
from benchmate.instrument import InstrumentConfig
before=Path('examples/hardware-d01-bringup/2026-10-29/reference-alignment-before-DMM')
after=Path('runs/hardware-d01-reference-alignment/20261029T141757-e5abc8312a')
profile_path=Path('examples/hardware-fixture-bringup/2026-10-29-followup/minima-three-point-analysis/provisional-calibration.json')
profile=json.loads(profile_path.read_text());sources=[before,after];summaries=[];last_pong=None;noise=[]
for source in sources:
 events=read_events(source);assert events[-1]['kind']=='run_completed'
 summary=json.loads((source/'summary.json').read_text());assert summary['held_ref_code']==1369
 assert summary['boot_id']=='a09aa39f4755ba059967f31ac9221cd3';summaries.append(summary)
 block=next(e['payload'] for e in events if e['kind']=='hold_raw_capture');rows=np.asarray(block['rows'])
 assert len(rows)==512 and np.all(rows[:,1]==1369) and block['overruns']==0
 noise.append({'sample_SD_counts':dict(zip(block['channels'],map(float,rows[:,2:6].std(axis=0,ddof=1)))),'min_counts':rows[:,2:6].min(axis=0).tolist(),'max_counts':rows[:,2:6].max(axis=0).tolist()})
 last_pong=next(e['payload'] for e in events if e['kind']=='postcheck')
supply=4.89;nominal=supply/16383
shifts={ch:(summaries[1]['mean_counts'][ch]-summaries[0]['mean_counts'][ch])*nominal*1000 for ch in ['A1','A2','A3','A4']}
assert max(map(abs,shifts.values()))<=3
anchor_counts={ch:(summaries[0]['mean_counts'][ch]+summaries[1]['mean_counts'][ch])/2 for ch in ['A1','A2','A3','A4']}
# Point anchors use the DMM only. Prior slopes are retained as assumptions;
# this point does not estimate either slope or certify a voltage range.
supply_ratio=supply/profile['nominal_supply_conversion_v']
g3=profile['channels']['A3']['gain_v_per_count']*supply_ratio;g4=nominal
gdac=profile['DAC_to_driver_path']['gain_v_per_code']*supply_ratio
latest=summaries[1]['mean_counts']
physical_drive=.0+1.632+g3*(latest['A3']-anchor_counts['A3'])
physical_ref=1.637+g4*(latest['A4']-anchor_counts['A4'])
old_code=1369;shift=(physical_ref-physical_drive)/gdac;new_code=old_code+round(shift)
assert abs(new_code-old_code)<=8 and abs((new_code-old_code)*gdac)<=.010
expected_drive=physical_drive+(new_code-old_code)*gdac
config=InstrumentConfig(vref_v=supply,ref_v=1.635)
# Explicit integer-code override for this calibration trial. Keep the physical
# estimate distinct from InstrumentConfig's old nominal voltage center.
clip_low=max(16,math.floor((physical_ref-1.1)*16383/supply));clip_high=min(16367,math.ceil((physical_ref+1.1)*16383/supply))
arm=f"ARM {last_pong['boot_id']} {new_code} {new_code-config.max_jump} {new_code+config.max_jump} {config.max_jump} 1200 20 {clip_low} {clip_high}\n"
p={'scope':'One same-boot near-REF centering calibration trial; automatic/general tracking remains disabled pending independent verification',
'boot_id':last_pong['boot_id'],'previous_uptime_ms':last_pong['uptime_ms'],'old_code':old_code,'old_max_jump_code':config.max_jump,'new_code':new_code,'supply_estimate_v':supply,'supply_remeasured_during_bracket':False,
'DMM_report':{'verbatim':'REF 전 1.637 / DRIVE 1.632 / OUT 1.634 / REF 후 1.637','REF_before_v':1.637,'DRIVE_v':1.632,'OUT_v':1.634,'REF_after_v':1.637,'range':'DC 2 V','exact_read_timestamps_unknown':True},
'bracket_mean_drift_mV':shifts,'bracket_limit_mV':3,'before_after_noise':noise,'anchor_mean_counts':anchor_counts,
'control_anchor':{'A3':{'anchor_v':1.632,'gain_v_per_count_assumed':g3},'A4':{'anchor_v':1.637,'gain_v_per_count_assumed':g4},'DAC_to_driver_gain_v_per_code_assumed':gdac,'A4_gain_calibrated':False,'existing_profile_modified':False},
'latest_estimated_DRIVE_v':physical_drive,'latest_estimated_REF_v':physical_ref,'requested_delta_codes':new_code-old_code,'predicted_delta_DRIVE_v':(new_code-old_code)*gdac,'predicted_DRIVE_after_v':expected_drive,'predicted_DRIVE_minus_REF_after_v':expected_drive-physical_ref,
'arm_command':arm.strip(),'hold_command':f"CAPTURE {last_pong['boot_id']} HOLD 512 2000 {new_code} 0",
'guards':{'same_boot_held_code_and_ADC_state_required':True,'pre_capture_mean_drift_mV_max':3,'raw_limits_exclusive':[16,16367],'max_code_move':8,'max_estimated_move_v':.010,'post_A4_mean_drift_mV_max':3,'post_ADC_DRIVE_minus_REF_abs_mV_max':3,'independent_DMM_DRIVE_minus_REF_abs_mV_max':3,'independent_DMM_REF_before_after_abs_mV_max':3},
'limits':['Point anchors are sequential and their ADC brackets differ; they do not prove simultaneity.','A4 slope is assumed and A3/DAC slopes are retained from provisional calibration.','This is only near the current REF, in this boot and unchanged fixture.','A successful independent DMM check supports one small centering move, not general tracking, absolute accuracy or full D2 acceptance.','No old prediction score is altered, and no OUT verification trace is used to adjust a forecast.'],
'source_hashes':{str(path):hashlib.sha256(path.read_bytes()).hexdigest() for path in [before/'events.jsonl',after/'events.jsonl',profile_path]}}
log=Recorder('runs/hardware-local-ref-centering-plan',mode='frozen_single_move_A3_A4_point_alignment_trial')
(log.path/'controller-source.py').write_bytes(Path(__file__).read_bytes());(log.path/'plan.json').write_text(json.dumps(p,indent=2)+'\n')
log.add('bracket_stability_result',{'mean_drift_mV':shifts,'declared_max_mV':3,'passed':True,'calibration_range_not_established':True})
log.add('centering_plan_frozen',{'sha256':hashlib.sha256((log.path/'plan.json').read_bytes()).hexdigest(),'old_code':old_code,'new_code':new_code,'physical_REF_estimate_v':physical_ref,'predicted_DRIVE_after_v':expected_drive,'independent_ADC_DMM_check_not_yet_acquired':True,'automatic_tracking_enabled':False})
log.add('run_completed',{'hardware_IO':False,'centering_trial_pending':True,'full_D2_accepted':False})
Path('runs/local-ref-centering-plan-path.txt').write_text(str(log.path/'plan.json')+'\n')
print(json.dumps({'record':str(log.path),'bracket_drift_mV':shifts,'old_code':old_code,'new_code':new_code,'predicted_move_mV':(new_code-old_code)*gdac*1000,'REF_estimate_v':physical_ref,'predicted_DRIVE_after_v':expected_drive}))
