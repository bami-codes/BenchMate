"""Effective A3 profile is bound to real QA while core diagnosis stays reused."""
import importlib.util
import json
from pathlib import Path

import pytest

from benchmate.a3_ref_guard import A3GuardMixin, VERSION
from benchmate.records import Recorder

ROOT = Path(__file__).resolve().parents[1]


def module():
    spec = importlib.util.spec_from_file_location('official_A3_test', ROOT / 'scripts/official_passive_A3.py')
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    return m


def design():
    return json.loads((ROOT / 'examples/reviewed-designs/2026-11-03-pilot/design-01.json').read_text())


def test_effective_protocol_qualifies_primary_and_keeps_original_core_mapping():
    m = module(); old = m.base.prepare(design()); new = m.prepare(design())
    assert new['source_sha256'] == old['source_sha256']
    assert new['diagnosis_policy'] == old['diagnosis_policy']
    assert new['guard_version'] == VERSION and new['primary_REF_channel'] == 'A3'
    assert new['A4_role'] == 'record_and_report_only'
    assert new['guard_limits']['REF_envelope_v'] == old['guard_limits']['A4_envelope_v']
    assert len(new['official_source_sha256']) == 84
    assert new['primary_REF_qualification']['events_sha256']
    assert new['api_plan']['requests_max'] == 8


def test_qualified_profile_constructs_adapter_without_serial_or_model(tmp_path):
    m = module(); d = design(); p = m.prepare(d)
    def denied(*a, **k):
        pytest.fail('No physical access during construction test')
    log = Recorder(tmp_path, mode='test_only')
    report = m.base.operator_report('initial_unloaded', fixture='unloaded', design_sha256=m.digest(d))
    bench = m.SettledBench(p, log, denied, design=d, initial_report=report,
        previous_boot_id='1'*32, preflight_boot_id='2'*32, approved=True,
        serial_factory=denied, ports=denied, sleep=denied)
    assert bench._capture.__func__ is A3GuardMixin._capture
    session = m.Session(bench, log, d, denied)
    assert session._predict.__func__ is m.base.Session._predict
    view = session.snapshot()
    assert view['reference_monitor']['primary'] == 'A3'
    assert view['photos_received'] is False and view['assembly_truth_received'] is False


def test_success_json_without_complete_QA_event_chain_is_rejected(tmp_path, monkeypatch):
    m = module(); file = tmp_path / 'result.json'
    file.write_text(json.dumps({'passed': True, 'guard_version': VERSION, 'frames': 8704}))
    monkeypatch.setattr(m, 'QUALIFICATION', file)
    with pytest.raises(ValueError, match='complete prospective A3 qualification log'):
        m.qualification()


def test_bad_prediction_stops_before_any_git_write(tmp_path, monkeypatch):
    m = module(); d = design(); p = m.prepare(d)
    (tmp_path / 'reviewed-design.json').write_text(json.dumps(d))
    bound = {'source_sha256': p['official_source_sha256']}
    def denied(*a):
        pytest.fail('Git touched before prediction hash check')
    monkeypatch.setattr(m.base, 'git', denied)
    with pytest.raises(ValueError, match='forecast mismatch'):
        m.publish_prediction(type('Log', (), {'path': tmp_path})(), bound, p, {}, '0'*64)
