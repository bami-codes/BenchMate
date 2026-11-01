# SAM: separate prompt-specificity experiment, November 1

Three new, preregistered calls on the **same metadata-free development photo**.
This does not replace or retry the earlier generic `capacitor` miss. Every new
response, empty result, decoded mask and overlay is retained. No Spark call or
hardware operation occurred. SAM remains optional for the repair demonstration.

[Plan committed before calls: 1599e13](https://github.com/bami-codes/BenchMate/commit/1599e13ce3fb08cdc6cc7c09e0a124745bb0618e).
The runner verified remote main and the published plan bytes before sending.
Plan SHA-256: `b2fc35318a40a60668af75f3ee71b12f578b359d228825be73885814733a6924`.
Input SHA-256: `9c5482333974f097e1cdb4f7575f7f13eb6692b8db9b6d14d63296c2f6df9d34`.
Endpoint: `https://api.meta.ai/v1/responses`, model `sam-3.1`.
Each request contained only the cleaned PNG and its exact concept text.

| Preregistered prompt | Matches | Request time | Visual review |
| --- | ---: | ---: | --- |
| `blue capacitor` | 0 | 2.599 s | Miss |
| `blue rectangular component` | 1 | 1.699 s | Blue box body follows the visible component; leads excluded |
| `film capacitor` | 0 | 2.508 s | Miss |

![All masks from blue rectangular component](<render/blue rectangular component-all-masks.png>)

The successful shape/color description is evidence of display feasibility on
this one selected image. It does not show recognition of the electrical part,
its value or wiring, nor identify an added capacitor in a two-capacitor D01.
The failed capacitor terms do not establish why the model missed them.
No automatic choice of the "best" prompt was used to suppress other outputs.
There is no pixel ground-truth mask or reliability score.

Returned mask: box `[534, 535, 696, 766]` (right/bottom exclusive), 162×231 raster,
33,269 foreground pixels, no resize. Reported confidence 0.9532 is model metadata,
not calibrated accuracy. The official `meta-sam-parser==0.1.0` decoded all three
responses without diagnostics. Rendering made zero new API calls or manual edits.

[All raw response paths and outcomes](result.json) · [All decoded outcomes](render/render-summary.json)
· [Qualitative review](qualitative-review.json) · [Original two-call SAM trial](../../../photo-model-probe/2026-11-01/20261101T001812-2e9c1094fe/README.md)

Original `pictures/` and local `pictures-clean/` remain ignored. Only the previously
published canonical PNG was sent. All committed PNG files were inspected for EXIF
and metadata: none were present. API token usage of zero text tokens is not a claim
that image requests are free.
