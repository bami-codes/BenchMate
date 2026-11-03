# Photo pipeline v2: observations, code decoding and five-view agreement

This new version preserves every v1 and OpenCV-follow-up result. The operator
requested it after those outputs were known. Case 01 is development/nonblind
reconfirmation, never the prospective test. Freeze this policy and source
snapshots, commit and push them before capturing the next case photograph.
That next newly captured image can be recorded as operator-attested prospective
input. A local timestamp or a new file alone does not prove capture time or
double blinding.

## Separation of responsibilities

SAM 3.1 gets only the metadata-free whole image and the generic prompt
`electronic component`, one request per photograph. No component-name prompt,
schematic, diagnosis, case label or intended value is supplied. Native masks,
responses, misses and parsing errors remain untouched.

Each valid native mask is refined by binary opening with radius 8% of its
short bounding dimension, keeping the largest surviving contour's convex hull.
This is a **derived body mask**, not a native SAM mask. Native masks remain.
Masks below 80 native pixels or over 25% of the photo are not read. The body
mask is explicitly mapped to full-source coordinates with nearest-neighbor
scaling. Foreground source pixels remain, and outside pixels become neutral
white. No text is inpainted. The hull may retain previously masked interior
pixels; they are actual source pixels, not generated marks.

The OpenCV fallback retains blue HSV contours H=90–135, S>=70, V>=30 after
7x7 closing and 3x3 opening. Eligible area >=2000, aspect 0.4–5, fill >=0.45.
Contours are ordered top-to-bottom then left-to-right. A contour duplicating a
SAM body by bbox IoU>=0.65 or containment>=0.85 is recorded rather than read
again. This fallback is color/geometry based, not a capacitor classifier.
All decisions are retained. At most the first eight eligible bodies are read;
extras remain explicitly not selected. No selection uses OCR values or scores.

## Fixed five views and literal schema

For each body the five views are baseline, Lab-L-only CLAHE (clip 2, grid 8x8),
board-reference WB, cubic 3x enlargement, and horizontal mirror. Enlarged views
are limited to 1600 pixels on the long edge; the actual size is retained.
WB uses bright low-saturation pixels (S<60, V>=60th percentile), at least 2000
pixels, and scales RGB channel means to their common mean. Missing reference
uses identity gains and is recorded. These are transformations of the **same
photograph**, not independent measurements or additional spatial information.

Five fresh Spark contexts per body run with at most five parallel workers.
The model reports kind, literal strings and alternatives, ordered band colors,
alternatives, uncalibrated per-band confidence and uncertainties. No value
field, circuit connectivity, port mapping, terminal-count requirement or desired
part hint is requested. Unknown kind does not discard surface text. Raw visible
output/tool arguments remain. No retry; failed views count in the denominator.

## Deterministic interpretation and one representative

The code interprets supported capacitor strings and valid 4/5/6-band resistor
sequences in both directions. Common three-digit pF codes and tolerance letters
follow the [MIT marking reference](https://web.mit.edu/rec/Handouts/capacitors.pdf);
resistor digits/multiplier/tolerance follow the
[Vishay color chart](https://www.vishay.com/docs/49411/resistor_color_code_calculator.pdf).
Voltage suffixes are conditional common-code interpretations, not verified
device ratings. Arbitrary digit substrings inside transistor labels are not
decoded as capacitors.

Mirror band order is normalized before tallies. Per-band counts remain, but
cannot synthesize a value absent from every actual complete-view interpretation.
The representative comes from valid full-view codes, ranked by number of
compatible views. A view with unresolved direction can support multiple values;
its support is not an exclusive ballot or a probability.

The UI-facing output is one **photo candidate + support/5**, with all candidates,
direction ambiguity, original observations and ties retained in data. Ties use
canonical kind/value order solely to choose a representative, and remain
explicit. All-unreadable returns null. There is no forced numeric answer and
no three-state confirmed/tentative/unreadable UI requirement. `5/5` means view
agreement, never correctness or calibrated confidence. E24/E96 do not filter or
choose a candidate: a real/custom/incorrect component need not be preferred.

## Measurement and independence

Photo transcription receives no measurement or diagnosis. A later crosscheck
must state its scope and provenance. A fitted effective series path of 25k
does not uniquely measure the photographed resistor. Code can show conditional
remaining series contribution after an explicitly confirmed component-to-path
binding, but cannot mark that individual value electrically verified from the
path alone. Preserve nonidentifiability and alternate photo values.

The existing official cohort remains measurement-first, with independent photos
after diagnosis. A later comparison is posthoc; it does not rewrite an old
prediction or claim the photo selected that run's experiments. Native diagnostic
verdicts and first-attempt selection stay unchanged.

## Artifacts and calls

`policy.json` and `source/` pin runtime/prompt/schema/decoder/settings before the
prospective capture. `prepared/` binds clean whole/full images and policy hash.
`sam-outcomes.json`, native SAM children and `native-SAM/` preserve localization.
`body-manifest.json`, body masks and five PNGs bind the actual vision inputs.
Each `vision/<body>/<view>/<run>/` has its own full event chain and raw reply.
`results.json.components[].decoded` holds the derived value/support/candidates;
`raw_views` links each independent literal output. These derived values are not
model-native numeric answers. No source DNG/GPS or API key is published.

Call plan per photo: SAM 1 plus Spark 5 times the selected body count. Two bodies
mean 10 Spark calls; four mean 20. Counts are announced after localization and
before vision calls. Actual usage is retained, with separate append-only local
reservations. Existing ledgers are not reset. Explicit execution marker prevents
accidental repetition. The implementation itself makes zero paid calls.
