# New case 01 — restored acquisition failure, preserved

The operator restored the same measured R1 at mini B3–B8, removed the two
external series resistors, moved green IN from large A37 to A35 and confirmed
USB-off wiring followed by reconnect. The separate unarmed PING preflight passed.
No previous diagnosis, photo, operator reading or assembly truth was supplied
to the fresh restored Spark context.

Restored child: `diagnosis-restored/20261103T135220-d19cb17641/` inside
[the new pair](../examples/reading-cohort/2026-11-03/records/20261103T125924-bf8f64512b/).
Boot: `c164157151946f5e683bb7b84280fd33`.

Spark inspected the experiment and selected `unloaded_step_small`. The runner
observed an unarmed boot, waited 10.009s, confirmed it again, sent one ARM and
confirmed armed REF output. The first preparatory REF HOLD then returned an
error rather than a capture:

```text
settling failed or cancelled
```

The host's `Unexpected instrument protocol` is its generic rejection of a
non-capture response. It is not evidence of malformed serial bytes or a changed
protocol version. Boot identity was unchanged. The error arrived 6,204ms after
the preceding armed PING, close to the unchanged 1,200ms+5,000ms firmware settling
timeout. This is consistent with A2 failing its settling condition. The firmware
also uses this message for cancellation by incoming serial bytes, so cancellation
cannot be categorically excluded from the message alone.

The firmware condition checks A2 for 20 samples within the original clipping
bounds and at most 20 ADC counts peak-to-peak. No raw block was returned, so the
record does **not** identify clipping versus noise, wiring/contact condition,
or another physical cause. No firmware change, threshold relaxation, correction
fit, automatic retry or extra stimulus followed.

- Accepted ADC frames: **0**.
- Selected diagnostic step executed: **no**.
- Host A3 3mV guard reached: **no**.
- Restored verdict / no-mismatch claim: **unavailable**.
- Operator subsequently confirmed **USB disconnected, restored wiring retained**.

The first new-cohort pair is terminal `run_failed`, counted and still the selected
first attempt. Its completed fault diagnosis, real SAM correspondence, isolated
4.71kΩ reading, fixed-interval score and original seal remain intact. The terminal
event and cohort index are authoritative; `state.json` records the last nonterminal
phase. Do not substitute the earlier prototype R01 or reopen this terminal chain.
Any later recovery QA or restored follow-up must be separately registered and
linked, retaining this failure in the accounting.

The failed restored stage used Spark **2** requests, estimated **$0.01127065**.
New-cohort cumulative usage is **Spark 11, SAM 1, estimated $0.09404385**.
Further hardware is stopped pending the operator's next-strategy choice.

Offline verification of the complete failed parent, including linked children:

```text
PASS events=351 forecasts=6 measurements=6 order_checks=28 prediction_files=2 run_status=run_failed head_sha256=16c4e82b898eafabdf2c1b82df7c1e18484bb440ebda5d71066324121d88d175 scope=internal_integrity+recorded_order creation_time=unproven
```

Restored child:

```text
PASS events=27 forecasts=1 measurements=0 order_checks=1 prediction_files=0 run_status=run_failed head_sha256=337e385b909043b55475ea062256db0c41302f1395ae5cc8516addc5c7416eb3 scope=internal_integrity+recorded_order creation_time=unproven
```

These PASS outputs describe record integrity/order; the experiments remain failed.
