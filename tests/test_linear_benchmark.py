import importlib.util
import json
from pathlib import Path

import httpx
import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('benchmark_linear', ROOT / 'scripts/benchmark_linear.py')
bl = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bl)


def protocol():
    return bl.load_protocol()


def test_specimens_are_deterministic_and_dev_is_separate():
    p = protocol()
    a, b = bl.generate_specimens(p), bl.generate_specimens(p)
    dev = bl.generate_specimens(p, dev=True)
    assert a == b
    assert {s['noise_seed'] for s in a}.isdisjoint({s['noise_seed'] for s in dev})
    counts = {}
    for s in a:
        counts[(s['task'], s['truth_class'])] = counts.get((s['task'], s['truth_class']), 0) + 1
    assert counts == {('A', 'nominal'): 8, ('A', 'r_changed'): 8, ('A', 'c_changed'): 8, ('A', 'both_changed'): 6,
                      ('B', 'rc'): 8, ('B', 'rc_input_branch'): 8}
    for s in a:
        cls = next(c for c in p['tasks'][s['task']]['classes'] if c['name'] == s['truth_class'])
        for k, (lo, hi) in cls['sampling_bounds'].items():
            assert lo <= s[k] <= hi
        if 'input_parallel_ohm' not in cls['sampling_bounds']:
            assert s['input_parallel_ohm'] is None


def test_committed_specimens_match_protocol_hash():
    if 'FILLED' in protocol()['specimens_sha256']:
        pytest.skip('specimens not yet written')
    bl.load_specimens(protocol())


def test_specimen_regeneration_tolerates_platform_rounding_not_value_changes(monkeypatch):
    original = bl.generate_specimens(protocol())
    import copy
    rounded = copy.deepcopy(original)
    rounded[0]['r_ohm'] *= 1 + 1e-15
    monkeypatch.setattr(bl, 'generate_specimens', lambda p: rounded)
    bl.load_specimens(protocol())
    rounded[0]['r_ohm'] *= 1.01
    with pytest.raises(SystemExit, match='protocol generator'):
        bl.load_specimens(protocol())


def test_scoring_rule():
    inside = {'in_family': True, 'truth_class': 'c_changed'}
    outside = {'in_family': False, 'truth_class': 'both_changed'}
    assert bl.outcome(inside, True, 'c_changed', 'verified_within_declared_candidates') == 'correct'
    assert bl.outcome(inside, True, 'r_changed', 'verified_within_declared_candidates') == 'wrong'
    assert bl.outcome(inside, False, '', 'all_candidates_inadequate') == 'false_rejection'
    assert bl.outcome(inside, False, '', 'unresolved') == 'abstained'
    assert bl.outcome(outside, True, 'r_changed', 'verified_within_declared_candidates') == 'wrong'
    assert bl.outcome(outside, False, '', 'all_candidates_inadequate') == 'rejected'
    assert bl.no_tool_outcome(inside, 'cannot_tell') == 'abstained'
    assert bl.no_tool_outcome(inside, 'c_changed') == 'correct'
    assert bl.no_tool_outcome(inside, None) == 'unparsed'
    assert bl.no_tool_outcome(outside, 'none_fit') == 'rejected'
    assert bl.no_tool_outcome(outside, 'r_changed') == 'wrong'


def test_hidden_session_withholds_ranking_only(tmp_path):
    from benchmate.records import Recorder
    s = bl.generate_specimens(protocol(), dev=True)[0]
    hidden = bl.make_session(s, protocol(), Recorder(str(tmp_path / 'h'), mode='t'), hidden=True)
    shown = bl.make_session(s, protocol(), Recorder(str(tmp_path / 's'), mode='t'))
    h, v = hidden.dispatch('inspect_experiment', {}), shown.dispatch('inspect_experiment', {})
    assert 'action_ranking' not in h and 'action_ranking' in v
    assert h['menu_actions'] == list(hidden.menu) and h['analysis'] == v['analysis']
    assert 'ranked menu' not in bl.HIDDEN_PROMPT and 'ranked menu' in bl.CONTINUOUS_PROMPT
    assert bl.HIDDEN_PROMPT.replace(bl.HIDDEN_PROMPT[bl.HIDDEN_PROMPT.index('Read the'):bl.HIDDEN_PROMPT.index('reasoning.') + 10], '') == \
        bl.CONTINUOUS_PROMPT.replace(bl.CONTINUOUS_PROMPT[bl.CONTINUOUS_PROMPT.index('Read the'):bl.CONTINUOUS_PROMPT.index('ranked menu.') + 12], '')


def test_engine_run_on_dev_specimen(tmp_path):
    p = protocol()
    s = next(x for x in bl.generate_specimens(p, dev=True) if x['truth_class'] == 'c_changed')
    row = bl.run_one(s, 'engine', 0, p, 'test', tmp_path)
    assert row['outcome'] == 'correct' and row['report_accepted'] and row['diagnostic_acquisitions'] <= 3
    assert row['choices'] and all(c['chosen'] == c['engine_top'] for c in row['choices'])


def test_baseten_adapter_round_trip(tmp_path, monkeypatch):
    from benchmate.providers_baseten import BasetenToolSession
    from benchmate.providers import ProviderError
    from benchmate.records import Recorder
    env = tmp_path / '.env'
    env.write_text('BASETEN_API_KEY=secret-test-key\n')
    seen = []
    replies = iter([
        {'id': 'r1', 'choices': [{'finish_reason': 'tool_calls', 'message': {'role': 'assistant', 'content': None,
          'tool_calls': [{'id': 'c1', 'type': 'function', 'function': {'name': 'inspect_experiment', 'arguments': '{}'}}]}}]},
        {'id': 'r2', 'choices': [{'finish_reason': 'stop', 'message': {'role': 'assistant', 'content': 'done'}}]},
    ])

    def handler(request):
        seen.append(json.loads(request.content))
        assert request.headers['Authorization'] == 'Bearer secret-test-key'
        return httpx.Response(200, json=next(replies))

    log = Recorder(str(tmp_path / 'runs'), mode='t')
    model = BasetenToolSession(prompt='P', tools=[{'type': 'function', 'name': 'inspect_experiment', 'description': 'd',
                                                    'parameters': {'type': 'object', 'properties': {}}, 'strict': True}],
                               log=log, env_path=str(env), budget_path=str(tmp_path / 'budget.json'),
                               client=httpx.Client(transport=httpx.MockTransport(handler)))
    call = model.next_call()
    assert call == {'call_id': 'c1', 'name': 'inspect_experiment', 'arguments': '{}'}
    assert seen[0]['tools'][0] == {'type': 'function', 'function': {'name': 'inspect_experiment', 'description': 'd',
                                   'parameters': {'type': 'object', 'properties': {}}, 'strict': True}}
    model.submit_result('c1', {'ok': True})
    with pytest.raises(ProviderError, match='exactly one tool call'):
        model.next_call()
    assert seen[1]['messages'][-1] == {'role': 'tool', 'tool_call_id': 'c1', 'content': '{"ok": true}'}
    assert model.requests == 2
    assert 'secret-test-key' not in (log.path / 'events.jsonl').read_text()
    assert json.loads((tmp_path / 'budget.json').read_text())['reserved_usd']['baseten'] == 2.0


def test_first_failure_survives_recovery_in_primary_score(tmp_path, monkeypatch, capsys):
    from types import SimpleNamespace
    monkeypatch.setattr(bl, 'RUNS', tmp_path)
    p = protocol(); specs = bl.generate_specimens(p, dev=True)
    s = next(x for x in specs if x['task'] == 'A' and x['in_family'])
    base = {'protocol_sha256': bl.sha256(bl.PROTOCOL), 'specimen': s['id'], 'replicate': 0,
            'task': 'A', 'arm': 'spark', 'provider_requests': 1}
    path = tmp_path/'dev/spark/results.jsonl'; path.parent.mkdir(parents=True)
    path.write_text('\n'.join(json.dumps(r) for r in [
        {**base, 'outcome': 'incomplete', 'attempt': 1},
        {**base, 'outcome': 'correct', 'attempt': 2}])+'\n')
    bl.cmd_score(SimpleNamespace(dev=True, write=False))
    scored = json.loads(capsys.readouterr().out)
    row = next(r for r in scored['table'] if r['arm']=='spark' and r['task']=='A')
    assert row['in_family_correct']=='0/1' and row['status']=='partial'
    assert row['provider_requests']==2 and row['all_attempts']==2 and row['transport_reruns']==1
    assert row['all_attempt_outcomes']['correct']==1 and row['abstained_or_incomplete']==1
    assert all('exact_mcnemar_p' not in r for r in scored['paired'])


def test_random_interval_keeps_repeats_in_same_circuit():
    rows = [{'specimen': s, 'outcome': o, 'replicate': r}
            for s,o in [('one','correct'),('two','abstained')] for r in range(3)]
    result = bl.interval(3, rows, random=True)
    assert result['wilson95'] is None and result['independent_specimens']==2
    assert result['cluster_bootstrap95']==[0.,1.]


def test_no_tool_failed_http_attempt_is_counted(tmp_path, monkeypatch):
    original_client = httpx.Client
    monkeypatch.setattr(bl, 'ROOT', tmp_path)
    (tmp_path/'.env').write_text('MODEL_API_KEY=benchmark-test-only\n')
    def handler(request):
        return httpx.Response(503, json={'error': 'development transport failure'})
    monkeypatch.setattr(httpx, 'Client', lambda **kwargs: original_client(
        transport=httpx.MockTransport(handler), **kwargs))
    s = next(x for x in bl.generate_specimens(protocol(), dev=True) if x['task']=='A')
    row = bl.run_one(s, 'no_tool', 0, protocol(), 'test', tmp_path/'runs')
    assert row['provider_requests']==1 and row['outcome']=='incomplete'
    assert 'HTTP 503' in row['error']


def test_request_limit_survives_resume(tmp_path, monkeypatch, capsys):
    from types import SimpleNamespace
    monkeypatch.setattr(bl, 'RUNS', tmp_path)
    monkeypatch.setattr(bl, 'validate_freeze', lambda *args, **kwargs: None)
    specs = [x for x in bl.generate_specimens(protocol(), dev=True) if x['task']=='B']
    path=tmp_path/'dev/spark/results.jsonl';path.parent.mkdir(parents=True)
    path.write_text(json.dumps({'protocol_sha256':bl.sha256(bl.PROTOCOL),
        'specimen':specs[0]['id'], 'replicate':0, 'provider_requests':8})+'\n')
    monkeypatch.setattr(bl, 'run_one', lambda *args: pytest.fail('Resumed cap must stop before a new run'))
    bl.cmd_run(SimpleNamespace(arm='spark', dev=True, task='B', limit=0, execute=True,
                              max_requests=8, rerun_transport=False))
    assert json.loads(capsys.readouterr().out)=={'stopped':'max_requests','used':8}


def test_source_freeze_matches_and_rejects_drift(monkeypatch):
    bl.validate_freeze(protocol())
    monkeypatch.setattr(bl, 'source_hashes', lambda: {'changed.py': 'bad'})
    with pytest.raises(SystemExit, match='source freeze mismatch'):
        bl.validate_freeze(protocol())


def test_publication_gate_rejects_before_evaluation(tmp_path, monkeypatch):
    from types import SimpleNamespace
    monkeypatch.setattr(bl, 'RUNS', tmp_path)
    def reject(*args, **kwargs):
        assert kwargs['publication'] is True
        raise SystemExit('unpublished')
    monkeypatch.setattr(bl, 'validate_freeze', reject)
    monkeypatch.setattr(bl, 'load_specimens', lambda *args: pytest.fail('No evaluation before publication'))
    with pytest.raises(SystemExit, match='unpublished'):
        bl.cmd_run(SimpleNamespace(arm='engine', dev=False))


def test_open_evaluation_requires_real_development_gate(tmp_path, monkeypatch):
    from types import SimpleNamespace
    monkeypatch.setattr(bl, 'RUNS', tmp_path)
    monkeypatch.setattr(bl, 'validate_freeze', lambda *args, **kwargs: None)
    monkeypatch.setattr(bl, 'load_specimens', lambda *args: pytest.fail('Adapter gate must precede evaluation'))
    with pytest.raises(SystemExit, match='actual Baseten development'):
        bl.cmd_run(SimpleNamespace(arm='spark_open', dev=False))


def test_interrupted_unindexed_attempt_blocks_silent_repeat(tmp_path, monkeypatch):
    from types import SimpleNamespace
    monkeypatch.setattr(bl, 'RUNS', tmp_path)
    monkeypatch.setattr(bl, 'validate_freeze', lambda *args, **kwargs: None)
    orphan=tmp_path/'dev/no_tool/devA01/interrupted/events.jsonl'
    orphan.parent.mkdir(parents=True);orphan.write_text('{}\n')
    monkeypatch.setattr(bl, 'run_one', lambda *args: pytest.fail('Cannot repeat an unaccounted attempt'))
    with pytest.raises(SystemExit, match='Unindexed interrupted'):
        bl.cmd_run(SimpleNamespace(arm='no_tool',dev=True,task='A',limit=1,execute=True,max_requests=1))
