# 01-F01: stopped during loaded pre-stimulus HOLD

The first official faulted attempt is **failed and counted**, selected as the
primary 01-F01 record. Run: `20261103T072121-1138ccf241`. It is not relabeled as
a pilot or replaced by a later successful run.

The first small unloaded step passed the original electrical/waveform checks.
Nominal was inadequate; changed R1 and changed C1 were both adequate, still
unresolved. Spark then selected a loaded small step. After the operator's
USB-off E30–A55 intervention, the new boot passed identity/firmware/ARM checks.
The third pre-stimulus HOLD failed, **before the loaded step was sent**.

| Quantity | Recorded result |
|---|---:|
| Completed diagnostic waveforms | 1 unloaded small step |
| Loaded / reserved waveforms acquired | 0 / 0 |
| Raw blocks / frames, including HOLD | 8 / 4096 |
| Actual Spark requests | 3 |
| Pinned-rate token estimate | $0.015367 |
| Final Spark diagnosis | Not reached |
| Correction / guard change / automatic retry | None |

Using the original guard's nominal conversion `count × 4.9 / 16383` (not an
independent physical voltage measurement), frame 477 at t=0.953998 s reads:

| Channel | Frame 477 (V) |
|---|---:|
| A1 IN | 1.605817 |
| A2 OUT | 0.650223 |
| A3 REF | 0.636465 |
| A4 REF | 0.656803 |

A2/A3/A4 share a roughly 1 V downward excursion while A1 changes by roughly
37 mV. Nearby frames show smaller disturbance. A4's three-HOLD block-mean
span is 3.192 mV, above the original 3 mV limit; A3's HOLD span and sample
envelopes fail too. No point is removed or new mean/RMS criterion substituted.

The command was constant HOLD. These logs do not independently distinguish
actual REF/contact/power behavior from acquisition corruption. The earlier
investigation left the current REF pull-down installation check open:
I10–I16 1 kohm and H16–H13 jumper. The operator has confirmed USB disconnected
with the loaded wiring retained. No subsequent stimulus or paid call occurred.

The successful uncorrected QA established unloaded operation only. Loaded
instrument QA should have preceded official execution. This official failure
stays counted; maintenance/follow-ups must be separate and cannot replace the
preselected first attempt. Present QA choices before repeating measurements.

Raw record and 80 source snapshots:
`examples/official-runs/2026-11-03/records/20261103T072121-1138ccf241/`.
The operator-only assembly file remains private; its event digest is retained.
Numeric analysis and the all-frame plot:
`examples/official-runs/2026-11-03/analysis/01-F01/`.

```sh
python -m benchmate verify examples/official-runs/2026-11-03/records/20261103T072121-1138ccf241
```

```text
PASS events=80 forecasts=2 measurements=1 order_checks=4 prediction_files=0 run_status=run_failed head_sha256=4a127dc9838913097700eeba8d3d14c8cec004905ce8caa4d1e1ab1ef0b8cd4a scope=internal_integrity+recorded_order creation_time=unproven
```

This PASS means record integrity and recorded order, not diagnosis success.
The second training forecast is intact; its stimulus was stopped by the guard.
The cost estimate uses preserved rates of $1.25/M uncached input, $0.15/M cached
input and $4.25/M output tokens, not a billing statement. Necessary future paid
calls are authorized without repeated approval; counts/costs remain reported.
