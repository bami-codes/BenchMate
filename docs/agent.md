# Spark controller — synthetic instrument

Implemented October 27, 2026 (Asia/Seoul). This is a live API integration on simulated observations, not a physical bench demonstration, nonlinear discovery result or reliability benchmark.

## Run

```sh
uv run benchmate agent --case b6
uv run benchmate agent --case d01-r
uv run benchmate replay runs/YOUR_AGENT_RUN
```

The Meta key remains in the local ignored `.env`. Meta `muse-spark-1.3` runs with `medium` reasoning by default; `--effort max` applies maximum reasoning to every request in that run. This is not yet the planned adaptive reasoning policy. Baseten remains a separate smoke test.

## Control and evidence

`workflow.py` selects a development fixture and keeps its truth inside the synthetic acquisition callback. `agent.py` has no simulator or private-file imports. The model sees only declared candidates, measured summaries, current engine analysis, action rankings and remaining budgets. Full observations stay in the run record. Initial B1 and B6 tool inputs are identical for the same noise seed.

1. `inspect_experiment` reads the common unloaded exploration and engine output.
2. `measure(action, reason)` executes Spark's chosen menu action. The controller checks the action and physical-acquisition budget; it does not substitute the engine's preferred action. Instrument instructions and the model's reason are recorded. Mounting is simulated.
3. `verify_prediction` requires one supported candidate, records its predicted waveform, then obtains an independent capture at a different development amplitude. Verification observations never enter fitting. This development confirmation is not the final D2-frozen nonlinear holdout condition.
4. `finish_report` records current explanation, unresolved scope and next observation. A `verified` verdict requires matching numerical verification. The free-text wording is model-authored and is not a separately validated semantic proof.

Rejected tool calls return an error without acquisition or state mutation. The model may correct the request within the same API budget. Abstentions are recorded as abstentions; they are not counted as successful diagnoses. Missing final reports, protocol errors and exhausted API budgets leave `run_failed` records with the partial state.

## Bounds and provenance

- One exploration, at most three diagnostic acquisitions, one independent confirmation. A DC pair costs two acquisitions. Total count includes exploration.
- At most eight HTTP requests; 4,096 output tokens and 64,000 bytes of input JSON per request. No automatic retries, provider substitutions or execution of model-provided code.
- Each request reserves $1 from the existing separate Meta local allowance. This is not an actual charge or provider billing receipt. Returned usage and latency are recorded.
- Opaque reasoning is replayed in memory for Responses API continuity, never written to records. Only visible calls/results, API usage and reports are logged.
- The synthetic source restriction is explicit. Hardware calibration and hardware integration remain pending. X1/X2 private assemblies are never accessed by the controller.

## Verification

Tests cover equal initial observations, choosing a nonoptimal action without silently replacing it, premature confirmation rejection, diagnostic/API budget enforcement, failed prediction without refitting, protocol errors, four complete mocked provider loops, error recovery and secret/hidden-reasoning exclusion. Live API development runs are recorded separately from tests; they use the known fixed candidates and are not the planned final ten-run evaluation.

The original day-one validation remains in `day1-validation.json` as a record of the earlier engine-only and connectivity milestones. Controller live results are recorded in `agent-validation.json` after execution.

First integration block: all four known development cases completed on their first live API attempt, with four requests per case. B1 and B6 selected the shunt DC pair; D01-R and D01-C selected the 10 kohm load. Each committed and passed its independent synthetic confirmation. End-to-end times were 7.63, 11.02, 10.08 and 5.91 seconds respectively, including API latency and simulated acquisition, excluding physical mounting. All attempts are retained in `examples/agent-*-synthetic`; see [the measured results](agent-validation.json). A four-case development check is not evidence of final reliability or hardware accuracy.
