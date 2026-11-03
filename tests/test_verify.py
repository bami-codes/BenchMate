"""The public verifier must reject rehashed records with broken causality too."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tarfile

import pytest

from benchmate.records import canonical
from benchmate.verify import verify_run


ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / "examples/netlist-diagnosis-v2/2026-11-02/development-records.tar.gz"
PILOT = ROOT / "examples/passive-pilot/2026-11-03/design-01-fault/20261102T164944-16f6a79a31"
REPAIR = ROOT / "examples/d01-repair-rehearsal/2026-11-01/final_success/20261101T003829-400778438d"
B5 = ROOT / "examples/b5-unloaded-spark/2026-10-30/20261030T133514-4ea9a8848e"


@pytest.fixture
def events():
    with tarfile.open(ARCHIVE) as archive:
        member = next(m for m in archive if m.name.endswith("events.jsonl"))
        return [json.loads(line) for line in archive.extractfile(member).read().splitlines()]


def rechain(events, target):
    """Attacker can rewrite the whole chain, but semantic checks still apply."""
    previous = "0" * 64
    output = []
    for index, original in enumerate(events):
        event = {k: v for k, v in original.items() if k != "sha256"}
        event.update(sequence=index, previous_sha256=previous)
        previous = hashlib.sha256(canonical(event)).hexdigest()
        output.append(json.dumps({**event, "sha256": previous}))
    target.write_text("\n".join(output) + "\n")
    return target


def find(events, kind, **payload):
    return next(i for i, e in enumerate(events) if e["kind"] == kind
                and all(e["payload"].get(k) == v for k, v in payload.items()))


def test_all_25_retained_netlist_mock_runs(tmp_path):
    with tarfile.open(ARCHIVE) as archive:
        members = [m for m in archive if m.name.endswith("events.jsonl")]
        assert len(members) == 25
        for member in members:
            path = tmp_path / "events.jsonl"
            path.write_bytes(archive.extractfile(member).read())
            result = verify_run(path)
            assert result["passed"], (member.name, result)
            assert result["forecasts"] == 4 and result["measurements"] == 5


@pytest.mark.parametrize("path", [PILOT, REPAIR, B5])
def test_retained_physical_pilot_and_legacy_prediction_families(path):
    result = verify_run(path)
    assert result["passed"], result
    assert result["forecasts"] > 0
    if path == PILOT:
        assert result["run_status"] == "run_failed"  # Integrity PASS != experiment success.


@pytest.mark.parametrize("change,reason", [
    ("content", "event_sha256_mismatch"),
    ("previous", "previous_sha256_mismatch"),
    ("sequence", "event_sequence_mismatch"),
    ("sha256", "event_sha256_mismatch"),
])
def test_unrehashed_tampering(events, tmp_path, change, reason):
    target = rechain(events, tmp_path / "events.jsonl")
    lines = target.read_text().splitlines()
    event = json.loads(lines[3])
    if change == "content":
        event["timestamp"] = "1900-01-01T00:00:00+00:00"
    elif change == "previous":
        event["previous_sha256"] = "1" * 64
    elif change == "sequence":
        event["sequence"] = 900
    else:
        event["sha256"] = "1" * 64
    lines[3] = json.dumps(event)
    target.write_text("\n".join(lines) + "\n")
    result = verify_run(target)
    assert not result["passed"] and result["error"] == reason
    assert result["events"] == 3


@pytest.mark.parametrize("kind", ["training_forecasts_frozen", "verification_forecast_frozen"])
def test_inner_forecast_hash_is_checked_after_valid_outer_rehash(events, tmp_path, kind):
    events[find(events, kind)]["payload"]["sha256"] = "f" * 64
    result = verify_run(rechain(events, tmp_path / "events.jsonl"))
    assert not result["passed"] and result["error"] == "frozen_prediction_hash_mismatch"
    assert result["events"] == len(events)


@pytest.mark.parametrize("role,kind", [
    ("training", "training_forecasts_frozen"), ("verification", "verification_forecast_frozen"),
])
def test_rehashed_prediction_after_measurement_fails(events, tmp_path, role, kind):
    frozen = events.pop(find(events, kind))
    index = find(events, "netlist_observation", purpose=role)
    events.insert(index + 1, frozen)
    result = verify_run(rechain(events, tmp_path / "events.jsonl"))
    assert not result["passed"]
    assert "before_" in result["error"]


def test_publication_must_precede_reserved_observation(events, tmp_path):
    publication = events.pop(find(events, "verification_publication"))
    index = find(events, "netlist_observation", purpose="verification")
    events.insert(index + 1, publication)
    result = verify_run(rechain(events, tmp_path / "events.jsonl"))
    assert result["error"] == "measurement_before_matching_publication"


@pytest.mark.parametrize("kind,field,reason", [
    ("verification_publication", "sha256", "publication_hash_mismatch"),
    ("reserved_prediction_scored", "prediction_sha256", "scored_prediction_hash_mismatch"),
    ("netlist_verification_completed", "frozen_sha256", "verification_prediction_hash_mismatch"),
])
def test_prediction_hash_references_are_bound(events, tmp_path, kind, field, reason):
    events[find(events, kind)]["payload"][field] = "f" * 64
    result = verify_run(rechain(events, tmp_path / "events.jsonl"))
    assert result["error"] == reason


def test_score_cannot_move_before_observation(events, tmp_path):
    score = events.pop(find(events, "reserved_prediction_scored"))
    events.insert(find(events, "netlist_observation", purpose="verification"), score)
    result = verify_run(rechain(events, tmp_path / "events.jsonl"))
    assert result["error"] == "score_before_matching_measurement"


def test_physical_capture_cannot_precede_plan_and_forecast(tmp_path):
    events = [json.loads(line) for line in (PILOT / "events.jsonl").read_text().splitlines()]
    index = next(i for i, e in enumerate(events) if e["kind"] == "serial_command"
                 and " STEP " in e["payload"]["request"])
    capture = events.pop(index)
    events.insert(find(events, "training_forecasts_frozen"), capture)
    result = verify_run(rechain(events, tmp_path / "events.jsonl"))
    assert result["error"] == "CAPTURE_before_forecast_acquisition_plan"


def test_settings_are_bound_to_the_correct_forecast(events, tmp_path):
    observation = events[find(events, "netlist_observation", purpose="verification")]
    observation["payload"]["settings"]["amplitude_v"] = .001
    result = verify_run(rechain(events, tmp_path / "events.jsonl"))
    assert result["error"] == "forecast_measurement_settings_mismatch"


def test_truncation_and_events_after_terminal(events, tmp_path):
    path = tmp_path / "events.jsonl"
    result = verify_run(rechain(events[:-1], path))
    assert result["error"] == "missing_terminal_event"
    result = verify_run(rechain(events + [deepcopy(events[1])], path))
    assert result["error"] == "event_after_terminal"


def test_duplicate_json_keys_cannot_be_hidden_by_normal_json_parsing(events, tmp_path):
    target = rechain(events, tmp_path / "events.jsonl")
    text = target.read_text().replace('"sequence": 0,', '"sequence": 0, "sequence": 0,', 1)
    target.write_text(text)
    assert verify_run(target)["error"] == "duplicate_JSON_key"


def test_expected_head_detects_a_fully_rewritten_but_internally_consistent_history(events, tmp_path):
    path = rechain(events, tmp_path / "events.jsonl")
    head = verify_run(path)["head_sha256"]
    events[2]["timestamp"] = "1900-01-01T00:00:00+00:00"
    rechain(events, path)
    assert verify_run(path)["passed"]  # No honest claim of external authentication.
    assert verify_run(path, expected_head=head)["error"] == "expected_head_mismatch"


def test_no_forecasts_does_not_silently_pass(events, tmp_path):
    target = rechain([events[0], events[-1]], tmp_path / "events.jsonl")
    assert verify_run(target)["error"] == "no_supported_frozen_prediction_hash"


def test_local_prediction_file_is_compared_to_the_embedded_freeze(events, tmp_path):
    target = rechain(events, tmp_path / "events.jsonl")
    frozen = events[find(events, "verification_forecast_frozen")]["payload"]
    content = {k: v for k, v in frozen.items() if k != "sha256"}
    prediction_file = tmp_path / "predictions-frozen.json"
    prediction_file.write_text(json.dumps(content))
    assert verify_run(target)["prediction_files"] == 1
    content["source"] = "tampered"
    prediction_file.write_text(json.dumps(content))
    assert verify_run(target)["error"] == "prediction_file_hash_mismatch"


def test_fresh_checkout_entrypoint_without_site_packages_or_environment_keys():
    completed = subprocess.run([sys.executable, "-S", "-m", "benchmate", "verify", str(REPAIR)],
                               cwd=ROOT, env={}, capture_output=True, text=True)
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert completed.stderr == "" and len(completed.stdout.splitlines()) == 1
    assert completed.stdout.startswith("PASS events=39 forecasts=1 measurements=2")
    assert "creation_time=unproven" in completed.stdout


def test_failure_is_one_line_and_nonzero_without_a_traceback(tmp_path):
    completed = subprocess.run([sys.executable, "-S", "-m", "benchmate", "verify", str(tmp_path)],
                               cwd=ROOT, env={}, capture_output=True, text=True)
    assert completed.returncode == 1 and completed.stderr == ""
    assert len(completed.stdout.splitlines()) == 1
    assert completed.stdout.startswith("FAIL events=0")


def test_frozen_runtime_files_are_unchanged():
    for name in ("docs/2026-11-02-frozen-sources.json",
                 "examples/netlist-diagnosis/2026-11-02/summary.json",
                 "examples/netlist-diagnosis-v2/2026-11-02/summary.json"):
        manifest = json.loads((ROOT / name).read_text())["source_sha256"]
        for file, expected in manifest.items():
            assert hashlib.sha256((ROOT / file).read_bytes()).hexdigest() == expected, file
