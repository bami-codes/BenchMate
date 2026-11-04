# Case03: terminal tests support the reduced sum, R1/R2 location unresolved

Pair: `runs/reading-cohort/20261104T041918-d1084cbeb4/`.
Public prefix: `examples/reading-cohort/2026-11-03/records/20261104T041918-d1084cbeb4/`.
Fault diagnostic: `diagnosis-faulted/20261104T042909-7ee516eccf/`.
The pair is still in progress; no operator component value, seal reveal,
restoration or restored rerun has yet occurred at this point in the record.

Scope and registration were published in **a2fd70a** before the new schematic
request. Fresh Spark transcribed R1 10kΩ IN-N1, R2 10kΩ N1-OUT, C1 1µF
OUT-REF, with no ambiguities. The operator confirmed the fresh reading and
USB-off fault assembly. Its private value/assembly record was sealed and never
supplied to Spark. The fixture port map contains only operator-confirmed lead
colors and contacts, not component values or labels inferred from known truth.

The shared v4 diagnosis AND training-only reading-profile adapter was published
in **2c135ab** before the first physical acquisition. Four independent analytic
software checks passed. The frame-anchored numerical model, original guards,
nine-millivolt whole AND regional criterion and1kΩ instrument path remain.

Fresh unarmed PING boot: `0bab4ee850d095931dbe488738dbdc0f`.
After the new-boot10second wait, Spark chose:

1. Unloaded large step, ±0.5V.
2. Loaded large step, ±0.5V.
3. Unloaded1Hz large sine,0.8V.

The operator connected and removed only E30-A55 for the selected load changes.
All guarded acquisitions passed. Nominal and changed:C1 were inadequate.
Both changed:R1 and changed:R2 were adequate, each fitting the varied resistor
to about **2,530.884Ω**, or a total series sum about **12,530.884Ω**.
This is a model estimate under the9mV engineering allowance, not an isolated
component measurement or a claim of exact resistance.

Models and command forecasts were frozen and pushed in
**968dd3dbeb990082beb2abb0f6aec39320456908** before two new reserved captures.
Both R1/R2 explanations passed without using reserved OUT in fitting:

| Reserved input | Whole RMS | Worst-region RMS | R1/R2 explanations |
|---|---:|---:|---|
| Unloaded step, ±0.35V |5.238mV|5.751mV|Both pass|
| Unloaded5Hz sine,0.65V |3.003mV|4.160mV|Both pass|

Native verdict: **indistinguishable**, components **R1,R2**, actor `muse_spark`,
source `physical`. Their terminal predictions are identical: the result does
not identify which board resistor changed. Native repair demonstration remains
false. The next useful operator reading must be selected by Spark and compared
with already-published source/range forecasts, not with a value supplied by the
runner or a photograph-derived value guess.

Numerical integrity/order audit passed: **236events**,4forecasts,5measurements,
19order checks,1prediction file. This is not proof of unique physical cause,
original creation time or calibrated component accuracy.

New usage so far: schematic1 + diagnostic6 = **7 Spark,0SAM**, estimated
**$0.06425980** ($0.00919170 intake + $0.05506810 diagnostic) from recorded
tokens at the retained cohort tariff, not a billing invoice. Reading cohort plus
labelled case02 demo reprocessing: **93Spark,4SAM,$0.93202170**. Offline software
checks added no paid call or hardware command.

The v3 candidate-kind/set photo stage and additive compound auditor are frozen
separately before photo receipt or operator value. Eleven contract tests pass.
An ongoing-prefix audit was exercised only in a temporary offline clone with
an explicit test-only terminal marker; it checked265events. The actual root
events and in-progress status were unchanged. This is an auditor integration
check, not a completed/failed physical pair. The complete pair command is
`python -m benchmate.reading_timing_verify_v4 <pair>`; numerical children retain
`python -m benchmate verify <child>`. Both are keyless/network-free.
