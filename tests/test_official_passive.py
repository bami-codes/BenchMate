"""Official metadata and permission boundaries, with no provider/serial calls."""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from benchmate import official_passive as official
from benchmate.netlist_diagnosis.design import digest
from benchmate.netlist_diagnosis.physical import operator_report
from benchmate.providers import MetaToolSession, ProviderError
from benchmate.records import Recorder, decode_events

ROOT = Path(__file__).resolve().parents[1]
DESIGN = ROOT / 'examples/reviewed-designs/2026-11-03-pilot/design-01.json'


def runner():
    spec = importlib.util.spec_from_file_location('official_runner_test', ROOT / 'scripts/official_passive.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_protocol_is_official_and_preserves_original_limits():
    p = official.prepare(json.loads(DESIGN.read_text()))
    assert p['official'] and not p['pilot'] and not p['excluded_from_evaluation']
    assert not p['k_correction'] and p['calibration_is_new'] is False
    assert p['api_plan']['requests_max'] == 8
    assert p['diagnosis_policy']['allowance_mV'] == 9
    assert p['configuration']['stable_delta_counts'] == 20
    assert p['instrument']['driver_series_ohm'] == 1000
    assert p['ADC_roles']['A3'].startswith('REF')
    assert 'PHYSICAL OFFICIAL' in p['api_plan']['prompt']
    assert 'PHYSICAL PASSIVE PILOT' not in p['api_plan']['prompt']
    assert len(official.preserved_sources()) == 76


def test_new_physical_session_never_relabels_a_mock(tmp_path):
    with pytest.raises(ValueError, match='relabel a mock'):
        official.Session(SimpleNamespace(source='mock'), Recorder(tmp_path, mode='test'),
                         json.loads(DESIGN.read_text()), lambda f, s: {})


def test_model_context_has_no_slot_truth_photo_or_prior_results(tmp_path):
    s = official.Session(SimpleNamespace(source='physical'), Recorder(tmp_path, mode='test'),
                         json.loads(DESIGN.read_text()), lambda f, s: {})
    view = s.snapshot()
    assert view['official'] and not view['pilot']
    assert view['photos_received'] is False and view['assembly_truth_received'] is False
    assert view['allowed_measurements'] == list(official.V2Session.snapshot(s)['allowed_measurements'])
    context = json.dumps(view)
    for hidden in ('slot_id', 'case_id', '01-F01', 'Rextra', '1098926', 'specimen_truth'):
        assert hidden not in context


def test_known_instrument_only_applies_to_command_forecast(monkeypatch):
    seen = []
    monkeypatch.setattr(official, 'predict', lambda model, inp: seen.append(deepcopy(model)) or [0])
    s = official.Session.__new__(official.Session)
    s.active = False
    model = {'elements': json.loads(DESIGN.read_text())['elements']}
    assert s._predict(model, {'source': 'command_input_only'}) == [0]
    assert len(seen[-1]['elements']) == len(model['elements']) + 1
    assert s._predict(model, {'source': 'physical_input_only'}) == [0]
    assert seen[-1] == model


def test_extra_allowance_stops_before_parent_transport(tmp_path, monkeypatch):
    path = tmp_path / 'budget.json'
    path.write_text(json.dumps({'authorized_by_operator': True, 'authorized_request_limit': 16,
                                'reserved_usd': {'meta': 16}}))
    model = official.OfficialModel.__new__(official.OfficialModel)
    model.budget_path = path
    def denied(self):
        pytest.fail('Request transport reached after allowance exhausted')
    monkeypatch.setattr(MetaToolSession, 'next_call', denied)
    with pytest.raises(ProviderError, match='allowance exhausted'):
        model.next_call()


def test_unconfirmed_assembly_stops_before_any_port_or_model_access(tmp_path, monkeypatch):
    m = runner()
    design = json.loads(DESIGN.read_text())
    initial = operator_report('initial_unloaded', fixture='unloaded', design_sha256=digest(design))
    assembly = {'schema': 'benchmate.operator_assembly_record.v1', 'operator_confirmed': False}
    def denied(*a, **k):
        pytest.fail('External access occurred before assembly validation')
    monkeypatch.setattr(m.list_ports, 'comports', denied)
    monkeypatch.setattr(m, 'OfficialModel', denied)
    with pytest.raises(ValueError, match='assembly'):
        m.validate_assembly(design, initial, assembly)


def test_no_primary_replacement_and_sequential_slot_requirement(tmp_path, monkeypatch):
    m = runner()
    policy = json.loads((ROOT / official.POLICY_FILE).read_text())
    monkeypatch.setattr(m, 'ROOT', tmp_path)
    index = m.index_for(policy)
    assert index['slots'][0]['slot_id'] == '01-F01'
    assert index['slots'][1]['slot_id'] == '01-R01'
    assert all(s['run_id'] is None for s in index['slots'])
    m.save(tmp_path / m.INDEX, index)
    index['selection_policy_sha256'] = 'f' * 64
    m.save(tmp_path / m.INDEX, index)
    with pytest.raises(ValueError, match='selection policy changed'):
        m.index_for(policy)


def test_registration_reopen_rejects_terminal_record(tmp_path):
    m = runner()
    log = Recorder(tmp_path, mode='test')
    log.add('official_protocol_frozen', {})
    resumed = m.reopen(log.path)
    resumed.add('run_failed', {'error': 'TEST ONLY'})
    events = decode_events(resumed.file.read_bytes(), include_hash=True)
    assert len(events) == 3 and events[-1]['kind'] == 'run_failed'
    with pytest.raises(ValueError, match='already started'):
        m.reopen(log.path)


def test_initial_loaded_intervention_compares_against_observed_preflight():
    calls = []
    b = official.Bench.__new__(official.Bench)
    b.fixture = None
    b.boot_id = '1' * 32
    b.preflight_boot = '2' * 32
    b.expect_preflight_boot = True
    b.log = SimpleNamespace(add=lambda *v: calls.append(v))
    b.confirm_external = lambda fixture: {'confirmed': fixture}
    assert b._confirm('output_load') == {'confirmed': 'output_load'}
    assert b.boot_id == '2' * 32 and not b.expect_preflight_boot
    assert calls[0][0] == 'preflight_boot_bound_before_initial_intervention'


def test_initial_unloaded_ping_must_match_preflight(monkeypatch):
    monkeypatch.setattr(official.PhysicalNetlistBench, '_ping', lambda *a: None)
    b = official.Bench.__new__(official.Bench)
    b.preflight_boot = '2' * 32
    b.expect_preflight_boot = True
    with pytest.raises(ValueError, match='changed since the preflight'):
        b._ping(None, SimpleNamespace(boot_id='3' * 32), 'initial', False)
    b._ping(None, SimpleNamespace(boot_id='2' * 32), 'initial', False)
    assert b.expect_preflight_boot is False
