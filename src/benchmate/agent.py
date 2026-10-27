"""Guarded experiment tools. No fixture IDs, simulator truth or private files.

Spark selects tools and writes the report. The numerical engine owns evidence,
acquisition limits and permission to confirm a candidate. This version only
accepts synthetic captures from the existing fixed-candidate development family.
"""
from copy import deepcopy
import json
import time
import numpy as np

from .engine import diagnose, rank_actions, verify_prediction
from .physics import Acquisition, ACTION_MENU, confirmation_for, predict


PROMPT = """You operate BenchMate, an evidence-driven circuit experiment assistant.
This run uses SYNTHETIC observations, not physical hardware. You receive declared
fixed candidate knowledge, never specimen identity or ground truth. Confidence
is conditional on those candidates and development noise assumptions only.

First call inspect_experiment. If candidates are unresolved, use its numerical
action ranking and observation summaries to choose measure(action, reason).
Explain in Korean why the observation can distinguish the surviving candidates.
Do not choose a useless repeated measurement while an affordable discriminating
measurement exists. You have 3 diagnostic acquisitions after common exploration;
a DC pair costs 2. Mounting is simulated. No human actually changes a circuit.

When one candidate fits, call verify_prediction before confirming it. This tool
records the prediction before acquiring fresh data at a different amplitude.
Verification data must never be used for fitting. A failed prediction or an
inadequate candidate family requires abstention, not a confident conclusion.

Finish by calling finish_report with concise Korean text in three fields:
current_explanation, unresolved, next_observation. Use verdict verified only
after successful verification, with the engine's supported candidate name.
Otherwise use verdict abstained and an empty candidate string. Explicitly state
the synthetic, fixed-candidate scope. Never infer a unique R and C from unloaded
tau alone or absence of an input branch from output voltage alone.
Do not end with a plain text answer: finish_report is the recorded final report.
Tool errors are observations too; correct the request within the fixed budget.
"""


def function_tool(name, description, properties=None):
    properties = properties or {}
    return {"type": "function", "name": name, "description": description,
            "parameters": {"type": "object", "properties": properties,
                           "required": list(properties), "additionalProperties": False},
            "strict": True}


TOOLS = [
    function_tool("inspect_experiment", "Read current evidence, declared candidates, action ranking and budgets."),
    function_tool("measure", "Choose a diagnostic action. Records a simulated instrument change and acquires new data.", {
        "action": {"type": "string", "enum": list(ACTION_MENU)},
        "reason": {"type": "string"}}),
    function_tool("verify_prediction", "Commit the supported candidate's prediction, then acquire independent confirmation. No refitting."),
    function_tool("finish_report", "Finish with a structured, evidence-constrained report. Verification is required for verdict verified.", {
        "verdict": {"type": "string", "enum": ["verified", "abstained"]},
        "candidate": {"type": "string"},
        "current_explanation": {"type": "string"},
        "unresolved": {"type": "string"},
        "next_observation": {"type": "string"}}),
]

INSTRUCTIONS = {
    "attach_10k_load": "OUT–REF에 10 kΩ 부하를 연결하고 DRIVE–IN은 0 Ω 점퍼로 연결합니다. 기존 션트는 제거합니다.",
    "attach_shunt_dc_pair": "DRIVE–IN의 0 Ω 점퍼를 1 kΩ 션트로 교체하고 OUT–REF 부하는 제거합니다. REF를 거쳐 두 DC 수준을 측정합니다.",
}


class ToolRejected(ValueError):
    pass


def observation_summary(capture):
    """Measured features, not fitted parameters or simulator component values."""
    data = capture["data"]
    dc = capture["settings"]["kind"] == "dc_pair"
    n = len(data["in_v"])
    tail = max(1, n // 10)
    return {"source": capture["source"], "settings": capture["settings"],
            "samples_per_channel": n,
            "observed_v": {k: (v if dc else {"first": v[0], "last_window_mean": float(np.mean(v[-tail:]))})
                           for k, v in data.items() if k != "time_s"},
            "raw_data_recorded": True}


class ExperimentSession:
    def __init__(self, candidates, acquire, log):
        self.candidates = list(candidates)
        self.acquire = acquire
        self.log = log
        self.start = time.monotonic()
        self.captures = []
        self.diagnostic_acquisitions = 0
        self.confirmation_acquisitions = 0
        self.simulated_mountings = 0
        self.inspected = False
        self.verification = None
        self.report = None
        self.actions = []
        self.last_settings = Acquisition()
        self._acquire(self.last_settings, "acquisition")
        self.analysis = diagnose(self.captures, self.candidates)
        self.initial_analysis = deepcopy(self.analysis)
        log.add("diagnosis", self.analysis)

    def _acquire(self, settings, kind):
        capture = self.acquire(settings)
        if capture.get("source") != "synthetic" or capture.get("settings") != settings.to_dict():
            raise ValueError("Agent requires synthetic observations with matching requested settings")
        self.log.add(kind, capture)
        if kind == "acquisition":
            self.captures.append(capture)
        return capture

    def snapshot(self):
        remaining = 3 - self.diagnostic_acquisitions
        ranked = rank_actions(self.candidates, self.analysis["supported_candidates"])
        for item in ranked:
            item["physical_acquisitions"] = Acquisition(**item["settings"]).physical_acquisitions
            item["affordable"] = item["physical_acquisitions"] <= remaining
        return {"source": "synthetic", "analysis": self.analysis,
                "declared_candidates": [{"name": c.name, "description": c.description} for c in self.candidates],
                "observations": [observation_summary(c) for c in self.captures],
                "action_ranking": ranked,
                "budget": {"exploration_used": 1, "diagnostic_used": self.diagnostic_acquisitions,
                           "diagnostic_remaining": remaining, "confirmation_used": self.confirmation_acquisitions,
                           "confirmation_limit": 1},
                "verification": self.verification}

    def dispatch(self, name, arguments):
        if self.report is not None:
            raise ToolRejected("Experiment already finished")
        schema = next((t["parameters"] for t in TOOLS if t["name"] == name), None)
        if schema is None or not isinstance(arguments, dict) or set(arguments) != set(schema["required"]):
            raise ToolRejected("Unknown tool or invalid argument fields")
        for key, spec in schema["properties"].items():
            value = arguments[key]
            if not isinstance(value, str) or len(value) > 1600 or ("enum" in spec and value not in spec["enum"]):
                raise ToolRejected("Invalid argument value: " + key)
        if name == "inspect_experiment":
            self.inspected = True
            return self.snapshot()
        if not self.inspected:
            raise ToolRejected("Read inspect_experiment before acting")
        if name == "measure":
            return self.measure(**arguments)
        if name == "verify_prediction":
            return self.verify()
        return self.finish(**arguments)

    def measure(self, action, reason):
        if self.analysis["status"] != "unresolved":
            raise ToolRejected("Diagnostic measurements require unresolved candidates; verify or report the current result")
        if not reason.strip():
            raise ToolRejected("Explain why this measurement is useful")
        settings = ACTION_MENU[action]
        if self.diagnostic_acquisitions + settings.physical_acquisitions > 3:
            raise ToolRejected("Diagnostic acquisition budget exhausted; report remaining ambiguity")
        self.log.add("instrument_request", {"action": action, "reason": reason,
                     "instruction": INSTRUCTIONS[action], "execution": "simulated",
                     "physical_human_action": False, "selected_by": "muse_spark"})
        self.diagnostic_acquisitions += settings.physical_acquisitions
        if (settings.shunt_ohm, settings.load_ohm) != (self.last_settings.shunt_ohm, self.last_settings.load_ohm):
            self.simulated_mountings += 1
        self.last_settings = settings
        self.actions.append(action)
        self._acquire(settings, "acquisition")
        self.analysis = diagnose(self.captures, self.candidates)
        self.log.add("diagnosis", self.analysis)
        return self.snapshot()

    def verify(self):
        if self.analysis["status"] != "verification_required" or self.confirmation_acquisitions:
            raise ToolRejected("Verification requires exactly one supported candidate and unused confirmation budget")
        winner = next(c for c in self.candidates if c.name == self.analysis["supported_candidates"][0])
        settings = confirmation_for(self.last_settings)
        prediction = predict(winner.model, settings)
        self.log.add("prediction_committed", {"candidate": winner.name, "settings": settings.to_dict(),
                                             "prediction": prediction})
        self.confirmation_acquisitions += 1
        capture = self._acquire(settings, "verification_acquisition")
        self.verification = verify_prediction(prediction, capture)
        self.log.add("verification", self.verification)
        passed = self.verification["passed"]
        self.analysis = {**self.analysis,
                         "status": "verified_within_declared_candidates" if passed else "prediction_failed",
                         "unresolved": "Broader configurations and hardware remain untested." if passed else
                                       "Independent prediction failed; do not confirm this circuit."}
        return self.snapshot()

    def finish(self, verdict, candidate, current_explanation, unresolved, next_observation):
        verified = self.analysis["status"] == "verified_within_declared_candidates"
        if verdict == "verified" and (not verified or self.analysis["supported_candidates"] != [candidate]):
            raise ToolRejected("Cannot confirm a candidate without a matching successful independent verification")
        if verdict == "abstained" and candidate:
            raise ToolRejected("An abstention must not name a confirmed candidate")
        if not all(t.strip() for t in (current_explanation, unresolved, next_observation)):
            raise ToolRejected("All three report fields must explain the result and its scope")
        self.report = {"verdict": verdict, "candidate": candidate,
                       "current_explanation": current_explanation, "unresolved": unresolved,
                       "next_observation": next_observation}
        self.log.add("agent_report", self.report)
        return {"accepted": True, "evidence_status": self.analysis["status"]}

    def summary(self):
        return {"source": "synthetic", "llm_used": True, "mode": "live_agent_with_synthetic_instrument",
                "initial_report": self.initial_analysis, "final_report": self.analysis,
                "agent_report": self.report, "selected_actions": self.actions,
                "verification": self.verification,
                "total_physical_acquisitions": 1 + self.diagnostic_acquisitions + self.confirmation_acquisitions,
                "diagnostic_acquisitions": self.diagnostic_acquisitions,
                "confirmation_acquisitions": self.confirmation_acquisitions,
                "simulated_mountings": self.simulated_mountings,
                "requested_human_actions": 0, "unrequested_human_interventions": 0,
                "elapsed_s": time.monotonic() - self.start,
                "scope": "Fixed synthetic candidates only; not hardware validation or nonlinear discovery. Free-text report is model-authored; structured verdict is checked against numerical evidence."}


def drive_agent(session, model):
    """Run until the model submits a checked report or the HTTP bound stops it."""
    seen_calls = set()
    while session.report is None:
        call = model.next_call()
        if call["call_id"] in seen_calls:
            raise RuntimeError("Provider reused a tool call ID")
        seen_calls.add(call["call_id"])
        session.log.add("tool_call", model.sanitize(call))
        try:
            if not isinstance(call["arguments"], str) or len(call["arguments"]) > 8192:
                raise ToolRejected("Tool arguments exceed the local bound")
            try:
                arguments = model.sanitize(json.loads(call["arguments"]))
            except (ValueError, TypeError):
                raise ToolRejected("Tool arguments must be valid JSON") from None
            result = session.dispatch(call["name"], arguments)
        except ToolRejected as exc:
            result = {"error": str(exc), "state_unchanged": True}
        session.log.add("tool_result", model.sanitize({"call_id": call["call_id"], "name": call["name"], "result": result}))
        model.submit_result(call["call_id"], result)
    return session.summary()
