"""Independent checks of the new upstream instrument impedance."""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import sys

import numpy as np
import pytest

from benchmate.netlist_diagnosis.menu import MENU, template
from benchmate.netlist_diagnosis.models import predict
from benchmate.passive_pilot import Session, command_model, source_hashes
from benchmate.netlist_diagnosis.design import review, CONFIRMATION, digest
from benchmate.netlist_diagnosis.physical import operator_report


def e(name, kind, a, b, value):
    return dict(name=name, kind=kind, a=a, b=b, value=value, model='none')


def test_wire_case_command_includes_load_and_capacitor_not_removed_as_unobservable():
    model = {'elements': [e('W1', 'W', 'IN', 'OUT', 0.),
                           e('R1', 'R', 'OUT', 'REF', 10000.), e('C1', 'C', 'OUT', 'REF', 1e-6)]}
    original = deepcopy(model)
    inp = template(MENU['unloaded_step_large'])
    curve = np.asarray(predict(command_model(model), inp))
    # Independent continuous-time step solution: 1k source, 10k load, 1uF.
    gain = 10000/11000; tau = (1000*10000/11000)*1e-6
    t = np.asarray(inp['data']['frame_time_s'])+.000105-.0005*51
    expected = np.where(t < 0, -.5*gain, .5*gain-gain*np.exp(-np.maximum(t, 0)/tau))
    assert np.max(abs(curve-expected)) < .0001
    assert model == original
    assert curve[-1] == pytest.approx(.5*gain, abs=1e-5)


def test_loaded_wire_case_forecast_includes_both_parallel_loads():
    model = {'elements': [e('W1', 'W', 'IN', 'OUT', 0.),
                           e('R1', 'R', 'OUT', 'REF', 10000.), e('C1', 'C', 'OUT', 'REF', 1e-6)]}
    inp = template(MENU['loaded_step_small'])
    curve = predict(command_model(model), inp)
    load = 1/(1/10000+1/9990)
    assert curve[-1] == pytest.approx(.2*load/(1000+load), abs=1e-5)


def test_conditioned_measured_input_does_not_double_count_upstream_resistor():
    model = {'elements': [e('R1', 'R', 'IN', 'OUT', 4700.), e('C1', 'C', 'OUT', 'REF', 1e-6)]}
    command = template(MENU['unloaded_step_large'])
    measured = template(MENU['unloaded_step_large'], source='physical_input_only')
    s = Session.__new__(Session); s.active = False
    actual = np.asarray(s._predict(model, measured))
    ideal = np.asarray(predict(model, measured))
    upstream = np.asarray(s._predict(model, command))
    assert np.array_equal(actual, ideal)
    assert np.max(abs(upstream-actual)) > .02


def test_internal_timing_node_is_retained_and_frozen_sources_are_intact():
    model = {'elements': [e('R1', 'R', 'IN', 'N1', 10000.),
                           e('R2', 'R', 'N1', 'OUT', 10000.), e('C1', 'C', 'OUT', 'REF', 1e-6)]}
    out = command_model(model)
    assert out['elements'][0]['a'] == 'N2'
    assert out['elements'][0]['b'] == 'N1'
    assert len(source_hashes()) == 76


def runner_fixture(tmp_path):
    script = Path(__file__).resolve().parents[1]/'scripts/passive_pilot.py'
    spec = importlib.util.spec_from_file_location('pilot_runner_under_test', script)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    design = review([e('R1', 'R', 'IN', 'OUT', 4700.), e('C1', 'C', 'OUT', 'REF', 1e-6)],
        source_sha256='a'*64, confirmation=CONFIRMATION, note='TEST FIXTURE ONLY; no physical approval')
    prepared = tmp_path/'prepared'; prepared.mkdir()
    (prepared/'reviewed-design.json').write_text(json.dumps(design))
    (prepared/'protocol.json').write_text(json.dumps(module.prepare(design)))
    report = tmp_path/'report.json'; report.write_text(json.dumps(operator_report(
        'initial_unloaded', fixture='unloaded', design_sha256=digest(design))))
    return module, design, prepared, report


@pytest.mark.parametrize('invalid', ['not_confirmed', 'bypassed_isolation', 'different_design'])
def test_unconfirmed_or_mismatched_assembly_stops_before_port_or_paid_call(tmp_path, monkeypatch, invalid):
    m, design, prepared, report = runner_fixture(tmp_path)
    assembly = dict(schema='benchmate.operator_assembly_record.v1', operator_confirmed=True,
        reviewed_design_sha256=digest(design), instrument_series_ohm=1000.,
        USB_off_wiring_confirmed=True, specimen_truth=[{'test_fixture': True}])
    if invalid == 'not_confirmed': assembly['operator_confirmed'] = False
    if invalid == 'bypassed_isolation': assembly['instrument_series_ohm'] = 0.
    if invalid == 'different_design': assembly['reviewed_design_sha256'] = 'b'*64
    path = tmp_path/'assembly.json'; path.write_text(json.dumps(assembly))
    def denied(*a, **k): pytest.fail('Port or paid provider touched before assembly validation')
    monkeypatch.setattr(m.list_ports, 'comports', denied)
    monkeypatch.setattr(m, 'MetaToolSession', denied)
    monkeypatch.setattr(sys, 'argv', ['passive_pilot.py', 'run', '--prepared', str(prepared),
        '--initial-report', str(report), '--assembly-record', str(path),
        '--previous-boot-id', '1'*32, '--execute'])
    with pytest.raises(ValueError, match='assembly truth'): m.main()


def test_absent_device_probe_retains_failure_without_serial_or_stimulus(tmp_path, monkeypatch):
    m, design, prepared, report = runner_fixture(tmp_path)
    monkeypatch.setattr(m.list_ports, 'comports', lambda: [])
    def denied(*a, **k): pytest.fail('Serial opened with no matching device')
    monkeypatch.setattr(m.serial, 'Serial', denied)
    out = tmp_path/'probe'
    monkeypatch.setattr(sys, 'argv', ['passive_pilot.py', 'probe', '--prepared', str(prepared),
                                    '--execute', '--output', str(out)])
    with pytest.raises(ValueError, match='absent or ambiguous'): m.main()
    from benchmate.records import read_events
    run = next(out.iterdir())
    events = read_events(run)
    assert events[-1]['kind'] == 'run_failed'
    assert not any(x['kind'] == 'serial_command' for x in events)
