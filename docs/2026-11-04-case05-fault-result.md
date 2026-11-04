# Case05 fault diagnosis passed; independent path reading/photo pending

Current local pair: `runs/reading-cohort/20261104T021333-c80ef3617e/`.
Public prefix: `examples/reading-cohort/2026-11-03/records/20261104T021333-c80ef3617e/`.
This pair is in progress, not completed. Its first fault diagnostic child is
`diagnosis-faulted/20261104T022359-f6e37b9f05/`.

The operator confirmed the fresh10k/1uF parallel design and direct IN-OUT wire,
then built it with R1 at **mini E8-E13**, rather than proposed D8-D13 (same two
nodes). This actual position is retained in the review and assembly records.
New unarmed PING boot was `a1076db4724a830c9681c2e5853b0fc3`.

Spark chose unloaded small step, loaded5Hz small sine, then unloaded1Hz large
sine. All guarded acquisitions passed. Nominal and the single-R/C-change models
failed; Spark proposed replacing the ideal IN-OUT connection with a series R2.
The fitted series path is **19,851.78774353608ohm**. No unique physical location
is identified by that terminal fit.

Native verdict: `structure_supported`, actor `muse_spark`, source `physical`.
Both held-back inputs passed without refitting:

| Input | Whole RMS | Worst region RMS |
|---|---:|---:|
| Unloaded step, ±0.35V |3.564mV|5.666mV|
| Unloaded5Hz sine,0.65V |2.131mV|3.498mV|

All remain below the unchanged9mV whole AND region limits. Frozen prediction
SHA256: `a4c74914682f3f62de1694e9d2b5965661ae9b135e45805cbb008d136cfb8700`.
Forecast publication commit: `a573c3c` before reserved acquisition.
Diagnostic audit PASS:241events,4forecasts,5waveforms,19order checks,1prediction
file, terminal head `25b30591d5465fc5496727f6fa136f0bc010d5337f021dbd673da57d5425e631`.
Native `physical_repair_demonstrated:false` stays unchanged.

The planned path-reading extension was then qualified using training OUT only.
Runtime, meter semantics, candidate-v3 wrapper and compound auditor were committed
and pushed in `28a57d2` before the new reading-selection call. Its near-short
category is0-10ohm before meter allowance; other values can reject both declared
placements. W1 remains installed and all three mini-board leads are disconnected
from the large fixture for that later DMM observation, retaining socket contacts.

Spark itself selected **W1 resistance**, explaining that its two location
intervals differ while R1/C1 intervals do not. Reading forecast SHA256
`2746d2be2e8ffdab19391646b16693ecfb151f65f921ae1cd5e7474bd4ea3e07`
was pushed in `7de51d648fb0641ad9b84414e845e43d88962448` before photo or reading.
No operator value, private assembly or photograph reached that selector.

So far: schematic1 + diagnostic7 + reading selection1 = **9 Spark**,0 SAM,
estimated **$0.09043140** at the retained token tariff, not a billing invoice.
Reading cohort plus the separately labelled case02 demo photo reprocessing:
**74 Spark,3 SAM,$0.73627245**.13 new offline checks passed; these are not hardware
evidence or a claim of broad accuracy.

Next: actual unchanged fault-state photo, generic SAM1 and candidate-kind/set
Spark1 (expected together about$0.015-0.03), operator port/candidate confirmation,
then the already-frozen isolated path reading. No extra wire move or DMM reading
has been requested yet. The seal is still closed. Restoration and fresh-context
rerun remain outstanding. No new firmware, k correction or relaxed guard is used.
