# Case04 corrected fault-state diagnosis: structure supported

The active pair is `runs/reading-cohort/20261103T150223-18d6f08ac9`.
Its fault child `diagnosis-faulted/20261103T150415-dad7112413` completed.
The pair itself is not complete: photograph/SAM/correspondence, operator reading,
seal reveal, external restoration and fresh-context rerun still follow.

The reviewed image is Claude's stock revision: R1=4.7k IN–OUT and R2=20k
OUT–REF. The completed 20k extraction was reused, not re-requested. The previous
22k extraction, host-link failure and wrong-E27 physical guard failure remain
counted and preserved. This successful child does not replace either failure.

Spark selected unloaded_step_small, loaded_step_small and
unloaded_sine_1hz_large. All25 guard blocks passed, retaining12,800 frames and
five scored waveforms (three training, two reserved). After the operator's
reported E27→E25 correction, HOLD IN/OUT/REF returned to approximately1.642V.

The small signals passed nominally, but the nominal model's large-sine RMS was
55.074mV. Single-value R1 and R2 alternatives also failed. Only then did Spark
propose D1 from OUT to REF, preserving both intended resistors. Its reason was
positive clipping with a negative half-wave remaining linear. The runtime fitted
the generic diode parameters from training only (IS≈2.682e-9A,N≈1.836,72 simulator
calls); training RMS values were3.134,2.375 and3.027mV. These are bounded model
parameters, not manufacturer characterization of the physical1N4148.

The frozen structure/parameters and command forecasts were pushed before reserved
measurements: commit `e80fa7b7fe000726e5873df59cda748623e2abc1`, SHA-256
`89e69fd6aa41239d6ed8b3360e15dea6ac45490f13567b3228825f0308cf14e2`.
Reserved conditional step RMS=3.616mV (worst region5.195mV); sine RMS=2.815mV
(worst region4.051mV). Both pass the unchanged9mV whole/region threshold with
no reserved-OUT refit. Native verdict: `structure_supported`; no unique physical
location/topology or ESP32 interior claim; native repair claim remains false.

Actual contact clarification: the operator reported the diode anode occupies E30,
so it was retained there. Known-load contact used C30–A55, then was removed from
those same holes. C30/E30 share the same upper OUT strip. This changes no load,
waveform or electrical setting. The generic E30 load instruction remains in the
raw request, while actual C30 instructions/responses and clarification are fully
recorded. Pre-load clarification was published in `a5e616b`. The original C30
assembly declaration is not silently rewritten as a visually verified E30 fact.

Offline child audit PASS:245 events,4 frozen forecasts,5 measured waveforms,
19 order checks,1 prediction file. Head:
`528c359881c3b9d66cf4369819e4544f0ed63be0d0f9cacb74b72141250eac9b`.
This checks integrity/recorded order, not actual creation time or wiring truth.

One subsequent Spark request selected R1 resistance. The only remaining bounded
catalog model is proposal:1: this reading is a component-value consistency check,
not a demonstration that another declared explanation was eliminated or that a
diode lies outside the photograph. Forecast commit
`67c2449cf669d14049eec8f427172aa1c91637ae`, SHA-256
`d2fe5561b8095e55f2721f9dc252f3cb132d7e99f6b57f1d9ec266337f2cfc78`.
20k-range isolated DMM interval is4355.7–5053.7Ω; printed-nominal interval is
4465–4935Ω. Other permitted DMM ranges retain their separately frozen allowances.
No picture or operator value has been used to tune these intervals.

This successful diagnosis used8 Spark requests, estimated$0.07352435; reading
selection used1, estimated$0.00807645. Case04 cumulative including earlier failed
stages:13 Spark,0 SAM,$0.10993050. Reading-cohort cumulative:30 Spark +1 SAM,
$0.26197630. Future photo stage:1 SAM +1 Spark correspondence, estimated$0.01–0.03.
