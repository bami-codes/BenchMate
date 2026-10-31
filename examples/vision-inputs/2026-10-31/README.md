# Synthetic image-reading evaluation inputs

These three deterministic circuit drawings are **test inputs**, not photographs
and not Spark outputs. [All three actual Spark responses are now retained](../../vision-spark/2026-10-31/20261031T060049-13a656638d/README.md). The answer key in `truth.json`
is local evaluation data and is excluded from every provider request.

| Input | Expected R | Expected C | Expected behavior | Actual Spark result |
| --- | --- | --- | --- | --- |
| case-01.png | 10 kΩ | 1 µF | Preserve R: IN–OUT and C: OUT–REF | Values/connections matched; review required |
| case-02.png | 4.7 kΩ | 470 nF | Same topology, read the different markings | Values/connections matched; review required |
| case-03.png | 22 kΩ | Unknown | Preserve unknown C; do not invent a nominal value | C remained null; incomplete; handoff blocked |

`prepared/` contains the metadata-free PNGs and an immutable manifest.
`request-plan.json` describes the exact three-request scope: each clean image,
its source-kind label, the reading prompt and report schema. No answer key,
earlier specimen data, filenames or ADC values are sent. Every visible reply and attempt is retained. This is a small development check, not a
vision accuracy benchmark.

Hand-drawn schematic and D01 assembly-photo checks remain pending input files.
Those require a separate image manifest; an assembly photo is never nominal
design truth and will not enter the blind B5/D01 diagnostic context.

The request plan’s approval-pending label is retained as its historical pre-call
state. The completed execution archive includes the later explicit authorization.
Bounding boxes are imprecise; see the separate post-hoc finding in the result archive.
