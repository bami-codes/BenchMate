# 01-F03: all training guards passed; local transport failure

Run `20261103T082308-07da0eb2ec` remains failed and counted. It is a separate
follow-up and never replaces first official attempt 01-F01.

Spark chose an unloaded 0.2 V step, loaded 0.2 V step and unloaded 5 Hz 0.15 V
sine. All three training waveforms and all 15 primary electrical guard blocks
passed, retaining 7,680 raw frames. The final training fit supported an effective
IN-to-OUT series resistance of 25.488 kohm; nominal and capacitor-change
families were inadequate. This does not locate that resistance physically.

After the third tool result, the next accumulated request exceeded the local
64,000-byte serialization bound. It was rejected before HTTP or budget
reservation. The precise failed payload size and opaque reasoning were not
persisted. No fifth request, reserved prediction publication, reserved capture
or final diagnosis occurred. This is a software failure, not a REF guard failure.

Actual Spark use: 4 requests, pinned-rate estimate $0.03160495. F01 through F03
total 11 requests and $0.07896260. All 84 registered source hashes were checked
against both current files and retained snapshots. Public archive omits the
local-only operator assembly truth; its recorded digest remains in the chain.

```text
PASS events=153 forecasts=3 measurements=3 order_checks=9 prediction_files=0 run_status=run_failed head_sha256=e746749266b8185845dcd881842fae56eddc9ae2ae892a97557295757102e118 scope=internal_integrity+recorded_order creation_time=unproven
```

The operator selected a fresh F04 after the prospective
[transport amendment](2026-11-03-transport-bound-amendment.md). Offline tests
passed with simulated HTTP only. The next run keeps A3 protection and every
physical/numerical criterion; it does not reuse F03 training as fresh evidence.
