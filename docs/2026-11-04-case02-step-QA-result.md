# Case02 unchanged-wiring fresh-boot step QA passed once

Run: `examples/reference-step-QA/2026-11-04/session01/stages/20261103T181948-1a4c8ff1d2/`.
Plan/source freeze: `9e2aaa0`, before the operator's `재연결 완료` report and
before any serial command. No wire/component was changed and no parallel GND
wire was added. The existing107 frozen diagnostic sources remain unchanged.

The selected single attempt completed: **one ARM, five blocks,2,560 frames,
15 serial commands**, all original primary-A3/trusted-channel guards passed.
Fresh boot `8ac568f48501d20bc0c1178c3c4d8024` was unarmed initially and differed
from the failed run. The recorded monotonic pre-ARM wait was **10.009955s**.

| Block | A3 raw mean V | A4 auxiliary raw mean V | Native guards |
|---|---:|---:|---|
| HOLD1 | 1.638501407 | 1.639367134 | pass |
| HOLD2 | 1.638497902 | 1.639321570 | pass |
| HOLD3 | 1.638547556 | 1.639238034 | pass |
| +/-0.35V step | 1.638727478 | 1.639650452 | pass |
| Return HOLD | 1.638373476 | 1.639261985 | pass |

Within this QA, cumulative A3 mean span was **0.354001671mV**, against the
unchanged3mV limit; A4 auxiliary span was **0.412417788mV**. The native step
timing/DAC-code check passed. The final PING confirmed current_code==ref_code1376.
The serial connection is closed; the last known output is parked at REF. The
operator has not yet been asked for a new boot or another diagnostic execution.

This result contrasts with the prior restored diagnostic's3.103648313mV A3 span,
but it is not an explanation for that failure. This QA used a new boot and did
not first run the large sine/earlier diagnostic history. Both boot and history
differ; no root cause is isolated and no stable cross-boot calibration is claimed.
No coefficient, threshold, sample selection, source value or official result was
adjusted using the passing QA. It is not a reserved-validation score or a completed
restored case. The failed original/continuation and successful fault/isolated-value
records are untouched. No further QA or diagnosis ran automatically after this pass.

Actual additional usage: **0 Spark,0 SAM,$0**. Case02 totals remain
22 Spark,1SAM,estimated$0.26752245; whole reading cohort58 Spark,2SAM,$0.57787355.

Fresh-clone standard-library audit, no keys/network:

```text
PASS events=44 run_status=run_completed head_sha256=f31a59a7945e10b6fa26c6adbde88c1c36b16edc3497f6bfc6f1502da88cf191 QA_passed=true scope=internal_integrity+recorded_order creation_time=unproven
```

This checks retained integrity/order and declared command bounds. It cannot prove
creation time, original wiring truth, operator authenticity or bench stability.
