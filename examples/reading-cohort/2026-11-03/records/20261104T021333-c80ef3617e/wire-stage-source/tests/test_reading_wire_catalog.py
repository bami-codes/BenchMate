from copy import deepcopy

import pytest

from benchmate.reading_wire_catalog import extend, series_part
from benchmate.reading_rules import make_forecast, score_reading


def setup_models():
    branches = [dict(name='R1', kind='R', a='OUT', b='REF', value=10000., model='none'),
                dict(name='C1', kind='C', a='OUT', b='REF', value=1e-6, model='none')]
    design = {'elements': branches + [dict(name='W1', kind='W', a='IN', b='OUT', value=0., model='none')]}
    model = {'elements': branches + [dict(name='Rx', kind='R', a='IN', b='OUT', value=20000., model='none')]}
    return design, model


def test_only_literal_series_replacement_with_unchanged_branches_is_eligible():
    design, model = setup_models()
    assert series_part(design, model) == 'Rx'
    other = deepcopy(model)
    other['elements'][0]['value'] = 11000.
    assert series_part(design, other) is None
    other = deepcopy(model)
    other['elements'][-1]['b'] = 'REF'
    assert series_part(design, other) is None


def test_reserved_capture_is_rejected_before_interval_generation():
    design, model = setup_models()
    with pytest.raises(ValueError, match='Only training'):
        extend({}, design, {'models': []}, {'survivors': ['proposal:1']}, [{'purpose': 'verification'}])


def test_wire_reading_can_select_either_placement_or_reject_both():
    from benchmate.netlist_diagnosis.bench import MockBench
    from benchmate.netlist_diagnosis.menu import MENU
    from benchmate.reading_catalog import build_catalog
    import json
    from pathlib import Path
    design, model = setup_models()
    b = MockBench(model['elements'], None, noise_sd_v=0.)
    captures = [b.acquire(MENU['unloaded_step_large'], 'training')]
    row = {'id': 'proposal:1', 'changed_component': None, 'model': model}
    frozen = {'models': [row]}
    verification = {'survivors': ['proposal:1'], 'frozen_sha256': 'a' * 64}
    catalog = build_catalog(design, frozen, verification, captures)
    c = extend(catalog, design, frozen, verification, captures)
    assert design['elements'][-1]['kind'] == 'W'
    assert c['components']['W1']['physical_kind'] == 'W'
    assert c['reserved_OUT_used_for_intervals'] == 0
    rules = json.loads((Path(__file__).parents[1] / 'docs/2026-11-03-reading-rules.json').read_text())
    request = {'component': 'W1', 'quantity': 'resistance', 'reason': 'Separate path location.', 'chosen_by': 'muse_spark'}
    forecast = make_forecast(request, c, rules)
    observed = {'component': 'W1', 'quantity': 'resistance', 'source': 'operator_dmm', 'unit': 'ohm',
        'photo': {'file': 'evidence.png', 'sha256': 'b' * 64},
        'power_off_confirmed': True, 'component_isolated_confirmed': True,
        'meter_range': 200000., 'meter_resolution': 100.}
    assert score_reading(forecast, {**observed, 'value': 0.})['fits'] == ['external_path:proposal:1']
    assert score_reading(forecast, {**observed, 'value': 20000.})['fits'] == ['on_board_path:proposal:1']
    assert score_reading(forecast, {**observed, 'value': 1000.})['fits'] == []
