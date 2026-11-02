"""Six-case integration and independent active-device checks; no API or USB."""
from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path

import numpy as np
import pytest
from scipy.optimize import root

from benchmate.agent import ToolRejected, drive_agent
from benchmate.netlist_diagnosis.cases import CATALOGUE as PASSIVE_CASES, mock_review
from benchmate.netlist_diagnosis.controller import ScriptedController
from benchmate.netlist_diagnosis.design import digest, CONFIRMATION
from benchmate.netlist_diagnosis.menu import MENU, RESERVED, template
from benchmate.netlist_diagnosis.models import validate_capture
from benchmate.netlist_diagnosis_v2 import led
from benchmate.netlist_diagnosis_v2.bench import LEDMockBench
from benchmate.netlist_diagnosis_v2.cases import CATALOGUE, LED_CASE, reviewed
from benchmate.netlist_diagnosis_v2.protocol import prepare, source_hashes
from benchmate.netlist_diagnosis_v2.session import Session

ROOT = Path(__file__).resolve().parents[1]


class Log:
    def __init__(self): self.events = []
    def add(self, kind, value): self.events.append((kind, deepcopy(value)))


@pytest.fixture(autouse=True)
def disable_external_execution(monkeypatch):
    import serial
    import benchmate.providers as providers
    def denied(*a, **kw): pytest.fail('Actual hardware or paid provider access is forbidden in this test.')
    monkeypatch.setattr(serial, 'Serial', denied)
    monkeypatch.setattr(providers, 'MetaToolSession', denied)


def independent_dc(vin, *, rb, beta=290., vf=2., load=None):
    """Ebers–Moll and diode equations, solved independently of SPICE."""
    vt = 8.617333262145e-5 * 300.15
    is_led = .001/np.expm1(vf/(2*vt))
    bias = 10000. if load is None else 1/(1/10000.+1/load)
    def equations(x):
        vb, vc, log_current = x
        current = np.exp(log_current)
        forward = 1e-14*np.expm1(vb/vt)
        reverse = 1e-14*np.expm1((vb-vc)/vt)
        return [((vin-vb)/rb-forward/beta-reverse/3)*1000,
                (forward-reverse-reverse/3-current-(1.646-vc)/(47000.+bias))*1000,
                5-current*1000-vc-current*2-2*vt*np.log1p(current/is_led)]
    initial = [.68, .08, math.log(.0029)] if rb < 1e5 else [.6, 2.9, math.log(.0002)]
    result = root(equations, initial)
    assert result.success and max(abs(np.asarray(equations(result.x)))) < 1e-6
    vb, vc, log_i = result.x
    out = (bias*vc+47000.*1.646)/(47000.+bias)
    return {'output_v': out, 'collector_v': vc, 'LED_current_a': math.exp(log_i)}


@pytest.mark.parametrize('rbase', [4700., 1e6])
@pytest.mark.parametrize('loaded', [False, True])
def test_active_spice_matches_independent_ebers_moll(rbase, loaded):
    settings = MENU['loaded_step_small' if loaded else 'unloaded_step_small']
    inp = template(settings)
    result = led.simulate(led.model(rbase=rbase, beta=290.), inp)
    # Samples comfortably before and after the step; the model is memoryless.
    for i in (20, 300):
        vin = 1.646+inp['data']['input_relative_origin_v'][i]
        expected = independent_dc(vin, rb=rbase, load=settings['load_ohm'])
        assert result['predicted_output_minus_ref_v'][i]+1.646 == pytest.approx(expected['output_v'], abs=2e-6)
        assert result['predicted_collector_v'][i] == pytest.approx(expected['collector_v'], abs=1e-5)
    assert not result['device_parameters_characterized']


def test_declared_attenuation_keeps_normal_and_fault_outputs_in_old_window():
    for beta in [200., 450.]:
        for vf in [1.7, 2.3]:
            for rb in [4700., 1e6]:
                result = led.simulate(led.model(rbase=rb, beta=beta, vf=vf), template(MENU['unloaded_sine_1hz_large']))
                lo, hi = result['measured_output_range_v']
                assert 1.0 < lo <= hi < 2.7
                assert max(abs(lo-1.646), abs(hi-1.646)) < .95
                assert result['peak_supply_current_a'] < .005
                assert result['peak_input_current_a'] < .003
    assert led.HARNESS['old_firmware_range_expansion_required'] is False
    assert led.HARNESS['required_connections'] == ['IN', 'OUT', 'REF', '5V', 'GND']


def test_gain_and_base_resistance_counterexample_is_indistinguishable_on_common_menu():
    high_r = led.model(rbase=1e6, beta=290.)
    weak_q = led.model(rbase=4700., beta=1.363)
    for settings in [*MENU.values(), *RESERVED]:
        inp = template(settings)
        a, b = np.asarray(led.predict(high_r, inp)), np.asarray(led.predict(weak_q, inp))
        assert np.max(abs(a-b)) < .001


@pytest.fixture(scope='module')
def active_session():
    log = Log(); bench = LEDMockBench(LED_CASE['software_truth'], log)
    def publish(frozen, sha):
        assert bench.count == 3 and frozen['verification_OUT_samples_used'] == 0
        assert digest(frozen) == sha
        return {'sha256': sha, 'published': True, 'remote': False}
    s = Session(bench, log, reviewed(LED_CASE), publish, actor='scripted_controller')
    controller = ScriptedController()
    result = drive_agent(s, controller)
    return s, bench, log, result


def test_sixth_case_uses_same_agent_menu_and_preserves_real_ambiguity(active_session):
    s, bench, log, result = active_session
    assert len(CATALOGUE) == 6
    assert result['agent_report']['verdict'] == 'indistinguishable'
    assert result['agent_report']['components'] == ['Q1', 'Rbase']
    assert result['selected_actions'] == ScriptedController().actions
    assert not result['llm_used'] and not result['active_hardware_qualified']
    assert all(e['purpose'] in ('training', 'verification') for k, e in log.events if k == 'netlist_observation')
    assert bench.count == 5


def test_active_holdout_is_published_before_capture_and_never_refitted(active_session):
    s, bench, log, result = active_session
    names = [k for k, _ in log.events]
    first = next(i for i, (k, v) in enumerate(log.events) if k == 'netlist_observation' and v['purpose'] == 'verification')
    assert names.index('verification_forecast_frozen') < names.index('verification_publication') < first
    assert digest(s.frozen) == s.verification['frozen_sha256']
    assert s.verification['refitted'] is False
    assert all(r['verification_outputs_used'] == 0 for r in s.frozen['models'])
    with pytest.raises(ToolRejected): s.dispatch('verify_prediction', {})


def test_agent_context_has_no_current_or_brightness_measurement_claim(active_session):
    s, bench, log, result = active_session
    context = json.dumps(s.snapshot())
    for hidden in ['mean_LED_current_a', 'evaluator_only_active_metrics', 'dim-led', 'GLG']:
        assert hidden not in context
    assert result['optical_brightness_measured'] is False


def test_raw_collector_and_arbitrary_active_topologies_are_not_accepted():
    changed = led.model(); changed['harness']['collector_to_OUT_ohm'] = 0
    with pytest.raises(ValueError): led.predict(changed, template(MENU['unloaded_step_small']))
    parts = deepcopy(led.PARTS); parts[-1]['nodes'] = ['COL', 'BASE', 'REF']
    with pytest.raises(ValueError): led.review(source_sha256='a'*64, confirmation=CONFIRMATION, note='Test.', parts=parts)


def test_absolute_dc_is_preserved_and_output_hold_subtraction_is_rejected():
    log = Log(); b = LEDMockBench(LED_CASE['software_repaired'], log, noise_sd_v=0)
    c = b.acquire(MENU['unloaded_step_small'], 'training')
    validate_capture(c)
    assert np.mean(c['output_minus_ref_v']) < -.2  # Subtracting an output HOLD would erase this information.
    s = Session(b, log, reviewed(LED_CASE), lambda f, h: {}, actor='scripted_controller')
    original = b.acquire
    def wrong_origin(settings, role):
        capture = original(settings, role); capture['reference_method'] = 'separate_output_HOLD_origin'
        return capture
    b.acquire = wrong_origin
    s.dispatch('inspect_experiment', {})
    with pytest.raises(ValueError): s.dispatch('measure', {'action': 'unloaded_step_small', 'reason': 'Check DC provenance.'})
    assert s.fatal


def test_unqualified_active_hardware_is_disabled_even_with_a_reviewed_design():
    class Physical:
        source = 'physical'
    design = led.review(source_sha256='a'*64, confirmation=CONFIRMATION, note='Test-only assertion.', simulated=False)
    with pytest.raises(ValueError): Session(Physical(), Log(), design, lambda f, h: {}, actor='muse_spark')
    p = prepare(design)
    assert not p['execution_authorized'] and not p['physical_LED_qualified']


def test_all_v1_runtime_sources_remain_exactly_frozen():
    old = json.loads((ROOT/'examples/netlist-diagnosis/2026-11-02/summary.json').read_text())['source_sha256']
    assert len(old) == 66
    for name, sha in old.items():
        assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest() == sha, name
    current = source_hashes()
    assert set(old) < set(current)


def test_incomplete_candidate_fitting_cannot_create_a_unique_diagnosis():
    log = Log(); b = LEDMockBench(LED_CASE['software_truth'], log)
    s = Session(b, log, reviewed(LED_CASE), lambda f, h: {}, actor='scripted_controller')
    s.dispatch('inspect_experiment', {})
    s.assessment = {'hypotheses': [{'id': 'changed:Rbase', 'status': 'adequate', 'model': led.model(rbase=1e6)}],
                    'all_inadequate': False, 'fitting_complete': False}
    assert s.snapshot()['verification_available'] is False
    with pytest.raises(ToolRejected): s.dispatch('verify_prediction', {})
    assert s.outcome()['verdict'] == 'abstained'


def test_optimizer_failure_is_not_a_failed_component_hypothesis(monkeypatch):
    from types import SimpleNamespace
    log = Log(); b = LEDMockBench(LED_CASE['software_repaired'], log)
    capture = b.acquire(MENU['unloaded_step_small'], 'training')
    def failed(fun, x0, **kw):
        return SimpleNamespace(x=x0, success=False, jac=np.zeros((512, len(x0))))
    monkeypatch.setattr(led, 'least_squares', failed)
    result = led.Fitter().fit([capture])
    assert result['status'] == 'fit_error'
    assert 'did not converge' in result['error']
