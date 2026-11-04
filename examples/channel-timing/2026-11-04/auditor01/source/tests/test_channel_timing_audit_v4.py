import json
from pathlib import Path
import shutil
import pytest

from benchmate.channel_timing_audit_v4 import verify

PUBLIC=Path('examples/channel-timing/2026-11-04/records/20261104T034748-10ab5af750')


def copied(tmp_path):
    root=tmp_path/'record';shutil.copytree(PUBLIC,root);return root


def test_real_committed_source_bound_record_passes_without_recalculation():
    r=verify(PUBLIC)
    assert r['passed'] and r['events']==238 and r['preflight_events_checked']==4


def test_protocol_tampering_is_detected_even_with_intact_event_chain(tmp_path):
    root=copied(tmp_path);p=root/'protocol.json';v=json.loads(p.read_text())
    v['guard_limits']['signal_envelope_v']=.99;p.write_text(json.dumps(v))
    with pytest.raises(ValueError,match='measurement_protocol_hash'):verify(root)


def test_result_file_cannot_disagree_with_original_terminal_event(tmp_path):
    root=copied(tmp_path);p=root/'result.json';v=json.loads(p.read_text())
    v['agent_report']['verdict']='abstained';p.write_text(json.dumps(v))
    with pytest.raises(ValueError,match='result_artifact_matches_chain'):verify(root)


def test_bound_preflight_file_tampering_is_detected(tmp_path):
    root=copied(tmp_path);p=root/'preflight/events.jsonl'
    p.write_bytes(p.read_bytes()+b'\n')
    with pytest.raises(ValueError):verify(root)
