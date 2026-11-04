#!/usr/bin/env python3
"""Offline, bidirectional, fixed-action sensitivity audit; never edits old runs."""
import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT/'src')]
from benchmate import channel_timing_v3 as new
from benchmate.netlist_diagnosis.models import score
from benchmate.records import decode_events


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def brief(check):
    return {k: check[k] for k in ('passed', 'RMS_mV', 'regions')}


def inventory():
    index = json.loads((ROOT/'examples/reading-cohort/2026-11-03/index.json').read_text())
    folders = list((ROOT/'runs').glob('*/*'))
    records, empty, seen = [], [], set()
    for item in index['attempts']:
        if item['case_id'] not in ('01', '04', '02', '05'):
            continue
        matches = [p for p in folders if p.is_dir() and p.name == item['run_id']]
        if len(matches) != 1:
            raise ValueError('Expected one original local attempt: '+item['run_id'])
        found = False
        for path in sorted(matches[0].rglob('events.jsonl')):
            if 'history' in path.parts or 'documentary-core' in path.parts:
                continue
            events = decode_events(path.read_bytes(), require_terminal=False)
            diagnostic = any(e['kind'] == 'netlist_observation' for e in events) or 'diagnosis-' in str(path)
            if not diagnostic:
                continue
            h = sha(path)
            if h in seen:
                continue
            seen.add(h); found = True
            records.append((item, path, events))
        if not found:
            empty.append({'case': item['case_id'], 'attempt': item['attempt'], 'run': item['run_id'],
                          'original_status': item['status'], 'scope': 'No diagnostic capture: intake or host-link failure unchanged.'})
    # Preserve the distinction between this reading-assisted cohort and the
    # earlier protocol now labelled development. Include every assigned original
    # official slot as a separate appendix, rather than silently omit it.
    legacy = json.loads((ROOT/'examples/official-runs/2026-11-03/index.json').read_text())
    for item in legacy['slots'] + legacy.get('followups', []):
        if not item.get('run_id') or item['case_id'] not in ('01', '04', '02', '05'):
            continue
        path = ROOT/'runs/official'/item['run_id']/'events.jsonl'
        events = decode_events(path.read_bytes(), require_terminal=False)
        h = sha(path)
        if h in seen:
            continue
        seen.add(h)
        records.append(({**item, 'attempt': item['slot_id'],
                         'reporting_group': 'prior_official_protocol_now_development'}, path, events))
    return records, empty


def inspect(item, path, events):
    captures = [e['payload'] for e in events if e['kind'] == 'netlist_observation']
    training = [c for c in captures if c['purpose'] == 'training']
    verification = [c for c in captures if c['purpose'] == 'verification']
    design_event = next((e for e in events if e['kind'] in ('netlist_protocol', 'netlist_v2_protocol')), None)
    native = next((e['payload'] for e in reversed(events) if e['kind'] == 'agent_report'), None)
    result = {'case': item['case_id'], 'attempt': item['attempt'], 'file': str(path.relative_to(ROOT)),
              'reporting_group': item.get('reporting_group', 'reading-assisted-v1'),
              'event_sha256': sha(path), 'original_terminal': events[-1]['kind'],
              'original_report': native, 'training_captures': len(training),
              'verification_captures': len(verification), 'official_result_changed': False,
              'fixed_parameter_checks': [], 'refitted_training': [], 'check_flips': []}
    if not training:
        result['counterfactual_scope'] = 'No complete guarded diagnostic capture; original failure remains.'
        return result
    if design_event is None:
        raise ValueError('Missing reviewed design in '+str(path))
    design = design_event['payload']['reviewed_design']['elements']
    final = next(e['payload'] for e in reversed(events) if e['kind'] == 'component_hypotheses_fitted')
    original_rows = final['hypotheses'] + [e['payload'] for e in events if e['kind'] == 'structure_fit']
    reserved = [e['payload'] for e in events if e['kind'] == 'reserved_prediction_scored']
    # Sensitivity of the exact original frozen/fitted parameters: no refit.
    for row in original_rows:
        if 'model' not in row:
            result['fixed_parameter_checks'].append({'id': row['id'], 'unavailable': row.get('error', 'no original model')})
            continue
        checks = []
        for i, c in enumerate(captures):
            old = row['training_checks'][i] if i < len(training) else reserved[i-len(training)]['conditional'].get(row['id'])
            if old is None:
                continue
            entry = {'purpose': c['purpose'], 'capture': i+1, 'settings': c['settings'], 'old': brief(old)}
            try:
                entry['new'] = brief(score(c, new.predict(row['model'], c['input_template'])))
                if old['passed'] != entry['new']['passed']:
                    result['check_flips'].append({'mode': 'original_parameters', 'id': row['id'],
                        'capture': i+1, 'purpose': c['purpose'], 'old_pass': old['passed'], 'new_pass': entry['new']['passed']})
            except (ValueError, RuntimeError) as exc:
                entry['new_error'] = str(exc)
                result['check_flips'].append({'mode': 'original_parameters', 'id': row['id'],
                    'capture': i+1, 'purpose': c['purpose'], 'old_pass': old['passed'], 'new_error': str(exc)})
            checks.append(entry)
        result['fixed_parameter_checks'].append({'id': row['id'], 'checks': checks})
    # Refit only existing component/topology parameters to TRAINING, never
    # timing parameters or held-back OUT. Agent choices are held fixed.
    assessment = new.assess(design, training, max_seconds=120.)
    rows = assessment['hypotheses']
    original_names = {e['name'] for e in design if e['kind'] != 'W'}
    for event in events:
        if event['kind'] != 'structure_proposed':
            continue
        proposed = event['payload']; elements = proposed['elements']
        added = [e['name'] for e in elements if e['name'] not in original_names and e['kind'] in ('R', 'C')]
        fitter = new.Fitter(max_calls=420, max_seconds=90.)
        try:
            row = fitter.fit(elements, training, hypothesis_id=proposed['id'], fit_names=added,
                             fit_diode=any(e['kind'] == 'D' for e in elements))
        except (ValueError, RuntimeError) as exc:
            row = {'id': proposed['id'], 'status': 'fit_error', 'error': str(exc)}
        rows.append(row)
    original_by_id = {r['id']: r for r in original_rows}
    for row in rows:
        old = original_by_id[row['id']]
        entry = deepcopy(row)
        entry['original_status'] = old['status']
        if row['status'] != old['status']:
            result['check_flips'].append({'mode': 'training_refit', 'id': row['id'],
                'old_status': old['status'], 'new_status': row['status']})
        entry['verification_checks'] = []
        if row['status'] == 'adequate':
            for c in verification:
                try:
                    entry['verification_checks'].append(brief(score(c, new.predict(row['model'], c['input_template']))))
                except (ValueError, RuntimeError) as exc:
                    entry['verification_checks'].append({'passed': False, 'evaluation_error': str(exc)})
        result['refitted_training'].append(entry)
    survivors = [r['id'] for r in result['refitted_training'] if r['status'] == 'adequate'
                 and len(r['verification_checks']) == 2 and all(c['passed'] for c in r['verification_checks'])]
    result['new_training_adequate'] = [r['id'] for r in rows if r['status'] == 'adequate']
    result['new_evaluation_errors'] = [r['id'] for r in rows if r['status'] == 'fit_error']
    if events[-1]['kind'] == 'run_failed':
        result['counterfactual_scope'] = 'Original guard/transport failure remains; available captured data are sensitivity checks only.'
        result['new_fixed_action_outcome'] = 'original_execution_failure'
    elif result['new_evaluation_errors']:
        result['counterfactual_scope'] = 'Numerical errors cannot establish hypothesis inadequacy or a new verdict.'
        result['new_fixed_action_outcome'] = 'numerical_error_not_a_verdict'
    elif len(verification) != 2:
        result['counterfactual_scope'] = 'No held-back pair exists; training changes cannot establish a diagnosis.'
        result['new_fixed_action_outcome'] = 'unverified_training_only'
    else:
        changed = sorted(x.split(':', 1)[1] for x in survivors if x.startswith('changed:'))
        verdict = 'consistent' if 'nominal' in survivors else (
            ('changed' if len(changed) == 1 else 'indistinguishable') if changed else
            ('structure_supported' if survivors else 'abstained'))
        result['new_fixed_action_outcome'] = verdict
        result['new_reserved_survivors'] = survivors
        result['counterfactual_scope'] = 'Post-hoc same-action numerical replay, not a new Spark decision or official verdict.'
        if native and native['verdict'] != verdict:
            result['check_flips'].append({'mode': 'posthoc_fixed_action_outcome', 'old': native['verdict'], 'new': verdict})
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', required=True)
    p.add_argument('--corpus', help='Committed JSON input manifest for a network/key-free replay from public logs.')
    args = p.parse_args()
    output = Path(args.output); output.mkdir(parents=True, exist_ok=False)
    if args.corpus:
        corpus = json.loads(Path(args.corpus).read_text())
        records, empty = [], corpus['unstarted_diagnostics']
        for row in corpus['records']:
            path = ROOT/row['public_file']
            if sha(path) != row['sha256']:
                raise ValueError('Committed input record changed: '+row['public_file'])
            records.append((row['item'], path, decode_events(path.read_bytes(), require_terminal=False)))
    else:
        records, empty = inventory()
    manifest = json.loads((ROOT/'examples/reading-cohort/2026-11-03/freeze/manifest.json').read_text())
    frozen = {n: sha(ROOT/n) for n in manifest['source_sha256']}
    if frozen != manifest['source_sha256']:
        raise ValueError('Original107-source freeze changed before regression.')
    started = time.monotonic()
    report = {'schema': 'benchmate.channel_timing_regression.v3',
              'scope': 'Every indexed reading-assisted-v1 case01/04/02/05 attempt, including failures and restored followups; archival mirrors deduplicated. Every assigned original official-protocol run is included separately as prior development.',
              'original_index_sha256': sha(ROOT/'examples/reading-cohort/2026-11-03/index.json'),
              'corpus_manifest_sha256': sha(Path(args.corpus)) if args.corpus else None,
              'API_requests': 0, 'hardware_commands': 0, 'new_timing_parameters': [],
              'allowance_mV': 9., 'official_results_changed': False,
              'unstarted_diagnostics': empty, 'records': []}
    for item, path, events in records:
        value = inspect(item, path, events)
        report['records'].append(value)
        print(json.dumps({'case': value['case'], 'attempt': value['attempt'], 'file': value['file'],
                          'old': None if value['original_report'] is None else value['original_report']['verdict'],
                          'new': value.get('new_fixed_action_outcome'), 'flips': len(value['check_flips'])}), flush=True)
    report['original_sources_unchanged'] = frozen == {n: sha(ROOT/n) for n in frozen}
    report['original_event_files_unchanged'] = all(sha(ROOT/r['file']) == r['event_sha256'] for r in report['records'])
    report['elapsed_s'] = time.monotonic()-started
    report['flip_count'] = sum(len(r['check_flips']) for r in report['records'])
    report['frozen_source_sha256'] = frozen
    (output/'regression.json').write_text(json.dumps(report, indent=2, allow_nan=False)+'\n')
    print(json.dumps({'records': len(records), 'unstarted': len(empty), 'flips': report['flip_count'], 'elapsed_s': report['elapsed_s']}))


if __name__ == '__main__':
    main()
