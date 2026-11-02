# Reference maintenance QA — not a circuit diagnosis

After the second pilot stopped at its A4 reference-drift guard, the operator
checked a spare jumper's continuity and replaced H50–Arduino A4 with the
electrically equivalent I50–Arduino A4 connection. D50–G50 and the DUT were kept.

The isolated QA source was committed before execution. It sends one ARM to REF
and at most ten fixed REF HOLD blocks, using the preserved electrical guards.
No Spark, STEP or SINE action is available. Three offline orchestration checks
passed: exactly bounded commands, stop on guard failure, and reject an unchanged
boot before ARM. Frozen diagnosis sources and firmware were not changed.

Run `20261102T163017-f02faa7857` stopped on its fourth HOLD (2,048 frames).
A4 block means were 1.639860, 1.640763, 1.640475 and 1.643791 V using nominal ADC
conversion. Their **3.931 mV** span exceeded the unchanged 3 mV limit. A1–A3
were comparatively stable at the fixed DAC setting. No cause is established:
the physical REF and A4 sensing path have not yet been independently separated.

Paid calls: **0**. Diagnostic step/sine commands: **0**. The remaining six planned
HOLD blocks were not sent. The raw data, failure, source copies and terminal
event chain are preserved. The chain and secret scan passed.

The next requested comparison temporarily moves the C28–A45 monitor lead to
E50–A45, so A3 and A4 sample the same physical REF through their existing input
paths. This is an instrument fault-isolation test, not an adopted new diagnosis
configuration or a relaxed guard. Operator completion is pending.

Before the comparison acquisition started, the operator corrected the E50
completion report: that contact is obstructed. The proposed alternative is J50,
the same lower column-50 REF node as G50/I50. J50–A45 completion is pending.
No comparison PING, ARM or HOLD was sent on the withdrawn E50 report.
