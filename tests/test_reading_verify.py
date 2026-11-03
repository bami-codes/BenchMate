"""Rehashed causality attacks on a synthetic parent using retained bench children.

Fixtures live only in tmp_path; they are not new physical runs or model calls.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

from benchmate.records import Recorder, canonical, decode_events
from benchmate.reading_rules import digest, score_reading
from benchmate.reading_verify import verify_run
from test_reading_rules import forecast, observation

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT/'examples/official-runs/2026-11-03/records'


def artifact(root, name, raw=b'fixture'):
    path = root/name; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(raw)
    return {'file': name, 'sha256': hashlib.sha256(raw).hexdigest()}


def link(log, directory, kind):
    events = decode_events((directory/'events.jsonl').read_bytes(), include_hash=True)
    log.add('child_record_bound', {'file': str((directory/'events.jsonl').relative_to(log.path)),
        'sha256': hashlib.sha256((directory/'events.jsonl').read_bytes()).hexdigest(),
        'head_sha256': events[-1]['sha256'], 'kind': kind})


@pytest.fixture
def pair(tmp_path):
    log = Recorder(tmp_path, mode='SYNTHETIC_READING_PARENT_TEST_ONLY')
    log.add('reading_pair_registered', {'cohort': 'reading-assisted-v1', 'source': 'synthetic_test_fixture'})
    assembly = {'source': 'synthetic fixture', 'specimen_truth': ['mock']}
    log.add('specimen_assembly_sealed', {'state': 'faulted', 'sha256': digest(assembly)})
    for state, record in [('faulted', '20261103T083824-7be77b51da'), ('restored', '20261103T113619-34ff2352b1')]:
        child = log.path/state; child.mkdir()
        for name in ('events.jsonl', 'predictions-frozen.json'):
            shutil.copyfile(ARCHIVE/record/name, child/name)
    link(log, log.path/'faulted', 'terminal_diagnosis')
    log.add('diagnosis_finished', {'state': 'faulted', 'record': 'faulted', 'agent_report': {'verdict': 'changed'}})
    f = forecast(); request = f['request']
    child = Recorder(log.path/'choice', mode='SYNTHETIC_SPARK_CHOICE_TEST_ONLY')
    child.add('run_completed', {'arguments': {k: v for k, v in request.items() if k != 'chosen_by'}})
    link(log, child.path, 'reading_selection')
    log.add('reading_requested', request)
    (log.path/'reading-forecast.json').write_text(json.dumps(f)+'\n')
    log.add('reading_forecast_frozen', {**f, 'sha256': digest(f)})
    log.add('reading_forecast_publication', {'sha256': digest(f), 'published': True, 'remote': True, 'commit': 'b'*40})
    for state in ('faulted', 'restored'):
        if state == 'restored':
            obs = observation(); obs['photo'] = artifact(log.path, 'evidence.png')
            log.add('reading_observed', obs); scored = score_reading(f, obs)
            log.add('reading_scored', scored)
            log.add('specimen_seal_opened', {'sealed_sha256': digest(assembly), 'assembly': assembly})
            log.add('operator_restoration_confirmed', {'USB_off': True, 'restored_intended_design': True, 'reading_isolation_reconnected': True})
            link(log, log.path/'restored', 'terminal_diagnosis')
            log.add('diagnosis_finished', {'state': 'restored', 'record': 'restored', 'agent_report': {'verdict': 'consistent'}})
        photo = artifact(log.path, state+'.png')
        log.add('board_photo_received', {'state': state, **photo, 'artifacts': []})
        manifest = artifact(log.path, state+'-manifest.json', b'{}')
        log.add('bodies_decoded', {'state': state, 'manifest': manifest['file'], 'sha256': manifest['sha256'], 'artifacts': [], 'bodies': ['sam-0']})
        proposal = {'state': state, 'sam_body': 'sam-0', 'component': 'R1', 'chosen_by': 'muse_spark', 'reason': 'Geometry only.'}
        child = Recorder(log.path/('binding-'+state), mode='SYNTHETIC_BINDING_TEST_ONLY')
        child.add('run_completed', {'arguments': {k: proposal[k] for k in ('sam_body', 'reason')}})
        link(log, child.path, 'body_binding')
        log.add('body_binding_proposed', proposal)
        log.add('body_binding', {**proposal, 'operator_confirmed': True})
    log.add('run_completed', {'reading_outcome': scored['outcome'], 'restored_verdict': 'consistent'})
    return log.path


def rechain(file, edit):
    events = [json.loads(x) for x in file.read_text().splitlines()]
    edit(events); previous = '0'*64; lines = []
    for i, e in enumerate(events):
        value = {k: v for k, v in e.items() if k != 'sha256'}
        value.update(sequence=i, previous_sha256=previous)
        previous = digest(value); lines.append(json.dumps({**value, 'sha256': previous}))
    file.write_text('\n'.join(lines)+'\n')


def test_full_pair_stdlib_cli_and_all_children(pair):
    r = verify_run(pair)
    assert r['passed'], r
    assert r['forecasts'] == 9 and r['measurements'] == 11
    out = subprocess.run([sys.executable, '-S', '-m', 'benchmate', 'verify', str(pair)], cwd=ROOT, capture_output=True, text=True)
    assert out.returncode == 0, out.stdout+out.stderr
    assert out.stdout.startswith('PASS ') and 'creation_time=unproven' in out.stdout


@pytest.mark.parametrize('kind,before', [
    ('reading_forecast_frozen', 'reading_observed'),
    ('reading_forecast_publication', 'reading_observed'),
    ('reading_observed', 'reading_forecast_publication'),
    ('body_binding', 'board_photo_received'),
    ('specimen_seal_opened', 'reading_scored'),
    ('operator_restoration_confirmed', 'specimen_seal_opened'),
])
def test_valid_rehash_cannot_hide_wrong_sequence(pair, kind, before):
    def edit(events):
        item = events.pop(next(i for i, e in enumerate(events) if e['kind'] == kind))
        index = next(i for i, e in enumerate(events) if e['kind'] == before)
        events.insert(index, item)
    rechain(pair/'events.jsonl', edit)
    assert not verify_run(pair)['passed']


def test_changed_score_fails_even_when_rehashed(pair):
    def edit(events):
        next(e for e in events if e['kind'] == 'reading_scored')['payload']['fits'] = ['changed:R1']
    rechain(pair/'events.jsonl', edit)
    assert verify_run(pair)['error'] == 'reading_score_not_deterministic'


def test_changed_child_or_evidence_fails(pair):
    (pair/'evidence.png').write_bytes(b'edited')
    assert verify_run(pair)['error'] == 'artifact_hash_mismatch'


def test_child_integrity_is_checked_and_path_escape_rejected(pair):
    def edit(events):
        next(e for e in events if e['kind'] == 'child_record_bound')['payload']['file'] = '../outside/events.jsonl'
    rechain(pair/'events.jsonl', edit)
    assert verify_run(pair)['error'] == 'unsafe_artifact_path'


def test_tampering_with_inner_forecast_hash_is_detected(pair):
    def edit(events):
        next(e for e in events if e['kind'] == 'reading_forecast_frozen')['payload']['sha256'] = 'f'*64
    rechain(pair/'events.jsonl', edit)
    assert verify_run(pair)['error'] == 'reading_forecast_hash_mismatch'


def test_legacy_command_still_verifies_retained_records():
    r = verify_run(ARCHIVE/'20261103T083824-7be77b51da')
    assert r['passed'] and r['events'] == 237
