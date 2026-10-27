import json
import httpx
import pytest
from benchmate.providers import smoke,ProviderError,reserve_budget
from benchmate.records import read_events


def env_file(tmp_path):
    p=tmp_path/".env";p.write_text("MODEL_API_KEY=test-meta-secret\nBASETEN_API_KEY=test-baseten-secret\n")
    return p


def test_meta_roundtrip_auto_only_and_reasoning_replay(tmp_path,monkeypatch):
    monkeypatch.delenv("MODEL_API_KEY",raising=False)
    requests=[]
    def handler(request):
        body=json.loads(request.content);requests.append(body)
        assert body["model"]=="muse-spark-1.3"
        assert body["tool_choice"]=="auto"
        assert body["store"] is False
        if len(requests)==1:
            return httpx.Response(200,json={"id":"r1","status":"completed","usage":{"input_tokens":10,"output_tokens":20},
                "output":[{"type":"reasoning","id":"rs_1","summary":[],"encrypted_content":"opaque"},
                          {"type":"function_call","call_id":"c1","name":"get_observation","arguments":"{}"}]})
        assert any(x.get("encrypted_content")=="opaque" for x in body["input"])
        assert body["input"][-1]["call_id"]=="c1"
        return httpx.Response(200,json={"id":"r2","status":"completed","usage":{"input_tokens":20,"output_tokens":30},
            "output":[{"type":"message","content":[{"type":"output_text","text":"tau alone cannot distinguish R and C"}]}]})
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        path,result=smoke("meta",client=client,env_path=env_file(tmp_path),output=tmp_path/"runs",budget_path=tmp_path/"budget.json")
    assert result["passed"] and len(requests)==2
    text=(path/"events.jsonl").read_text()
    assert "test-meta-secret" not in text and "opaque" not in text
    assert read_events(path)[-1]["kind"]=="run_completed"


def test_baseten_exact_hackathon_model_and_message_pairing(tmp_path,monkeypatch):
    monkeypatch.delenv("BASETEN_API_KEY",raising=False)
    calls=[]
    def handler(request):
        body=json.loads(request.content);calls.append(body)
        assert body["model"]=="meta-models/muse-spark-open-1026"
        if len(calls)==1:
            return httpx.Response(200,json={"id":"b1","usage":{},"choices":[{"finish_reason":"tool_calls","message":{"role":"assistant","content":None,"tool_calls":[{"id":"c1","type":"function","function":{"name":"get_observation","arguments":"{}"}}]}}]})
        assert body["messages"][-2]["tool_calls"][0]["id"]==body["messages"][-1]["tool_call_id"]
        return httpx.Response(200,json={"id":"b2","usage":{},"choices":[{"finish_reason":"stop","message":{"role":"assistant","content":"Measure with an output load."}}]})
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        _,result=smoke("baseten",client=client,env_path=env_file(tmp_path),output=tmp_path/"runs",budget_path=tmp_path/"budget.json")
    assert result["passed"] and len(calls)==2


def test_plain_text_without_tool_is_failure_and_not_retried(tmp_path,monkeypatch):
    monkeypatch.delenv("MODEL_API_KEY",raising=False)
    calls=[]
    def handler(request):
        calls.append(request)
        return httpx.Response(200,json={"output":[{"type":"message","content":[]}],"usage":{}})
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(ProviderError,match="real tool call"):
            smoke("meta",client=client,env_path=env_file(tmp_path),output=tmp_path/"runs",budget_path=tmp_path/"budget.json")
    assert len(calls)==1
    run=next((tmp_path/"runs").iterdir())
    assert read_events(run)[-1]["kind"]=="run_failed"


def test_provider_error_body_is_not_logged(tmp_path,monkeypatch):
    monkeypatch.delenv("MODEL_API_KEY",raising=False)
    with httpx.Client(transport=httpx.MockTransport(lambda request:httpx.Response(401,text="test-meta-secret"))) as client:
        with pytest.raises(ProviderError,match="HTTP 401") as exc:
            smoke("meta",client=client,env_path=env_file(tmp_path),output=tmp_path/"runs",budget_path=tmp_path/"budget.json")
    assert "test-meta-secret" not in str(exc.value)
    assert "test-meta-secret" not in next((tmp_path/"runs").glob("*/events.jsonl")).read_text()


def test_budget_reservation_fails_closed(tmp_path):
    file=tmp_path/"budget.json"
    file.write_text(json.dumps({"version":1,"reserved_usd":{"meta":120}}))
    with pytest.raises(ProviderError,match="allowance"):
        reserve_budget(file,"meta",1)
    assert json.loads(file.read_text())["reserved_usd"]["meta"]==120
