# Case05 restored attempt2: consistent on fresh conditional held-back tests

Result: **No mismatch in the tests Spark chose**.

Local run: `runs/channel-timing-followup/20261104T034748-10ab5af750/`.
Public run: `examples/channel-timing/2026-11-04/records/20261104T034748-10ab5af750/`.
Case-level linking summary: `examples/channel-timing/2026-11-04/case05-completion.json`.

The general frame-anchored v4 code, source snapshots, full engineering regression,
independent analytic controls and counted attempt2 registration were committed
and pushed in **7675361**, before this run's PING, paid requests or stimuli.
The rejected first linear interpolation and adverse results remain in **ba95743**.
Original107 sources, earlier official verdicts and selected-first-attempt flags
remain unchanged. Original05 restored attempt1 remains counted **abstained**.
Attempt2 is a separate counted followup and is not first-selected.

## Actual restored setup and choices

The operator confirmed “USB 연결 완료 · 복원·무부하 배선 그대로” after the
v4 publication. The mini-board stayed W1 B3-B8, R1 10kΩ E8-E13 and C1 105
C8-C13. Green IN remained large A35→mini A3; original OUT/REF and the1kΩ
instrument/REF/GND wiring were retained. External20kΩ and output-load/bypass
jumpers were absent initially. No mini-board component was changed.

Fresh unarmed PING boot: `15dfdfcfbb82a3e13af0824cebdfa1a0`.
The runner waited10seconds after observed new boots. Spark independently chose:

1. Unloaded small step, ±0.2V.
2. Loaded large step, ±0.5V.
3. Unloaded5Hz small sine,0.15V.

The operator connected and removed only E30-A55 for the two requested fixture
changes. All25 logged electrical guards passed, with raw A3 primary3mV unchanged.
No k/gain/offset/timing parameter was fitted. Existing R1/C1 alternatives remain
unobservable under W1 and measured-IN conditioning; the nominal family passes
but this does not establish every component value.

## New prospective reserved verification

Training parameters and command forecasts were frozen and remotely published
before the two new held-back captures in commit
**6a6a87fde87c988ada84d386359bdadc5853daa8**.
Prediction SHA256:
`facfcb669c676cd0e22d6775badea086aa2dd395e9841208aada4c6be601ced1`.
No reserved OUT was used for fitting, and there was no retry or post-holdout fit.

| Fresh reserved input | Conditional whole RMS | Conditional worst region RMS | Conditional result |
|---|---:|---:|---|
| Unloaded step, ±0.35V |2.616mV|4.344mV|Pass|
| Unloaded5Hz sine,0.65V |3.007mV|3.930mV|Pass|

Every region and whole-waveform score is below the unchanged9mV threshold.
Native verdict: **consistent**, actor `muse_spark`, source `physical`.
Survivors include nominal, changed:R1 and changed:C1. The input-parallel R/C
ambiguity remains explicitly unresolved. The standard caption is therefore
conditional absence of mismatch, not proof all parts are correct.

The separate pre-measurement command-input predictions are also retained:

| Fresh reserved input | Command whole RMS | Command worst region RMS | Command result |
|---|---:|---:|---|
| Step |5.635mV|12.666mV|Fail|
| Sine |2.400mV|3.146mV|Pass|

The step command forecast failed its regional limit. It assumes the declared
ideal buffered DAC plus1kΩ rather than the newly measured input waveform; this
is a retained drive-path-model limitation. It does not pass merely because the
conditional check passes. The registered diagnostic criterion is the separately
reported measured-IN conditional check. No driver level was refitted from OUT.

Native `physical_repair_demonstrated:false` remains unchanged. The case-level
summary separately records the operator's external-only restoration followed by
a consistent new-context rerun. Spark's new-context phrase “No repair made”
refers to its current diagnostic actions; earlier operator repair history was
not supplied to that model context. The summary does not overwrite its report.

## Evidence, audit and usage

No additional photograph, SAM or operator value request was made. The unchanged
mini-board uses its retained original fault-capture photograph with that capture
label; it is not presented as a newly taken restored image. The original fault
diagnosis,19.85kΩ fit, published W1 path forecast, SAM→W1 selection, isolated DMM
report and subsequent sealed20kΩ assembly reveal remain in the original pair.

Keyless numerical audit: **238 events**,4forecasts,5measurements,19order checks,
1frozen prediction file, PASS. The extra keyless compound audit also rechecked
the **484-event original pair**, qualified source/evidence hashes and counting.
An additive audit-only checker also validates the4-event bound preflight and
registered protocol/design/result artifacts. Four tamper-control tests passed.
This checker was added after the run; it changes no numerical/runtime source,
forecast, threshold, measurement or verdict.
These audits prove retained internal integrity and recorded order, not original
creation time, physical wiring truth, calibrated meter accuracy or unique cause.

```sh
PYTHONPATH=src .venv/bin/python -S -m benchmate verify \
  examples/channel-timing/2026-11-04/records/20261104T034748-10ab5af750
PYTHONPATH=src .venv/bin/python -S -m benchmate.channel_timing_audit_v4 \
  examples/channel-timing/2026-11-04/records/20261104T034748-10ab5af750
```

Actual new Spark requests: **6**, estimated **$0.06467530** from recorded tokens;
new SAM requests:0. Case05 cumulative: **21 Spark,1SAM,$0.22192085**.
Reading cohort plus separately labelled case02 demo reprocessing:
**86 Spark,4SAM,$0.86776190**. Estimates use the retained cohort tariff, not
billing invoices or SDK reservation amounts. All offline tests and verification
added zero API requests and zero hardware commands.

The runner confirmed final output at REF and returned normally. The last fixture
state is restored and unloaded. Remaining case work is03 and the separately
qualified06 LED path, with LED last.
