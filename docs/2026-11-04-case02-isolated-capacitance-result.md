# Case02: unordered isolated capacitance reading supports the existing diagnosis

Supplement: `examples/reading-groups/2026-11-04/records/20261103T174217-008035637b/`.
Original pair: `examples/reading-cohort/2026-11-03/records/20261103T165506-b6ad3e8cf7/`.

The operator reported:

> USB 분리 / 각각 완전 분리 / 2µF / sam-2 표시 0.451µF / sam-3 표시 0.101µF

This answers the instruction to disconnect USB, wait ten seconds after the power
LED goes out, remove each capacitor completely and measure separately. USB-off,
individual isolation and the selected 2uF range are explicit in the reply. The
discharge-wait flag records completion of the preceding instruction, not a
software-timed wait or an independent voltage measurement. Values are operator
reports at the confirmed 0.001uF display resolution, not Spark surface readings
or independently authenticated DMM photographs. No further photograph is needed
for these reports. The prior photo links the two body IDs to their positions.

The exact group forecast was frozen and remotely published in
`f6a792ed7cc56985c7aac070f41dffd2acc451be` before these electrical values; its
publication receipt was pushed in `3be14f9`. The earlier 474 marking report is
explicitly already known. This is not a new blind test. No interval, meter
allowance, terminal fit or reserved result was changed after receiving values.

| Observed body | Isolated DMM, uF | Unique matching component | Frozen indicated interval, uF |
|---|---:|---|---:|
| sam-2, upper capacitor | 0.451 | C1, conditional on changed:C1 | 0.3986116783–0.5924583914 |
| sam-3, lower capacitor | 0.101 | C2, conditional on changed:C1 | 0.08825–0.11225 |

Both possible bijections were evaluated. Only `{C1:sam-2,C2:sam-3}` passes. The
reversed assignment fails. The nominal reference, C1 indicated interval
0.9005–1.1045uF, does not match either assignment. It remains a rejected terminal
reference, never a resurrected survivor. The result is
`fits:["changed:C1"]`, `outcome:one_explanation_remains`,
`body_identity_status:unique_under_surviving_forecast`, `refitted:false` and
`nearest_value_assignment:false`. No additional active terminal family was
eliminated: changed:C1 was already the sole reserved-validated survivor.

Thus the original terminal result now has a separate isolated-value consistency
check and a conditional physical repair location. The actual C1 reading 0.451uF
is below the intended 1uF; C2 reads 0.101uF against the intended 0.1uF. The bench
point fit remains 0.4717739307uF for C1, with other values held fixed. Agreement
means the new readings lie in the **predeclared engineering envelopes**, including
5% plus two counts of meter allowance. It is not a meter calibration, a claim of
exact agreement, or proof that these bounded hypotheses exhaust all possibilities.

The supplement is completed. The original pair remains terminal `run_failed`
at its binding-format validator, head
`0d0ec3edf91379cd43a017986d0c9ca5fd0feed67d3aea2cdbc04b771a9137f8`.
Its native fault diagnosis remains `changed:C1`; no failed history or first-attempt
selection has been replaced. This completed reading supplement is **not** a
completed repair pair. Original 107 frozen source files remain unchanged.

## Sealed assembly review and next physical state

After scoring the isolated observations, the existing locally sealed assembly
was reviewed. Its canonical SHA-256
`f3a987ceba0e6d52a70ea3d6ba1913b324ae3679de2e80643d9ecffeba985d3c`
matches the original `specimen_assembly_sealed` commitment. It records C1 marked
474 at mini C8–C13, C2 marked104 at E8–E13, R1 10k at B3–B8 and R2 20k at D8–D13.
This retained construction record agrees with the post-reading location; it was
not supplied to the diagnostic or correspondence model. This document releases
that review **after** scoring and **before** the operator's restoration request.
It does not append to the already terminal parent or supplement.

Next restoration, with USB off: replace the removed upper 474 with a 1uF/105
capacitor at **C8–C13**; reinstall the same measured lower 104 at **E8–E13**.
Keep R1 10k B3–B8, R2 20k D8–D13, green IN large A35→mini A3 and the 1k instrument
path. Large C30–A55 load and A55–C35 bypass stay absent; the external diode stays
absent. All other instrument/REF/GND wiring stays as before. Restoration is
**requested, not yet confirmed**. Fresh-context restored diagnosis and a new
actual restored-state whole-board photo are still outstanding; the changed C1
means the old photograph cannot be called a restored-state capture.

No API or bench command was executed to record/score these manual readings.
Usage remains attempt2: **9 Spark,1 SAM,estimated$0.11860230**; case02 including
attempt1: **17 Spark,1 SAM,$0.21665225**; reading cohort: **53 Spark,2 SAM,$0.52700335**.
The future restored diagnosis uses at most8 Spark, previously about$0.06–0.12;
its calls, actual tokens and photo-stage costs will be announced/recorded when
executed under the standing authorization.

Offline supplement audit (standard library, no keys/network):

```text
PASS events=11 run_status=run_completed head_sha256=b9ed9bb9365a50afd75202d08bd2fa73e8156536894bb3ec0b03cb894371e445 scope=internal_integrity+recorded_order creation_time=unproven
```

This verifies retained integrity/order and deterministic scoring, not original
creation time, physical wiring truth, meter accuracy or operator authenticity.
