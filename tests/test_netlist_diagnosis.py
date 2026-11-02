"""Offline numerical and protocol checks. Never access a model API or serial."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import math

import numpy as np
import pytest

from benchmate.agent import ToolRejected
from benchmate.netlist_diagnosis.bench import MockBench, GuardedCallbackBench
from benchmate.netlist_diagnosis.cases import CATALOGUE, mock_review, part, specimen
from benchmate.netlist_diagnosis.design import review, checked, digest, CONFIRMATION
from benchmate.netlist_diagnosis.menu import MENU, RESERVED, template
from benchmate.netlist_diagnosis.models import assess, validate_capture
from benchmate.netlist_diagnosis.session import DiagnosisSession
from benchmate.netlist_diagnosis.simulation import simulate

ROOT = Path(__file__).resolve().parents[1]


class Log:
    def __init__(self): self.events = []
    def add(self, kind, value): self.events.append((kind, deepcopy(value)))


def analytic(settings, *, resistance=10000., capacitance=1e-6):
    """Independent linear recurrence; no SPICE output enters this oracle."""
    inp = template(settings, source='mock_adc_input_only')
    d, s = inp['data'], inp['settings']
    t = np.asarray(d['frame_time_s'])
    u = np.asarray(d['input_relative_origin_v'])
    load = settings['load_ohm']
    g = 1. if load is None else load/(load+resistance)
    tau = resistance*capacitance*g
    dt = s['period_us']*1e-6
    if s['kind'] == 'step':
        rel = t+105e-6-s['step_index']*dt
        a = settings['amplitude_v']
        y = np.where(rel < 0, -a*g, a*g-2*a*g*np.exp(-np.maximum(rel, 0)/tau))
    else:
        alpha = math.exp(-dt/tau)
        delay = math.exp(-105e-6/tau)
        cycle = round(1/(s['frequency_hz']*dt))
        # Explicitly settle a separate discrete-time reference implementation.
        state = 0.
        for x in np.tile(u[:cycle], 40):
            state = alpha*state+(1-alpha)*g*x
        y = []
        for x in u:
            y.append(delay*state+(1-delay)*g*x)
            state = alpha*state+(1-alpha)*g*x
        y = np.asarray(y)
    return {'source': 'mock', 'purpose': 'training', 'voltage_basis': 'REF_relative_v1',
            'all_guards_passed': True, 'fresh_measurement': True, 'settings': deepcopy(settings),
            'input_template': inp, 'output_minus_ref_v': y.tolist(),
            'boot_id': 'analytic-boot', 'reference_id': 'analytic-zero-ref'}


class AnalyticBench:
    source = 'mock'
    def __init__(self, *, corrupt_reserved=False):
        self.count = 0; self.freeze = None; self.corrupt = corrupt_reserved
    def bind_forecast(self, sha): self.freeze = sha
    def acquire(self, settings, role):
        assert role != 'verification' or self.freeze
        self.count += 1
        r = 40000. if role == 'verification' and self.corrupt else 20000.
        c = analytic(settings, resistance=r)
        c['purpose'] = role
        return c
    def metadata(self): return {'source': 'mock', 'physical_measurements': 0, 'acquisitions': self.count}


@pytest.fixture(autouse=True)
def no_external_execution(monkeypatch):
    import serial
    import benchmate.providers as providers
    def denied(*args, **kwargs): pytest.fail('Unexpected hardware or paid model call.')
    monkeypatch.setattr(serial, 'Serial', denied)
    monkeypatch.setattr(providers, 'MetaToolSession', denied)


def session(bench=None, publication=None):
    log = Log()
    bench = bench or AnalyticBench()
    publish = publication or (lambda f, sha: {'sha256': sha, 'published': True, 'remote': False})
    s = DiagnosisSession(bench, log, mock_review(CATALOGUE[0]), publish, actor='scripted_controller')
    return s, bench, log


def measured(s):
    s.dispatch('inspect_experiment', {})
    for action in ['unloaded_step_small', 'loaded_step_small']:
        s.dispatch('measure', {'action': action, 'reason': 'Independent numerical protocol check.'})


def test_independent_analytic_truth_identifies_r_without_fitting_reserved_output():
    design = [part('R1', 'R', 'IN', 'OUT', 10000), part('C1', 'C', 'OUT', 'REF', 1e-6)]
    training = [analytic(MENU[k], resistance=20000) for k in ['unloaded_step_small', 'loaded_step_small']]
    result = assess(design, training)
    assert result['fitting_complete']
    assert [r['id'] for r in result['hypotheses'] if r['status'] == 'adequate'] == ['changed:R1']
    fitted = next(r for r in result['hypotheses'] if r['id'] == 'changed:R1')
    assert fitted['fitted_parameters']['R1'] == pytest.approx(20000., rel=.002)
    assert fitted['verification_outputs_used'] == 0


def test_all_actions_are_available_first_and_selected_order_is_not_overridden():
    s, b, log = session()
    with pytest.raises(ToolRejected): s.dispatch('measure', {'action': 'loaded_step_small', 'reason': 'Check.'})
    snap = s.dispatch('inspect_experiment', {})
    assert set(snap['allowed_measurements']) == set(MENU)
    s.dispatch('measure', {'action': 'loaded_step_small', 'reason': 'Choose the loaded action first.'})
    assert s.actions == ['loaded_step_small'] and b.count == 1
    assert log.events[-3][0] == 'training_forecasts_frozen'


def test_freeze_and_publication_precede_reserved_capture_and_reporting_is_gated():
    s, b, log = session()
    measured(s)
    with pytest.raises(ToolRejected):
        s.dispatch('finish_report', {'verdict': 'changed', 'components': ['R1'], 'explanation': 'x', 'limits': 'x'})
    before = deepcopy(s.assessment)
    s.dispatch('verify_prediction', {})
    assert s.assessment == before
    assert s.outcome() == {'verdict': 'changed', 'components': ['R1']}
    assert s.verification['refitted'] is False
    assert digest(s.frozen) == s.receipt['sha256'] == b.freeze
    names = [k for k, _ in log.events]
    observations = [i for i, (k, v) in enumerate(log.events) if k == 'netlist_observation' and v['purpose'] == 'verification']
    assert names.index('verification_forecast_frozen') < names.index('verification_publication') < observations[0]
    assert s.frozen['verification_OUT_samples_used'] == 0
    for name, args in [('measure', {'action': 'unloaded_step_small', 'reason': 'Refit.'}), ('verify_prediction', {})]:
        with pytest.raises(ToolRejected): s.dispatch(name, args)
    s.dispatch('finish_report', {'verdict': 'changed', 'components': ['R1'], 'explanation': 'A conditional R-path mismatch.', 'limits': 'No physical localization.'})


def test_failed_reserved_check_does_not_refit_or_turn_into_success():
    s, b, log = session(AnalyticBench(corrupt_reserved=True))
    measured(s); before = deepcopy(s.assessment)
    s.dispatch('verify_prediction', {})
    assert s.outcome() == {'verdict': 'abstained', 'components': []}
    assert before == s.assessment
    with pytest.raises(ToolRejected): s.dispatch('verify_prediction', {})


def test_publication_failure_stops_before_any_reserved_acquisition():
    s, b, log = session(publication=lambda f, sha: {'sha256': '0'*64, 'published': True})
    measured(s)
    with pytest.raises(ValueError): s.dispatch('verify_prediction', {})
    assert s.fatal and b.count == 2 and b.freeze is None
    with pytest.raises(ToolRejected): s.dispatch('verify_prediction', {})


def test_reserved_observation_cannot_enter_fit_and_bad_provenance_is_rejected():
    c = analytic(MENU['unloaded_step_small'])
    c['purpose'] = 'verification'
    with pytest.raises(ValueError): assess(CATALOGUE[0]['design'], [c])
    for field, bad in [('source', 'synthetic'), ('fresh_measurement', False), ('all_guards_passed', False)]:
        c = analytic(MENU['unloaded_step_small']); c[field] = bad
        with pytest.raises(ValueError): validate_capture(c)


def test_simulator_budget_exhaustion_is_not_evidence_of_a_missing_structure():
    result = assess(CATALOGUE[0]['design'], [analytic(MENU['unloaded_step_small'])], max_calls=1)
    assert not result['fitting_complete'] and not result['all_inadequate']
    assert any(r['status'] == 'fit_error' for r in result['hypotheses'])


def test_input_bypass_value_cannot_be_inferred_from_conditioned_output():
    case = CATALOGUE[1]
    design = deepcopy(case['design'])
    design[2]['a'] = 'IN'  # A separate input-bypass example, not the catalogue's parallel output capacitors.
    inp = template(MENU['unloaded_step_small'])
    a = simulate(design, inp)
    changed = deepcopy(design); changed[2]['value'] = 1e-9
    b = simulate(changed, inp)
    assert a['predicted_output_minus_ref_v'] == b['predicted_output_minus_ref_v']
    assert a['unobservable_input_branches'] == ['Cbypass']
    assert a['conditional_source_current_is_not_total_DUT_current']


def test_series_resistor_location_is_exactly_ambiguous_even_with_load():
    design = CATALOGUE[2]['design']
    a, b = deepcopy(design), deepcopy(design)
    a[0]['value'] = 2200.; b[1]['value'] = 2200.
    for action in ['unloaded_step_small', 'loaded_step_small']:
        inp = template(MENU[action])
        ya = simulate(a, inp)['predicted_output_minus_ref_v']
        yb = simulate(b, inp)['predicted_output_minus_ref_v']
        assert np.max(abs(np.asarray(ya)-yb)) < 1e-7


def test_jumper_design_is_not_silently_replaced_by_a_fake_series_resistor():
    case = CATALOGUE[4]
    inp = template(MENU['loaded_step_small'])
    result = simulate(case['design'], inp)
    assert result['simulator_invocations'] == [{'explicit_ideal_jumper': True}]
    assert set(result['unobservable_input_branches']) == {'Rload', 'Cdecouple'}
    assert np.max(abs(np.asarray(result['predicted_output_minus_ref_v'])-inp['data']['input_relative_origin_v'])) < 1e-7


def test_truth_and_case_names_are_absent_from_agent_context():
    log = Log(); case = CATALOGUE[0]
    b = MockBench(specimen(case), log)
    s = DiagnosisSession(b, log, mock_review(case), lambda f, h: {}, actor='scripted_controller')
    context = json.dumps(s.snapshot())
    for hidden in ['Rhidden', 'pin-output', 'forum.arduino', 'evaluator-truth', '20000']:
        assert hidden not in context


def test_invalid_design_and_unapproved_physical_callback_cannot_run():
    value = mock_review(CATALOGUE[0])
    value['confirmation'] = 'Looks fine'
    with pytest.raises(ValueError): checked(value)
    with pytest.raises(ValueError): GuardedCallbackBench(lambda *a: pytest.fail(), Log(), protocol={}, approved=False)
    value = deepcopy(CATALOGUE[0]['design']); value[0]['kind'] = 'Q'
    with pytest.raises(ValueError): review(value, source_sha256='a'*64, confirmation=CONFIRMATION, note='Test.')


def test_frozen_legacy_sources_are_byte_for_byte_preserved():
    manifest = json.loads((ROOT/'docs/2026-11-02-frozen-sources.json').read_text())
    assert len(manifest['source_sha256']) == 53
    for relative, sha in manifest['source_sha256'].items():
        assert hashlib.sha256((ROOT/relative).read_bytes()).hexdigest() == sha, relative


def physical_fixture(*, stale=False):
    from types import SimpleNamespace
    from test_physical_bench import FakeBoard
    from benchmate.netlist_diagnosis.physical import PhysicalNetlistBench, operator_report
    from benchmate.netlist_diagnosis.protocol import prepare
    case = CATALOGUE[0]
    design = review(case['design'], source_sha256='a'*64, confirmation=CONFIRMATION,
                    note='FAKE-BOARD TEST ONLY: no human or actual hardware assertion.', simulated=False)
    p = prepare(design)
    board = FakeBoard(p); log = Log()
    initial = operator_report('initial_unloaded', fixture='unloaded', design_sha256=digest(design))
    def confirm(fixture):
        board.loaded = fixture == 'output_load'
        if not stale:
            board.armed = False; board.code = 0
            board.boot = ('d' if board.boot == 'b'*32 else 'e')*32
            board.uptime = 0
        return operator_report('connect_output_load' if board.loaded else 'remove_output_load',
                               fixture=fixture, design_sha256=digest(design))
    bench = PhysicalNetlistBench(p, log, confirm, design=design, initial_report=initial,
                                previous_boot_id='a'*32, approved=True,
                                serial_factory=board.factory,
                                ports=lambda: [SimpleNamespace(vid=p['USB_identity'][0], pid=p['USB_identity'][1],
                                              serial_number=p['USB_identity'][2], device='FAKE_NOT_A_DEVICE')],
                                sleep=lambda _: None)
    return bench, board, log


def test_fake_serial_adapter_accepts_agent_chosen_load_order_and_unloaded_sine():
    b, board, log = physical_fixture()
    for name in ['unloaded_step_small', 'loaded_step_small', 'unloaded_sine_5hz_small']:
        capture = b.acquire(MENU[name], 'training')
        validate_capture(capture, role='training')
        assert capture['source'] == 'physical'
        assert capture['reference_scope'].startswith('Provisional')
    assert b.capture_attempts == 15 and b.human_interventions == 2
    assert sum(c[0] == 'ARM' for c in board.commands) == 3
    assert sum(c[0] == 'RESET' for c in board.commands) == 0


def test_fake_serial_stale_boot_stops_before_another_stimulus():
    b, board, log = physical_fixture(stale=True)
    b.acquire(MENU['unloaded_step_small'], 'training')
    before = b.capture_attempts
    with pytest.raises(ValueError): b.acquire(MENU['loaded_step_small'], 'training')
    assert b.stopped and b.capture_attempts == before
    count = len(board.commands)
    with pytest.raises(RuntimeError): b.acquire(MENU['loaded_step_small'], 'training')
    assert len(board.commands) == count


def test_physical_adapter_pauses_for_a_load_if_the_agent_selects_loaded_first():
    b, board, log = physical_fixture()
    result = b.acquire(MENU['loaded_step_small'], 'training')
    assert result['settings']['load_ohm'] == 9990.
    assert b.human_interventions == 1
    reports = [v for k, v in log.events if k == 'operator_wiring_confirmation']
    assert reports[0]['choice'] == 'connect_output_load'


def test_operator_confirmation_uses_fixed_english_choices_and_exact_design():
    from benchmate.netlist_diagnosis.physical import operator_report
    with pytest.raises(ValueError): operator_report('I did it', fixture='unloaded', design_sha256='a'*64)
    with pytest.raises(ValueError): operator_report('connect_output_load', fixture='unloaded', design_sha256='a'*64)
    report = operator_report('remove_output_load', fixture='unloaded', design_sha256='a'*64)
    assert report['USB_connected'] and report['USB_off_wiring_confirmed']
    assert report['verbatim'].startswith('USB was off;')


def test_diode_fit_against_an_independent_shockley_root_solver():
    from scipy.optimize import brentq
    from benchmate.netlist_diagnosis.models import Fitter
    r1, r2, isat, n = 4700., 22000., 3e-9, 1.9
    thermal = 8.617333262145e-5*300.15
    captures = []
    for key in ['loaded_step_small', 'unloaded_sine_1hz_large']:
        settings = MENU[key]
        inp = template(settings, source='mock_adc_input_only')
        u = np.asarray(inp['data']['input_relative_origin_v'])
        conductance = 1/r2 + (0 if settings['load_ohm'] is None else 1/settings['load_ohm'])
        def output(vin):
            def balance(vd):
                current = isat*np.expm1(vd/(n*thermal))
                vout = vd+current  # Fixed 1 ohm diode series resistance.
                return (vin-vout)/r1-conductance*vout-current
            vd = brentq(balance, min(vin, 0)-.001, max(vin, 0)+.001, xtol=1e-14)
            return vd+isat*np.expm1(vd/(n*thermal))
        captures.append({'source': 'mock', 'purpose': 'training', 'voltage_basis': 'REF_relative_v1',
                         'all_guards_passed': True, 'fresh_measurement': True, 'settings': deepcopy(settings),
                         'input_template': inp, 'output_minus_ref_v': [output(v) for v in u],
                         'boot_id': 'analytic-diode', 'reference_id': 'known-zero'})
    value = deepcopy(CATALOGUE[3]['design']) + [part('Dextra', 'D', 'OUT', 'REF')]
    result = Fitter(max_calls=240).fit(value, captures, hypothesis_id='proposal:1', fit_diode=True)
    assert result['status'] == 'adequate'
    assert result['fitted_parameters']['diode_N'] == pytest.approx(n, rel=.02)
    assert result['fitted_parameters']['diode_IS'] == pytest.approx(isat, rel=.1)
    assert result['verification_outputs_used'] == 0
