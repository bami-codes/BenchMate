"""Capacitance intake cannot bypass isolation, display resolution or role rules."""
from copy import deepcopy
import json
from pathlib import Path
import pytest

from benchmate.reading_group_experiment import METER, score


def forecast():
    return {'bodies': ['sam-2', 'sam-3'], 'meter': deepcopy(METER), 'scope': 'Test allowance only.',
            'explanations': [{'id': 'changed:C1', 'role': 'active',
                              'intervals': {'C1': [.398e-6, .593e-6], 'C2': [.088e-6, .113e-6]}},
                             {'id': 'nominal', 'role': 'reference',
                              'intervals': {'C1': [.9e-6, 1.105e-6], 'C2': [.088e-6, .113e-6]}}]}


def observation():
    return {'source': 'operator_dmm', 'power_off_confirmed': True, 'discharge_wait_confirmed': True,
            'readings': [{'body': b, 'value': v, 'unit': 'uF', 'range_F': 2e-6,
                          'resolution_F': 1e-9, 'isolated_confirmed': True}
                         for b, v in [('sam-2', .471), ('sam-3', .101)]]}


def test_actual_pair_has_conditional_mapping_and_never_uses_marking():
    result = score(forecast(), observation())
    assert result['fits'] == ['changed:C1']
    assert result['conditional_unique_binding'] == {'C1': 'sam-2', 'C2': 'sam-3'}
    assert result['source'] == 'operator_dmm' and result['new_blind_test'] is False


@pytest.mark.parametrize('key,value', [('isolated_confirmed', False), ('range_F', 20e-6),
                                     ('resolution_F', 10e-9), ('value', .4715),
                                     ('value', 2.), ('value', float('nan')), ('unit', 'kohm'),
                                     ('body', 'sam-1')])
def test_wrong_component_source_range_or_precision_stops(key, value):
    obs = observation()
    obs['readings'][0][key] = value
    with pytest.raises(ValueError):
        score(forecast(), obs)


def test_no_in_circuit_capacitance_or_duplicate_body_is_accepted():
    for key, value in [('power_off_confirmed', False), ('discharge_wait_confirmed', False), ('source', 'operator_marking')]:
        obs = observation()
        obs[key] = value
        with pytest.raises(ValueError):
            score(forecast(), obs)
    obs = observation()
    obs['readings'][1]['body'] = 'sam-2'
    with pytest.raises(ValueError):
        score(forecast(), obs)
    f = forecast()
    f['meter']['available'] = False
    with pytest.raises(ValueError):
        score(f, observation())


@pytest.fixture
def supplement(tmp_path, monkeypatch, capsys):
    from benchmate import reading_group_experiment as group
    from benchmate.records import Recorder
    if not (group.ROOT/group.PARENT/'events.jsonl').exists():
        pytest.skip('Retained parent evidence is not installed.')
    logs = []
    def recorder(*_, **kw):
        log = Recorder(tmp_path, **kw)
        logs.append(log)
        return log
    monkeypatch.setattr(group, 'Recorder', recorder)
    monkeypatch.setattr(group, 'export', lambda _: None)
    group.register()  # Local files only; no model, network or hardware.
    capsys.readouterr()
    return group, logs[0]


def test_supplement_binds_failed_parent_and_detects_changed_forecast(supplement):
    group, log = supplement
    result = group.verify(log.path)
    assert result['passed'] and result['events'] == 6
    reg = json.loads((log.path/'registration.json').read_text())
    assert result['parent_head_sha256'] == reg['parent_head_sha256']
    assert reg['parent_status_unchanged'] == 'run_failed'
    assert reg['counted_new_physical_attempt'] is False
    f = json.loads((log.path/'group-reading-forecast.json').read_text())
    f['explanations'][0]['intervals']['C1'][1] *= 2
    (log.path/'group-reading-forecast.json').write_text(json.dumps(f))
    assert group.verify(log.path)['passed'] is False


def test_publication_must_precede_values_and_complete_score_is_recomputed(supplement):
    group, log = supplement
    f = json.loads((log.path/'group-reading-forecast.json').read_text())
    log.add('reading_forecast_publication', {'commit': 'a'*40, 'remote': True,
            'file': 'group-reading-forecast.json', 'sha256': group.sha(log.path/'group-reading-forecast.json'),
            'before_new_electrical_values': True, 'before_printed_474_report': False})
    log.add('group_state', {'phase': 'awaiting_isolated_values'})
    assert group.verify(log.path)['passed']
    o = observation()
    result = group.score(f, o)
    group.save(log.path/'group-reading-observation.json', o)
    group.save(log.path/'group-reading-score.json', result)
    log.add('group_reading_observed', o)
    log.add('group_reading_scored', result)
    log.add('run_completed', {'outcome': result['outcome'], 'repair_pair_completed': False})
    assert group.verify(log.path)['passed']
    log.add('run_completed', {'outcome': result['outcome'], 'repair_pair_completed': False})
    assert group.verify(log.path)['passed'] is False


def test_values_without_publication_fail_even_with_a_valid_hash_chain(supplement):
    group, log = supplement
    log.add('group_reading_observed', observation())
    assert group.verify(log.path)['passed'] is False
