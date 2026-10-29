from pathlib import Path
import sys,json,hashlib
ROOT=Path('/Users/bami/Documents/metaai');sys.path.insert(0,str(ROOT/'src'))
from benchmate.records import Recorder,read_events
source=ROOT/'examples/hardware-d01-repair/2026-10-30/model-freeze/20261029T151250-08a588f6dc/plan.json'
prior=json.loads(source.read_text());repair=prior['models']['repair_to_declared_nominal_C']
R=repair['R_ohm'];C=repair['C_f'];branch=prior['load_ohm'];shunt=996.;fraction=shunt/(shunt+branch)
plan={
 'scope':'Known-passive B1/B6 engineering gate within two declared input-branch alternatives; not a blinded five-family diagnosis or final benchmark.',
 'operator_preparation_report':'USB 분리 / OUT 부하 점퍼 제거 / 1kΩ 실측 0.996 kΩ',
 'preparation':{'USB_disconnected':True,'OUT_lead_E30_A55_removed':True,'original_RC_retained':True,'shunt_measured_outside_circuit_ohm':shunt,'shunt_not_yet_installed':True},
 'fixed_RC':{'R_ohm':R,'C_f':C,'tau_s':R*C,'output_gain_from_measured_IN':1.,'source':str(source.relative_to(ROOT)),'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest()},
 'branch_resistor_ohm':branch,'branch_value_source':'Previously reported fixture/intervention resistor 9.99 kohm; now available for the declared IN-REF intervention.',
 'shunt_ohm':shunt,
 'conditions_in_order':[
   {'id':'b1_bypass','branch_installed':False,'shunt_installed':False},
   {'id':'b6_bypass','branch_installed':True,'shunt_installed':False},
   {'id':'b6_shunt','branch_installed':True,'shunt_installed':True},
   {'id':'b1_shunt','branch_installed':False,'shunt_installed':True}],
 'label_policy':'Condition labels are operator/evaluation metadata, never a diagnostic answer. Both branch hypotheses are evaluated identically under each instrument shunt setting.',
 'common_stimulus':{'kind':'step','amplitude_v':.2,'samples':512,'period_us':500,'step_index':51},
 'baseline':{'separate_HOLD_blocks':3,'samples_per_block':512,'period_us':2000,'freeze_A1_A2_origin_before_scored_step':True},
 'return_guard':{'HOLD_blocks':1,'samples':512,'period_us':2000},
 'conditional_OUT_predictions':'Both branch alternatives share the same fixed RC response conditional on measured A1. No scored OUT is used to fit gain, tau, offset or initialization.',
 'current_observable':{
    'definition':'D = mean(A3-A1)_high - mean(A3-A1)_low, and DeltaDrive = mean(A3)_high - mean(A3)_low, using provisional affine maps.',
    'low_window':'First 51 samples, preceded by firmware settled low drive.',
    'high_window':'Last 100 samples; at least 150 ms after the step.',
    'samples_trimmed':0,'all_A1_A3_samples_in_each_window_used':True,
    'no_branch_prediction':'D = 0',
    'branch_with_bypass_prediction':'D = 0; output-only observations do not distinguish the declared branch alternatives.',
    'branch_with_shunt_prediction':'D = DeltaDrive * measured_shunt / (measured_shunt + declared_branch_resistor)',
    'branch_shunt_fraction':fraction,'illustrative_D_at_0_4V_DeltaDrive_mV':fraction*.4*1000,
    'conditional_input_used':'Only measured A3 drive excursion supplies DeltaDrive; A1 enters the scored drop, never its predicted value.',
    'interpretation':'Two settled levels within one step block, not two independently acquired DC blocks. Count the actual block and both levels explicitly.'},
 'engineering_limits':{'OUT_whole_and_each_step_region_RMS_mV_max':9,
    'step_regions_ms':[['pre_step',None,0],['0_to_5ms',0,5],['5_to_20ms',5,20],['20_to_80ms',20,80],['after_80ms',80,None]],
    'current_two_level_prediction_absolute_error_mV_max':9,
    'A4_block_mean_span_mV_max':3,'stationary_channel_mean_span_mV_max':3,
    'max_prediction_time_error_us':25,'DAC_code_error_max':0,
    'minimum_measured_drive_excursion_v':.30,
    'basis':'Predeclared development engineering allowances, not calibrated noise confidence or final detection limits.'},
 'gate_rule':'Both bypass conditions must pass the common OUT response and zero-drop check while leaving branch alternatives unresolved. With the same shunt, each specimen must pass its corresponding current prediction and reject the other. Complete both shunted controls before claiming the gate; do not revise limits or subtract a B6-fitted offset.',
 'wiring':{'B1_bypass':'OUT E30-A55 removed; 11 B28-B35 and 14 B50-B23 retained; no IN branch.',
   'B6_bypass':'With USB off, add A55-C35 only; OUT E30-A55 must remain absent; C23-A60 return and jumper 14 retained.',
   'B6_shunt':'With USB off, replace jumper 11 B28-B35 with measured 996 ohm resistor, keeping input branch.',
   'B1_shunt':'With USB off, remove complete A55-C35 input-branch lead, keeping same measured shunt.',
   'interlock':'Never install OUT E30-A55 and IN A55-C35 simultaneously; never leave jumper 11 in parallel with the shunt.'},
 'power_policy':'Known passive fixture only; fresh boot identity and one explicit REF ARM after confirmed USB-off wiring. Retain last 4.89 V supply estimate and small +/-0.2 V stimulus; record that supply is not remeasured. Raw REF, rail, path-return and timing guards must pass before accepting data. This is not calibrated absolute bias or a general boot-continuation policy.',
 'automatic_A4_control':False,'automatic_retry_or_rearm':False,'Spark_invoked':False,'full_D2_accepted':False,
 'physical_gate_complete':False,
}
base=ROOT/'examples/hardware-b1-b6-gate/2026-10-30';assert not base.exists()
log=Recorder(base/'plan-freeze',mode='common_B1_B6_protocol_frozen_before_first_gate_capture')
(log.path/'controller-source.py').write_bytes(Path(__file__).read_bytes())
(log.path/'plan.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2)+'\n');digest=hashlib.sha256((log.path/'plan.json').read_bytes()).hexdigest()
log.add('operator_preparation_confirmed',{'verbatim':plan['operator_preparation_report'],'shunt_ohm':shunt})
log.add('common_protocol_frozen',{'plan_sha256':digest,'all_four_conditions_pending':True,'thresholds_fixed_before_gate_data':True})
log.add('run_completed',{'hardware_IO':False,'plan_sha256':digest,'B1_USB_reconnection_pending':True})
(base/'README.md').write_text(f'''# B1/B6 physical gate — protocol frozen, no gate captures yet

The operator removed the E30-A55 OUT-load jumper with USB disconnected and
reported a separate shunt of **996 ohm**. The 9.99 kohm resistor and its REF
return remain installed but disconnected at the OUT end.

The [common plan](plan-freeze/{log.path.name}/plan.json) is fixed before all
four conditions: B1 bypass, B6 bypass, B6 with shunt, B1 with the same shunt.
Both alternatives share the same measured-IN conditional OUT response, with
tau **{R*C*1000:.5f} ms** fixed from the earlier pre-repair estimate and the
nominal repair C. Two settled step levels yield the A3-minus-A1 contrast.
The branch-plus-shunt model predicts **{fraction:.8f} times measured DRIVE
excursion**, about **{fraction*.4*1000:.3f} mV** for 0.4 V drive excursion;
the no-branch model predicts zero. Limits and control comparisons are frozen.

This is a known-passive, two-alternative engineering check, not full five-family
blind diagnosis, two independent DC captures or a calibrated detection limit.
The smaller +/-0.2 V stimulus is reported explicitly; the registered ideal
+/-1 V contrast of 181.8 mV is not being claimed here.

First requested state is restored B1 with jumper 11 retained and no load/input
branch. New shunt installation and later rewiring require their own USB-off
confirmation. All four conditions remain pending.
''')
(ROOT/'runs/b1-b6-gate-plan-path.txt').write_text(str(log.path/'plan.json')+'\n')
assert read_events(log.path)[-1]['kind']=='run_completed'
print(json.dumps({'plan':str(log.path/'plan.json'),'tau_ms':R*C*1000,'shunt_ohm':shunt,'branch_drop_fraction':fraction,'illustrative_drop_mV':fraction*.4*1000,'plan_sha256':digest,'hardware_IO':False}))
