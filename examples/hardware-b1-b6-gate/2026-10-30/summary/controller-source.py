"""Aggregate the four predeclared controls; no changed limits or offset fit."""
from pathlib import Path
import hashlib,json,sys
ROOT=Path('/Users/bami/Documents/metaai');sys.path.insert(0,str(ROOT/'src'))
from benchmate.records import Recorder,read_events
base=ROOT/'examples/hardware-b1-b6-gate/2026-10-30'
common_path=Path((ROOT/'runs/b1-b6-gate-plan-path.txt').read_text().strip())
common=json.loads(common_path.read_text());common_sha=hashlib.sha256(common_path.read_bytes()).hexdigest()
rows=[];boots=[];source_hashes=[];frozen_rules=[]
for spec in common['conditions_in_order']:
    folder=base/spec['id'];result_path=folder/'capture/result.json'
    p=json.loads((folder/'condition/condition.json').read_text());r=json.loads(result_path.read_text())
    condition_events=read_events(folder/'condition');events=read_events(folder/'capture')
    assert condition_events[-1]['kind']==events[-1]['kind']=='run_completed'
    assert p['condition_id']==r['condition_id']==spec['id']
    assert p['model_plan_sha256']==common_sha
    assert r['prediction_sha256']==hashlib.sha256((folder/'condition/condition.json').read_bytes()).hexdigest()
    assert p['shunt_ohm']==(common['shunt_ohm'] if spec['shunt_installed'] else 0)
    freeze=next(e for e in condition_events if e['kind']=='gate_condition_frozen')
    origin=next(e for e in events if e['kind']=='pre_stimulus_origin_frozen')
    step=next(e for e in events if e['kind']=='serial_command' and ' STEP ' in e['payload']['request'])
    assert freeze['timestamp']<events[0]['timestamp'] and origin['sequence']<step['sequence']
    common_fields=['configuration','waveforms','engineering_limits','guard_limits','pre_stimulus_origin','voltage_conversion',
                   'predictor_sha256','branch_evaluator_sha256','capture_controller_sha256','branch_ohm','current_error_limit_v']
    frozen_rules.append({k:p[k] for k in common_fields})
    score=r['scores']['step'];ev=score['current_evidence']
    expected=['input_branch' if spec['branch_installed'] else 'no_input_branch'] if spec['shunt_installed'] else ['no_input_branch','input_branch']
    guards=[e['payload']['checks'] for e in events if e['kind']=='reference_guard']
    assert len(guards)==4
    checks={'conditional_OUT':r['conditional_transfer_check_passed'],
            'electrical_and_return_guards':all(all(g.values()) for g in guards+[score['electrical_guards']]),
            'expected_alternatives':r['supported_branch_alternatives']==expected,
            'no_scored_OUT_refit':r['scored_OUT_samples_used_for_refit']==0,
            'all_frames_counted':r['total_frames']==2560 and r['capture_attempts']==5}
    rows.append({'condition':spec['id'],'shunt_ohm':p['shunt_ohm'],'OUT_RMS_mV':score['models']['no_input_branch']['RMS_mV'],
                 'A4_mean_span_mV':r['A4_mean_span_mV'],'drop_contrast_mV':ev['observed_drop_contrast_v']*1000,
                 'drive_excursion_v':ev['drive_excursion_v'],'current_scores':ev['scores'],
                 'supported_alternatives':r['supported_branch_alternatives'],'checks':checks,'passed':all(checks.values()),
                 'frames':r['total_frames'],'boot_id':r['boot_id']})
    boots.append(r['boot_id']);source_hashes.append({'path':str(result_path.relative_to(ROOT)),'sha256':hashlib.sha256(result_path.read_bytes()).hexdigest()})
assert len(set(boots))==4
assert all(r==frozen_rules[0] for r in frozen_rules[1:]),'Common model or rules changed between conditions'
passed=all(r['passed'] for r in rows)
summary={'scope':common['scope'],'common_plan_sha256':common_sha,'all_four_conditions_recorded':True,
         'common_rule_equality_checked':True,'gate_passed':passed,'conditions':rows,'source_result_hashes':source_hashes,
         'total_frames':sum(r['frames'] for r in rows),'scored_frames':4*512,'stationary_frames':4*2048,
         'B6_minus_B1_shunted_contrast_mV':rows[2]['drop_contrast_mV']-rows[3]['drop_contrast_mV'],
         'B1_offset_subtracted_for_scoring':False,'condition_label_used_for_diagnostic_scoring':False,
         'condition_label_used_only_to_check_expected_control_outcome':True,
         'absolute_voltage_validation':False,'Spark_invoked':False,'blinded_benchmark':False}
log=Recorder(ROOT/'runs/hardware-b1-b6-gate-summary',mode='predeclared_four_condition_gate_aggregation')
(log.path/'controller-source.py').write_bytes(Path(__file__).read_bytes())
(log.path/'result.json').write_text(json.dumps(summary,indent=2)+'\n')
log.add('common_gate_evaluated',summary);log.add('run_completed',{'gate_passed':passed,'hardware_IO':False})
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
fig,axes=plt.subplots(1,2,figsize=(10,4),layout='constrained')
x=list(range(4));labels=['B1 / bypass','B6 / bypass','B6 / 996Ω','B1 / 996Ω']
axes[0].bar(x,[r['drop_contrast_mV'] for r in rows],color=['#7090a5','#7090a5','#177b73','#177b73'])
axes[0].axhline(0,color='#555',lw=.8);axes[0].set_ylabel('Change in DRIVE − IN (mV)')
axes[0].set_title('Measured two-level current contrast')
axes[1].bar(x,[r['OUT_RMS_mV'] for r in rows],color='#177b73')
axes[1].axhline(9,color='#b24735',ls='--',label='Frozen 9 mV allowance')
axes[1].set_ylabel('Conditional OUT RMS (mV)');axes[1].set_title('Same fixed RC model in all conditions');axes[1].legend(fontsize=8)
for ax in axes:ax.set_xticks(x,labels,rotation=20,ha='right');ax.spines[['top','right']].set_visible(False)
fig.suptitle('Known-passive B1/B6 engineering controls · ±0.2 V command',fontsize=12)
fig.savefig(log.path/'four-condition-gate.png',dpi=160);plt.close(fig)
(ROOT/'runs/b1-b6-gate-summary-path.txt').write_text(str(log.path)+'\n')
print(json.dumps({'record':str(log.path),'gate_passed':passed,'total_frames':summary['total_frames'],'contrast_mV':summary['B6_minus_B1_shunted_contrast_mV']}))
