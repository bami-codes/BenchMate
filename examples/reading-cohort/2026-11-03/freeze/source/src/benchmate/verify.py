"""Offline record integrity and prospective-order checks, never an experiment.

Only the standard library is used. No source snapshots are executed, no paths
inside the record are followed, and no keys, providers or serial APIs are read.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re

from .records import canonical


FORECASTS = {
    "training_forecasts_frozen", "verification_forecast_frozen",
    "b5_predictions_frozen", "repair_prediction_frozen",
}
PUBLICATIONS = {
    "verification_publication": "verification_forecast_frozen",
    "b5_prediction_publication": "b5_predictions_frozen",
    "repair_prediction_publication": "repair_prediction_frozen",
}
SHA256 = re.compile(r"[0-9a-f]{64}\Z")
SCOPE = "scope=internal_integrity+recorded_order creation_time=unproven"


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _object(pairs):
    value = {}
    for key, item in pairs:
        _require(key not in value, "duplicate_JSON_key")
        value[key] = item
    return value


def _constant(value):
    raise ValueError("nonfinite_JSON_number")


def _digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


class Audit:
    def __init__(self):
        self.events = 0
        self.forecasts = 0
        self.prediction_files = 0
        self.measurements = 0
        self.order_checks = 0
        self.head = "0" * 64
        self.run_status = "unknown"
        self.latest = {}
        self.published = {}
        self.training = None
        self.plan = None
        self.observed = {"netlist": [], "b5": [], "repair": []}
        self.scored = {"netlist": 0, "b5": 0, "repair": 0}

    def before(self, freeze_kind, settings=None, *, publication=False):
        frozen = self.latest.get(freeze_kind)
        _require(frozen is not None, "measurement_before_" + freeze_kind)
        if publication:
            _require(self.published.get(freeze_kind) == frozen["sha256"],
                     "measurement_before_matching_publication")
        if settings is not None:
            if freeze_kind == "training_forecasts_frozen":
                _require(frozen is self.training, "training_forecast_missing_or_already_used")
                expected = frozen["settings"]
            else:
                family = {"verification_forecast_frozen": "netlist",
                          "b5_predictions_frozen": "b5", "repair_prediction_frozen": "repair"}[freeze_kind]
                menu = (frozen["policy"]["reserved"] if family == "netlist" else
                        frozen["protocol"]["reserved"] if family == "b5" else
                        frozen["policy"]["repair_checks"])
                index = len(self.observed[family])
                _require(index < len(menu), "extra_reserved_measurement")
                expected = menu[index]
            _require(settings == expected, "forecast_measurement_settings_mismatch")
        self.order_checks += 1
        return frozen

    def event(self, event, *, netlist):
        kind, p = event["kind"], event["payload"]
        if kind in FORECASTS:
            _require(isinstance(p, dict), "invalid_forecast_payload")
            sha = p.get("sha256")
            _require(isinstance(sha, str) and SHA256.fullmatch(sha), "missing_forecast_sha256")
            _require(_digest({k: v for k, v in p.items() if k != "sha256"}) == sha,
                     "frozen_prediction_hash_mismatch")
            if kind == "training_forecasts_frozen":
                _require(self.training is None, "unused_training_forecast_replaced")
                _require("verification_forecast_frozen" not in self.latest, "training_after_verification_freeze")
                self.training = p
            else:
                _require(kind not in self.latest, "verification_forecast_replaced")
                if kind == "verification_forecast_frozen":
                    _require(self.training is None, "verification_before_training_measurement")
            self.latest[kind] = p
            self.forecasts += 1
        elif ("forecast" in kind or "prediction" in kind) and kind.endswith("_frozen"):
            raise ValueError("unsupported_frozen_prediction_kind:" + kind)
        elif kind in ("netlist_reference_origins_frozen", "b5_ADC_origin_frozen"):
            field = "id" if kind == "b5_ADC_origin_frozen" else "sha256"
            _require(_digest({k: v for k, v in p.items() if k != field}) == p.get(field),
                     "frozen_reference_hash_mismatch")
        elif kind == "pre_stimulus_origin_frozen":
            # Historical origin records hashed default JSON spacing plus LF,
            # before adding the phase and sha256 fields; do not use canonical().
            content = {k: v for k, v in p.items() if k not in ("phase", "sha256")}
            raw = (json.dumps(content, sort_keys=True) + "\n").encode()
            _require(hashlib.sha256(raw).hexdigest() == p.get("sha256"),
                     "frozen_reference_hash_mismatch")

        if kind in PUBLICATIONS:
            freeze_kind = PUBLICATIONS[kind]
            frozen = self.before(freeze_kind)
            _require(p.get("sha256") == frozen["sha256"] and p.get("published") is True,
                     "publication_hash_mismatch")
            self.published[freeze_kind] = frozen["sha256"]

        # Bind physical acquisition to its forecast BEFORE serial CAPTURE, not
        # merely before the processed observation is appended afterward.
        if kind == "netlist_physical_acquisition_plan":
            role = p["purpose"]
            _require(role in ("training", "verification"), "unknown_measurement_role")
            freeze_kind = "training_forecasts_frozen" if role == "training" else "verification_forecast_frozen"
            frozen = self.before(freeze_kind, p["settings"], publication=role == "verification")
            if role == "verification":
                _require(p.get("prediction_sha256") == frozen["sha256"], "acquisition_prediction_hash_mismatch")
            self._plan(p["settings"], freeze_kind)
        elif kind == "b5_capture_requested" and p.get("purpose") == "verification":
            self.before("b5_predictions_frozen", p["settings"], publication=True)
            self._plan(p["settings"], "b5_predictions_frozen")
        elif kind == "physical_acquisition_plan_frozen" and str(p.get("phase", "")).startswith("repair_"):
            self.before("repair_prediction_frozen", p["settings"], publication=True)
            self._plan(p["settings"], "repair_prediction_frozen")
        elif kind == "serial_command":
            request = str(p.get("request", "")).split()
            if len(request) >= 3 and request[0] == "CAPTURE" and request[2] != "HOLD":
                if netlist or self.plan is not None:
                    _require(self.plan is not None, "CAPTURE_before_forecast_acquisition_plan")
                    _require(not self.plan["captured"], "duplicate_scored_CAPTURE")
                    s = self.plan["settings"]
                    _require(len(request) == 7 and request[2].lower() == s["kind"]
                             and int(request[3]) == s["samples"] and int(request[4]) == s["period_us"],
                             "CAPTURE_plan_mismatch")
                    self.before(self.plan["freeze_kind"], s,
                                publication=self.plan["freeze_kind"] != "training_forecasts_frozen")
                    self.plan["captured"] = True

        if kind == "netlist_observation":
            role = p["purpose"]
            _require(role in ("training", "verification"), "unknown_measurement_role")
            freeze_kind = "training_forecasts_frozen" if role == "training" else "verification_forecast_frozen"
            self.before(freeze_kind, p["settings"], publication=role == "verification")
            self._physical_observation(p, freeze_kind)
            if role == "training":
                self.training = None
            else:
                self.observed["netlist"].append(p["settings"])
            self.measurements += 1
        elif kind == "b5_observation" and p.get("purpose") == "verification":
            self.before("b5_predictions_frozen", p["settings"], publication=True)
            self._physical_observation(p, "b5_predictions_frozen")
            self.observed["b5"].append(p["settings"])
            self.measurements += 1
        elif kind in ("physical_observation", "mock_rc_observation") and str(p.get("phase", "")).startswith("repair_"):
            self.before("repair_prediction_frozen", p["settings"], publication=True)
            self._physical_observation(p, "repair_prediction_frozen")
            self.observed["repair"].append(p["settings"])
            self.measurements += 1

        score_kinds = {"reserved_prediction_scored": ("netlist", "verification_forecast_frozen", "prediction_sha256"),
                       "b5_reserved_check": ("b5", "b5_predictions_frozen", "frozen_sha256"),
                       "repair_prediction_comparison": ("repair", "repair_prediction_frozen", "prediction_sha256")}
        if kind in score_kinds:
            family, freeze_kind, field = score_kinds[kind]
            frozen = self.before(freeze_kind, publication=True)
            _require(p.get(field) == frozen["sha256"], "scored_prediction_hash_mismatch")
            index = self.scored[family]
            _require(index < len(self.observed[family]) and p.get("settings") == self.observed[family][index],
                     "score_before_matching_measurement")
            self.scored[family] += 1
        if kind in ("netlist_verification_completed", "b5_verification"):
            freeze_kind = "verification_forecast_frozen" if kind.startswith("netlist") else "b5_predictions_frozen"
            frozen = self.before(freeze_kind, publication=True)
            _require(p.get("frozen_sha256") == frozen["sha256"], "verification_prediction_hash_mismatch")
            family = "netlist" if kind.startswith("netlist") else "b5"
            _require(self.scored[family] == len(self.observed[family]) == len(p["checks"]),
                     "verification_before_scored_measurements")
            if family == "netlist":
                _require(len(self.observed[family]) == len(frozen["policy"]["reserved"]),
                         "verification_before_all_reserved_measurements")
        elif kind == "repair_verification_completed":
            frozen = self.before("repair_prediction_frozen", publication=True)
            _require(self.scored["repair"] == len(self.observed["repair"]) == len(frozen["policy"]["repair_checks"]),
                     "verification_before_all_reserved_measurements")

    def _plan(self, settings, freeze_kind):
        _require(self.plan is None, "unconsumed_acquisition_plan_replaced")
        self.plan = {"settings": settings, "freeze_kind": freeze_kind, "captured": False}

    def _physical_observation(self, payload, freeze_kind):
        if payload.get("source") == "physical":
            _require(self.plan is not None and self.plan["captured"]
                     and self.plan["settings"] == payload["settings"]
                     and self.plan["freeze_kind"] == freeze_kind,
                     "physical_observation_without_matching_CAPTURE")
            self.plan = None


def verify_run(path, *, expected_head=None):
    """Return a printable result even for corrupt/missing/incomplete records."""
    audit = Audit()
    error = None
    try:
        path = Path(path)
        if path.is_dir():
            path = path / "events.jsonl"
        record_root = path.parent
        events = []
        with path.open(encoding="utf-8") as stream:
            for line in stream:
                event = json.loads(line, object_pairs_hook=_object, parse_constant=_constant)
                _require(isinstance(event, dict) and set(event) ==
                         {"sequence", "timestamp", "kind", "payload", "previous_sha256", "sha256"},
                         "invalid_event_fields")
                _require(type(event["sequence"]) is int and event["sequence"] == audit.events,
                         "event_sequence_mismatch")
                _require(event["previous_sha256"] == audit.head, "previous_sha256_mismatch")
                sha = event["sha256"]
                _require(isinstance(sha, str) and SHA256.fullmatch(sha), "invalid_event_sha256")
                _require(_digest({k: v for k, v in event.items() if k != "sha256"}) == sha,
                         "event_sha256_mismatch")
                _require(isinstance(event["kind"], str) and event["kind"], "invalid_event_kind")
                _require(not events or events[-1]["kind"] not in ("run_completed", "run_failed"),
                         "event_after_terminal")
                if not events:
                    _require(event["kind"] == "run_started", "missing_run_started")
                events.append(event)
                audit.events += 1
                audit.head = sha
        _require(events and events[-1]["kind"] in ("run_completed", "run_failed"), "missing_terminal_event")
        audit.run_status = events[-1]["kind"]
        if expected_head is not None:
            _require(SHA256.fullmatch(expected_head) and audit.head == expected_head, "expected_head_mismatch")
        netlist = any(e["kind"] in ("netlist_protocol", "netlist_v2_protocol", "netlist_observation",
                                   "netlist_physical_acquisition_plan") for e in events)
        for event in events:
            audit.event(event, netlist=netlist)
        _require(audit.forecasts > 0, "no_supported_frozen_prediction_hash")
        prediction_file = record_root / "predictions-frozen.json"
        if prediction_file.exists():
            frozen = json.loads(prediction_file.read_text(encoding="utf-8"),
                                object_pairs_hook=_object, parse_constant=_constant)
            _require(_digest(frozen) in {p["sha256"] for k, p in audit.latest.items()
                                        if k != "training_forecasts_frozen"},
                     "prediction_file_hash_mismatch")
            audit.prediction_files += 1
        if audit.run_status == "run_completed":
            _require(audit.training is None and audit.plan is None, "unfinished_measurement")
    except (ValueError, OSError, UnicodeError, KeyError, TypeError, IndexError,
            AttributeError, OverflowError, RecursionError) as exc:
        # Keep diagnostic output on one line; never echo record payloads/paths.
        error = re.sub(r"[^A-Za-z0-9_.:+-]", "_", str(exc))[:180] or type(exc).__name__
    return {"passed": error is None, "events": audit.events, "forecasts": audit.forecasts,
            "prediction_files": audit.prediction_files,
            "measurements": audit.measurements, "order_checks": audit.order_checks,
            "head_sha256": audit.head, "run_status": audit.run_status, "error": error}


def format_result(result):
    status = "PASS" if result["passed"] else "FAIL"
    fields = " ".join(f"{k}={result[k]}" for k in
                      ("events", "forecasts", "measurements", "order_checks", "prediction_files", "run_status", "head_sha256"))
    reason = "" if result["error"] is None else " reason=" + result["error"]
    return f"{status} {fields}{reason} {SCOPE}"


def main(argv=None):
    parser = argparse.ArgumentParser(prog="python -m benchmate verify",
                                     description="Offline integrity and recorded prospective-order checks; not a creation-time proof.")
    parser.add_argument("path", help="Run folder or events.jsonl")
    parser.add_argument("--expected-head", help="Compare against an independently retained terminal event SHA-256")
    args = parser.parse_args(argv)
    result = verify_run(args.path, expected_head=args.expected_head)
    print(format_result(result))
    return 0 if result["passed"] else 1
