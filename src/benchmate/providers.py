"""Bounded live tool-call smoke test. This is not the autonomous bench agent.

The Meta endpoint currently only accepts tool_choice=auto. Use explicit tool
instructions, validate real calls, and report failure if none is returned.
No API key, Authorization header or encrypted reasoning is written to run logs.
"""
import fcntl
import json
from pathlib import Path
import time
import httpx
from .config import load_keys, redact
from .records import Recorder

PROVIDERS={
    "meta":{"url":"https://api.meta.ai/v1/responses","model":"muse-spark-1.3","key":"MODEL_API_KEY","cap_usd":120.0},
    "baseten":{"url":"https://inference.baseten.co/v1/chat/completions","model":"meta-models/muse-spark-open-1026","key":"BASETEN_API_KEY","cap_usd":80.0},
}

TOOL={"type":"function","name":"get_observation","description":"Read the current synthetic RC experiment observation. Must be called before reporting.",
      "parameters":{"type":"object","properties":{},"required":[],"additionalProperties":False},"strict":True}
PROMPT=("This is a BenchMate API connectivity test with SYNTHETIC data, not real hardware. "
        "Call get_observation exactly once to get the observation. Do not guess its contents. "
        "After receiving it, give a short Korean report: what is known, what remains unresolved, "
        "and which additional measurement distinguishes the declared hypotheses. Do not claim a unique R or C from tau alone.")
OBSERVATION={"source":"synthetic","instrument":"ideal_voltage_drive","load_ohm":None,
             "measured_tau_s":0.020,"declared_hypotheses":[{"r_ohm":20000,"c_f":1e-6},{"r_ohm":10000,"c_f":2e-6}],
             "available_next_measurements":["step with 10 kohm OUT-to-REF load","repeat unloaded step"]}


class ProviderError(RuntimeError): pass


def reserve_budget(path, provider, reserve_usd):
    """Reserve before sending, under an OS lock. Failed/unknown calls remain reserved.

Day-one uses a conservative $1 per HTTP request, max 4k output tokens and a 24k
byte JSON payload. Meta's published prices are lower than this reserve. Baseten
hackathon rates remain unverified: this is a local spending allowance, not a
guaranteed billing cap. No application can cap calls made outside this process.
"""
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    with path.open("a+") as f:
        fcntl.flock(f,fcntl.LOCK_EX)
        f.seek(0);raw=f.read()
        data=json.loads(raw) if raw else {"version":1,"reserved_usd":{}}
        current=float(data["reserved_usd"].get(provider,0))
        if current+reserve_usd>PROVIDERS[provider]["cap_usd"]:
            raise ProviderError("Local provider spending allowance exhausted")
        data["reserved_usd"][provider]=round(current+reserve_usd,6)
        f.seek(0);f.truncate();json.dump(data,f);f.flush()
        fcntl.flock(f,fcntl.LOCK_UN)


def smoke(provider, *, effort="medium", output="runs", env_path=".env", client=None,
          budget_path=".private/api-budget.json"):
    if provider not in PROVIDERS: raise ValueError("Unknown provider")
    if effort not in ("medium","max"): raise ValueError("Unsupported smoke-test effort")
    cfg=PROVIDERS[provider];keys=load_keys(env_path);key=keys[cfg["key"]]
    if not key: raise ProviderError(f"Set {cfg['key']} in the local ignored .env file")
    if provider=="baseten" and effort!="medium":
        raise ProviderError("Baseten reasoning controls are not assumed equivalent to Meta")
    log=Recorder(output,mode="live_api_with_synthetic_tool")
    log.add("provider_configuration",{"provider":provider,"model":cfg["model"],
            "reasoning_effort":effort if provider=="meta" else "provider_default",
            "max_http_requests":2,"max_output_tokens_per_request":4096,
            "tool_choice":"auto","billing_note":"$1 local allowance reserved per request; not actual charged cost"})
    own=client is None
    http=client or httpx.Client(timeout=90.0,follow_redirects=False)
    total_usage=[]
    start=time.monotonic()

    def post(payload):
        encoded=json.dumps(payload).encode()
        if len(encoded)>24000: raise ProviderError("Smoke payload exceeds the local bound")
        reserve_budget(budget_path,provider,1.0)
        begin=time.monotonic()
        try:
            response=http.post(cfg["url"],json=payload,headers={"Authorization":"Bearer "+key})
        except httpx.HTTPError as exc:
            raise ProviderError("Provider network failure: "+type(exc).__name__) from None
        if response.status_code>=400:
            # Never echo provider error bodies, headers or credentials.
            raise ProviderError(f"{provider} returned HTTP {response.status_code}; check account/model access")
        body=response.json()
        usage=body.get("usage",{})
        total_usage.append(usage)
        log.add("api_response",redact({"provider":provider,"response_id":body.get("id"),
                                      "usage":usage,"elapsed_s":time.monotonic()-begin,
                                      "status":body.get("status")},keys))
        return body

    try:
        if provider=="meta":
            base={"model":cfg["model"],"reasoning":{"effort":effort},"max_output_tokens":4096,
                  "store":False,"include":["reasoning.encrypted_content"],"tools":[TOOL],
                  "tool_choice":"auto","parallel_tool_calls":False}
            initial=[{"role":"user","content":PROMPT}]
            first=post({**base,"input":initial})
            calls=[item for item in first.get("output",[]) if item.get("type")=="function_call"]
            if len(calls)!=1: raise ProviderError("Expected one real tool call; model returned a different response")
            call=calls[0]
            if call.get("name")!="get_observation" or json.loads(call.get("arguments","null"))!={}:
                raise ProviderError("Model requested an invalid tool or arguments")
            log.add("tool_call",{"name":call["name"],"arguments":{},"call_id":call["call_id"]})
            log.add("tool_result",OBSERVATION)
            # Preserve encrypted reasoning and function call/result correspondence in memory.
            follow=initial+first["output"]+[{"type":"function_call_output","call_id":call["call_id"],"output":json.dumps(OBSERVATION)}]
            second=post({**base,"input":follow})
            if any(i.get("type")=="function_call" for i in second.get("output",[])):
                raise ProviderError("Model exceeded the one-tool smoke-test budget")
            text="\n".join(c.get("text","") for item in second.get("output",[]) if item.get("type")=="message" for c in item.get("content",[]) if c.get("type")=="output_text")
            if second.get("status") not in (None,"completed"):
                raise ProviderError("Model response did not complete")
        else:
            function={k:v for k,v in TOOL.items() if k!="type"}
            base={"model":cfg["model"],"max_tokens":4096,"tools":[{"type":"function","function":function}],"tool_choice":"auto"}
            messages=[{"role":"user","content":PROMPT}]
            first=post({**base,"messages":messages})
            message=first["choices"][0]["message"]
            calls=message.get("tool_calls",[])
            if len(calls)!=1: raise ProviderError("Expected one real tool call; model returned a different response")
            call=calls[0];fn=call.get("function",{})
            if fn.get("name")!="get_observation" or json.loads(fn.get("arguments","null"))!={}:
                raise ProviderError("Model requested an invalid tool or arguments")
            log.add("tool_call",{"name":fn["name"],"arguments":{},"call_id":call["id"]})
            log.add("tool_result",OBSERVATION)
            messages += [message,{"role":"tool","tool_call_id":call["id"],"content":json.dumps(OBSERVATION)}]
            second=post({**base,"messages":messages})
            choice=second["choices"][0]
            if choice.get("finish_reason")!="stop" or choice["message"].get("tool_calls"):
                raise ProviderError("Model did not finish within the smoke-test budget")
            text=choice["message"].get("content","")
        if not isinstance(text,str) or not text.strip(): raise ProviderError("Model returned no final visible report")
        summary={"passed":True,"provider":provider,"model":cfg["model"],"source":"live_api_with_synthetic_tool",
                 "tool_round_trips":1,"http_requests":2,"report":redact(text,keys),"usage":total_usage,
                 "elapsed_s":time.monotonic()-start,"reserved_allowance_usd":2.0,
                 "scope":"Connectivity and tool protocol only; not a hardware or diagnosis evaluation."}
        log.add("run_completed",summary)
        return log.path,summary
    except Exception as exc:
        safe=str(exc) if isinstance(exc,ProviderError) else "Protocol failure: "+type(exc).__name__
        log.add("run_failed",{"error":redact(safe,keys),"elapsed_s":time.monotonic()-start})
        raise ProviderError(redact(safe,keys)+f"; record: {log.path}") from None
    finally:
        if own: http.close()
