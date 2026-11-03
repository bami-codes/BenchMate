#!/usr/bin/env python3
"""Keep primary failures fixed; register and run separate follow-up attempts.

The frozen original Session, Bench, prompt, protocol and publisher are reused.
Only registration/accounting can resolve a failed predecessor via a completed
follow-up; it never changes the predecessor or chooses diagnostic experiments.
"""
from datetime import datetime, timezone
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'src'))
from scripts import official_passive as base
from benchmate.instrument import validate_boot_id
from benchmate.netlist_diagnosis.design import checked, digest
from benchmate.records import Recorder, read_events

EXTRA = ('scripts/official_passive_followup.py', 'docs/2026-11-03-official-followup-amendment.md')


def entries(index):
    return index['slots'] + index.get('followups', [])


def resolved(index, slot):
    return slot['status'] == 'completed' or any(
        f.get('followup_of') == slot['slot_id'] and f['status'] == 'completed'
        and f.get('verification_completed') is True for f in index.get('followups', []))


def select_slot(index, slot_id):
    primary = next((s for s in index['slots'] if s['slot_id'] == slot_id), None)
    if primary is not None:
        if primary['run_id'] is not None:
            raise ValueError('Primary slot already assigned; never replace it.')
        if any(not resolved(index, s) for s in index['slots'] if s['order'] < primary['order']):
            raise ValueError('Earlier required slot remains unresolved.')
        return primary
    match = re.fullmatch(r'(\d{2})-([FR])(\d{2})', slot_id)
    if match is None or int(match[3]) < 2:
        raise ValueError('Explicit numbered follow-up slot required.')
    original_id = match[1] + '-' + match[2] + '01'
    original = next(s for s in index['slots'] if s['slot_id'] == original_id)
    family = [s for s in entries(index) if s['slot_id'].startswith(match[1] + '-' + match[2])]
    if original['status'] != 'failed' or any(s['status'] not in ('failed', 'completed') for s in family):
        raise ValueError('A terminal primary failure and no concurrent attempt are required.')
    if int(match[3]) != max(int(s['slot_id'].split('-')[1][1:]) for s in family) + 1:
        raise ValueError('Follow-up attempt number must be contiguous; no silent skipped attempts.')
    followup = {**original, 'slot_id': slot_id, 'run_id': None, 'status': 'not_started',
                'selected_for_case_demo': False, 'counted': False, 'required': False,
                'followup_of': original_id, 'selection': 'followup_never_replaces_primary',
                'attempt_ordinal': int(match[3])}
    for key in ('registration_file', 'protocol_sha256', 'error', 'verdict'):
        followup.pop(key, None)
    index.setdefault('followups', []).append(followup)
    return followup


def full_sources(protocol):
    sources = dict(protocol['official_source_sha256'])
    for name in EXTRA:
        sources[name] = hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
    return sources


def check_sources(bound):
    for name, sha in bound['source_sha256'].items():
        if hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != sha:
            raise ValueError('Registered follow-up source changed: ' + name)


def update_index(run_id, **changes):
    index = json.loads((ROOT / base.INDEX).read_text())
    next(s for s in entries(index) if s['run_id'] == run_id).update(changes)
    base.save(ROOT / base.INDEX, index)


def register(args):
    design, protocol = base.load_prepared(args.prepared)
    initial = json.loads(Path(args.initial_report).read_text())
    assembly = json.loads(Path(args.assembly_record).read_text())
    base.validate_assembly(design, initial, assembly)
    policy = json.loads((ROOT / base.POLICY_FILE).read_text())
    index = base.index_for(policy)
    slot = select_slot(index, args.slot)
    case = next(c for c in policy['cases'] if c['case_id'] == slot['case_id'])
    if digest(design) != case['reviewed_design_sha256']:
        raise ValueError('Same reviewed intended design required.')
    recovery = None
    if 'followup_of' in slot:
        if args.QA_result is None:
            raise ValueError('Successful separate recovery QA required before a follow-up.')
        qa_file = Path(args.QA_result)
        qa = json.loads(qa_file.read_text())
        qa_plan = json.loads((qa_file.parent / 'plan.json').read_text())
        if (qa.get('passed') is not True or qa.get('SPARK_requests') != 0
                or qa.get('blocks') != 12 or digest(qa_plan['protocol']) != digest(protocol)):
            raise ValueError('Matching completed 12-HOLD recovery QA required.')
        recovery = {'result_file': str(qa_file), 'result_sha256': hashlib.sha256(qa_file.read_bytes()).hexdigest(),
                    'scope': qa['scope'], 'OUT_used_as_diagnostic_training': False}
    preflight_events = read_events(args.preflight_run)
    preflight = preflight_events[-1]['payload']
    previous = validate_boot_id(args.previous_boot_id)
    if (preflight_events[-1]['kind'] != 'run_completed' or preflight.get('armed') is not False
            or preflight.get('commands') != ['PING'] or preflight.get('stimuli') != 0
            or validate_boot_id(preflight['boot_id']) == previous):
        raise ValueError('New unarmed PING preflight after confirmed USB-off setup required.')
    log = Recorder(args.output, mode='spark_physical_official_passive_followup_or_restored')
    public = Path('examples/official-runs/2026-11-03/registrations') / (log.path.name + '.json')
    bound = {'schema': 'benchmate.official_run_binding.v1', 'run_id': log.path.name,
             'slot_id': slot['slot_id'], 'case_id': slot['case_id'], 'state': slot['state'],
             'cohort_plan_id': policy['cohort_plan_id'], 'official': True, 'counted': True,
             'pilot': False, 'excluded_from_evaluation': False, 'source': 'physical', 'actor': 'muse_spark',
             'selected_for_case_demo': slot['selected_for_case_demo'], 'followup_of': slot.get('followup_of'),
             'attempt_ordinal': slot.get('attempt_ordinal', 1),
             'orchestration_version': 'official-passive-followup-v2',
             'selection_policy_sha256': digest(policy), 'reviewed_design_sha256': digest(design),
             'protocol_sha256': digest(protocol), 'source_sha256': full_sources(protocol),
             'source_commit': base.git('rev-parse', 'HEAD'), 'assigned_utc': datetime.now(timezone.utc).isoformat(),
             'first_paid_request_already_sent': False, 'first_stimulus_already_sent': False,
             'run_started_event_sha256': log.previous, 'public_registration': str(public),
             'recovery_QA': recovery}
    for name, value in {'official-registration': bound, 'protocol': protocol, 'reviewed-design': design,
                        'initial-operator-report': initial, 'operator-assembly-local-only': assembly,
                        'preflight': {'record': str(args.preflight_run), 'previous_boot_id': previous,
                                      'observed_unarmed_boot_id': preflight['boot_id']}}.items():
        base.save(log.path / (name + '.json'), value)
    for name in bound['source_sha256']:
        target = log.path / 'source' / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((ROOT / name).read_bytes())
    log.add('official_run_bound', bound)
    log.add('operator_assembly_record_local_only', {'sha256': digest(assembly), 'transmitted_to_model': False})
    log.add('official_protocol_frozen', {'protocol_sha256': digest(protocol), 'source_sha256': bound['source_sha256'],
                                      'official': True, 'pilot': False, 'excluded_from_evaluation': False})
    base.save(ROOT / public, bound)
    slot.update(run_id=log.path.name, status='registered', counted=True,
                registration_file=str(public), protocol_sha256=digest(protocol))
    base.save(ROOT / base.INDEX, index)
    print(json.dumps({'record': str(log.path), 'slot': args.slot, 'registration': str(public),
                      'paid_calls': 0, 'hardware_commands': 0}), flush=True)


def run(args):
    if not args.execute:
        raise ValueError('Explicit authorized --execute required.')
    record = Path(args.record)
    bound = base.registration(record)
    check_sources(bound)
    design = checked(json.loads((record / 'reviewed-design.json').read_text()))
    protocol = json.loads((record / 'protocol.json').read_text())
    initial = json.loads((record / 'initial-operator-report.json').read_text())
    base.validate_assembly(design, initial, json.loads((record / 'operator-assembly-local-only.json').read_text()))
    if protocol != base.prepare(design) or digest(protocol) != bound['protocol_sha256']:
        raise ValueError('Frozen protocol mismatch.')
    if (json.loads(base.git('show', 'HEAD:' + bound['public_registration'])) != bound
            or base.git('ls-remote', 'origin', 'refs/heads/main').split()[0] != base.git('rev-parse', 'HEAD')):
        raise ValueError('Registration must be committed and pushed before execution.')
    index = json.loads((ROOT / base.INDEX).read_text())
    if not any(s['run_id'] == bound['run_id'] and s['status'] == 'registered' for s in entries(index)):
        raise ValueError('Attempt is not registered or has already executed.')
    log = base.reopen(record)
    with (record / 'execution-started.json').open('x') as file:
        json.dump({'attempt_started': True, 'registration': bound['public_registration']}, file)
    update_index(bound['run_id'], status='running')
    bench = model = None
    try:
        ports = [p for p in base.list_ports.comports()
                 if (p.vid, p.pid, p.serial_number) == tuple(protocol['USB_identity'])]
        if len(ports) != 1:
            raise ValueError('Expected Minima absent or ambiguous; no paid request or serial opened.')
        preflight = json.loads((record / 'preflight.json').read_text())
        bench = base.Bench(protocol, log, lambda f: base.intervention(log, design, f), design=design,
            initial_report=initial, approved=True, previous_boot_id=preflight['previous_boot_id'],
            preflight_boot_id=preflight['observed_unarmed_boot_id'])
        def publish(frozen, sha):
            check_sources(bound)
            return base.publish(log, bound, protocol, frozen, sha)
        session = base.Session(bench, log, design, publish)
        model = base.OfficialModel(prompt=base.PROMPT, tools=session.tools, log=log, effort='medium',
                                  env_path=ROOT / '.env', budget_path=base.BUDGET, max_requests=8)
        print(json.dumps({'stage': 'started', 'record': str(record), 'slot_id': bound['slot_id']}), flush=True)
        result = model.sanitize({**base.drive_agent(session, model), **model.metadata(), 'official_run': bound})
        base.save(record / 'result.json', result)
        log.add('run_completed', result)
        verified = bool(result.get('verification') and result['verification']['survivors'])
        update_index(bound['run_id'], status='completed', verdict=result['agent_report']['verdict'],
                     verification_completed=verified)
        print(json.dumps({'stage': 'completed', 'record': str(record), 'report': result['agent_report'],
                          'http_requests': result['http_requests']}), flush=True)
    except (Exception, KeyboardInterrupt) as exc:
        result = {'error': str(exc) if isinstance(exc, (ValueError, RuntimeError)) else type(exc).__name__,
                  'instrument': bench.metadata() if bench else {}, 'automatic_retry': False,
                  'official_run': bound, **(model.metadata() if model else {})}
        if model:
            result = model.sanitize(result)
        base.save(record / 'result.json', result)
        log.add('run_failed', result)
        update_index(bound['run_id'], status='failed', error=result['error'])
        print(json.dumps({'stage': 'failed', 'record': str(record), 'error': result['error'],
                          'http_requests': result.get('http_requests', 0)}), flush=True)
        raise SystemExit(1)
    finally:
        if model:
            model.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    p = sub.add_parser('register')
    for name in ('prepared', 'slot', 'initial-report', 'assembly-record', 'previous-boot-id', 'preflight-run'):
        p.add_argument('--' + name, required=True)
    p.add_argument('--QA-result')
    p.add_argument('--output', default=str(ROOT / 'runs/official'))
    p = sub.add_parser('run')
    p.add_argument('--record', required=True)
    p.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    (register if args.command == 'register' else run)(args)


if __name__ == '__main__':
    main()
