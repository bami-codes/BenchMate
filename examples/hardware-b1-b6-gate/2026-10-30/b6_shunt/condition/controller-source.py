"""Freeze the next shunted condition without changing common scoring rules."""
from pathlib import Path
import hashlib,json,sys
ROOT=Path('/Users/bami/Documents/metaai');sys.path.insert(0,str(ROOT/'src'))
from benchmate.records import Recorder,read_events

report=json.loads(Path(sys.argv[1]).read_text())
condition_id=report['condition_id']
assert condition_id in ('b6_shunt','b1_shunt')
assert report['USB_connected'] is True and report['preparation_verbatim'] and report['connection_verbatim']
previous_path=Path((ROOT/'runs/b1-b6-gate-capture-path.txt').read_text().strip())
previous=json.loads((previous_path/'result.json').read_text())
assert read_events(previous_path)[-1]['kind']=='run_completed'
assert previous['condition_id']=={'b6_shunt':'b6_bypass','b1_shunt':'b6_shunt'}[condition_id]
base=ROOT/'examples/hardware-b1-b6-gate/2026-10-30/b1_bypass/condition'
p=json.loads((base/'condition.json').read_text())
common_path=ROOT/p['model_plan'];common=json.loads(common_path.read_text())
sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
assert sha(common_path)==p['model_plan_sha256']
assert sha(ROOT/'src/benchmate/measured_input.py')==p['predictor_sha256']
assert sha(ROOT/'src/benchmate/branch_gate.py')==p['branch_evaluator_sha256']
assert sha(Path('/private/tmp/benchmate-capture-branch-gate.py'))==p['capture_controller_sha256']
branch_installed=condition_id=='b6_shunt'
p.update(condition_id=condition_id,shunt_ohm=common['shunt_ohm'],previous_boot_id=previous['boot_id'],
         preceding_condition_record=str(previous_path.relative_to(ROOT)),
         operator_removal_report=report['preparation_verbatim'],
         operator_connection_report=report['connection_verbatim'],
         operator_power_report='USB reconnected per operator; last 4.89 V supply estimate retained, not remeasured. Measured 996 ohm shunt installed at B28-B35; jumper 11 fully removed; OUT E30-A55 absent; jumper 14 and REF return retained. IN branch '+('installed.' if branch_installed else 'removed.'))
p['startup_policy']=common['power_policy']
p.pop('operator_RESET_report',None)
log=Recorder(ROOT/'runs/hardware-b1-b6-condition',mode=condition_id+'_under_frozen_common_gate')
for src,name in [(Path(__file__),'controller-source.py'),(Path('/private/tmp/benchmate-capture-branch-gate.py'),'capture-controller.py'),
                 (base/'provisional-calibration.json','provisional-calibration.json'),(common_path,'common-plan.json')]:
    (log.path/name).write_bytes(src.read_bytes())
(log.path/'operator-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
(log.path/'condition.json').write_text(json.dumps(p,ensure_ascii=False,indent=2)+'\n')
digest=sha(log.path/'condition.json')
log.add('operator_state_report',report)
log.add('gate_condition_frozen',{'sha256':digest,'common_plan_sha256':p['model_plan_sha256'],'no_gate_measurement_used':True,'condition':condition_id})
log.add('run_completed',{'hardware_IO':False,'condition_sha256':digest,'capture_pending':True})
(ROOT/'runs/b1-b6-condition-path.txt').write_text(str(log.path/'condition.json')+'\n')
print(json.dumps({'condition':str(log.path/'condition.json'),'condition_sha256':digest,'shunt_ohm':p['shunt_ohm'],'previous_boot_id':p['previous_boot_id'],'common_scoring_unchanged':True}))
