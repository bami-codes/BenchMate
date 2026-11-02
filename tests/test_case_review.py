"""Case isolation, provenance and fail-closed handoffs for the recorded workflow."""
from copy import deepcopy
import json
from pathlib import Path
import threading

import httpx
import pytest

from benchmate.case_review.service import CaseStore, Conflict
from benchmate.case_review.web import make_server
from benchmate.design_replay import D01, VISION, D01_SHA, VISION_SHA

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def store(tmp_path):
    return CaseStore(ROOT, tmp_path/'cases')


def start(store, scope='recorded_walkthrough'):
    return store.create('Why is the RC response slow?', scope)


def review(store, case, candidate=None):
    m = case['manifest']
    return store.review(m['case_id'], m['revision'], candidate or m['intended_design']['draft_candidate'],
                        'Software test review of values and connections')


def test_local_question_never_relabels_archived_inputs(store):
    paths = [ROOT/D01/'events.jsonl', ROOT/VISION/'events.jsonl']
    before = [p.read_bytes() for p in paths]
    case = review(store, start(store))
    case = store.link_replay(case['manifest']['case_id'], 2)
    m = case['manifest']
    assert m['question']['sent_to_model'] is False
    assert m['question']['included_in_historical_experiment'] is False
    assert m['intended_design']['source_date_kst'] == '2026-10-31'
    assert m['intended_design']['vision_record_sha256'] == VISION_SHA
    link = m['experiment_link']
    assert link['source_date_kst'] == '2026-10-30' and link['record_sha256'] == D01_SHA
    assert not link['same_specimen_established'] and not link['new_measurement']
    assert not link['question_was_input_to_run']
    assert link['relationship'] == 'same_nominal_design_only'
    assert m['observed_assembly'] is None and m['capture_state'] is None
    assert m['measurement_registry'] == [] and m['answer'] is None and m['operator_request'] is None
    assert all(value is False for value in m['capabilities'].values())
    assert [p.read_bytes() for p in paths] == before
    assert D01_SHA.encode() in store.replay(m['case_id'])


def test_review_is_per_case_and_current_revision_only(store):
    first, second = start(store), start(store)
    identity = first['manifest']['case_id']
    with pytest.raises(Conflict):
        store.link_replay(identity, 1)
    reviewed = review(store, first)
    with pytest.raises(Conflict):
        review(store, first)
    for stale in (1, True, '2', 2.0):
        with pytest.raises(Conflict):
            store.link_replay(identity, stale)
    with pytest.raises(Conflict):
        store.link_replay(second['manifest']['case_id'], 1)
    with pytest.raises(Conflict):
        store.replay(second['manifest']['case_id'])
    linked = store.link_replay(identity, reviewed['manifest']['revision'])
    with pytest.raises(Conflict):
        review(store, linked)
    with pytest.raises(Conflict):
        store.link_replay(identity, linked['manifest']['revision'])


@pytest.mark.parametrize('change,code', [
    ('unknown_value', 'needs_information'), ('unknown_connection', 'needs_information'),
    ('ambiguity', 'needs_information'), ('unsupported', 'unsupported_design'),
    ('topology', 'unsupported_design'), ('out_of_range', 'unsupported_design'),
    ('mismatch', 'nominal_design_mismatch'), ('different_specimen', 'different_specimen'),
])
def test_unsafe_or_unrelated_design_cannot_link(store, change, code):
    case = start(store, 'different_specimen' if change == 'different_specimen' else 'recorded_walkthrough')
    candidate = deepcopy(case['manifest']['intended_design']['draft_candidate'])
    if change == 'unknown_value': candidate['components'][0]['value_si'] = None
    if change == 'unknown_connection': candidate['components'][0]['a'] = 'UNKNOWN'
    if change == 'ambiguity': candidate['ambiguities'] = ['Unclear wire']
    if change == 'unsupported': candidate['status'] = 'unsupported'
    if change == 'topology': candidate['components'][0]['a'] = 'REF'
    if change == 'out_of_range': candidate['components'][0]['value_si'] = 999
    if change == 'mismatch': candidate['components'][1]['value_si'] = 470e-9
    result = review(store, case, candidate)
    assert result['replay_eligibility']['code'] == code
    assert result['replay_eligibility']['allowed'] is False
    with pytest.raises(Conflict): store.link_replay(result['manifest']['case_id'], 2)


def test_unknown_can_be_resolved_without_erasing_prior_review(store):
    case = start(store); candidate = deepcopy(case['manifest']['intended_design']['draft_candidate'])
    candidate['components'][1]['value_si'] = None
    unresolved = review(store, case, candidate)
    folder = store.output/case['manifest']['case_id']
    previous = (folder/'revision-0002.json').read_bytes()
    resolved = review(store, unresolved, case['manifest']['intended_design']['original_candidate'])
    assert resolved['replay_eligibility']['allowed']
    assert (folder/'revision-0002.json').read_bytes() == previous
    assert resolved['manifest']['intended_design']['original_candidate'] == case['manifest']['intended_design']['original_candidate']


def test_reload_keeps_history_and_detects_modified_revision(store):
    result = review(store, start(store)); identity = result['manifest']['case_id']
    folder = store.output/identity
    before = {p.name:p.read_bytes() for p in folder.iterdir()}
    restored = CaseStore(ROOT, store.output)
    assert restored.get(identity) == result
    assert {p.name:p.read_bytes() for p in folder.iterdir()} == before
    path = folder/'revision-0001.json'
    corrupt = json.loads(path.read_bytes()); corrupt['manifest']['question']['text'] = 'Changed question'
    path.write_text(json.dumps(corrupt))
    with pytest.raises(Conflict): restored.get(identity)
    assert restored.summaries()[0]['status'] == 'integrity_error'
    with pytest.raises(Conflict): restored.replay(identity)


def test_concurrent_confirmation_is_consumed_once(store):
    case = review(store, start(store)); identity = case['manifest']['case_id']
    results = []
    def link():
        try: results.append(store.link_replay(identity, 2)['manifest']['revision'])
        except Conflict: results.append('conflict')
    threads = [threading.Thread(target=link) for _ in range(2)]
    for thread in threads: thread.start()
    for thread in threads: thread.join()
    assert sorted(map(str, results)) == ['3', 'conflict']


@pytest.fixture
def client(tmp_path):
    server = make_server(root=ROOT, output=tmp_path/'http-cases', port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
    base = f'http://127.0.0.1:{server.server_port}'
    try:
        with httpx.Client(base_url=base) as http:
            page = http.get('/')
            token = page.text.split('name="benchmate-session" content="')[1].split('"')[0]
            http.headers.update({'Origin':base, 'X-BenchMate-Session':token})
            yield http, server
    finally:
        server.shutdown(); server.server_close(); thread.join()


def test_http_flow_export_reload_and_replay_content(client):
    http, server = client
    for asset in ('/', '/app.js', '/style.css', '/schematic.png'):
        assert http.get(asset).status_code == 200
    response = http.post('/api/cases', json={'question':'Why slow?', 'scope':'recorded_walkthrough'})
    assert response.status_code == 201
    case = response.json()['manifest']; path = f"/api/cases/{case['case_id']}"
    assert http.get(path+'/replay').status_code == 409
    args = {'revision':1, 'candidate':case['intended_design']['draft_candidate'], 'review_note':'HTTP test review'}
    assert http.post(path+'/review', json=args).status_code == 200
    assert http.post(path+'/link-replay', json={'revision':2}).status_code == 200
    export = http.get(path+'/export'); restored = http.get(path)
    assert export.json() == restored.json()
    assert export.headers['content-disposition'].startswith('attachment;')
    replay = http.get(path+'/replay')
    assert replay.status_code == 200 and D01_SHA in replay.text
    assert "frame-ancestors 'self'" in replay.headers['content-security-policy']
    state = http.get('/api/state').json()
    assert state['paid_api_calls'] == 0 and not state['hardware_IO']
    assert len(state['cases']) == 1
    assert len(list(server.case_store.output.rglob('revision-*.json'))) == 3


def test_http_rejects_cross_origin_invalid_payload_and_execution_routes(client):
    http, _ = client
    body = {'question':'Start DAC now', 'scope':'recorded_walkthrough'}
    for headers in ({'Origin':'https://evil.example'}, {'Host':'evil.example'}, {'X-BenchMate-Session':''}):
        assert http.post('/api/cases', json=body, headers=headers).status_code == 403
    assert http.get('/api/state', headers={'Origin':'https://evil.example'}).status_code == 403
    for body in ({'question':'', 'scope':'recorded_walkthrough'}, {'question':'x', 'scope':'live'},
                 {'question':True, 'scope':'recorded_walkthrough'}, {'question':'x', 'scope':'recorded_walkthrough','run':True}):
        assert http.post('/api/cases', json=body).status_code == 400
    assert http.post('/api/cases', content='{"question":NaN,"scope":"recorded_walkthrough"}', headers={'Content-Type':'application/json'}).status_code == 400
    assert http.post('/api/cases', content='x'*64001, headers={'Content-Type':'application/json'}).status_code == 400
    for route in ('/api/run', '/api/extract', '/api/serial', '/api/cases/'+'a'*32+'/run'):
        assert http.post(route, json={}).status_code == 404
    assert http.get('/api/cases/%2e%2e').status_code == 404
    assert http.get('/api/state').json()['cases'] == []
