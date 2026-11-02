"""Real subprocess transport tests with a scripted mock; no paid API or USB."""
import json
from pathlib import Path
import re
import threading
import time
import uuid

import httpx
import pytest

from benchmate.case_review.runner_bridge import RunnerBridge
from benchmate.case_review.runner_contract import read_json, verified_protocol
from benchmate.case_review.service import CaseStore, Conflict
from benchmate.case_review.web import make_server

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def bridge(tmp_path):
    store = CaseStore(ROOT, tmp_path / 'cases')
    b = RunnerBridge(ROOT, store, confirmation_timeout_s=10)
    yield b
    b.close()


def case(b):
    created = b.store.create('Software QA: why is the RC response slow?', 'recorded_walkthrough')['manifest']
    return b.store.confirm_for_replay(created['case_id'], created['revision'], created['intended_design']['draft_candidate'])['manifest']


def launch(b, fault='none', c=None, run_id=None):
    c = c or case(b)
    req = {'revision': c['revision'], 'mode': 'scripted_mock', 'fault': fault, 'launch_id': run_id or uuid.uuid4().hex}
    return b.launch(c['case_id'], req), c, req


def wait(b, run_id, *, action=None, terminal=False):
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline:
        s = b.snapshot(run_id)
        if action and s['pending_request'] and s['pending_request']['action'] == action:
            return s
        if terminal and s['status'] not in ('running', 'awaiting_operator', 'cancelling'):
            child = b.children.get(run_id)
            if child:
                child.wait(timeout=3)
            return s
        if action and s['status'] not in ('running', 'awaiting_operator'):
            pytest.fail(json.dumps(s))
        time.sleep(.03)
    pytest.fail('Timed out: ' + json.dumps(b.snapshot(run_id)))


def report(s):
    p = s['pending_request']
    keys = ('request_id', 'action', 'fixture', 'prediction_sha256', 'expected_boot_id', 'wiring_revision', 'request_sha256', 'simulated')
    return {**{k: p[k] for k in keys}, **{k: True for k in p['required_checks']},
            'verbatim': 'SOFTWARE QA simulated action; no human touched hardware.'}


def advance(b, run_id, action):
    s = wait(b, run_id, action=action)
    b.respond(run_id, report(s))
    return s


def all_events(b, run_id):
    return b._events(b._folder(run_id))


def test_interactive_full_run_uses_actual_channel_and_preserves_archive(bridge):
    pinned = verified_protocol(ROOT)['source_sha256']
    s, c, req = launch(bridge)
    run_id = s['run_id']
    load = wait(bridge, run_id, action='attach_output_load')
    assert load['mock_waveforms'] == 1
    time.sleep(.55)
    assert bridge.snapshot(run_id)['mock_waveforms'] == 1
    assert load['pending_request']['physical_action_requested'] is False
    assert 'SIMULATION ONLY' in load['pending_request']['instruction']
    bridge.respond(run_id, report(load))
    repair = wait(bridge, run_id, action='restore_nominal_capacitance')
    assert repair['mock_waveforms'] == 3 and repair['publication']['remote'] is False
    prediction = bridge.predictions(run_id)
    assert prediction['sha256'] == repair['pending_request']['prediction_sha256']
    assert prediction['predictions']['post_repair_scored_OUT_used'] == 0
    before = bridge._folder(run_id) / 'reviewed-design.json'
    assert read_json(before) == c['intended_design']['reviewed']
    bridge.respond(run_id, report(repair))
    done = wait(bridge, run_id, terminal=True)
    assert done['status'] == 'completed' and done['result']['repair_verified']
    assert done['mock_waveforms'] == 5 and done['result']['Spark_authored'] is False
    assert done['physical_measurements'] == done['paid_api_calls'] == 0
    assert done['result']['instrument']['real_serial_commands'] == 0
    assert bridge.store.get(c['case_id'])['manifest'] == c
    assert verified_protocol(ROOT)['source_sha256'] == pinned
    events = all_events(bridge, run_id)
    kinds = [e['kind'] for e in events]
    assert kinds.count('bridge_operator_response_consumed') == 2
    assert kinds.index('repair_prediction_publication') < next(e['sequence'] for e in events if e['kind'] == 'mock_rc_observation' and e['payload']['phase'] == 'repair_step')
    assert bridge.launch(c['case_id'], req)['run_id'] == run_id
    assert len(bridge.children) == 1
    assert bridge.list_runs(c['case_id'])[0]['status'] == 'completed'
    gathered, cursor = [], -1
    while True:
        page = bridge.events(run_id, cursor)
        gathered += page['events']
        if not page['events']: break
        cursor = page['next_after']
    assert gathered == events


def test_gate_concurrency_and_response_identity(bridge):
    created = bridge.store.create('Software QA', 'recorded_walkthrough')['manifest']
    with pytest.raises(Conflict): launch(bridge, c=created)
    s, c, req = launch(bridge)
    run_id = s['run_id']
    assert bridge.launch(c['case_id'], req)['run_id'] == run_id
    with pytest.raises(Conflict): launch(bridge, c=c)
    for change in ({'revision': True}, {'revision': 1}, {'mode': 'physical'}, {'fault': 'unknown'}, {'launch_id': '../escape'}):
        with pytest.raises((Conflict, ValueError)): bridge.launch(c['case_id'], {**req, **change})
    s = wait(bridge, run_id, action='attach_output_load')
    valid = report(s)
    for change in ({'request_id': 'f'*32}, {'expected_boot_id': 'f'*32}, {'prediction_sha256': 'f'*64},
                   {'request_sha256': 'f'*64}, {'wiring_revision': True}, {'simulated': False},
                   {'USB_connected': False}, {'verbatim': ''}, {'extra': True}):
        with pytest.raises((Conflict, ValueError)): bridge.respond(run_id, {**valid, **change})
        assert bridge.snapshot(run_id)['mock_waveforms'] == 1
    bridge.respond(run_id, valid)
    with pytest.raises(Conflict): bridge.respond(run_id, valid)
    repair = wait(bridge, run_id, action='restore_nominal_capacitance')
    with pytest.raises(Conflict): bridge.respond(run_id, valid)
    assert bridge.snapshot(run_id)['mock_waveforms'] == 3
    audits = [read_json(p)['kind'] for p in (bridge._folder(run_id) / 'bridge-actions').glob('*.json')]
    assert audits.count('operator_response_rejected') == 11
    bridge.cancel(run_id, 'Software QA cancellation at repair')
    done = wait(bridge, run_id, terminal=True)
    assert done['status'] == 'cancelled' and done['mock_waveforms'] == 3
    assert done['result']['repair_verified'] is False


@pytest.mark.parametrize('fault,status,waveforms', [
    ('publication_failure', 'failed', 3), ('stale_boot', 'failed', 4),
    ('reset_during_reserved', 'failed', 5), ('repair_failed', 'completed', 5),
    ('reserved_failure', 'completed', 5),
])
def test_faults_never_become_verified_or_restart(bridge, fault, status, waveforms):
    s, _, _ = launch(bridge, fault)
    run_id = s['run_id']
    advance(bridge, run_id, 'attach_output_load')
    if fault != 'publication_failure': advance(bridge, run_id, 'restore_nominal_capacitance')
    done = wait(bridge, run_id, terminal=True)
    assert done['status'] == status
    assert done['result']['repair_verified'] is False
    assert done['mock_waveforms'] == waveforms
    assert done['automatic_retry'] is False and done['paid_api_calls'] == 0
    with pytest.raises(Conflict): bridge.respond(run_id, {})
    if fault == 'publication_failure':
        assert not any(e['kind'] == 'bridge_operator_context' and e['payload']['action'] == 'restore_nominal_capacitance' for e in all_events(bridge, run_id))


def test_timeout_and_server_restart_do_not_resume(bridge):
    bridge.timeout = .2
    s, _, _ = launch(bridge)
    done = wait(bridge, s['run_id'], terminal=True)
    assert done['status'] == 'timed_out' and done['mock_waveforms'] == 1
    restarted = RunnerBridge(ROOT, bridge.store)
    try:
        assert restarted.snapshot(s['run_id'])['status'] == 'timed_out'
        assert restarted.children == {}
        with pytest.raises(Conflict): restarted.respond(s['run_id'], {})
    finally: restarted.close()


def test_detached_worker_is_not_adopted_or_confirmed(bridge):
    s, _, _ = launch(bridge)
    run_id = s['run_id']
    load = wait(bridge, run_id, action='attach_output_load')
    observer = RunnerBridge(ROOT, bridge.store)
    try:
        assert observer.snapshot(run_id)['status'] == 'interrupted'
        with pytest.raises(Conflict): observer.respond(run_id, report(load))
        assert observer.children == {}
    finally: observer.close()
    bridge.cancel(run_id, 'Software QA stop')
    assert wait(bridge, run_id, terminal=True)['status'] == 'cancelled'


def test_close_stops_worker_without_an_ack(bridge):
    s, _, _ = launch(bridge)
    run_id = s['run_id']
    wait(bridge, run_id, action='attach_output_load')
    bridge.close()
    assert bridge.children[run_id].poll() is not None
    assert bridge.snapshot(run_id)['mock_waveforms'] == 1
    assert bridge.snapshot(run_id)['status'] == 'cancelled'


def test_protocol_drift_blocks_spawn(bridge, monkeypatch):
    def reject(_): raise ValueError('Frozen D01 source mismatch')
    monkeypatch.setattr('benchmate.case_review.runner_bridge.verified_protocol', reject)
    with pytest.raises(ValueError): launch(bridge)
    assert not list(bridge.output.iterdir()) and not bridge.children


def test_corrupted_event_and_prediction_are_rejected(bridge):
    s, _, _ = launch(bridge)
    run_id = s['run_id']
    advance(bridge, run_id, 'attach_output_load')
    wait(bridge, run_id, action='restore_nominal_capacitance')
    folder = bridge._folder(run_id)
    location = read_json(folder / 'record-location.json')['path']
    prediction = folder / location / 'predictions-frozen.json'
    prediction.write_text('{}')
    with pytest.raises(ValueError): bridge.predictions(run_id)
    bridge.cancel(run_id, 'Stop before corrupting test record')
    wait(bridge, run_id, terminal=True)
    events = folder / location / 'events.jsonl'
    raw = events.read_bytes()
    events.write_bytes(raw.replace(b'run_started', b'run_changed', 1))
    with pytest.raises(ValueError): bridge.snapshot(run_id)
    events.write_bytes(raw)


def test_http_bridge_preserves_origin_guard_and_old_routes(tmp_path):
    server = make_server(root=ROOT, output=tmp_path / 'http', port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
    try:
        with httpx.Client(base_url=f'http://127.0.0.1:{server.server_port}', trust_env=False) as client:
            page = client.get('/').text
            token = re.search(r'<meta name="benchmate-session" content="([^"]+)"', page).group(1)
            headers = {'X-BenchMate-Session': token}
            assert client.get('/api/runner-capabilities').json()['live_enabled'] is False
            c = client.post('/api/cases', headers=headers, json={'question': 'HTTP QA', 'scope': 'recorded_walkthrough'}).json()['manifest']
            c = client.post(f"/api/cases/{c['case_id']}/confirm", headers=headers,
                json={'revision': c['revision'], 'candidate': c['intended_design']['draft_candidate']}).json()['manifest']
            url = f"/api/cases/{c['case_id']}/runs"
            body = {'revision': c['revision'], 'mode': 'scripted_mock', 'fault': 'none', 'launch_id': uuid.uuid4().hex}
            assert client.post(url, json=body).status_code == 403
            assert client.post(url, headers={**headers, 'Origin': 'https://evil.example'}, json=body).status_code == 403
            result = client.post(url, headers=headers, json=body)
            assert result.status_code == 200, result.text
            run_id = result.json()['run_id']
            load = wait(server.runner_bridge, run_id, action='attach_output_load')
            assert client.get(url).json()[0]['run_id'] == run_id
            assert client.get(f'/api/runs/{run_id}/events?after=-1').status_code == 200
            assert client.get(f'/api/runs/{run_id}/predictions').status_code == 409
            assert client.post('/api/run', headers=headers, json={}).status_code == 404
            assert client.post(f'/api/runs/{run_id}/respond', headers=headers, json=report(load)).status_code == 200
            repair = wait(server.runner_bridge, run_id, action='restore_nominal_capacitance')
            assert client.get(f'/api/runs/{run_id}/predictions').status_code == 200
            assert client.post(f'/api/runs/{run_id}/respond', headers=headers, json=report(repair)).status_code == 200
            done = wait(server.runner_bridge, run_id, terminal=True)
            assert done['result']['repair_verified']
            assert client.get(f"/api/cases/{c['case_id']}/timeline?cursor=139").status_code == 200
    finally:
        server.shutdown(); server.server_close(); thread.join(timeout=3)
