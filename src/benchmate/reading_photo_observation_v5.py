"""Source-frozen isolated reading after a preserved failed photo-stage parent."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

from .records import Recorder, decode_events
from .reading_rules import digest, score_reading
from .reading_candidates_v3 import parse
from .reading_timing_verify_v4 import chain, verify_pair, require, check_file

ROOT = Path(__file__).resolve().parents[2]
PUBLIC = Path('examples/reading-photo-observation/2026-11-04')
SOURCES = ('src/benchmate/reading_photo_observation_v5.py',
           'tests/test_reading_photo_observation_v5.py',
           'docs/2026-11-04-photo-observation-continuation-v5.md')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path, value):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n')


def binding_receipt(proposal, confirmation):
    if (proposal.get('mapping_status') != 'unique' or proposal.get('sam_body') is None
            or proposal.get('chosen_by') != 'muse_spark'
            or set(confirmation) != {'accepted', 'operator_verbatim'}
            or confirmation['accepted'] is not True
            or not isinstance(confirmation['operator_verbatim'], str)
            or not confirmation['operator_verbatim'].strip()):
        raise ValueError('Actual yes/no acceptance of a unique Spark correspondence required.')
    return {**proposal, 'operator_confirmed': True,
            'operator_verbatim': confirmation['operator_verbatim'],
            'binding_version': 'mixed-localizer-photo-v5',
            'surface_values_used_for_scoring': False}


def validate_body_record(parent, follow, plan):
    pe = chain(parent / 'events.jsonl')
    require(sha(parent/'events.jsonl') == plan['parent_events_sha256']
            and pe[-1]['sha256'] == plan['parent_head_sha256'], 'retained_parent_changed')
    events = chain(follow/'events.jsonl')
    links = [e['payload'] for e in events if e['kind'] == 'child_record_bound']
    require(len(links) == 1 and links[0]['kind'] == 'body_candidates_v5', 'expected_one_body_child')
    link = links[0]; child = check_file(follow, link)
    ce = chain(child, link['head_sha256'])
    require(ce[-1]['kind'] == 'run_completed' and ce[-1]['payload']['requests'] == 1, 'body_child_incomplete')
    args = ce[-1]['payload']['arguments']
    tool = next(e['payload']['tool'] for e in ce if e['kind'] == 'model_request_frozen')
    require(tool == plan['tool'], 'body_tool_not_published_tool')
    proposal = json.loads((follow/'candidate-proposal.json').read_text())
    parsed = parse(args, plan['candidate_ids_supplied'])
    require(all(proposal[k] == v for k, v in parsed.items()), 'proposal_not_raw_Spark_choice')
    for name, expected in plan['inputs'].items():
        relative = name.split(parent.name+'/', 1)[1] if parent.name in name else name.split(plan['parent'].split('/')[-1]+'/', 1)[1]
        require(sha(parent/relative) == expected, 'retained_body_input_changed')
    return proposal, len(events) + len(ce)


def begin(parent, follow, plan_file, report_file):
    from scripts import reading_experiment_timing_v4 as r
    r.check_freeze()
    parent=Path(parent).resolve();follow=Path(follow).resolve();plan_file=Path(plan_file).resolve()
    audit=verify_pair(parent)
    if not audit['passed'] or audit['run_status']!='run_failed':
        raise ValueError('Preserved verified failed parent required.')
    plan=json.loads(plan_file.read_text())
    proposal,_=validate_body_record(parent,follow,plan)
    confirmation=json.loads(Path(report_file).read_text())
    binding=binding_receipt(proposal,confirmation)
    forecast=json.loads((parent/'reading-forecast.json').read_text())
    require(binding['component']==forecast['request']['component'],'target_changed')
    log=Recorder(ROOT/'runs/reading-photo-observation',mode='isolated_reading_after_photo_input_failure_v5')
    shutil.copytree(parent,log.path/'history/original',ignore=shutil.ignore_patterns('*-local-only.json'))
    shutil.copytree(follow,log.path/'history/body-followup')
    shutil.copyfile(plan_file,log.path/'history/body-request-plan.json')
    shutil.copyfile(parent/'reading-forecast.json',log.path/'reading-forecast.json')
    reg={'schema':'benchmate.photo_observation_continuation.v5','case_id':json.loads((parent/'state.json').read_text())['case_id'],
         'run_id':log.path.name,'parent_run_id':parent.name,'original_status':'run_failed',
         'original_failure_counted':True,'original_selection_unchanged':True,'blind_test':False,
         'parent_head_sha256':audit['head_sha256'],'body_followup_head_sha256':chain(follow/'events.jsonl')[-1]['sha256'],
         'reading_forecast_sha256':digest(forecast),'source_sha256':{n:sha(ROOT/n) for n in SOURCES},
         'public_registration':str(PUBLIC/'registrations'/(log.path.name+'.json')),
         'new_model_calls':0,'new_hardware_commands':0,'original_reading_ranges_unchanged':True,
         'parent_sealed_assembly_available_locally_only':True}
    save(log.path/'registration.json',reg);save(ROOT/reg['public_registration'],reg)
    log.add('photo_observation_continuation_registered',reg)
    log.add('retained_reading_evidence_bound',{'artifacts':[{'file':str(f.relative_to(log.path)),'sha256':sha(f)} for f in
        [log.path/'history/original/events.jsonl',log.path/'history/body-followup/events.jsonl',log.path/'history/body-request-plan.json',log.path/'reading-forecast.json']]})
    save(log.path/'body-binding.json',binding);log.add('body_binding',binding)
    state(log,'awaiting_reading_observation')
    print(json.dumps({'record':str(log.path),'public_registration':reg['public_registration'],'new_API_calls':0,'new_hardware_commands':0}))


def state(log,phase):
    value={'phase':phase};log.add('reading_continuation_state',value);save(log.path/'state.json',value)


def opened(record,phases):
    path=Path(record).resolve();events=decode_events((path/'events.jsonl').read_bytes(),require_terminal=False,include_hash=True)
    require(events[-1]['kind'] not in ('run_completed','run_failed'),'terminal_continuation')
    control=next(e['payload'] for e in reversed(events) if e['kind']=='reading_continuation_state')
    require(control['phase'] in phases,'wrong_continuation_phase')
    reg=json.loads((path/'registration.json').read_text())
    for n,h in reg['source_sha256'].items():require(sha(ROOT/n)==h,'reading_stage_source_changed')
    log=Recorder.__new__(Recorder);log.path=path;log.file=path/'events.jsonl';log.previous=events[-1]['sha256'];log.sequence=len(events)
    return log,reg


def observe(record,report_file,evidence=None):
    from scripts import reading_experiment_timing_v4 as r
    log,reg=opened(record,['awaiting_reading_observation']);r.committed(ROOT/reg['public_registration'])
    report=json.loads(Path(report_file).read_text())
    require(set(report)=={'reading','operator_verbatim'} and isinstance(report['operator_verbatim'],str),'exact_free_reading_report_required')
    if evidence:
        from .known_design import sanitize_image
        raw,_=sanitize_image(Path(evidence).read_bytes())
    else:raw=(log.path/'history/original/photo-faulted/prepared/input.png').read_bytes()
    observation={**report['reading'],'photo':{'file':'reading-evidence.png','sha256':hashlib.sha256(raw).hexdigest()}}
    forecast=json.loads((log.path/'reading-forecast.json').read_text());scored=score_reading(forecast,observation)
    with (log.path/'reading-evidence.png').open('xb') as f:f.write(raw)
    log.add('reading_evidence_scope',{'operator_meter_photograph':bool(evidence),'numeric_authentication_by_image':bool(evidence),
        'scope':'Operator-supplied meter photo; no automated value reading.' if evidence else 'Original board context only; value is an operator report, not image authentication.'})
    log.add('operator_reading_reported',{'operator_verbatim':report['operator_verbatim']})
    log.add('reading_observed',observation);log.add('reading_scored',scored)
    save(log.path/'reading-observation.json',observation);save(log.path/'reading-score.json',scored)
    state(log,'awaiting_reveal' if scored['outcome']=='one_explanation_remains' else 'awaiting_reading_decision')
    print(json.dumps(scored))


def reveal(record):
    log,reg=opened(record,['awaiting_reveal'])
    parent=ROOT/'runs/reading-cohort'/reg['parent_run_id']
    assembly=json.loads((parent/'faulted-assembly-local-only.json').read_text())
    original=chain(log.path/'history/original/events.jsonl')
    seal=next(e['payload']['sha256'] for e in original if e['kind']=='specimen_assembly_sealed' and e['payload']['state']=='faulted')
    require(digest(assembly)==seal,'original_assembly_seal_changed')
    log.add('specimen_seal_opened',{'state':'faulted','sealed_sha256':seal,'assembly':assembly,
        'after_reading_score':True,'transmitted_to_diagnosis':False})
    result={'case_id':reg['case_id'],'parent_run_id':reg['parent_run_id'],'original_failed_status_preserved':True,
        'reading_outcome':json.loads((log.path/'reading-score.json').read_text())['outcome'],
        'repair_completed':False,'restored_diagnosis_completed':False,'new_API_calls':0,'new_hardware_commands':0}
    save(log.path/'result.json',result);log.add('run_completed',result)
    print(json.dumps(result))


def verify(record,allow_active=False):
    path=Path(record)
    events=decode_events((path/'events.jsonl').read_bytes(),require_terminal=not allow_active,include_hash=True)
    require(not any(e['kind'] in ('run_completed','run_failed') for e in events[:-1]),'event_after_terminal')
    reg=next(e['payload'] for e in events if e['kind']=='photo_observation_continuation_registered')
    require(json.loads((path/'registration.json').read_text())==reg,'registration_changed')
    for n,h in reg['source_sha256'].items():require(sha(ROOT/n)==h,'source_changed')
    parent=path/'history/original';audit=verify_pair(parent)
    require(audit['passed'] and audit['run_status']=='run_failed' and audit['head_sha256']==reg['parent_head_sha256'],'failed_parent_audit')
    follow=path/'history/body-followup';plan=json.loads((path/'history/body-request-plan.json').read_text())
    proposal,extra=validate_body_record(parent,follow,plan)
    require(chain(follow/'events.jsonl')[-1]['sha256']==reg['body_followup_head_sha256'],'body_followup_head_changed')
    forecast=json.loads((path/'reading-forecast.json').read_text())
    require((path/'reading-forecast.json').read_bytes()==(parent/'reading-forecast.json').read_bytes()
            and digest(forecast)==reg['reading_forecast_sha256'],'inherited_forecast_changed')
    binding=observed=scored=revealed=None
    for e in events:
        k,p=e['kind'],e['payload']
        if k=='retained_reading_evidence_bound':
            for a in p['artifacts']:check_file(path,a)
        elif k=='body_binding':
            require(binding is None and observed is None,'binding_order')
            expected=binding_receipt(proposal,{'accepted':True,'operator_verbatim':p['operator_verbatim']})
            require(p==expected and json.loads((path/'body-binding.json').read_text())==p,'binding_not_Spark_confirmation');binding=p
        elif k=='reading_observed':
            require(binding is not None and observed is None,'reading_before_confirmed_body_or_duplicate')
            check_file(path,p['photo']);observed=p
        elif k=='reading_scored':
            require(observed is not None and scored is None and p==score_reading(forecast,observed),'score_not_frozen_source_specific');scored=p
        elif k=='specimen_seal_opened':
            require(scored is not None and len(scored['fits'])==1 and revealed is None,'seal_before_unique_reading')
            seals=[a['payload']['sha256'] for a in chain(parent/'events.jsonl') if a['kind']=='specimen_assembly_sealed' and a['payload']['state']=='faulted']
            require(seals==[p['sealed_sha256']] and digest(p['assembly'])==p['sealed_sha256'],'seal_not_original');revealed=p
        elif k=='run_completed':
            require(scored is not None and revealed is not None and json.loads((path/'result.json').read_text())==p,'completion_before_reading_and_seal')
            require(p['original_failed_status_preserved'] is True and p['repair_completed'] is False and p['restored_diagnosis_completed'] is False,'overstated_completion')
    return {'passed':True,'events':len(events)+audit['events']+extra,'root_events':len(events),'run_status':events[-1]['kind'],
            'head_sha256':events[-1]['sha256'],'scope':'internal_integrity+recorded_order','creation_time':'unproven'}


def main():
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='command',required=True)
    a=sub.add_parser('begin')
    for k in ('parent','binding','plan','confirmation'):a.add_argument('--'+k,required=True)
    for name in ('observe','reveal','verify'):
        a=sub.add_parser(name);a.add_argument('record')
        if name=='observe':a.add_argument('--report',required=True);a.add_argument('--evidence')
        if name=='verify':a.add_argument('--allow-active',action='store_true')
    a=p.parse_args()
    if a.command=='begin':begin(a.parent,a.binding,a.plan,a.confirmation)
    elif a.command=='observe':observe(a.record,a.report,a.evidence)
    elif a.command=='reveal':reveal(a.record)
    else:print(json.dumps(verify(a.record,a.allow_active)))


if __name__=='__main__':main()
