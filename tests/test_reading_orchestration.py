"""No serial/network: state gates, false attribution and immutable old sources."""
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from benchmate.records import Recorder, decode_events

ROOT = Path(__file__).resolve().parents[1]


def module():
    spec = importlib.util.spec_from_file_location('reading_experiment_test', ROOT/'scripts/reading_experiment.py')
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    return m


def pair(tmp_path, monkeypatch, phase):
    m = module(); monkeypatch.setattr(m, 'ROOT', tmp_path); monkeypatch.setattr(m, 'check_freeze', lambda: {})
    log = Recorder(tmp_path/'runs/reading-cohort', mode='synthetic_state_gate_test')
    m.state(log, phase, current_photo='faulted', requested_component='R1')
    return m, log


def test_observation_before_prediction_or_binding_rejected(tmp_path, monkeypatch):
    m, log = pair(tmp_path, monkeypatch, 'awaiting_reading_selection')
    with pytest.raises(ValueError, match='Stage unavailable'):
        m.observe(SimpleNamespace(record=log.path))
    assert len(decode_events(log.file.read_bytes(), require_terminal=False)) == 2


def test_body_override_keeps_original_proposal_and_names_operator(tmp_path, monkeypatch):
    m, log = pair(tmp_path, monkeypatch, 'awaiting_faulted_body_confirmation')
    d = log.path/'photo-faulted'; (d/'decoded').mkdir(parents=True)
    proposal = {'component': 'R1', 'sam_body': None, 'chosen_by': 'muse_spark', 'reason': 'Ambiguous.', 'operator_confirmed': False}
    m.save(d/'binding-proposal.json', proposal)
    m.save(d/'decoded/body-manifest.json', {'components': [{'id': 'sam-0', 'localizer': 'SAM-derived body mask'}]})
    m.confirm_body(SimpleNamespace(record=log.path, accept=False, operator_body='sam-0'))
    assert json.loads((d/'binding-proposal.json').read_text()) == proposal
    binding = json.loads((d/'body-binding.json').read_text())
    assert binding['chosen_by'] == 'operator' and binding['operator_confirmed'] is True
    with pytest.raises(ValueError, match='Stage unavailable'):
        m.confirm_body(SimpleNamespace(record=log.path, accept=True, operator_body=None))


def test_null_model_binding_cannot_be_confirmed_as_Spark(tmp_path, monkeypatch):
    m, log = pair(tmp_path, monkeypatch, 'awaiting_faulted_body_confirmation')
    d = log.path/'photo-faulted'; d.mkdir()
    m.save(d/'binding-proposal.json', {'sam_body': None})
    with pytest.raises(ValueError, match='Confirm the actual proposal'):
        m.confirm_body(SimpleNamespace(record=log.path, accept=True, operator_body=None))


def test_old_physical_and_photo_freezes_remain_exact():
    m = module()
    p = m.preserved.prepare(json.loads((ROOT/'examples/reviewed-designs/2026-11-03-pilot/design-01.json').read_text()))
    assert len(p['official_source_sha256']) == 87
    from benchmate.photo_v2.pipeline import check_policy
    policy = check_policy(ROOT/'examples/photo-v2/2026-11-03/frozen-v2-final/policy.json')
    assert len(policy['source_sha256']) == 13
    assert m.preserved.USB_WAIT_SECONDS == 10
