"""Muse Spark Open on Baseten (chat completions) with the same bounded tool loop as
MetaToolSession: one tool call per turn, no retries, no provider switching, no key
or hidden reasoning in logs, $1 local allowance reserved per request.

Used by the linear benchmark's spark_open arm. Reasoning effort is provider default.
"""
import json
import time
import httpx
from .config import load_keys, redact
from .providers import PROVIDERS, ProviderError, reserve_budget


def chat_tool(tool):
    """Responses-style function tool -> chat-completions tool (same name/schema)."""
    return {"type": "function", "function": {k: v for k, v in tool.items() if k != "type"}}


class BasetenToolSession:
    def __init__(self, *, prompt, tools, log, env_path=".env", budget_path=".private/api-budget.json",
                 client=None, max_requests=8, max_output_tokens=4096, max_payload_bytes=64000):
        if not 1 <= max_requests <= 8 or max_output_tokens not in (4096, 8192) or max_payload_bytes not in (64000, 128000):
            raise ValueError("Unsupported bounded provider configuration")
        self.keys = load_keys(env_path)
        self.cfg = PROVIDERS["baseten"]
        self.key = self.keys.get(self.cfg["key"])
        if not self.key:
            raise ProviderError("Set BASETEN_API_KEY in the local ignored .env file")
        self.log, self.budget_path = log, budget_path
        self.own = client is None
        self.http = client or httpx.Client(timeout=120.0, follow_redirects=False)
        self.max_requests, self.max_payload_bytes = max_requests, max_payload_bytes
        self.requests, self.usage, self.api_elapsed_s = 0, [], 0.0
        self.pending_call = None
        self.messages = [{"role": "user", "content": prompt}]
        self.base = {"model": self.cfg["model"], "max_tokens": max_output_tokens,
                     "tools": [chat_tool(t) for t in tools], "tool_choice": "auto", "parallel_tool_calls": False}
        log.add("provider_configuration", {"provider": "baseten", "model": self.cfg["model"],
                "reasoning_effort": "provider_default", "temperature": "provider_default",
                "max_http_requests": max_requests, "max_output_tokens_per_request": max_output_tokens,
                "max_payload_bytes": max_payload_bytes, "tool_choice": "auto",
                "billing_note": "$1 local allowance reserved per request; not actual charged cost"})

    def sanitize(self, value):
        return redact(value, self.keys)

    def next_call(self):
        if self.pending_call is not None:
            raise ProviderError("Previous tool call has no result")
        if self.requests >= self.max_requests:
            raise ProviderError("Agent HTTP request budget exhausted")
        payload = {**self.base, "messages": self.messages}
        if len(json.dumps(payload).encode()) > self.max_payload_bytes:
            raise ProviderError("Agent payload exceeds the local bound")
        reserve_budget(self.budget_path, "baseten", 1.0)
        self.requests += 1
        begin = time.monotonic()
        try:
            response = self.http.post(self.cfg["url"], json=payload, headers={"Authorization": "Bearer " + self.key})
        except httpx.HTTPError as exc:
            raise ProviderError("Provider network failure: " + type(exc).__name__) from None
        finally:
            self.api_elapsed_s += time.monotonic() - begin
        if response.status_code >= 400:
            raise ProviderError(f"baseten returned HTTP {response.status_code}; check account/model access")
        try:
            body = response.json()
            usage = body.get("usage", {})
            self.usage.append(usage)
            choice = body["choices"][0]
            message = choice["message"]
            self.log.add("api_response", self.sanitize({"provider": "baseten", "response_id": body.get("id"),
                         "usage": usage, "elapsed_s": time.monotonic() - begin,
                         "finish_reason": choice.get("finish_reason")}))
            calls = message.get("tool_calls") or []
            if len(calls) != 1:
                raise ProviderError("Agent must return exactly one tool call per turn")
            call = calls[0]
            function = call.get("function") or {}
            if not all(isinstance(v, str) and v for v in (call.get("id"), function.get("name"), function.get("arguments"))):
                raise ProviderError("Invalid provider tool-call envelope")
            self.messages.append(message)
            self.pending_call = call["id"]
            return {"call_id": call["id"], "name": function["name"], "arguments": function["arguments"]}
        except (KeyError, IndexError, TypeError, ValueError, AttributeError):
            raise ProviderError("Invalid provider response protocol") from None

    def submit_result(self, call_id, result):
        if call_id != self.pending_call:
            raise ProviderError("Tool result does not match the outstanding call")
        self.messages.append({"role": "tool", "tool_call_id": call_id,
                              "content": json.dumps(result, ensure_ascii=False, allow_nan=False)})
        self.pending_call = None

    def metadata(self):
        return {"provider": "baseten", "model": self.cfg["model"], "reasoning_effort": "provider_default",
                "http_requests": self.requests, "usage": self.usage,
                "api_elapsed_s": self.api_elapsed_s, "reserved_allowance_usd": float(self.requests)}

    def close(self):
        if self.own:
            self.http.close()
