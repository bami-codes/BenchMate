# BenchMate

BenchMate chooses measurements that distinguish circuit hypotheses, commits a prediction, and checks it against a new observation. Built during the Meta Global AI Developer Hackathon, starting October 27, 2026 (Asia/Seoul), as a solo indie project.

## Current evidence

Implemented: continuous one-state RC inference, live Muse Spark experiment control, model-authored nonlinear netlists executed by ngspice, a synthetic repair sequence and an offline execution viewer. **All diagnosis results so far use synthetic observations. No hardware accuracy, physical repair or holdout generalization has been demonstrated.**

- Parameter fitting and normalized evidence integration are separate. The tau=RC transformation preserves the original R/C prior. Mystery specimens share the same two structure families; schematic repair priors require explicit `--mode repair`.
- Whole traces and predefined transient/phase regions use common noise whitening. Per-channel AR(1) parameters are supported; current defaults are uncalibrated synthetic assumptions.
- The 85-condition menu includes six configurable frequencies, 0.2/1 V sines, steps, 4.7k/10k loads and shunt states. The physical frequency limit remains pending D2.
- Generated element connections and diode orientation reach ngspice unchanged. Only numerical R/C values are refined on training observations. Both reserved predictions precede both verification acquisitions.
- D01 repair predicts the replacement's effect before simulated component replacement, then checks two new observations.
- D2 DAC/ADC firmware compiles for UNO R4 WiFi and Minima, with 512-sample raw blocks and actual per-channel read-completion timestamps. It has not been uploaded or physically validated.

See [latest validation](docs/preboard-validation.json). Both nonlinear attempts are retained: the first max-reasoning call exhausted its 4,096-token output cap before a proposal; the second used an explicit 8,192-token cap and passed two synthetic verification conditions. This is a development check, not a reliability estimate.

## Run

Python 3.11+, `uv`, and ngspice for nonlinear work:

```sh
uv sync --extra dev
uv run benchmate doctor
uv run pytest -q
# Engine only, no API calls:
uv run benchmate simulate --case b6 --r-scale 1.01 --c-scale 1.05
uv run benchmate simulate --case d01-r --mode repair
uv run benchmate repair --case d01-c
# Live Spark, with MODEL_API_KEY in local .env:
uv run benchmate agent --case b6
uv run benchmate agent --case d01-r --mode repair
uv run benchmate discover
uv run benchmate repair --case d01-r --live
```

`--case` selects simulator truth only. The model receives observations and declared knowledge, not specimen identity. Current `--mode` is a user declaration, never selected automatically from the case ID. `discover` defaults to max reasoning; ordinary `agent` defaults to medium. Temperature is the provider default. `repair --live` uses Spark for diagnosis and numerical posterior predictions for repair. All currently use synthetic instruments.

## Review recorded evidence

```sh
uv run benchmate replay examples/discovery-synthetic
uv run benchmate view examples/discovery-synthetic --output runs/discovery-report.html
```

Open the HTML locally. It contains the report, observed/predicted waveforms, generated netlist, logical instrument connections and event history. Moving backward hides later reports/observations. It makes no API calls and is a read-only recording viewer, not a hardware control UI.

JSONL replay/export verifies the hash chain. This is not external attestation or proof against complete record rewriting. `runs/` is ignored; reviewed examples are explicitly exported. Earlier fixed-value milestones remain in historical examples/tests and `workflow.py`/`engine.py`; current CLI diagnosis uses `experiments.py`/`inference.py`.

## Hardware preparation

```sh
sh scripts/arduino.sh board list
sh scripts/arduino.sh compile --fqbn arduino:renesas_uno:unor4wifi firmware/bringup
sh scripts/arduino.sh compile --fqbn arduino:renesas_uno:unor4wifi firmware/instrument
```

Start with non-driving raw bring-up. Then follow [D2 instrument instructions](docs/instrument.md): establish REF with the DUT disconnected, attach the test circuit, and request capture separately. Supply/DAC reference is entered from measurement. Compilation does not establish waveform quality, sample rate or accuracy. Hardware inference remains blocked pending fixture calibration.

## Providers and bounds

- Meta: `https://api.meta.ai/v1/responses`, `muse-spark-1.3`. Encrypted reasoning is replayed in memory, never logged.
- Baseten connectivity: `https://inference.baseten.co/v1/chat/completions`, exactly `meta-models/muse-spark-open-1026`. Use `benchmate api-smoke --provider baseten`.
- Integrated runs allow at most eight requests. Ordinary calls allow 4,096 output tokens / 64 KB JSON; nonlinear discovery allows 8,192 / 128 KB. No automatic retries or silent provider substitutions.
- $1 is reserved per bounded request from separate Meta ($120) and Baseten ($80) local allowances. Reservations are **not actual charges** and can stop work before credits are spent. External usage and unverified Baseten pricing are separate.
- Keys stay in `.env`; private assemblies stay in `.private/`. Neither is committed. Raw records omit credentials and hidden reasoning.

## Scope

The mystery grammar is currently one-state RC with/without an input branch, not the full planned two-stage grammar. Priors, numerical convergence and approximate predictive checks are documented in [inference notes](docs/inference.md). The nonlinear result uses a generic development diode model, not characterized physical 1N4148 parameters. Fair baseline evaluation, physical repeatability and the final ten-run block remain pending.

D2 must establish supply/REF, DAC/buffer behavior, offsets/gain, actual channel timing/jitter, noise/model error, current detection, settling and usable frequencies. X2 stays unopened until final pipeline freeze. See [preregistration](docs/preregistration.md) and [holdout commitments](docs/holdout-commitments.json).

## Provenance

Implemented during the event: circuit solvers, inference, tools, provider transport, netlist validation/ngspice harness, synthetic repair, records/viewer, firmware and tests. Developed with Codex assistance. Muse Spark runs in the included agent/discovery recordings; Spark Open has a connectivity recording. Muse Code has not yet been used.

Dependencies/tools: NumPy, SciPy, HTTPX, pySerial, pytest, Arduino CLI/Renesas UNO R4 core, ngspice and GitHub CLI. MIT license; dependencies retain their own licenses.
