# BenchMate

BenchMate chooses measurements that distinguish circuit hypotheses, then checks its predictions against observations.

This repository starts during the Meta Global AI Developer Hackathon on October 27, 2026 (Asia/Seoul). It is a solo indie project. The target is a low-voltage, low-frequency bench assistant using Muse Spark and an Arduino UNO R4 fixture.

## Status

Day-one prototype: four synthetic RC experiments run through ambiguity, action ranking, a new acquisition, a committed prediction and a fresh verification. A live Muse Spark controller now chooses measurement and verification tools on the synthetic instrument and submits a structured report. The engine owns numerical evidence and enforces acquisition limits and confirmation requirements.

No hardware accuracy, successful physical repairs, B5 nonlinear discovery or holdout generalization result has been demonstrated yet. Synthetic data is always labeled as synthetic. The current finite-candidate engine is not the planned continuous Bayesian/model-discovery engine.

## Quick start

Python 3.11+ on macOS or Linux:

```sh
uv sync --extra dev
uv run benchmate doctor
uv run pytest -q
uv run benchmate simulate --case b6
uv run benchmate simulate --case d01-r
# Replace the path with the run directory printed by simulate:
uv run benchmate replay runs/YOUR_RUN
# Included, reviewable synthetic recording:
uv run benchmate replay examples/b6-synthetic
```

Other fixtures: `b1`, `d01-c`. Simulator truth lives in `simulation.py`; the diagnosis module receives observations and declared candidate knowledge only. Its decision logic never receives fixture IDs or private holdout files.

The initial unloaded observations leave both candidates unresolved. Numerical prediction separation ranks a shunt DC pair for B1/B6 and a 10 kohm load for D01. A prediction is recorded before independent confirmation data is acquired. DC pairs count as two physical acquisitions; confirmation is one fresh step.

## Live Spark experiment controller

With `MODEL_API_KEY` in the ignored local `.env`:

```sh
uv run benchmate agent --case b6
uv run benchmate agent --case d01-r
# Replay the returned path without spending tokens:
uv run benchmate replay runs/YOUR_AGENT_RUN
# Included live-model run on synthetic observations (no API call):
uv run benchmate replay examples/agent-b6-synthetic
```

Spark receives observations and declared candidates, chooses from ranked actions, requests independent verification and writes a three-part report. It cannot see fixture identity or truth. The model's selected action is executed as requested; it is not silently replaced by the top-ranked action. Invalid calls return tool errors, and a confirmed verdict is accepted only after a matching independent prediction succeeds.

Each run permits one common exploration, at most three diagnostic acquisitions and one confirmation, with at most eight Meta API requests. Default reasoning is `medium`; `--effort max` changes it for the entire run. Temperature remains the provider default. Raw captures, model decisions, tool errors, committed predictions, verification and usage are recorded. Synthetic mounting does not count as a real human intervention.

`simulate` remains engine-only; `agent` calls the live model with synthetic instrument data; `api-smoke` checks connectivity. None is a live hardware experiment. See [controller design and validation](docs/agent.md).

The first live controller check completed all four development cases, one attempt each, using four API requests per case. B1/B6 selected the shunt DC pair; both D01 variants selected the 10 kohm load. All four then passed independent synthetic prediction checks. These are integration checks, not a success-rate estimate. [All four recordings and measured results](docs/agent-validation.json) are included.

## Provider connection

Create `.env` from `.env.example` and enter keys locally. Never commit that file.

```sh
uv run benchmate api-smoke --provider meta
uv run benchmate api-smoke --provider meta --effort max
uv run benchmate api-smoke --provider baseten
```

- Meta: `https://api.meta.ai/v1/responses`, `muse-spark-1.3`, automatic tool selection and stateless encrypted reasoning replay.
- Baseten: `https://inference.baseten.co/v1/chat/completions`, exactly `meta-models/muse-spark-open-1026`.
- A smoke test makes at most two HTTP requests and runs a tool that returns **synthetic** observations. There are no automatic retries or provider substitutions. Protocol success is not a diagnosis benchmark.
- Runs store visible reports, tool calls, usage and latency, not API keys or encrypted reasoning. Failed and incomplete runs are explicit.
- Local allowance: $1 is reserved per bounded HTTP request, with separate Meta ($120) and Baseten ($80) totals. Reservations are not actual charges. Baseten hackathon pricing remains unverified, so this allowance is not a guaranteed provider billing cap. Usage elsewhere is not covered.

## Hardware bring-up

Install `arduino-cli` and `ngspice`. The wrapper keeps Arduino packages in the ignored project `.arduino` directory:

```sh
sh scripts/arduino.sh core update-index
sh scripts/arduino.sh core install arduino:renesas_uno
sh scripts/arduino.sh board list
sh scripts/arduino.sh compile --fqbn arduino:renesas_uno:unor4wifi firmware/bringup
```

Bring-up firmware supports PING and buffered raw ADC acquisition only; DAC drive is disabled. It records A1–A4 with per-channel read-completion timestamps. It does not provide calibrated voltage or sample-aperture timing. Hardware inference is deliberately unavailable until the D2 fixture calibration exists. See [the Korean day-one guide](docs/day1.md) for upload and capture instructions.

## Records and validation

`runs/` is ignored by default. Each run is an append-only JSONL event chain. Replay checks integrity and displays the stored result without calling a model. A hash chain detects modification against the stored chain, but is not an external timestamp or proof against complete rewriting.

Tests cover closed-form RC behavior, unobservable branches, shunt Ohm's-law values, D01 discrimination, wrong-family rejection, independent verification failure, stimulus constraints, truth separation, corrupted/incomplete records, provider protocols, credential redaction and hardware packet validation. Controller checks also cover premature confirmation, failed verification, acquisition/API budgets and model error recovery. When ngspice is installed, independent operating-point cross-checks also run.

See [the day-one validation record](docs/day1-validation.json) and the included `examples/` recordings. API examples contain live model responses to synthetic observations. They are connectivity evidence, not hardware trials or generalization results.

## Experiment commitments

See [the preregistration](docs/preregistration.md) and [the holdout commitments](docs/holdout-commitments.json). The private assembly files are deliberately excluded from Git. Hashes commit to a configuration; they do not establish a blind test or prove that data was never inspected.

## Built during the hackathon

Developed during the event: the Python circuit model, finite-candidate engine, live Spark controller with a synthetic instrument, JSONL records/replay, provider probes, raw-acquisition firmware and tests. Code was developed with Codex assistance. Muse Spark controls the integrated synthetic experiments; Spark Open is used in the Baseten provider probe. Muse Code has not yet been used.

Reused dependencies/tools: NumPy, SciPy, HTTPX, pySerial, pytest, Arduino CLI, Arduino Renesas UNO R4 core, ngspice and GitHub CLI. Planning documents predate the implementation and are not represented as working software. [Initial experiment protocol](docs/preregistration.md) records the distinction.

## Scope

Only the declared fixed RC candidates are supported today. Independent Gaussian synthetic noise is a development assumption. Continuous parameter marginalization, calibrated AR(1) likelihood, nonlinear netlist generation/validation, hardware agent integration, fixture calibration and user-facing instruction graphics remain to be implemented. No claim of replacing an oscilloscope or diagnosing arbitrary powered circuits is made.

License: MIT; third-party dependencies retain their own licenses.
