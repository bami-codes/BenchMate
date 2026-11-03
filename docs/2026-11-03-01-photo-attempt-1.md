# Case 01 faulted photograph, attempt 1: values unreadable

The operator supplied one ProRAW board photograph after physical diagnosis
01-F04 and before restoration. No separate close-up photographs were supplied.
The original DNG remains ignored/private. Fixed camera-WB conversion, metadata
removal and mild sharpening were committed before API calls. Both unsharpened
and sharpened full-resolution PNGs are retained, with their conversion record.

The photograph was sufficient to attempt segmentation and reading. The actual
results do **not** establish that its capture quality is sufficient for reliable
marking transcription. There were no processing adjustments after these results.

| Stage | Native result | Review |
|---|---|---|
| SAM `resistor` | One exact-size mask, no parser diagnostic | Visible axial resistor |
| SAM `capacitor` | One exact-size mask, no parser diagnostic | The same axial resistor; box capacitor missed |
| Spark on resistor-concept crop | R, value null, uncertain color bands | `unreadable` |
| Spark on capacitor-concept crop | R, value null, uncertain color bands | Independently recognizes the false-positive crop as R; `unreadable` |

Both crops came from the 3024x4032 converted source, using SAM coordinates from
the 1200x1600 input and fixed 15% padding. Neither was upscaled. Every returned
mask and both independent readings were retained. The capacitor reading is
missing: it was never supplied to Spark as a crop, so this is not an OCR failure
on the capacitor. The capacitor-concept name was not given to either reader.

`components.json` retains native values, markings and ambiguities. `review.json`
is a separate observer review, not model output. No nominal value, previous
diagnosis, manual band interpretation or known assembly truth fills the nulls.
This photo result does not change the completed physical diagnosis.

Four child event chains pass the complete `read_events` hash audit. They contain
no frozen electrical forecasts and are not presented as diagnosis-verifier runs.
The [photo record](../examples/official-photos/2026-11-03/01-faulted/review.json)
contains each retained event head and the precise input/result links.

Actual API use: **SAM 2 requests + Spark vision 2 requests**. The standard-rate
estimate is **$0.005 SAM + $0.01755840 Spark = $0.02255840**. SAM is per image;
Spark uses actual recorded input/cached/output tokens. Rates were checked against
[Meta's pricing page](https://dev.meta.ai/docs/pricing-rate-limits).
Together with F01–F04 this scope totals 19 Spark requests, two SAM requests and
an estimated $0.14875730. These estimates are not an invoice.

No further call or restoration followed the unreadable results. Recommended
next capture: keep one whole-board photograph, use landscape framing with the
board filling 80–90% of frame width, illuminate diffusely and focus on the
markings. The RAW recipe stays fixed. A new photograph/attempt must retain this
first result rather than replacing it. Alternatively the operator can retain
unreadable evidence and proceed to restoration with that limitation explicit.
