"""Additive candidate-set photo/readout stage for v4 reading pairs."""
import argparse
import json
from pathlib import Path
import re
import sys

from .records import decode_events
from .reading_candidates_v3 import parse
from .reading_rules import score_reading

ROOT=Path(__file__).resolve().parents[2]
SOURCES=('src/benchmate/reading_photo_stage_v4.py','src/benchmate/reading_timing_verify_v4.py',
         'tests/test_reading_photo_stage_v4.py','docs/2026-11-04-reading-photo-stage-v4.md')
ACTIVE=False


def runtime():
    sys.path.insert(0,str(ROOT))
    from scripts import reading_experiment_timing_v4
    return reading_experiment_timing_v4


def validate_ports(value):
    if (set(value)!={'schema','operator_confirmed','source','ports','component_values_or_reference_assignments_included'}
            or value['schema']!='benchmate.operator_photo_ports.v1' or value['operator_confirmed'] is not True
            or value['component_values_or_reference_assignments_included'] is not False
            or set(value['ports'])!={'IN','OUT','REF'}):
        raise ValueError('Only operator-confirmed connector ports, without component identities/values.')
    for port in value['ports'].values():
        if (set(port)!={'wire_color','mini_contact'} or not re.fullmatch('[a-z]{2,16}',port['wire_color'])
                or not re.fullmatch('[A-E](?:[1-9]|1[0-7])',port['mini_contact'])):
            raise ValueError('Simple wire color and mini-board contact required.')
    return value['ports']


def qualify(record):
    r=runtime();log=r.open_pair(record,['awaiting_reading_selection','awaiting_faulted_photo'])
    if (log.path/'photo-candidate-scope.json').exists() or (log.path/'photo-faulted').exists():
        raise ValueError('Qualify exactly once before photo receipt.')
    scope={'schema':'benchmate.reading_photo_candidate_stage.v4','source_sha256':{n:r.sha(ROOT/n) for n in SOURCES},
        'candidate_version':'candidate-kind-set-v3','surface_value_reading':False,
        'operator_port_context':'Only explicitly confirmed connector colors and coordinates, never part values/identities.',
        'unique_binding':'Actual Spark reference proposal confirmed yes/no; ambiguous candidates require a separate group plan.',
        'operator_numeric_evidence':'Optional meter photo; otherwise original board context explicitly not numeric authentication.',
        'restored_consistent':'New photo and generic SAM display only; no invented component reference or repeated value request.',
        'public_manifest':str(r.PUBLIC/'photo-v4-scopes'/log.path.name/'scope.json')}
    r.save(log.path/'photo-candidate-scope.json',scope);r.save(ROOT/scope['public_manifest'],scope)
    for n in SOURCES:
        p=log.path/'photo-stage-source'/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((ROOT/n).read_bytes())
    log.add('photo_candidate_stage_qualified',{'file':'photo-candidate-scope.json','sha256':r.sha(log.path/'photo-candidate-scope.json'),
        'public_manifest':scope['public_manifest'],'before_photo':True,'before_operator_reading':True})
    print(json.dumps({'public_scope':scope['public_manifest'],'paid_requests':0,'hardware_commands':0}))


def opened(record,phases):
    r=runtime();log=r.open_pair(record,phases);scope=json.loads((log.path/'photo-candidate-scope.json').read_text())
    for n,h in scope['source_sha256'].items():
        if r.sha(ROOT/n)!=h:raise ValueError('Frozen photo-stage source changed: '+n)
    return r,log,scope


def bind(record,execute):
    global ACTIVE
    r,log,scope=opened(record,['awaiting_faulted_binding'])
    r.committed(ROOT/scope['public_manifest']);r.start_stage(log,'faulted-candidates-v3',execute);ACTIVE=True
    from .reading_candidates_v3 import request
    from .reading_transport import call
    content,tool,ids,inventory=request(log.path,log.control['requested_component'])
    ports_file=log.path/'operator-photo-ports.json';ports_sha=None
    if ports_file.exists():
        ports=validate_ports(json.loads(ports_file.read_text()));ports_sha=r.sha(ports_file)
        content[0]['text']+='\nOperator-confirmed connector ports only (not component references or values):\n'+json.dumps(ports)
    log.add('candidate_request_inputs_frozen',{'inputs':inventory,'tool':tool,'operator_ports_sha256':ports_sha,
        'operator_values_supplied':False})
    child,result=call(content,tool=tool,output=log.path/'photo-faulted/candidates-v3',budget=r.BUDGET)
    r.linked(log,child,'body_candidates_v3')
    proposal={'state':'faulted','component':log.control['requested_component'],'chosen_by':'muse_spark',
        'operator_confirmed':False,'surface_values_read':False,**parse(result['arguments'],ids)}
    r.save(log.path/'photo-faulted/candidate-proposal.json',proposal);log.add('body_candidates_proposed',proposal)
    r.state(log,'awaiting_faulted_candidate_confirmation' if proposal['mapping_status']=='unique' else 'awaiting_candidate_group_decision')
    print(json.dumps(proposal))


def confirm(record,report_file):
    r,log,_=opened(record,['awaiting_faulted_candidate_confirmation'])
    report=json.loads(Path(report_file).read_text());proposal=json.loads((log.path/'photo-faulted/candidate-proposal.json').read_text())
    if set(report)!={'accepted','operator_verbatim'} or report.get('accepted') is not True or not isinstance(report.get('operator_verbatim'),str) or not report['operator_verbatim'].strip():
        raise ValueError('Confirm actual Spark proposal; rejection/group decisions must remain explicit.')
    if proposal['mapping_status']!='unique' or proposal['sam_body'] is None:
        raise ValueError('Do not force an ambiguous candidate group into an operator truth label.')
    manifest=json.loads((log.path/'photo-faulted/decoded/body-manifest.json').read_text())
    body=next(c for c in manifest['components'] if c['id']==proposal['sam_body'])
    binding={**proposal,'operator_confirmed':True,'operator_verbatim':report['operator_verbatim'],
        'binding_version':'candidate-kind-set-v3','localizer':body['localizer']}
    r.save(log.path/'photo-faulted/body-binding.json',binding);log.add('body_binding',binding)
    r.state(log,'awaiting_reading_observation')


def observe(record,report_file,evidence=None):
    r,log,_=opened(record,['awaiting_reading_observation'])
    report=json.loads(Path(report_file).read_text())
    from .known_design import sanitize_image
    raw,_=sanitize_image(Path(evidence).read_bytes()) if evidence else ((log.path/'photo-faulted/prepared/input.png').read_bytes(),None)
    import hashlib
    observed={**report,'photo':{'file':'reading-evidence.png','sha256':hashlib.sha256(raw).hexdigest()}}
    forecast=json.loads((log.path/'reading-forecast.json').read_text());scored=score_reading(forecast,observed)
    with (log.path/'reading-evidence.png').open('xb') as f:f.write(raw)
    log.add('reading_evidence_scope',{'operator_meter_photograph':bool(evidence),
        'scope':'Meter photograph supplied by operator' if evidence else 'Original board context only; numeric value is operator report, not image authentication.'})
    log.add('reading_observed',observed);log.add('reading_scored',scored)
    r.save(log.path/'reading-observation.json',observed);r.save(log.path/'reading-score.json',scored)
    r.state(log,'awaiting_reveal' if scored['outcome']=='one_explanation_remains' else 'awaiting_reading_decision',reading_outcome=scored['outcome'])
    print(json.dumps(scored))


def restored_scope(record):
    r,log,_=opened(record,['awaiting_restored_photo'])
    if log.control['restored_verdict']!='consistent' or (log.path/'photo-restored').exists():
        raise ValueError('Declare omission only for consistent restored diagnosis, before photo receipt.')
    p=log.path/'restored-photo-scope.json'
    if p.exists():raise ValueError('Restored scope already declared.')
    value={'reason':'consistent_no_implicated_component','SAM_role':'documentary_display_only',
        'Spark_binding_requests':0,'operator_value_requests':0,'new_photo_required':True,'component_identity_claimed':False}
    r.save(p,value);log.add('restored_photo_scope_declared',{'file':p.name,'sha256':r.sha(p),**value})


def finish(record):
    r,log,_=opened(record,['awaiting_restored_binding'])
    scope=json.loads((log.path/'restored-photo-scope.json').read_text())
    if log.control['restored_verdict']!='consistent' or scope['component_identity_claimed'] is not False:
        raise ValueError('Documentary-only finish requires a consistent rerun and declared omission.')
    fault=log.path/'photo-faulted/prepared/input.png';restored=log.path/'photo-restored/prepared/input.png'
    if r.sha(fault)==r.sha(restored):raise ValueError('Changed mini-board repair needs a new restored capture, not reused pixels.')
    log.add('restored_documentary_completed',{'manifest':'photo-restored/decoded/body-manifest.json',
        'sha256':r.sha(log.path/'photo-restored/decoded/body-manifest.json'),'SAM_role':'documentary_display_only',
        'Spark_binding_requests':0,'operator_value_requests':0,'component_identity_claimed':False})
    r.state(log,'awaiting_pair_completion')
    r.finish(argparse.Namespace(record=record))


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('action',choices=['qualify','bind','confirm','observe','restored-scope','finish'])
    p.add_argument('record');p.add_argument('--report');p.add_argument('--evidence');p.add_argument('--execute',action='store_true');a=p.parse_args()
    try:
        if a.action=='qualify':qualify(a.record)
        elif a.action=='bind':bind(a.record,a.execute)
        elif a.action=='confirm':confirm(a.record,a.report)
        elif a.action=='observe':observe(a.record,a.report,a.evidence)
        elif a.action=='restored-scope':restored_scope(a.record)
        else:finish(a.record)
    except (Exception,KeyboardInterrupt) as exc:
        if ACTIVE:
            r=runtime();phase=json.loads((Path(a.record)/'state.json').read_text())['phase'];log=r.open_pair(a.record,[phase])
            linked={e['payload']['file'] for e in decode_events(log.file.read_bytes(),require_terminal=False) if e['kind']=='child_record_bound'}
            for f in Path(a.record).resolve().rglob('events.jsonl'):
                if f!=log.file and str(f.relative_to(Path(a.record).resolve())) not in linked:
                    try:r.linked(log,f.parent,'failed_stage_retained')
                    except ValueError:pass
            log.add('run_failed',{'stage':a.action,'error':str(exc) if isinstance(exc,(ValueError,RuntimeError)) else type(exc).__name__,'automatic_retry':False})
            r.update_index(log.path.name,status='failed',failed_stage=a.action)
        raise


if __name__=='__main__':main()
