"""Prospective case05 setup; keeps the frozen numerical experiment untouched."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]


def runtime():
    sys.path.insert(0, str(ROOT))
    from scripts import reading_experiment
    return reading_experiment


def declare(record):
    r = runtime()
    log = r.open_pair(record, ['awaiting_schematic_intake'])
    events = r.decode_events(log.file.read_bytes(), require_terminal=False)
    if log.control['case_id'] != '05' or any(e['kind'] in ('child_record_bound', 'case05_workflow_scope_frozen') for e in events):
        raise ValueError('Declare once, before case05 image intake or measurements.')
    names = ['src/benchmate/reading_case05_setup.py', 'src/benchmate/reading_candidates_v3.py',
             'docs/2026-11-04-reading-case05-start.md']
    scope = {'schema': 'benchmate.case05_workflow_scope.v1',
        'before_schematic_intake': True, 'before_physical_stimulus': True,
        'original_107_frozen_sources_unchanged': True,
        'source_sha256': {n: r.sha(ROOT / n) for n in names},
        'schematic_wire_adapter': 'Operator confirms the visible IN-OUT direct connection as W1; never attributed to the R/C image reader.',
        'physical': 'Same raw A3 3mV guard, auxiliary A4, 1k instrument path, 9mV whole/region scores, >=10s after new unarmed boot.',
        'followup_observable': 'Only if a useful ambiguity remains: Spark chooses the component and quantity; isolated W1 path resistance needs a separately published numeric observable/profile before any operator reading.',
        'wire_qualification_pending': True,
        'photo': 'One generic SAM call and the v3 candidate-kind/set plus nullable individual-binding contract; no surface-value reader.',
        'stage_extensions': 'Any new catalog, reading or compound-audit adapter is versioned and committed before its corresponding paid/observation stage, never silently edits the frozen runtime.',
        'restored_photo': 'No duplicate mini-board photo for operator-confirmed unchanged mini configuration and external-only repair; retain the original capture label.',
        'calls_planned_max': {'Spark': 19, 'SAM': 1}, 'no_automatic_retry_after_failure': True}
    r.save(log.path / 'case05-workflow-scope.json', scope)
    public = r.PUBLIC / 'case05-scopes' / log.path.name / 'scope.json'
    r.save(ROOT / public, scope)
    log.add('case05_workflow_scope_frozen', {'file': 'case05-workflow-scope.json',
        'sha256': r.sha(log.path / 'case05-workflow-scope.json'), 'public_manifest': str(public),
        'before_schematic_intake': True, 'before_physical_stimulus': True})
    print(json.dumps({'record': str(log.path), 'public_scope': str(public), 'paid_calls': 0, 'hardware': 0}))


def confirm(record, note):
    r = runtime()
    log = r.open_pair(record, ['awaiting_design_confirmation'])
    scope = json.loads((log.path / 'case05-workflow-scope.json').read_text())
    for n, h in scope['source_sha256'].items():
        if r.sha(ROOT / n) != h:
            raise ValueError('Setup source changed.')
    result = json.loads((log.path / 'schematic-result.json').read_text())
    candidate = result['candidate']
    if candidate['status'] != 'needs_review' or len(candidate['components']) != 2:
        raise ValueError('Explicitly review the two intended branches before confirming W1.')
    elements = []
    for c in candidate['components']:
        if c['kind'] not in ('R', 'C') or c['value_si'] is None or set(c['nodes']) != {'OUT', 'REF'}:
            raise ValueError('Both read branches must be OUT-REF before the visible wire adapter is applied.')
        elements.append(dict(name=c['name'], kind=c['kind'], a=c['nodes'][0], b=c['nodes'][1], value=c['value_si'], model='none'))
    elements.append(dict(name='W1', kind='W', a='IN', b='OUT', value=0., model='none'))
    from .netlist_diagnosis.design import review, CONFIRMATION
    design = review(elements, source_sha256=r.sha(log.path / 'schematic.png'), confirmation=CONFIRMATION,
                    note=note + ' Visible direct IN-OUT wire W1 added by operator confirmation, not Spark component transcription.')
    r.save(log.path / 'reviewed-design.json', design)
    log.add('intended_design_operator_confirmed', {'reviewed_design': design, 'confirmed_by': 'operator',
        'operator_added_wire': 'W1 IN-OUT', 'original_image_ambiguities': candidate['ambiguities']})
    r.state(log, 'awaiting_faulted_setup')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('action', choices=['declare', 'confirm'])
    p.add_argument('record')
    p.add_argument('--operator-note')
    args = p.parse_args()
    if args.action == 'declare':
        declare(args.record)
    elif not args.operator_note:
        raise ValueError('Actual operator design confirmation required.')
    else:
        confirm(args.record, args.operator_note)


if __name__ == '__main__':
    main()
