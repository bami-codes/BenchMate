"""No real API/serial: accumulated history, fail-closed bounds and protocol scope."""
import importlib.util
import json
from pathlib import Path

import httpx
import pytest

from benchmate.official_transport_v2 import OfficialModel, MAX_PAYLOAD_BYTES
from benchmate.providers import ProviderError
from benchmate.records import Recorder, decode_events

ROOT = Path(__file__).resolve().parents[1]


def setup(tmp_path, monkeypatch):
    monkeypatch.delenv('MODEL_API_KEY', raising=False)
    env = tmp_path / '.env'
    env.write_text('MODEL_API_KEY=transport-unit-test-secret\n')
    budget = tmp_path / 'budget.json'
    budget.write_text(json.dumps({'authorized_by_operator': True,
        'authorized_request_limit': 8, 'reserved_usd': {'meta': 0}}))
    return env, budget, Recorder(tmp_path / 'logs', mode='offline_transport_test')


def test_large_history_keeps_opaque_items_and_pairing_then_stops_at_eight(tmp_path, monkeypatch):
    env, budget, log = setup(tmp_path, monkeypatch)
    requests = []
    opaque = 'opaque-unit-only-' + 'x' * 150000

    def handler(request):
        body = json.loads(request.content)
        requests.append(body)
        if len(requests) > 1:
            assert body['input'][1]['encrypted_content'] == opaque
            assert body['input'][-1]['call_id'] == 'call-' + str(len(requests) - 1)
            assert json.loads(body['input'][-1]['output']) == {'observation': 'v' * 8000}
        n = len(requests)
        output = [{'type': 'function_call', 'call_id': 'call-' + str(n),
                   'name': 'inspect_experiment', 'arguments': '{}'}]
        if n == 1:
            output.insert(0, {'type': 'reasoning', 'encrypted_content': opaque})
        return httpx.Response(200, json={'status': 'completed', 'usage': {}, 'output': output})

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        model = OfficialModel(prompt='unit test', tools=[], log=log, env_path=env,
                              budget_path=budget, client=client)
        for _ in range(8):
            call = model.next_call()
            model.submit_result(call['call_id'], {'observation': 'v' * 8000})
        with pytest.raises(ProviderError, match='allowance exhausted|budget exhausted'):
            model.next_call()
    assert len(requests) == 8
    assert json.loads(budget.read_text())['reserved_usd']['meta'] == 8
    assert model.metadata()['max_payload_bytes'] == MAX_PAYLOAD_BYTES
    raw = log.file.read_text()
    assert opaque not in raw and 'transport-unit-test-secret' not in raw
    events = decode_events(log.file.read_bytes(), require_terminal=False)
    config = next(e['payload'] for e in events if e['kind'] == 'provider_configuration')
    assert config['max_payload_bytes'] == MAX_PAYLOAD_BYTES
    sizes = [e['payload']['bytes'] for e in events if e['kind'] == 'provider_payload_size']
    assert max(sizes) > 128000 and max(sizes) < MAX_PAYLOAD_BYTES


def test_over_bound_rejected_before_http_or_budget_reservation(tmp_path, monkeypatch):
    env, budget, log = setup(tmp_path, monkeypatch)
    def denied(request):
        pytest.fail('Oversized request reached HTTP')
    with httpx.Client(transport=httpx.MockTransport(denied)) as client:
        model = OfficialModel(prompt='x' * MAX_PAYLOAD_BYTES, tools=[], log=log,
                              env_path=env, budget_path=budget, client=client)
        before = budget.read_bytes()
        with pytest.raises(ProviderError, match='payload exceeds'):
            model.next_call()
        assert model.requests == 0 and budget.read_bytes() == before


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / ('scripts/' + name + '.py'))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def test_new_profile_changes_only_transport_and_bound_source_identity():
    old = load('official_passive_A3'); new = load('official_passive_A3_v2')
    design = json.loads((ROOT / 'examples/reviewed-designs/2026-11-03-pilot/design-01.json').read_text())
    a, b = old.prepare(design), new.prepare(design)
    assert b['api_plan']['max_payload_bytes'] == MAX_PAYLOAD_BYTES
    assert len(b['official_source_sha256']) == 87
    for key, value in a.items():
        if key == 'api_plan':
            assert {k: v for k, v in value.items() if k != 'max_payload_bytes'} == {
                k: v for k, v in b[key].items() if k != 'max_payload_bytes'}
        elif key not in ('official_source_sha256', 'official_runtime_version'):
            assert b[key] == value
    assert set(b) - set(a) == {'transport_version'}
    assert new.OfficialModel is OfficialModel
    assert new.Session._predict is old.Session._predict
    assert new.SettledBench._capture is old.SettledBench._capture
