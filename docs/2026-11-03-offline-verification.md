# Offline evidence verification

From the root of a fresh clone, with Python 3.11 or newer:

```sh
python -m benchmate verify <run-folder>
```

Use `python3` if that is the local executable name. No installation, third-party
packages, API keys, `.env`, network, ngspice or hardware are needed. The command
reads records only. A checkout entry point resolves `src/benchmate` without
changing the frozen `cli.py`. The legacy installed `benchmate` console script
is unchanged; use the exact `python -m benchmate verify` command.

Exactly one stdout line; exit **0 for PASS, 1 for FAIL**. Fields: `events`
(hash-checked events), `forecasts` (embedded forecast hashes), `measurements`
(forecast-bound observations), `order_checks`, `prediction_files`, `run_status`
and terminal `head_sha256`. FAIL includes a reason. On a chain failure, `events`
counts its verified prefix; on a later semantic failure, it can count the full
chain.

## Checks

- Every event's SHA-256, its `previous_sha256` link and contiguous zero-based
  sequence. First link: 64 zeroes. First event: `run_started`. Last event:
  `run_completed` or `run_failed`, with no later events. Duplicate JSON keys,
  malformed JSON and non-finite numbers are rejected.
- The payload of each `training_forecasts_frozen`,
  `verification_forecast_frozen`, `b5_predictions_frozen` and
  `repair_prediction_frozen` is rehashed without its inner `sha256`, using the
  original `records.canonical` encoding. Netlist/B5 reference-origin hashes and
  historical pre-stimulus origin hashes use their original encodings too.
- A training forecast precedes its matching netlist observation with the same
  settings; it cannot cover multiple observations. Reserved verification needs
  a preceding matching freeze and publication receipt. Settings follow the
  frozen reserved menu; score/completion references must match its digest and
  follow the observations.
- For physical netlist measurements, the forecast precedes the acquisition plan
  **and non-HOLD serial CAPTURE command**, as well as the resulting observation.
  CAPTURE kind, sample count and sample period match its plan. B5 reserved and
  D01 repair measurements have corresponding checks. Pre-stimulus HOLD captures
  are calibration, not scored observations.
- If `<run-folder>/predictions-frozen.json` exists, its canonical hash must
  match a recorded verification/repair freeze. Passive pilot publication stores
  an envelope elsewhere: the embedded event forecast and receipt digest are
  checked, but its URL is not fetched and its remote commit is not authenticated.

No source snapshot is executed and no event-specified path/URL is opened. The
fixed sibling `predictions-frozen.json` is the only optional sidecar read.
Older formats lacking supported embedded forecast hashes, and QA-only records,
fail with `no_supported_frozen_prediction_hash`; they are not silently promoted
to verified prediction evidence.

A failed experiment can **PASS this audit with `run_status=run_failed`**. PASS
does not assert successful diagnosis, restored hardware, correct measurements,
genuine hardware/model provenance, reproducible simulations, or successful
completion of every planned test.

## Scope and time: README-ready sentence

> Checks internal record integrity, frozen-prediction hashes and recorded predict-before-measure order; it does not prove creation time or rule out a fully rewritten hash chain. Timing is supported separately by the frozen protocol and published preregistration commit history.

The output repeats the short form
`scope=internal_integrity+recorded_order creation_time=unproven`. Event timestamps
are self-reported, and Git author/commit times are not an independent timestamp
authority. Published preregistration and prediction commits corroborate the
protocol's order; this offline command does not authenticate their availability
or clock time.

To compare against a terminal digest retained **independently before review**:

```sh
python -m benchmate verify <run-folder> --expected-head <retained-sha256>
```

A fully regenerated history can pass its own chain, but fails an independently
pinned `--expected-head`. Copying the current output into that option provides
no independent protection.

## Exact preserved-rehearsal output

This is the **Nov 1 scripted/mock repair rehearsal**, not a new physical case or
an official result. No new model or hardware calls were made.

```sh
python -m benchmate verify examples/d01-repair-rehearsal/2026-11-01/final_success/20261101T003829-400778438d
```

```text
PASS events=39 forecasts=1 measurements=2 order_checks=6 prediction_files=1 run_status=run_completed head_sha256=3214630351e6f79ed4819a1ae1e35ff19482bc3853f770fc6fc12f822564e76b scope=internal_integrity+recorded_order creation_time=unproven
```

Once the chosen official run exists, replace the path and output with its actual
output. Do not present this rehearsal as physical restoration evidence.

## Restoration caption: site and video

Use **“No mismatch in the tests Spark chose”** for the restored run only when
its recorded netlist `agent_report.verdict` is `consistent` and its actual actor
is `muse_spark`. Preserve the raw engine enum. Mock/scripted records must name
their actual actor.

The frozen engine already has this meaning:

- `netlist_diagnosis/session.py:outcome` returns `consistent` only when `nominal`
  survives verification: an adequate training model that then passed both
  reserved conditional checks. The allowance is 9 mV for the whole waveform
  **and every region**.
- The prompt explicitly defines a nominal pass as no mismatch detected by the
  checks, not proof that all parts are correct. It is measured-IN conditional
  predictive adequacy, not unique identification or a comprehensive health test.
- Spark chooses training experiments; the two reserved inputs are fixed by the
  protocol. Keep this adjacent detail: “Spark chose the training experiments;
  two reserved inputs were fixed in advance.”
- Other verdicts, guard failures and missing verification retain their actual
  outcome. `verify` PASS alone cannot justify the caption. Link the operator's
  restoration record and fresh run separately, preserving the runtime's
  `physical_repair_demonstrated:false`.

Root README, site and video are Claude-owned; their requested changes are in
`2026-11-02-claude-review.md`. Codex has not edited those files.
