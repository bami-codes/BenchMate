# Case04 completed: supported clamp, diode removal, consistent rerun

Record: `examples/reading-cohort/2026-11-03/records/20261103T150223-18d6f08ac9/`.
The earlier host-link failure and wrong-E27 HOLD failure remain counted. This
completed continuation is not silently substituted as the first attempt.

Fault state: Spark chose three training experiments, rejected nominal and both
single-resistor alternatives, then proposed OUT→REF D1. The frozen proposed
structure passed reserved step/sine checks at3.616/2.815mV. This is predictive
support for a bounded structure, not a unique physical-location or chip-interior
claim. The operator subsequently removed the actual E30–E25 diode, retaining the
mini-board R1/R2 and D23–D25 REF jumper.

Restored state: a fresh Spark context saw only the same intended4.7k/20k netlist
and new observations. It chose unloaded small step, loaded small step and
unloaded5Hz small sine. All25 guard blocks passed, retaining12,800 frames.
Nominal reserved RMS: step2.975mV (worst region4.428), sine3.449mV (worst5.108),
all below the unchanged9mV whole/region limit. Native verdict: `consistent`.
Exact caption: **No mismatch in the tests Spark chose**. Nearby changed-value
models also fit; no claim all parts are correct. Native repair claim stays false.

Restored forecasts were published before either reserved capture in
`90e65c1d38ca2ef5ad5b9b7add5eed8eb696840c`; SHA-256
`af03587cc417de0bc51bd7edff280991201292774a088b64e8324375429b01d5`.
The restored child independently passes the unchanged original verifier:
235 events,4 forecasts,5 measured waveforms,19 order checks,1 prediction file.

## Unneeded reading withdrawn

The mandatory extra R1 request was not necessary to distinguish any remaining
declared explanations or choose the external repair. The user correctly raised
this. R1 was not isolated or measured, no reading score exists, and its published
forecast was **not exercised**. Its already-spent selection request/$0.00807645
remain counted. The root explicitly records a post-diagnosis workflow correction,
not retrospective compliance with the original mandatory-reading path.

This criterion is about useful discrimination/repair localization, not the
`structure_supported` label alone. The original diagnosis, numerical thresholds,
forecasts and failures were not changed. Original107 runtime source hashes remain.

The uploaded image is retained as documentary evidence. Its original DNG stays
private; fixed RAW conversion created metadata-free PNGs after the withdrawal.
Assistant preview was for publication quality only. No Spark/SAM image call,
component body-binding call or value reading was performed for case04. This is
not a claim of case04 SAM coverage or photo-based diode-absence verification.
No new restored mini-board photo was required for external-only repair.

## Verification and actual usage

Use `python -m benchmate.reading_terminal_pair verify <record folder>` for the
complete amended pair. The frozen `python -m benchmate verify <child folder>`
continues to verify each diagnostic child; the original root verifier still
requires a completed numeric reading. README/site examples must use the new
compound command for this record, not claim the old root command passed.

Full audit PASS:607 retained events,10 frozen forecasts,10 measured waveforms,
45 order checks,3 prediction files. Counts include retained prior failure and
withdrawn forecast records: they do not mean each forecast was physically tested.
Terminal head:
`d0e887cbaae82226633c15b10b11bfa5bfa1fd324cc005fe76449a3d10e90d3c`.
The one-line output is in `verification.txt`; keys/network are not needed.
Integrity/recorded-order verification does not prove original creation time,
wiring truth or operator assertions.

Restored run:6 Spark requests,$0.04837480 estimated from tokens. Case04 total,
including all failed stages and withdrawn selection:19 Spark,0 SAM,$0.15830530.
New reading-cohort total:36 Spark +1 SAM,$0.31035110. Conversion and local
verification added0 Meta calls/$0. SDK dollar reservations are not actual cost.

Last observed physical state: diode removed, C30–A55 load absent, mini-board
unchanged, output parked at REF, USB connected. No active serial controller.
