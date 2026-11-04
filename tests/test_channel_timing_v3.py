from copy import deepcopy
import numpy as np
import pytest

from benchmate import channel_timing_v3 as timing
from benchmate.netlist_diagnosis.models import predict as old_predict, score
from benchmate.netlist_diagnosis.menu import RESERVED, template
from scripts.timing_synthetic_v3 import analytic_capture, specimens


def test_independent_direct_cap_truth_exposes_skew_and_new_rule_handles_it():
    _, r, rl, c, elements = specimens()[0]
    capture = analytic_capture(RESERVED[0], r, rl, c)
    model = {'elements': elements}
    old = score(capture, old_predict(model, capture['input_template']))
    result = timing.simulate(elements, capture['input_template'])
    new = score(capture, result['predicted_output_minus_ref_v'])
    assert not old['passed'] and new['passed']
    assert result['scored_output_samples_used'] == 0
    assert result['fitted_timing_parameters'] == []


def test_frame_held_source_is_a_negative_control_not_hidden_by_a_pass_claim():
    _, r, rl, c, elements = specimens()[1]
    capture = analytic_capture(RESERVED[0], r, rl, c)
    old = score(capture, old_predict({'elements': elements}, capture['input_template']))
    new = score(capture, timing.predict({'elements': elements}, capture['input_template']))
    # A generic FOH cannot promise to preserve a real DAC step between sparse
    # observations. Keep this counterexample as a deployment qualification gate.
    assert old['passed']
    assert not new['passed']


def test_command_forecast_remains_exactly_the_existing_held_DAC_model():
    elements = specimens()[1][-1]; command = template(RESERVED[0])
    assert timing.predict({'elements': elements}, command) == old_predict({'elements': elements}, command)


@pytest.mark.parametrize('field', ['output_minus_ref_v', 'fitted_delay_s', 'fitted_gain'])
def test_input_boundary_rejects_out_and_tuning_fields(field):
    inp = template(RESERVED[0], source='mock_adc_input_only')
    inp['data'][field] = [0.]*512
    with pytest.raises(ValueError):timing.stimulus(inp)


def test_actual_timestamps_not_assumed_53us_are_used_and_input_is_not_mutated():
    inp = template(RESERVED[0], source='mock_adc_input_only')
    inp['data']['input_delay_s'] = [30e-6]*512
    inp['data']['output_delay_s'] = [140e-6]*512
    saved = deepcopy(inp)
    _, t, _, di, do, _, knots, _, samples, _ = timing.stimulus(inp)
    assert inp == saved
    np.testing.assert_allclose(samples, t+do)
    np.testing.assert_allclose(knots[1:-1], t+di)


def test_reserved_outputs_cannot_enter_the_reused_training_fitter():
    _, r, rl, c, elements = specimens()[0]
    capture = analytic_capture(RESERVED[0], r, rl, c)
    with pytest.raises(ValueError, match='Reserved outputs'):
        timing.assess(elements, [capture])


def test_memoryless_divider_constant_input_is_invariant():
    model = {'elements': specimens()[-1][-1]}
    inp = template(RESERVED[0], source='mock_adc_input_only')
    inp['data']['input_relative_origin_v'] = [.2]*512
    np.testing.assert_allclose(timing.predict(model, inp), old_predict(model, inp), atol=1e-8)
