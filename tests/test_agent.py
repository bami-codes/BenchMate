import ast
import json
from pathlib import Path

import httpx
import numpy as np
import pytest

from benchmate import agent
from benchmate.agent import ExperimentSession, ToolRejected
from benchmate.engine import candidate_set
from benchmate.providers import ProviderError
from benchmate.records import Recorder, read_events
from benchmate.simulation import FIXTURES, acquire
from benchmate.workflow import run_agent


def report(candidate="", verdict="abstained"):
    return {"verdict": verdict, "candidate": candidate,
            "current_explanation": "합성 데이터의 선언된 후보 안에서 얻은 결과입니다.",
            "unresolved": "실제 하드웨어와 더 넓은 회로군은 확인하지 않았습니다.",
            "next_observation": {"kind":"menu_action","action":"attach_shunt_dc_pair","requirement":"","reason":"Repeat the input-current check after calibration."}}


def make_session(tmp_path, case="b6", faulty_confirmation=False):
    task = "input-branch" if case in ("b1", "b6") else "rc-fault"
    rng = np.random.default_rng(3)
    calls = []
    def instrument(settings):
        calls.append(settings)
        capture = acquire(FIXTURES[case], settings, rng=rng)
        if faulty_confirmation and settings.amplitude_v == 0.3:
            capture["data"]["out_v"] = (np.asarray(capture["data"]["out_v"]) + 0.2).tolist()
        return capture
    log = Recorder(tmp_path / "runs", mode="test")
    return ExperimentSession(candidate_set(task), instrument, log), calls


def test_same_unloaded_observations_give_same_initial_agent_input(tmp_path):
    a, _ = make_session(tmp_path / "a", "b1")
    b, _ = make_session(tmp_path / "b", "b6")
    assert a.dispatch("inspect_experiment", {}) == b.dispatch("inspect_experiment", {})
    snapshot = a.snapshot()
    def keys(value):
        if isinstance(value, dict):
            return set(value).union(*(keys(v) for v in value.values()))
        if isinstance(value, list):return set().union(*(keys(v) for v in value))
        return set()
    assert not keys(snapshot)&{'fixture','fixture_id','ground_truth','seed','noise_sd_v'}
    assert all('"'+case+'"' not in json.dumps(snapshot) for case in ('b1','b6'))
    tree = ast.parse(Path(agent.__file__).read_text())
    imports = [n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)]
    assert "simulation" not in imports
    assert ".private" not in Path(agent.__file__).read_text()


def test_premature_confirmation_and_invalid_tool_never_acquire(tmp_path):
    session, calls = make_session(tmp_path)
    with pytest.raises(ToolRejected, match="inspect"):
        session.dispatch("measure", {"action": "attach_shunt_dc_pair", "reason": "measure current"})
    session.dispatch("inspect_experiment", {})
    with pytest.raises(ToolRejected, match="Cannot confirm"):
        session.dispatch("finish_report", report("rc_input_branch", "verified"))
    with pytest.raises(ToolRejected, match="Verification requires"):
        session.dispatch("verify_prediction", {})
    with pytest.raises(ToolRejected):
        session.dispatch("measure", {"action": "shell", "reason": "run a command"})
    assert len(calls) == 1 and session.report is None


def test_nonoptimal_action_is_executed_without_silently_replacing_it(tmp_path):
    session, calls = make_session(tmp_path)
    session.dispatch("inspect_experiment", {})
    session.dispatch("measure", {"action": "attach_10k_load", "reason": "Try output loading"})
    assert calls[-1].load_ohm == 10000
    assert session.analysis["status"] == "unresolved"
    session.dispatch("measure", {"action": "attach_shunt_dc_pair", "reason": "Now measure input current"})
    assert session.diagnostic_acquisitions == 3
    session.dispatch("verify_prediction", {})
    session.dispatch("finish_report", report("rc_input_branch", "verified"))
    assert session.summary()["total_physical_acquisitions"] == 5
    assert session.summary()["simulated_mountings"] == 2


def test_budget_denial_does_not_touch_instrument(tmp_path):
    session, calls = make_session(tmp_path)
    session.dispatch("inspect_experiment", {})
    for _ in range(2):
        session.dispatch("measure", {"action": "attach_10k_load", "reason": "Repeated development check"})
    with pytest.raises(ToolRejected, match="budget"):
        session.dispatch("measure", {"action": "attach_shunt_dc_pair", "reason": "too expensive now"})
    assert len(calls) == 3 and session.diagnostic_acquisitions == 2
    session.dispatch("finish_report", report())
    assert session.summary()["agent_report"]["verdict"] == "abstained"


def test_failed_independent_prediction_cannot_be_refitted_or_confirmed(tmp_path):
    session, _ = make_session(tmp_path, faulty_confirmation=True)
    session.dispatch("inspect_experiment", {})
    session.dispatch("measure", {"action": "attach_shunt_dc_pair", "reason": "measure current"})
    diagnostic_before = json.dumps(session.captures)
    session.dispatch("verify_prediction", {})
    assert session.analysis["status"] == "prediction_failed"
    assert json.dumps(session.captures) == diagnostic_before
    assert session.verification["refitted_on_verification"] is False
    with pytest.raises(ToolRejected, match="Cannot confirm"):
        session.dispatch("finish_report", report("rc_input_branch", "verified"))
    with pytest.raises(ToolRejected):
        session.dispatch("verify_prediction", {})
    session.dispatch("finish_report", report())


def env_file(tmp_path, monkeypatch):
    monkeypatch.delenv("MODEL_API_KEY", raising=False)
    p = tmp_path / ".env"
    p.write_text("MODEL_API_KEY=test-agent-secret\n")
    return p


@pytest.mark.parametrize("case,action,winner,total", [
    ("b1", "attach_shunt_dc_pair", "rc", 4),
    ("b6", "attach_shunt_dc_pair", "rc_input_branch", 4),
    ("d01-r", "attach_10k_load", "r_changed", 3),
    ("d01-c", "attach_10k_load", "c_changed", 3),
])
def test_real_transport_loop_with_mock_model_decisions(tmp_path, monkeypatch, case, action, winner, total):
    requests = []
    turns = [("inspect_experiment", {}), ("measure", {"action": action, "reason": "test-agent-secret chooses this experiment"}),
             ("verify_prediction", {}), ("finish_report", report(winner, "verified"))]
    def handler(request):
        body = json.loads(request.content)
        requests.append(body)
        i = len(requests) - 1
        assert "temperature" not in body and body["tool_choice"] == "auto"
        assert body["model"] == "muse-spark-1.3" and body["store"] is False
        assert body["reasoning"]["effort"] == "medium"
        if i:
            assert body["input"][-1]["call_id"] == f"c{i-1}"
            assert any(x.get("encrypted_content") == "opaque-private-reasoning" for x in body["input"])
            observed = json.loads(body["input"][-1]["output"])
            if i == 1:
                assert observed["analysis"]["status"] == "unresolved"
            if i == 3:
                assert observed["verification"]["passed"]
        name, args = turns[i]
        return httpx.Response(200, json={"id": f"r{i}", "status": "completed", "usage": {"input_tokens": 10, "output_tokens": 20},
                    "output": [{"type": "reasoning", "encrypted_content": "opaque-private-reasoning", "summary": []},
                               {"type": "function_call", "call_id": f"c{i}", "name": name, "arguments": json.dumps(args)}]})
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        path, summary = run_agent(case, client=client, env_path=env_file(tmp_path, monkeypatch),
                                 output=tmp_path / "runs", budget_path=tmp_path / "budget.json")
    assert len(requests) == summary["http_requests"] == 4
    assert summary["agent_report"]["candidate"] == winner
    assert summary["agent_report"]["verdict"] == "verified"
    assert summary["total_physical_acquisitions"] == total
    assert summary["llm_used"] and summary["requested_human_actions"] == 0
    events = read_events(path)
    kinds = [e["kind"] for e in events]
    assert kinds.index("prediction_committed") < kinds.index("verification_acquisition")
    text = (path / "events.jsonl").read_text()
    assert "test-agent-secret" not in text and "opaque-private-reasoning" not in text
    assert events[-1]["payload"] == summary


def test_repeated_inspection_stops_at_api_budget_and_records_failure(tmp_path, monkeypatch):
    requests = []
    def handler(request):
        requests.append(request)
        return httpx.Response(200, json={"status": "completed", "output": [
            {"type": "function_call", "call_id": str(len(requests)), "name": "inspect_experiment", "arguments": "{}"}]})
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(ProviderError, match="request budget"):
            run_agent("b6", client=client, env_path=env_file(tmp_path, monkeypatch), output=tmp_path / "runs",
                      budget_path=tmp_path / "budget.json", max_requests=2)
    assert len(requests) == 2
    event = read_events(next((tmp_path / "runs").iterdir()))[-1]
    assert event["kind"] == "run_failed"
    assert event["payload"]["partial_result"]["total_physical_acquisitions"] == 1


@pytest.mark.parametrize("response,match", [
    ({"status": "incomplete", "output": []}, "did not complete"),
    ({"status": "completed", "output": [{"type": "message", "content": []}]}, "exactly one tool"),
    ({"status": "completed", "output": None}, "protocol"),
])
def test_invalid_or_unfinished_provider_response_does_not_execute(tmp_path, monkeypatch, response, match):
    with httpx.Client(transport=httpx.MockTransport(lambda _: httpx.Response(200, json=response))) as client:
        with pytest.raises(ProviderError, match=match):
            run_agent("b6", client=client, env_path=env_file(tmp_path, monkeypatch), output=tmp_path / "runs",
                      budget_path=tmp_path / "budget.json")
    last = read_events(next((tmp_path / "runs").iterdir()))[-1]
    assert last["kind"] == "run_failed"
    assert last["payload"]["http_requests"] == 1


def test_invalid_tool_request_returns_error_to_model_before_recovery(tmp_path, monkeypatch):
    requests = []
    def handler(request):
        body = json.loads(request.content)
        requests.append(body)
        i = len(requests)
        if i == 1:
            name, args = "inspect_experiment", "{}"
        elif i == 2:
            name, args = "finish_report", json.dumps(report("rc", "verified"))
        else:
            result = json.loads(body["input"][-1]["output"])
            assert "Cannot confirm" in result["error"]
            name, args = "finish_report", json.dumps(report())
        return httpx.Response(200, json={"status": "completed", "output": [
            {"type": "function_call", "call_id": str(i), "name": name, "arguments": args}]})
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        _, result = run_agent("b6", client=client, env_path=env_file(tmp_path, monkeypatch), output=tmp_path / "runs",
                              budget_path=tmp_path / "budget.json")
    assert result["agent_report"]["verdict"] == "abstained"
    assert result["total_physical_acquisitions"] == 1
