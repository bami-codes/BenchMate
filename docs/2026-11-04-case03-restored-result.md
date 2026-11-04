# Case03 restored diagnostic result; documentary photo pending

The isolated operator reading was **R1 = 2.22kΩ**, USB off, fully removed,
20kΩ range. The unchanged pre-photo source/range-specific intervals retained
`changed:R1` and rejected `changed:R2`. The original sealed assembly was opened
after scoring. Its nominal R1 was 2.2kΩ. The operator then replaced R1 at mini
B3–B8 with 10kΩ and confirmed all other wiring retained.

Restored-only follow-up:
`examples/reading-cohort/2026-11-03/records/20261104T051005-fac3d07c86`.
Fresh-context numerical child: `diagnosis-restored/20261104T051133-4d80b9f294`.
Spark selected unloaded small step, loaded small step and unloaded 5Hz small
sine. The two reserved inputs were fixed by the protocol. The forecast was
published as `0253fba41f3b9dc61c6c5d69250c3127938c2878` before verification;
logical SHA-256 `ec9a9d2e57477f58ea72158b04fc845a767ed02b67b27211c72924251b43c3ce`.

| Nominal design, reserved input | Measured-IN whole RMS | Worst region | Conditional result | Command-only worst region |
| --- | ---: | ---: | --- | ---: |
| Unloaded ±0.35V step | 7.223mV | 8.212mV | PASS | 9.762mV, FAIL |
| Unloaded 5Hz, 0.65V sine | 4.239mV | 5.656mV | PASS | 6.849mV, PASS |

Whole and every-region limits stayed at 9mV. The command-only step failure is
retained separately. Native verdict: **consistent**, source physical, actor
muse_spark, components empty, native physical-repair claim false. Nominal and
bounded one-value changes all survived conditional checks, so this is no proof
that every part is correct or that the explanation is unique. The caption stays
**No mismatch in the tests Spark chose**.

The numerical child passed its keyless 236-event hash/prediction/order audit.
The incomplete compound prefix passed 566 events, including the retained failed
original and completed reading. Its original first-attempt failure stays counted.
The new follow-up is still active pending its documentary photo; it is not yet
reported as a completed full photo/repair pair.

The restored photo scope was declared before photo intake: new actual restored
photo, **1 generic SAM only**, documentary display, **0 Spark reference/value
requests and 0 operator readings**. The replacement changed the mini-board, so
a new whole-board capture is required. No close-ups are required. Native masks
will be preserved, without claimed restored component identity.

Actual restored diagnosis: **6 Spark, $0.05070545 estimated**. Case03 so far:
**15 Spark, 1 SAM, $0.13866115 estimated**. Remaining photo request: **1 SAM,
$0.0025 estimated**. These are retained-tariff estimates, not invoices.

```sh
PYTHONPATH=src python -S -m benchmate.reading_restored_after_photo_v5 verify <record> --allow-active
```

This checks internal integrity and recorded order, not creation time, physical
truth or meter accuracy. Pre-observation Git publication supplies separate
process evidence. No numerical criterion, frozen source or prior verdict changed.
