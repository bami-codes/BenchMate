"""Source semantics, free input, uncertainty, dimensional checks and abstention."""
from copy import deepcopy
import json
from pathlib import Path

import pytest

from benchmate.reading_rules import make_forecast, score_reading, validate_forecast

ROOT = Path(__file__).resolve().parents[1]


def rules():
    return json.loads((ROOT/'docs/2026-11-03-reading-rules.json').read_text())


def catalog():
    return {'components': {'R1': {'kind': 'R', 'value': 4700.}}, 'explanations': [
        {'id': 'changed:R1', 'components': {'R1': {'electrical_interval': [23900., 26400.],
          'printed_nominal': None, 'interval_rule': {'training_only': True}}}},
        {'id': 'external_equivalent:changed:R1', 'components': {'R1': {
          'electrical_interval': [4465., 4935.], 'printed_nominal': 4700.,
          'interval_rule': {'unchanged_design_tolerance': .05}}}}]}


def forecast():
    return make_forecast({'component': 'R1', 'quantity': 'resistance', 'reason': 'Separate actual R1 from total series path.',
                          'chosen_by': 'muse_spark'}, catalog(), rules())


def observation(value=4.71, **changes):
    return {'component': 'R1', 'quantity': 'resistance', 'value': value, 'unit': 'kohm', 'source': 'operator_dmm',
        'photo': {'file': 'evidence.png', 'sha256': 'a'*64}, 'power_off_confirmed': True,
        'component_isolated_confirmed': True, 'meter_range': 20000., 'meter_resolution': 10., **changes}


def test_isolated_reading_can_resolve_location_but_marking_cannot():
    f = forecast()
    assert score_reading(f, observation())['fits'] == ['external_equivalent:changed:R1']
    marked = observation(4.7, source='operator_marking', meter_range=None, meter_resolution=None,
                         power_off_confirmed=False, component_isolated_confirmed=False)
    assert score_reading(f, marked)['outcome'] == 'indistinguishable'
    assert len(score_reading(f, marked)['fits']) == 2


@pytest.mark.parametrize('value,expected', [(25., ['changed:R1']), (40., []), (.1, [])])
def test_free_values_are_not_answer_choices(value, expected):
    assert score_reading(forecast(), observation(value, meter_range=200000., meter_resolution=100.))['fits'] == expected


def test_actual_value_hypothesis_retains_arbitrary_markings():
    obs = observation(1000., source='operator_marking', meter_range=None, meter_resolution=None)
    assert score_reading(forecast(), obs)['fits'] == ['changed:R1']


def test_overlapping_intervals_do_not_force_winner():
    c = catalog(); c['explanations'][0]['components']['R1']['electrical_interval'] = [4000., 6000.]
    f = make_forecast(forecast()['request'], c, rules())
    assert score_reading(f, observation())['outcome'] == 'indistinguishable'


@pytest.mark.parametrize('changes', [
    {'value': float('nan')}, {'value': float('inf')}, {'value': -1}, {'value': True},
    {'component': 'R2'}, {'quantity': 'capacitance'}, {'unit': 'uF'}, {'source': 'spark_vision'},
    {'power_off_confirmed': False}, {'component_isolated_confirmed': False},
    {'meter_range': 20.}, {'meter_range': 2000.}, {'meter_resolution': 100.},
    {'value': 4.711}, {'meter_resolution': None},
])
def test_invalid_or_unqualified_readings_rejected(changes):
    with pytest.raises(ValueError):
        score_reading(forecast(), observation(**changes))


def test_observation_cannot_supply_explanation_or_change_bounds():
    o = observation(); o['explanation'] = 'external'
    with pytest.raises(ValueError):
        score_reading(forecast(), o)
    f = forecast(); f['photo_received'] = True
    with pytest.raises(ValueError):
        validate_forecast(f)


def test_all_explanation_sources_have_own_frozen_rules():
    f = forecast()
    assert len(f['forecasts']) == 4
    actual = next(x for x in f['forecasts'] if x['source'] == 'operator_dmm')
    assert len(actual['rule']['intervals_by_meter_range']) == 4
    assert actual['rule']['confidence_interval'] is False
    assert rules()['dmm']['F']['available'] is False
