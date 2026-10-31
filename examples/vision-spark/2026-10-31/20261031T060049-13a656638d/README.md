# First actual Spark vision evaluation — synthetic schematics

**Three authorized Muse Spark 1.3 max requests, three original responses retained,
zero hardware actions and no retries.** All three matched the pre-existing answer
key for visible component values, connections and preservation of an unknown C.
This is a small development check on clean drawings, **not a real-photo accuracy
benchmark or electrical verification**.

| Image | Expected | Spark's actual reading | Connections | Status / nominal handoff |
| --- | --- | --- | --- | --- |
| 01 | 10 kΩ, 1 µF | 10 kΩ, 1 µF | R: IN–OUT; C: OUT–REF — matches | `needs_review`; nominal candidate only |
| 02 | 4.7 kΩ, 470 nF | 4.7 kΩ, 470 nF | R: IN–OUT; C: OUT–REF — matches | `needs_review`; nominal candidate only |
| 03 | 22 kΩ, C marked `?` | 22 kΩ, C = `null` | R: IN–OUT; C: OUT–REF — matches | `incomplete`; nominal handoff blocked |

The third response explicitly says:

> C1 capacitance value shown as '?' and not legible as farads — operator must confirm intended value

No candidate was silently corrected or confirmed by an operator. The candidate
time constants (10.0 ms and 2.209 ms) come from the read labels, not measurement.

## Every original output

- **image-01** — [clean input](attempts/20261031T060050-8f3ccccdc9/input.png), [literal tool arguments](attempts/20261031T060050-8f3ccccdc9/arguments.txt), [all visible output and usage](attempts/20261031T060050-8f3ccccdc9/response-visible.json), [parsed candidate](attempts/20261031T060050-8f3ccccdc9/result.json), [hash-chained events](attempts/20261031T060050-8f3ccccdc9/events.jsonl).
- **image-02** — [clean input](attempts/20261031T060107-5492ab7ee4/input.png), [literal tool arguments](attempts/20261031T060107-5492ab7ee4/arguments.txt), [all visible output and usage](attempts/20261031T060107-5492ab7ee4/response-visible.json), [parsed candidate](attempts/20261031T060107-5492ab7ee4/result.json), [hash-chained events](attempts/20261031T060107-5492ab7ee4/events.jsonl).
- **image-03** — [clean input](attempts/20261031T060116-0192856444/input.png), [literal tool arguments](attempts/20261031T060116-0192856444/arguments.txt), [all visible output and usage](attempts/20261031T060116-0192856444/response-visible.json), [parsed candidate](attempts/20261031T060116-0192856444/result.json), [hash-chained events](attempts/20261031T060116-0192856444/events.jsonl).

## Localization limitation

The returned component boxes should **not** be treated as precise localization.
This was noticed after the value/connection check and is recorded separately as
a post-hoc diagnostic, not added retrospectively to the original scoring rule.

For example, image 03's C1 box maps to x=643.5–767.8, y=317.2–345.8 on the
1100×650 image. The drawn capacitor plates span x=590–710 at y=345 and y=367;
the lower plate is outside the box. A symbol-body containment check is false
for all six returned boxes, but the prompt did not specify a tight box convention,
so this is not a general localization accuracy estimate. No box was corrected,
used to target SAM, or used as a repair instruction. Reviewed selection and an
actual mask-quality test remain necessary for that future feature.

## Provenance and limits

- The input drawings, separate answer key, manifest, prompt and output schema
  were committed in `9fb9e7f` before these calls. [Input scope and answer key](../../../vision-inputs/2026-10-31/README.md).
- Each fresh request contained one sanitized image, its source-kind label and
  the same reading instructions/report schema. No filename/path, answer key,
  prior diagnosis, D01 photograph or ADC data was sent. `store=false`.
- Total API elapsed time: **43.263 seconds** (17.329, 8.734, 17.200 seconds).
  Reported tokens: 5,829 input + 6,073 output = 11,902 total. This is reported
  usage, not a verified invoice. Three $1 local allowances were reserved;
  the local reserve is not the actual price.
- [Authorization](authorization.json), [audit](audit.json),
  [copy provenance](provenance.json), [batch events](events.jsonl),
  [batch result](result.json) and the exact executed source snapshot are retained.
- Four event hash chains, all three payload/image hashes, literal tool arguments
  and the four source files were checked locally. No external attestation.
- The two intended RC designs still require human review and a new experiment
  protocol. Hand-drawn schematics, real breadboard photos, resistor color bands,
  occlusions, general topology recognition and precise localization are untested.

Reproduce the local audit without API/hardware calls, from the repository root:

```sh
uv run --extra vision python scripts/audit_vision_batch.py --run examples/vision-spark/2026-10-31/20261031T060049-13a656638d --inputs examples/vision-inputs/2026-10-31 --source-commit 9fb9e7f2c808f5dff9f2c05a0a05b1dd6803efc5 --output /tmp/benchmate-vision-audit.json
```
