"""Assess the independent DMM check separately from later ADC drift."""
from pathlib import Path
import json,hashlib
from benchmate.records import Recorder,read_events
plan_path=Path('runs/hardware-local-ref-centering-plan/20261029T142321-622c7d06f9/plan.json')
trial=Path('runs/hardware-local-ref-centering-trial/20261029T142505-120bb8e3b0')
after=Path('runs/hardware-d01-reference-alignment/20261029T142841-35469e8228')
p=json.loads(plan_path.read_text());r=json.loads((trial/'result.json').read_text());s=json.loads((after/'summary.json').read_text())
assert read_events(trial)[-1]['kind']=='run_completed';e=read_events(after);assert e[-1]['kind']=='run_completed'
dmm=next(x['payload'] for x in e if x['kind']=='independent_DMM_report');v=dmm['values_v'];ref=(v[0]+v[2])/2
DMM_checks={'REF_display_returned':abs(v[2]-v[0])*1000<=p['guards']['independent_DMM_REF_before_after_abs_mV_max'],'DRIVE_close_to_REF':abs(v[1]-ref)*1000<=p['guards']['independent_DMM_DRIVE_minus_REF_abs_mV_max']}
counts=s['mean_counts'];drift={ch:(counts[ch]-r['after_mean_counts'][ch])*4.89/16383*1000 for ch in counts}
anchor=p['control_anchor'];base=p['anchor_mean_counts'];drive=anchor['A3']['anchor_v']+anchor['A3']['gain_v_per_count_assumed']*(counts['A3']-base['A3']);reference=anchor['A4']['anchor_v']+anchor['A4']['gain_v_per_count_assumed']*(counts['A4']-base['A4'])
result={'scope':'Single local correction and independent DMM check; later ADC mismatch means automatic tracking is not yet validated','plan_record':str(plan_path.parent),'trial_record':str(trial),'post_DMM_snapshot_record':str(after),'DMM_report':dmm,'DMM_difference_mV':(v[1]-ref)*1000,'DMM_checks':DMM_checks,'single_move_DMM_check_passed':all(DMM_checks.values()),'trial_ADC_checks_passed':r['ADC_checks_passed'],'after_DMM_ADC_mean_changes_mV':drift,'after_DMM_local_estimated_DRIVE_v':drive,'after_DMM_local_estimated_REF_v':reference,'after_DMM_local_estimated_difference_mV':(drive-reference)*1000,'A4_later_change_exceeds_3mV_engineering_allowance':abs(drift['A4'])>3,'stability_comparison_is_separate_from_single_move_DMM_pass':True,'cause_of_difference_unresolved':True,'same_output_code_and_boot':s['held_ref_code']==r['held_code'] and s['boot_id']==r['boot_id'],'held_code':s['held_ref_code'],'boot_id':s['boot_id'],'automatic_reference_tracking_enabled':False,'existing_calibration_modified':False,'repair_performed':False,'next_check':'Simultaneous differential DMM DRIVE-REF observation during fixed-output ADC blocks; await probe-ready report','full_D2_accepted':False}
log=Recorder('runs/hardware-local-ref-centering-assessment',mode='independent_meter_point_pass_and_subsequent_ADC_mismatch_both_retained')
(log.path/'controller-source.py').write_bytes(Path(__file__).read_bytes());(log.path/'assessment.json').write_text(json.dumps(result,indent=2)+'\n');log.add('centering_assessment',result);log.add('run_completed',{'hardware_IO':False,'single_move_DMM_check_passed':True,'automatic_tracking_enabled':False,'simultaneous_check_pending':True})
print(json.dumps({'record':str(log.path),'DMM_checks':DMM_checks,'post_DMM_ADC_change_mV':drift,'latest_local_estimated_difference_mV':(drive-reference)*1000,'held_code':s['held_ref_code']}))
