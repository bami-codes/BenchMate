# Case05: restored run abstained; original fault/location evidence retained

Pair: `examples/reading-cohort/2026-11-03/records/20261104T021333-c80ef3617e/`.
Local pair: `runs/reading-cohort/20261104T021333-c80ef3617e/`.
Restored child: `diagnosis-restored/20261104T030600-47c67ef048/`.
The pair's evidence collection is closed. Its restored verdict is **abstained**,
not consistent and not a demonstrated successful repair.

The operator confirmed “복원 완료 · 미니보드 그대로 · USB 재연결” after the
USB-off external-20k removal, green IN fixture-end change A31 to A35 and original
OUT/REF reconnection request. W1 B3-B8, R1 10kΩ E8-E13 and C1 105 C8-C13 stayed
unchanged. Fresh unarmed PING boot: `9cc85a5d2949f74d7ef57d1b8bbd1861`.
The restored assembly was sealed locally and never supplied to Spark.

Spark independently selected unloaded small step, loaded small step and
unloaded 5Hz small sine. The operator completed both requested load changes,
and every guarded acquisition passed. There was no guard failure or automatic
retry/rearm. Final output-at-REF confirmation is retained.

| Training input | Nominal whole RMS | Nominal worst region RMS | Nominal fit |
|---|---:|---:|---|
| Unloaded step, ±0.2V |3.728mV|9.303mV, 0–5ms|Rejected|
| Loaded step, ±0.2V |2.854mV|10.167mV, 0–5ms|Rejected|
| Unloaded 5Hz sine, 0.15V |4.438mV|5.986mV|Pass|

The whole AND every-region limit remains 9mV. Single R1/C1 variants cannot
alter conditional OUT when W1 ties it to measured IN, so those shunt values
remain unobservable here. Spark made no new structure proposal and ended with
`abstained`: small bipolar residuals, including OUT above IN, were not explained
by its passive alternatives. No reserved verification was run, no reserved
prediction file was published, and `physical_repair_demonstrated:false` remains.
`restored_caption` is null: **“No mismatch in the tests Spark chose” does not
apply to this run**.

The first fault diagnosis and path-reading result remain intact: terminal series
path 19.85kΩ passed held-back tests; the source-specific isolated mini-board
reading supported the external-path explanation; the subsequently opened seal
contained the nominal external 20kΩ. This does not turn the restored abstention
into a pass. No repeat mini-board photo, SAM call or value reading was requested;
the original photograph retains its original fault-capture label.

## Post-hoc timing check, not an official replacement score

After the abstention, only existing logs and source were inspected. Recorded
A1/A2 `analogRead` completion skew is 52–53µs. The frozen explicit-wire adapter
holds each measured IN value across a command frame. It therefore does not
represent a changing IN level between the channel reads during an edge.

An exploratory calculation interpolated measured IN linearly at the recorded
OUT completion timestamps, without fitting any offset, gain, time shift or
other parameter. Whole/worst-region RMS became:

| Input | Post-hoc whole RMS | Post-hoc worst region RMS |
|---|---:|---:|
| Unloaded step |3.450mV|3.805mV|
| Loaded step |2.516mV|6.460mV|
| Unloaded sine |4.370mV|5.872mV|

These numbers support investigating the input interpolation/time model.
Completion timestamps are not calibrated aperture times, and interpolation
does not establish the actual between-sample waveform. Hardware channel
response and connection effects are not excluded. This is not proof of cause,
a runtime change or an official rescore. The original verdict remains abstained.
The separately labelled calculation is retained in
`examples/reading-cohort/2026-11-03/posthoc/case05-restored-timing/analysis.json`,
bound to the original child event-file hash. Any prospective replacement needs
separate qualification before new hardware work. No new automatic attempt is
authorized by this analysis.

## Verification and usage

The keyless restored-child verifier passed: **160 events**,3 forecasts,
3 measurements,9 order checks,0 reserved-prediction files.
The keyless wire compound verifier passed on the completed public copy:
**484 events**,8 forecasts,9 observations,33 order checks,2 prediction files.
These are record-integrity/order results, not diagnostic-accuracy passes or
proof of original creation time. The audit result is in
`examples/reading-cohort/2026-11-03/audits/20261104T021333-c80ef3617e-wire.json`.

New restored diagnostic usage: **5 Spark requests, estimated $0.04948945**.
Case05 total: **15 Spark,1 SAM, estimated $0.15724555**.
Reading cohort plus separately labelled case02 photo reprocessing:
**80 Spark,4 SAM, estimated $0.80308660**. Estimates use the retained cohort
tariff, not billing invoices; reservation amounts are not presented as charges.
All post-hoc analysis, scoring, rendering and verification added zero requests
and zero hardware commands.

The operator then confirmed **“USB 분리 완료 · 배선 유지”**. The board is
disconnected with restored no-load wiring retained. No retry has been started.
