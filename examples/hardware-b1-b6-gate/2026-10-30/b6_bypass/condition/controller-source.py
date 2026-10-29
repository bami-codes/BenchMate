from pathlib import Path
import sys,json,hashlib
ROOT=Path('/Users/bami/Documents/metaai');sys.path.insert(0,str(ROOT/'src'))
from benchmate.records import Recorder,read_events
from benchmate.instrument import InstrumentConfig,capture_command
common_path=Path((ROOT/'runs/b1-b6-gate-plan-path.txt').read_text().strip());common=json.loads(common_path.read_text())
common_sha=hashlib.sha256(common_path.read_bytes()).hexdigest()
assert read_events(common_path.parent)[-1]['payload']['plan_sha256']==common_sha
source=ROOT/'examples/hardware-d01-repair/2026-10-30/conditional-protocol-after-reset/protocol.json'
p=json.loads(source.read_text());config=InstrumentConfig(**p['configuration'])
settings={k:v for k,v in common['common_stimulus'].items() if k!='step_index'}
request=capture_command(config,boot_id='1'*32,**settings);amplitude=int(request.split()[5]);n=settings['samples'];index=n//10
p.update(scope=common['scope'],condition_id='b6_bypass',shunt_ohm=0.,branch_ohm=common['branch_resistor_ohm'],current_error_limit_v=.009,
    model_plan=str(common_path.relative_to(ROOT)),model_plan_sha256=common_sha,
    previous_boot_id='df30dadf96e11e908eeb1caac6bb961d',
    operator_removal_report='USB 분리 / IN 분기 연결(A55–C35) / IN 삐 / REF 삐 / 추가 확인: D55↔F22(OUT) 무음',
    operator_power_report='B6 USB connected per operator; previous supply estimate 4.89 V retained, not remeasured. IN branch A55-C35 installed; OUT E30-A55 absent; jumper 11 bypass and jumper 14 retained.',
    operator_connection_report=json.loads(Path('/private/tmp/benchmate-b6-connected.json').read_text())['verbatim'],
    decision=common['gate_rule'])
for key in ['operator_RESET_report','preceding_attempt','preceding_attempt_status','operator_post_failure_DMM_report','development_replay_not_independent_verification','original_failure_preserved']:
    p.pop(key,None)
p['startup_policy']=common['power_policy']
p['hookup_confirmation_record']=(ROOT/'runs/b6-bypass-hookup-path.txt').read_text().strip()
p['waveforms']=[{'settings':settings,'warmup_frames':0,
    'expected_DAC_codes':[config.ref_code+(-amplitude if i<index else amplitude) for i in range(n)],
    'nominal_A2_time_s':[(i*settings['period_us']+105)*1e-6 for i in range(n)],
    'predictions':{name:{'gain':1.,'tau_s':common['fixed_RC']['tau_s']} for name in ['no_input_branch','input_branch']}}]
p['engineering_limits']['reference_guard_A4_block_mean_span_mV_max']=3
p['guard_captures']={'count':4,'samples':512,'period_us':2000,'positions':['baseline 1','baseline 2','baseline 3','after step']}
p['predictor_sha256']=hashlib.sha256((ROOT/'src/benchmate/measured_input.py').read_bytes()).hexdigest()
p['branch_evaluator_sha256']=hashlib.sha256((ROOT/'src/benchmate/branch_gate.py').read_bytes()).hexdigest()
p['capture_controller_sha256']=hashlib.sha256(Path('/private/tmp/benchmate-capture-branch-gate.py').read_bytes()).hexdigest()
p['protocol_revision_after_observed_failure']=False
p['all_four_conditions_use_same_rules']=True
p['condition_label_not_used_to_select_supported_alternative']=True
p['predictor_validation']='16 unit tests passed for measured-input RC prediction and identical branch-evidence rules in all four shunt/specimen combinations.'
log=Recorder(ROOT/'runs/hardware-b1-b6-condition',mode='b6_bypass_under_frozen_common_gate')
for src,name in [(Path(__file__),'controller-source.py'),(Path('/private/tmp/benchmate-capture-branch-gate.py'),'capture-controller.py'),
                 (source.parent/'provisional-calibration.json','provisional-calibration.json'),(common_path,'common-plan.json')]:
    (log.path/name).write_bytes(src.read_bytes())
(log.path/'condition.json').write_text(json.dumps(p,ensure_ascii=False,indent=2)+'\n');sha=hashlib.sha256((log.path/'condition.json').read_bytes()).hexdigest()
log.add('operator_state_report',{'preparation':p['operator_removal_report'],'USB_connection_report':p['operator_connection_report'],'new_shunt_not_installed':True})
log.add('gate_condition_frozen',{'sha256':sha,'common_plan_sha256':common_sha,'no_gate_measurement_used':True,'condition':'b6_bypass'})
log.add('run_completed',{'hardware_IO':False,'condition_sha256':sha,'capture_pending':True})
(ROOT/'runs/b1-b6-condition-path.txt').write_text(str(log.path/'condition.json')+'\n')
print(json.dumps({'condition':str(log.path/'condition.json'),'condition_sha256':sha,'ref_code':config.ref_code,'shunt_ohm':0,'tau_ms':common['fixed_RC']['tau_s']*1000,'hardware_IO':False}))
