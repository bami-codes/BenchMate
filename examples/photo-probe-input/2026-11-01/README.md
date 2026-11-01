# Real-photo development probe — November 1, 2026

Input: the user-selected IMG_8885 cleaned copy. The original `pictures/` folder
is excluded from Git and is never read by this runner. Other cleaned photos stay
local. The six supplied JPEG copies have no EXIF/GPS tags; their ordinary JFIF
container fields are not location data. The selected copy was rebuilt from RGB
pixels as a 1200 × 1600 PNG with no metadata before transmission/publication.

The image shows a foreground mini breadboard with one resistor and one blue box
capacitor, and background bench hardware. No nominal values, identity of a fault,
assembly instructions or earlier measurement results are provided to the models.
Ports are not labelled IN/OUT/REF; visual connections may remain unresolved.

The user requested three calls: one Spark max assembly-photo transcription,
then separate SAM `capacitor` and `resistor` concept requests. The exact scopes
and payload hashes are frozen in [plan/plan.json](plan/plan.json). Destination:
`https://api.meta.ai/v1/responses`. Existing local credentials authenticate only.
No original files/metadata, other five photos, local paths, ADC arrays, earlier
circuit results or answer key are sent. One request per task, no retries. All
responses, failures and empty segmentations are retained. No hardware is operated.

SAM uses a documented non-streaming request for this single still image,
one-bit masks and confidence output. All returned matches are decoded with the
pinned official `meta-sam-parser==0.1.0`; unmodified masks are retained and every
match is shown. Colored overlays are deterministic visualization of model output,
not hand-corrected masks. This is one selected development image, without pixel
truth or a general accuracy claim. Confidence is not a circuit diagnosis.

Sources: [SAM request options](https://dev.meta.ai/docs/sam/segmenting),
[output grammar](https://dev.meta.ai/docs/sam/reading-segmentation),
[official parser](https://dev.meta.ai/docs/sam/client-libraries).

The execution receipt is created exclusively before the first paid call. It
prevents rerunning the same frozen plan by accident. Results will be published
separately; this document is the pre-call plan, not a completed test.
