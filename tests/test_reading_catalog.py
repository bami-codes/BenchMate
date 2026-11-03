"""Exercise real ngspice exact-equivalence and training-only profiles."""
from copy import deepcopy
import json
from pathlib import Path

import numpy as np
import pytest

from benchmate.netlist_diagnosis.menu import template, MENU
from benchmate.netlist_diagnosis.models import predict
from benchmate.reading_catalog import build_catalog

ROOT = Path(__file__).resolve().parents[1]


def fixture():
    d = json.loads((ROOT/'examples/reviewed-designs/2026-11-03-pilot/design-01.json').read_text())
    m = {'elements': deepcopy(d['elements'])}; m['elements'][0]['value'] = 24700.
    settings = next(v for v in MENU.values() if v['kind'] == 'step' and v['load_ohm'] is None)
    inp = template(settings); inp['source'] = 'mock_adc_input_only'
    c = dict(source='mock', voltage_basis='REF_relative_v1', purpose='training', all_guards_passed=True,
        fresh_measurement=True, settings=settings, input_template=inp, output_minus_ref_v=predict(m, inp),
        boot_id='mock', reference_id='mock-independent-ref')
    row = dict(id='changed:R1', changed_component='R1', model=m)
    return d, {'models': [row]}, {'survivors': ['changed:R1'], 'frozen_sha256': 'a'*64}, [c]


def test_equivalent_generated_without_truth_and_interval_uses_training_only():
    d, f, v, captures = fixture()
    c = build_catalog(d, f, v, captures)
    assert len(c['explanations']) == 2
    changed, external = c['explanations']
    assert changed['components']['R1']['printed_nominal'] is None
    assert external['components']['R1']['printed_nominal'] == 4700.
    assert external['equivalence']['training_max_difference_v'] < .0001
    profile = changed['components']['R1']['interval_rule']
    assert profile['reserved_OUT_used'] == 0
    assert profile['statistical_confidence_interval'] is False
    low, high = changed['components']['R1']['electrical_interval']
    assert low < 24700. < high
    assert np.max(np.abs(np.asarray(predict(changed['model'], captures[0]['input_template']))-
                         np.asarray(predict(external['model'], captures[0]['input_template'])))) < .0001


def test_reserved_capture_cannot_enter_reading_interval_fit():
    d, f, v, captures = fixture(); captures[0]['purpose'] = 'verification'
    with pytest.raises(ValueError, match='Only training'):
        build_catalog(d, f, v, captures)


def test_no_survivor_cannot_fabricate_reading_hypotheses():
    d, f, v, captures = fixture(); v['survivors'] = []
    with pytest.raises(ValueError, match='Verified'):
        build_catalog(d, f, v, captures)
