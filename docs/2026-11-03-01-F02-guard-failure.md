# 01-F02: failed A4 guard, separately counted follow-up

Run `20261103T074537-7424df4144` is failed and counted as a follow-up. It never
replaces primary 01-F01. The unchanged engine and model used a fresh context.
Every USB intervention had a recorded wait of at least 10 seconds after an
observed unarmed PING. Original A4 guards were still active in this attempt.

Spark selected large unloaded step, large loaded step, then unloaded 5 Hz
0.15 V sine. Both steps passed their original guards and waveform checks.
Training left the increased-effective-series-resistance family adequate
(about 25.23 kohm), while nominal and C-change families were inadequate.
The third waveform's raw A4 mean guard failed before waveform scoring,
assessment update or reserved prediction publication. No final diagnosis or
reserved capture occurred.

| Reference metric, third training acquisition | A3 | A4 |
|---|---:|---:|
| Last HOLD → sine block mean change (mV) | −0.229 | +3.707 |
| Span across three HOLDs and sine (mV) | 0.229 | 4.327 |

All raw samples and 82 sources are retained. Event integrity and order audit:

```text
PASS events=142 forecasts=3 measurements=2 order_checks=8 prediction_files=0 run_status=run_failed head_sha256=0c46dfd78fd859b5ad170942708924028b6a368f3e9f28763935fa6236c870b0 scope=internal_integrity+recorded_order creation_time=unproven
```

Actual Spark: 4 requests, pinned-rate estimate $0.03199065. With F01: 7 requests,
$0.04735765. No paid request followed the failure. The operator reports USB
still connected and board untouched. The failure is not retroactively changed
by the prospective [A3 REF guard amendment](2026-11-03-A3-REF-amendment.md).
