# Synthetic image-reading evaluation inputs

These three deterministic circuit drawings are **test inputs**, not photographs
and not Spark outputs. All API results are pending. The answer key in `truth.json`
is local evaluation data and is excluded from every provider request.

| Input | Expected R | Expected C | Expected behavior | Actual Spark result |
| --- | --- | --- | --- | --- |
| case-01.png | 10 kΩ | 1 µF | Preserve R: IN–OUT and C: OUT–REF | Pending |
| case-02.png | 4.7 kΩ | 470 nF | Same topology, read the different markings | Pending |
| case-03.png | 22 kΩ | Unknown | Preserve unknown C; do not invent a nominal value | Pending |

`prepared/` contains the metadata-free PNGs and an immutable manifest.
`request-plan.json` describes the exact three-request scope: each clean image,
its source-kind label, the reading prompt and report schema. No answer key,
earlier specimen data, filenames or ADC values are sent. Every visible reply
and failed attempt will be retained. This is a small development check, not a
vision accuracy benchmark.

Hand-drawn schematic and D01 assembly-photo checks remain pending input files.
Those require a separate image manifest; an assembly photo is never nominal
design truth and will not enter the blind B5/D01 diagnostic context.
