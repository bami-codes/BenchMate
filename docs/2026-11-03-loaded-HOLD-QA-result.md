# Loaded HOLD-only QA passed

All 12 blocks / 6144 frames passed the unchanged original guards after the
operator selected QA and reconnected USB with E30–A55 retained.
Boot: `9d874027b29d263f410dafa4842bc3f5`. Final PING confirmed REF output.

| Channel | Raw block-mean span (mV) |
|---|---:|
| A1 IN | 0.134 |
| A2 OUT | 0.401 |
| A3 REF | 0.251 |
| A4 REF | 0.242 |

Exactly 28 commands: one ARM, twelve HOLD captures, fifteen PINGs. No step,
sine, fitting, firmware upload, correction, guard change, manual mV reading or
paid request occurred. All 71 event hashes and 82 pinned source hashes were
verified. The original 80 sources are preserved with 01-F01; the two new QA
sources are copied with this result.

This supports constant-HOLD repeatability on this loaded configuration and
boot. It does not identify the cause of the earlier roughly 1 V excursion or
establish that it cannot recur. Future captures retain the original guards.
01-F01 stays failed, counted, and selected as the primary first attempt.

Record: `examples/loaded-HOLD-QA/2026-11-03/session01/`.
`read_events` validates the maintenance chain. The public `verify` command
requires forecast hashes; it intentionally does not promote HOLD-only QA to
prediction evidence.

Next: register 01-F02 after USB-off E30–A55 removal and a fresh unarmed PING.
Reuse the same intended design, prompt, model and engine. No QA data or prior
diagnosis enters the fresh Spark context.
