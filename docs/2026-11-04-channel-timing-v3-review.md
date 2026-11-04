# Recorded-channel timing candidate: tested, rejected for hardware

The fixed, general interpolation candidate was implemented and evaluated within
the operator's 45-minute offline scope. **It is not qualified or activated.**
It helps the direct-input-capacitor control but can reject analytically correct
other circuits. Case05 restored attempt2 has not started. The existing case05
abstention remains counted and every original official result stays unchanged.

## Implementation and unchanged rules

`src/benchmate/channel_timing_v3.py` accepts the same bounded passive R/C/D/W
netlists. For measured-input templates, source knots use each recorded frame
time plus A1 completion delay; the source is piecewise linear between those
knots, with endpoint holds. OUT is sampled at frame time plus its own A2 delay.
The actual timestamp arrays are used: **53µs is not hardcoded in the model**.
Known pre-measurement DAC command templates retain their original held-command
semantics. The same rule is used for all passive topologies, with no case labels
or specimen truth supplied to the solver.

There are no fitted delay, gain, offset or other new timing parameters. No OUT
samples are accepted by the prediction function. Existing R/C and diode
parameters may still be fitted using the original bounded training-only fitter;
reserved OUT never enters those fits. The original simulator current/voltage
bounds, menu, raw A3 3mV guard and whole AND every-region **9mV** scorer remain.
All original107 frozen sources have their original hashes. The live experiment
runtime still imports the original backend; this offline candidate is not
silently substituted into it. LED hardware remains separately unqualified.

Nine focused software tests passed, including input/OUT separation, recorded
timestamp use, reserved-output exclusion, unchanged command forecasts, an
independent positive control and an explicitly expected negative control.
Passing these software tests does not mean the model passed qualification.

## Independent analytic controls

The truth generator in `scripts/timing_synthetic_v3.py` is independent of both
ngspice prediction paths. It solves the declared ideal DAC hold → 1kΩ instrument
resistor → DUT series resistance → parallel R/C response analytically, and then
samples IN and OUT 53µs apart. It covers seven representative normal/fault
circuits, each with the eight menu inputs and two reserved settings: **70 checks**.
These are simulations, not physical evidence. The series-R-chain control is
representative, not a new measurement or validation of case03's actual board.

For the 05-type 1µF∥10kΩ direct-input load with the reserved ±0.35V step:

| Predictor | Whole RMS | Worst region RMS | Result |
|---|---:|---:|---|
| Original |1.846mV|13.206mV|Fail|
| Recorded-time linear candidate |0.416mV|2.749mV|Pass|

But other-design invariance **fails**. Across the other60 controls,17 formerly
passing checks fail under the candidate. For example, a correct 4.7kΩ/1µF RC
with the same instrument resistor and reserved step goes from **1.284mV** to
**15.788mV** worst-region RMS. The20kΩ series-chain reserved-step control stays
passing (0.103→5.912mV), illustrating that the regression is not universal.
All70 outcomes, including unchanged and adverse cases, are in `synthetic.json`.

This is an independently known counterexample, not merely disagreement with old
official outcomes. A line between sparse measured IN points can smooth a real
DAC jump before its command boundary and change the drive seen by a dynamic
circuit. Recorded completion times alone do not establish that between-sample
waveform. The 05 improvement is not sufficient evidence for general deployment.
The precise physical cause of the original case05 residual is not proven.

## Complete original-record regression

`scripts/timing_regression_v3.py` covers every assigned current-cohort01/04/02/05
attempt, including failed and restored-only followups. Twelve diagnostic logs
contain44 complete captures. Case04's earlier intake failure has no diagnostic
log and is separately listed rather than omitted. Five assigned original
official-protocol runs, now development relative to the reading-assisted
pipeline, add16 captures in a separate reporting group. Total: **17 unique logs,
60 captures**. Archival mirrors are deduplicated by complete event-file hash.

Two comparisons are retained: (1) original fitted/frozen parameters rescored
without refitting, and (2) training-only refits of the same declared hypotheses
and the same Spark-proposed structures, followed by the original reserved
captures where they exist. This holds the agent's actions fixed. It cannot
predict what Spark would choose under a new model and is not a new experiment.

Six same-action replay outcomes turn from non-abstention into abstention:

| Reporting group | Record | Original | Candidate replay |
|---|---|---|---|
| Current |01 fault, attempt1|changed|abstained|
| Current |01 restored followup, attempt2|consistent|abstained|
| Current |04 fault, attempt3|structure_supported|abstained|
| Current |02 fault, attempt2|changed|abstained|
| Current |02 restored followup, attempt4|consistent|abstained|
| Prior protocol / development |01-R01|consistent|abstained|

Current04 restored and05 fault retain their replay outcomes. Prior01-F04 also
retains its changed verdict. Case05 restored's nominal/R1/C1 training fits turn
adequate, but its reserved pair was never acquired; its status is therefore
**unverified training only**, not consistent. Original guard/transport failures
stay execution failures, even when some complete captures can be rescored.

There are **79 changes at different decision levels**:58 fixed-parameter
waveform pass/fail flips (11 fail→pass,47 pass→fail),15 training-refit status
flips and the6 replay outcomes above. These are not79 independent runs.
The full table includes every change in both directions; unchanged regional
scores and errors are retained in the JSON as well:

- `examples/channel-timing/2026-11-04/candidate01/all-changes.md`
- `examples/channel-timing/2026-11-04/candidate01/replay/regression.json`

The committed `corpus.json` binds all17 logs to already-public files by SHA256,
so no private run folder, API key or network request is needed to reproduce the
offline calculations (local Python dependencies and ngspice are required):

```sh
PYTHONPATH=src .venv/bin/python scripts/timing_regression_v3.py \
  --corpus examples/channel-timing/2026-11-04/candidate01/corpus.json \
  --output /tmp/benchmate-timing-replay-new
PYTHONPATH=src .venv/bin/python scripts/timing_synthetic_v3.py \
  --output /tmp/benchmate-timing-synthetic-new.json
```

Use a previously nonexistent output path. Original source and input event-file
hashes were checked before/after the regression; all remain unchanged.

## Hardware decision and next attempt

This candidate is frozen as **offline-only / rejected for hardware**, with its
source snapshot, synthetic controls, complete regression and next-attempt plan.
It has no new hardware entry point and does not change existing registrations.
No hardware QA or case05 attempt2 was run. A prospective plan names the next
case05 restored diagnostic **attempt2**, links the counted original abstention,
and blocks execution until a suitable model and separate QA are qualified,
committed and pushed. A later success must not replace the original selection.

Further general work must distinguish measured sample timestamps from actual
within-frame DAC/IN behavior, while retaining the counterexamples above. A
case05-only patch or a result-fitted timing constant is not accepted as a general
fix. For now the board remains USB-disconnected with restored wiring unchanged.

New paid requests: **Spark0, SAM0, $0**. New hardware commands: **0**. No DNG,
location metadata, frontend file or hidden case-mapping file was used or changed.
