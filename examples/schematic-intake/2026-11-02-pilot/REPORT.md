# Six real Spark schematic readings — pilot

One actual Muse Spark 1.3 request per image, six total, with no retry or discarded
attempt. Inputs are pixel-sanitized copies of the six committed design PNGs.
The common R/C/D/Q reader supports Q terminal order collector/base/emitter.
No case mapping JSON, original filename, forum title, assembly truth, photograph
or hardware observation was included in any request. Hardware commands: zero.

| Image | Spark's provisional transcription |
|---|---|
| 01 | R1 4.7 kΩ IN–OUT; C1 1 µF OUT–REF |
| 02 | R1 10 kΩ IN–OUT; C1 1 µF, C2 0.1 µF and R2 22 kΩ parallel OUT–REF |
| 03 | R1 10 kΩ IN–N1; R2 10 kΩ N1–OUT; C1 1 µF OUT–REF |
| 04 | R1 4.7 kΩ IN–OUT; R2 22 kΩ OUT–REF |
| 05 | R1 10 kΩ and C1 1 µF OUT–REF; explicit description that IN and OUT share a direct wire |
| 06 | R1 4.7 kΩ IN–BASE; R2 1 kΩ VCC–ANODE; red LED ANODE–COL; BC547B C=COL, B=BASE, E=GND |

Codex compared component values and connections to the images. All six are
consistent with their visible schematics. This is not an independent vision
accuracy benchmark, physical diagnosis result or completed operator approval.
Bounding boxes are provisional visual outputs; localization accuracy was not
scored. No image-reading result has been edited.

05's W1 will be an explicit operator addition in the confirmation record, not
a model-reported component. 06 was actually read by Spark, including Q1 and the
red LED; no manual fallback was needed. Its reviewed runtime uses explicit
operator-approved R1→Rbase and R2→Rled aliases and a separately declared known
47k/10k measurement harness. User confirmation is pending at this report's
creation; the provisional results cannot authorize physical work by themselves.

Usage: 12,546 input tokens (3,366 cached), 10,240 output tokens. Estimated Standard
cost **$0.0554999**, using $1.25/M input, $0.15/M cached input, $4.25/M output.
This is a token-based estimate, not an account invoice. The old local request
guard reserved $6; reservations are not actual charges. Pricing source:
https://dev.meta.ai/docs/pricing-rate-limits

Each attempt retains its cleaned `input.png`, request plan and payload hash,
visible reply, original tool arguments, result and terminal event hash chain.
All six chains and PNG chunk/CRC checks passed. The source snapshot and manifest
pin the exact code used. Originals retain C2PA provenance; it is absent from the
actual transmitted images, as confirmed by the chunk-aware verifier.

## Operator confirmation, Nov 3 KST

The user confirmed the six readings subject to two checks against the original
tool arguments. Both passed: 05's R1 and C1 each have nodes OUT–REF; 06's R2 has
nodes VCC–ANODE and its LED nodes are ANODE–COL in anode/cathode order.
No additional model request or edited model output was used for these checks.
The user authorized W1 and the active-profile aliases/harness upon those checks.
The six reviewed designs and their image/argument hash bindings are retained in
[the approval record](../../reviewed-designs/2026-11-03-pilot/approval.json).
This approves the intended designs; it does not assert the design-01 specimen
has been wired or that the LED hardware path is qualified.
