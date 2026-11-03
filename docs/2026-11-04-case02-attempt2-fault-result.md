# Case 02 attempt 2: C1 change passed reserved validation

Attempt2: `runs/reading-cohort/20261103T165506-b6ad3e8cf7/`.
The complete, terminal fault diagnostic child is exported at
`examples/reading-cohort/2026-11-03/records/20261103T165506-b6ad3e8cf7/diagnosis-faulted/20261103T165737-23bd08387e/`.
The parent pair is still open, awaiting a new corrected-state photograph;
this child export is not a completed fault/restoration pair.

The operator confirmed moving474 from C3–C8 to C8–C13 with USB off, retaining
the other components and reconnecting USB. Attempt1 remains counted, failed and
first-selected. Its post-hoc photo/acknowledged wiring error are retained
separately and never sent to this fresh diagnostic model.

The new schematic extraction matches the same previously operator-confirmed
10k/1uF/0.1uF/20k intended circuit. Reuse of that identical intended-content
confirmation is explicit in the parent chain, not an invented new user reply.
All107 frozen source hashes, firmware, A3 raw3mV protection, common1k instrument
path, independent origins,9mV whole/regional score and ten-second boot wait remain.

Spark chose unloaded small step, loaded large step and unloaded5Hz small sine.
Only changed C1 passed the training whole/regional checks. Final fitted C1:
**0.4717739307uF**. All25 guard blocks passed, retaining12,800 raw frames.

The terminal forecasts were frozen and remotely published before either reserved
capture in commit `b16588ec6a42aea62a7788d355efa59a9183eb02`; prediction SHA-256
`a7c6ae0e6575f52d8344c55f8e54236e4adfbccd11555f4019a8f1d962d70501`.
No reserved OUT entered fitting. Reserved changed-C1 scores:

| Input | Whole RMS mV | Worst region mV | Passed |
|---|---:|---:|---|
| Unloaded step | 3.216 | 3.421 | yes |
| Unloaded5Hz sine | 1.556 | 2.291 | yes |

Native verdict `changed`, component `C1`. This is a bounded one-component-change
diagnosis conditional on measured IN; it does not establish unique global
topology or every physical component. The existing positive-capacitance,
single-change model distinguishes this large decrease despite the two parallel
capacitors' general sum ambiguity. No simulator or timing adjustment was needed
for these particular corrected captures; this does not qualify all fast circuits.

## Next photo/reading scope

Spark selected C1/capacitance for the operator reading. Source-specific forecasts
were published before photo/value intake in
`8a1269d75d7e64862cba1c7ddd60f87b13a2924a`, SHA-256
`849495903bd1840275f113582bf20a636a97b8e65eb7423afd28ba16848a6860`.
Only one bounded terminal explanation already remains. Photo/body correspondence
and a printed-marking observation are for physical repair localization and
nominal-label documentation; do not claim they eliminate another terminal family.
Markings do not measure actual electrical capacitance or rule out damage behind
an unchanged label. Their frozen interval is therefore unconstrained.

The frozen rules explicitly mark DMM capacitance unavailable pending capability
qualification. The placeholder DMM interval does not authorize such a reading.
Do not request capacitor isolation or reinterpret a marking as a DMM result.
The old miswired-state case2 photo is not a photograph of the corrected specimen.
Use one new corrected-state whole-board photograph, then SAM and Spark body
correspondence, with operator confirmation or a labelled operator override.
The pair's numeric reading/score, seal reveal, restoration and fresh-context
restored diagnosis remain pending.

Actual usage so far: schematic1 + diagnostic6 + reading selection1 = **8 Spark,
0 SAM, estimated$0.10232285**. Case02 including attempt1: **16 Spark,0 SAM,
$0.20037280**. All reading-cohort work: **52 Spark,1 SAM,$0.51072390**.
Token estimates are separate from SDK reservations and invoices.

Child verification, without keys/network:

```text
PASS events=235 forecasts=4 measurements=5 order_checks=19 prediction_files=1 run_status=run_completed head_sha256=3ba0b84cdb9cb02d279969da495d30dac615144737504a6a4e8fa0c87bc732c8 scope=internal_integrity+recorded_order creation_time=unproven
```

This checks retained integrity and recorded order, not original creation time,
physical wiring truth or a completed repair. Last observed output is parked at
REF, load absent, controller closed, USB still connected per the last user report.
