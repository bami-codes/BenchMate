#!/usr/bin/env python3
"""A3-primary official passive runtime; retained first failures, fresh model context.

Copies only orchestration from the frozen follow-up runner. The new guard mixin
changes trusted channels; numerical fitting, menu, scoring and tools are reused.
"""
from datetime import datetime, timezone
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'src'))
from scripts import official_passive as base
from benchmate.instrument import validate_boot_id
from benchmate.a3_ref_guard import A3GuardMixin, VERSION
from benchmate.netlist_diagnosis.design import checked, digest
from benchmate.records import Recorder, read_events

EXTRA = ('scripts/official_passive_A3.py', 'src/benchmate/a3_ref_guard.py',
         'docs/2026-11-03-A3-REF-amendment.md', 'docs/2026-11-03-A3-official-protocol.md')
PROMPT = base.PROMPT + '\nPrimary REF protection uses A3 at the fixed 3 mV raw block-mean span limit. A4 is auxiliary recorded evidence, never a predictor or stopping channel. No k/offset correction is fitted.\n'
QUALIFICATION = Path('examples/A3-reference-QA/2026-11-03/session01/result.json')


def qualification():
    file = ROOT / QUALIFICATION
    result = json.loads(file.read_text())
    logs = list((file.parent / 'stages').glob('*/events.jsonl'))
    if len(logs) != 1:
        raise ValueError('One complete prospective A3 qualification log required.')
    events = read_events(logs[0])
    guards = [e['payload'] for e in events if e['kind'] == 'physical_electrical_guard']
    waves = [e['payload'] for e in events if e['kind'] == 'physical_waveform_check']
    if (result.get('passed') is not True or result.get('guard_version') != VERSION
            or result.get('frames') != 8704 or events[-1]['kind'] != 'run_completed'
            or events[-1]['payload'] != result or len(guards) != 17 or len(waves) != 7
            or not all(g.get('primary_REF_channel') == 'A3' and all(g['checks'].values()) for g in guards)
            or not all(all(w['checks'].values()) for w in waves)):
        raise ValueError('Completed primary A3 waveform qualification required.')
    plan = json.loads((file.parent / 'plan.json').read_text())
    if plan['sources']['src/benchmate/a3_ref_guard.py'] != hashlib.sha256((ROOT / 'src/benchmate/a3_ref_guard.py').read_bytes()).hexdigest():
        raise ValueError('Qualified A3 guard source changed.')
    return file, result, hashlib.sha256(logs[0].read_bytes()).hexdigest()


def prepare(design):
    p = base.prepare(design)
    qfile, q, event_sha = qualification()
    p.update(official_runtime_version='official-passive-A3-v1', guard_version=VERSION,
             primary_REF_channel='A3', A4_role='record_and_report_only',
             primary_guard_channels=['A1', 'A2', 'A3'],
             reference_guard='A3 raw REF block-mean span <=3 mV; unchanged limits for trusted channels; A4 auxiliary',
             primary_REF_qualification={'file': str(QUALIFICATION), 'sha256': hashlib.sha256(qfile.read_bytes()).hexdigest(),
                                        'events_sha256': event_sha, 'scope': q['scope']})
    p['guard_limits']['REF_envelope_v'] = p['guard_limits']['A4_envelope_v']
    p['official_source_sha256'] = full_sources(p)
    p['api_plan']['prompt'] = PROMPT
    return p


def load_prepared(directory):
    directory = Path(directory)
    design = checked(json.loads((directory / 'reviewed-design.json').read_text()))
    protocol = json.loads((directory / 'protocol.json').read_text())
    if protocol != prepare(design):
        raise ValueError('A3 protocol, qualification or sources changed.')
    return design, protocol


class Session(base.Session):
    def snapshot(self):
        return {**super().snapshot(), 'reference_monitor': {'version': VERSION, 'primary': 'A3', 'block_mean_span_mV_max': 3., 'A4': 'auxiliary_record_only'}}

    def summary(self):
        return {**super().summary(), 'guard_version': VERSION, 'primary_REF_channel': 'A3', 'A4_role': 'record_and_report_only'}

USB_WAIT_SECONDS = 10.


class SettledBench(A3GuardMixin, base.Bench):
    """After observing a new unarmed boot, wait >=10 s before ARM/capture."""
    def __init__(self, *args, **kwargs):
        self.startup_waited_boot = None
        super().__init__(*args, **kwargs)

    def _ping(self, board, continuity, label, armed):
        super()._ping(board, continuity, label, armed)
        if not armed and continuity.boot_id != self.startup_waited_boot:
            self.log.add('usb_startup_wait_started', {'boot_id': continuity.boot_id,
                'minimum_s': USB_WAIT_SECONDS, 'anchor': 'Observed unarmed PING after operator-confirmed USB reconnect',
                'ARM_or_CAPTURE_during_wait': False})
            start = time.monotonic()
            self.sleep(USB_WAIT_SECONDS)
            super()._ping(board, continuity, label + '_after_USB_wait', False)
            elapsed = time.monotonic() - start
            if elapsed < USB_WAIT_SECONDS:
                raise ValueError('Minimum USB startup wait not reached; no ARM.')
            self.startup_waited_boot = continuity.boot_id
            self.log.add('usb_startup_wait_completed', {'boot_id': continuity.boot_id,
                'minimum_s': USB_WAIT_SECONDS, 'elapsed_monotonic_s': elapsed})


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
    design, protocol = load_prepared(args.prepared)
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
                or qa.get('guard_version') != VERSION or qa.get('frames') != 8704
                or qa_plan['baseline_protocol']['reviewed_design_sha256'] != digest(design)
                or qa_plan['sources']['src/benchmate/a3_ref_guard.py'] != protocol['official_source_sha256']['src/benchmate/a3_ref_guard.py']):
            raise ValueError('Matching completed A3 waveform QA required.')
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
             'orchestration_version': 'official-passive-A3-v1',
             'guard_version': VERSION, 'primary_REF_channel': 'A3', 'A4_role': 'record_and_report_only',
             'minimum_USB_reconnect_wait_s': USB_WAIT_SECONDS,
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


def publish_prediction(log, bound, protocol, frozen, sha):
    check_sources(bound)
    design = checked(json.loads((log.path / 'reviewed-design.json').read_text()))
    if digest(frozen) != sha or protocol != prepare(design):
        raise ValueError('Frozen A3 protocol or forecast mismatch.')
    if base.git('branch', '--show-current') != 'main' or base.git('diff', '--cached', '--name-only'):
        raise ValueError('Clean index on main required for prediction publication.')
    if base.git('remote', 'get-url', 'origin') != 'https://github.com/bami-codes/BenchMate.git':
        raise ValueError('Unexpected publication destination.')
    (log.path / 'predictions-frozen.json').write_bytes(base.canonical(frozen) + b'\n')
    envelope = {'schema': 'benchmate.official_prediction_envelope.v1', 'official': True,
                'pilot': False, 'excluded_from_evaluation': False, 'run_id': bound['run_id'],
                'slot_id': bound['slot_id'], 'cohort_plan_id': bound['cohort_plan_id'],
                'guard_version': VERSION, 'primary_REF_channel': 'A3',
                'protocol_sha256': digest(protocol), 'source_sha256': protocol['official_source_sha256'],
                'prediction_sha256': sha, 'prediction': frozen}
    raw = base.canonical(envelope) + b'\n'
    if base.redact(raw.decode(), base.load_keys(ROOT / '.env')) != raw.decode():
        raise ValueError('Prediction secret scan failed.')
    relative = Path('examples/official-freezes/2026-11-03') / log.path.name / 'predictions.json'
    target = ROOT / relative; target.parent.mkdir(parents=True, exist_ok=False); target.write_bytes(raw)
    base.git('add', '--', str(relative))
    if base.git('diff', '--cached', '--name-only') != str(relative):
        raise ValueError('Unexpected staged file.')
    base.git('diff', '--cached', '--check')
    base.git('commit', '-m', 'Freeze A3-guard official prediction before reserved physical capture')
    commit = base.git('rev-parse', 'HEAD'); base.git('push', 'origin', 'HEAD:main')
    if base.git('ls-remote', 'origin', 'refs/heads/main').split()[0] != commit:
        raise ValueError('Remote receipt not confirmed; no reserved capture.')
    return {'sha256': sha, 'published': True, 'remote': True, 'commit': commit,
            'url': f'https://github.com/bami-codes/BenchMate/blob/{commit}/{relative}'}


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
    if protocol != prepare(design) or digest(protocol) != bound['protocol_sha256']:
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
        bench = SettledBench(protocol, log, lambda f: base.intervention(log, design, f), design=design,
            initial_report=initial, approved=True, previous_boot_id=preflight['previous_boot_id'],
            preflight_boot_id=preflight['observed_unarmed_boot_id'])
        def publish(frozen, sha):
            check_sources(bound)
            return publish_prediction(log, bound, protocol, frozen, sha)
        session = Session(bench, log, design, publish)
        model = base.OfficialModel(prompt=PROMPT, tools=session.tools, log=log, effort='medium',
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
    p = sub.add_parser('prepare')
    p.add_argument('--reviewed-design', required=True); p.add_argument('--output', required=True)
    p = sub.add_parser('register')
    for name in ('prepared', 'slot', 'initial-report', 'assembly-record', 'previous-boot-id', 'preflight-run'):
        p.add_argument('--' + name, required=True)
    p.add_argument('--QA-result')
    p.add_argument('--output', default=str(ROOT / 'runs/official'))
    p = sub.add_parser('run')
    p.add_argument('--record', required=True)
    p.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    if args.command == 'prepare':
        design = checked(json.loads(Path(args.reviewed_design).read_text()))
        out = Path(args.output); out.mkdir(parents=True, exist_ok=False)
        base.save(out / 'reviewed-design.json', design); base.save(out / 'protocol.json', prepare(design))
        print(json.dumps({'prepared': str(out), 'paid_calls': 0, 'hardware_commands': 0}))
    else:
        (register if args.command == 'register' else run)(args)


if __name__ == '__main__':
    main()
