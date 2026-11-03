"""No actual requests: bounded failure handling, visible evidence and secrets."""
import json

import httpx
import pytest

from benchmate.reading_transport import call
from benchmate.records import read_events


@pytest.mark.parametrize('status,body', [
    (500, {}),
    (200, {'status': 'incomplete', 'usage': {'output_tokens': 4096}, 'output': []}),
    (200, {'status': 'completed', 'output': [{'type': 'function_call', 'name': 'wrong', 'arguments': '{}'}]}),
])
def test_provider_failures_sent_once_no_retry_and_retained(tmp_path, monkeypatch, status, body):
    from benchmate import config
    monkeypatch.setattr(config, 'load_keys', lambda _: {'MODEL_API_KEY': 'unit-test-not-a-real-key'})
    sent = []
    def handle(request):
        sent.append(request)
        return httpx.Response(status, json=body)
    with httpx.Client(transport=httpx.MockTransport(handle)) as client:
        with pytest.raises(RuntimeError, match='no retry'):
            call([{'type': 'input_text', 'text': 'fixture'}], tool={'name': 'expected'}, output=tmp_path/'runs',
                 budget=tmp_path/'budget.json', client=client)
    assert len(sent) == 1
    events = read_events(next((tmp_path/'runs').iterdir()))
    assert events[-1]['kind'] == 'run_failed'
    assert json.loads((tmp_path/'budget.json').read_text())['reserved_usd']['meta'] == 1
    assert 'unit-test-not-a-real-key' not in json.dumps(events)


def test_completed_visible_tool_preserved_without_hidden_reasoning(tmp_path, monkeypatch):
    from benchmate import config
    monkeypatch.setattr(config, 'load_keys', lambda _: {'MODEL_API_KEY': 'unit-test-not-a-real-key'})
    body = {'status': 'completed', 'usage': {'input_tokens': 10, 'output_tokens': 12}, 'output': [
        {'type': 'reasoning', 'encrypted_content': 'opaque-not-for-log'},
        {'type': 'function_call', 'name': 'expected', 'arguments': '{"component":"R1"}'}]}
    with httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(200, json=body))) as client:
        run, result = call([{'type': 'input_text', 'text': 'fixture'}], tool={'name': 'expected'},
            output=tmp_path/'runs', budget=tmp_path/'budget.json', client=client)
    assert result['arguments'] == {'component': 'R1'}
    visible = (run/'response-visible.json').read_text()
    assert 'opaque-not-for-log' not in visible and 'R1' in visible
