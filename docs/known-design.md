# Check a known design — image intake

This is a new, separate entry workflow. It does not retroactively attach a photo
to the D01 run, change a B5 protocol, or power a circuit. Three actual Spark max calls on synthetic schematics are complete: both fully
labelled drawings matched their R/C values and connections, and the drawing with
C marked `?` remained incomplete with a null value. [All original outputs and
audit](../examples/vision-spark/2026-10-31/20261031T060049-13a656638d/README.md).
These are clean-drawing development checks. Real-photo evaluation is **pending**;
the user confirmed no hand-drawn schematic or D01-board photo is available yet.

1. Choose **intended schematic** or **assembled circuit** and select a JPEG,
   PNG or WebP. The local service applies EXIF orientation, limits the image to
   1600 pixels on its longest edge and reconstructs a clean PNG from pixels.
   It checks that no image metadata remains. The original photo is not copied
   into the run, sent to Meta or committed.
2. Review the cleaned preview. In explicitly enabled API mode, **Read with
   Spark** sends only that image, its source kind and the reading prompt/schema
   to `https://api.meta.ai/v1/responses`, using `muse-spark-1.3`, max effort and
   up to 8192 output tokens. No previous diagnosis, ADC, answer key, filename or
   local path is supplied. One request per image/source-kind pair, at most ten
   per server session, no automatic retries. All attempts are retained.
3. Review the image-derived components, connections, ambiguities and candidate
   netlist. Unreadable values remain null; occluded connections remain unknown.
   The literal visible response/tool arguments are saved before validation.
   Hidden reasoning is not saved. Invalid JSON/schema output remains failed.
4. Correct the transcription if necessary and save an explicit operator review.
   The original candidate remains unchanged. The current handoff accepts only
   an intended single-R / single-C IN→OUT→REF low-pass with complete labels,
   no ambiguities and bounded values. Assembly photos cannot become nominal
   design truth. A saved review is **not electrical verification**.
5. Download the reviewed design for a future experiment protocol. **The existing
   physical RC runner still has its own frozen nominal design; automatic
   arbitrary-design hardware execution is not implemented.**

## Run locally

```sh
uv sync --extra vision
uv run python scripts/known_design.py serve
```

Open the printed loopback URL. Default mode permits image preparation/review of
the preview and blocks every paid call. `serve --execute --max-requests 10`
explicitly enables paid vision reads. The browser cannot see the API key, and
cross-origin mutation requests are rejected. The service makes no hardware calls.

For a reviewable batch, prepare images first (this makes no API call):

```sh
uv run python scripts/known_design.py prepare --kind intended_schematic --image /path/to/schematic.png --output runs/vision-prepared/my-batch
uv run python scripts/known_design.py batch --manifest runs/vision-prepared/my-batch/manifest.json
```

The printed plan includes the cleaned-image hashes, prompt, schema and request
count. Execution additionally requires `--execute --approved-manifest-sha256 HASH`.
An exclusive execution receipt prevents silently re-running the same batch.
Each image gets a fresh context. A malformed response is not repaired with an
extra prompt. All visible responses, failures and source hashes are retained.

## Evaluation plan

`scripts/make_vision_fixtures.py` generates three explicit synthetic schematics:
10 kΩ / 1 µF, 4.7 kΩ / 470 nF, and 22 kΩ / **unreadable capacitance**. The local
answer key is separate from provider input. Compare all three on component
values, node connections and preservation of the unknown value. These three
development fixtures are not a general vision accuracy benchmark.

Then separately evaluate a user's hand-drawn intended schematic and a D01
assembly photo. Do not mix a revealed fault assembly into blind diagnosis or
claim the photograph specifies the intended nominal design. Publishing any
photo requires reviewing its visible contents as well as removing metadata.
No X1/X2 image or hidden assembly is part of this workflow.

Source: [Meta image understanding](https://dev.meta.ai/docs/image-understanding).
The functional report tool uses the existing Responses tool-call envelope;
its arguments are additionally checked locally. Vision can misread a marking.
Bench measurements can reveal inconsistencies but do not guarantee detection
of every visual error or identify every alternative uniquely.

## Local validation

Image/core/provider/viewer checks passed 33 tests in total. The two loopback-server
tests initially could not bind inside the sandbox and passed with local network
permission; no external API was used. After the last display/review changes, all
14 image-workflow tests passed again. Browser QA passed 14 checks at 1440 and 390
pixel widths using an explicitly labelled software fixture, with zero real model
calls. See [UI result](known-design-ui-validation.json).

## Observed location limitation

The three actual responses contain approximate boxes that do not enclose the
full drawn component symbols. Image 03’s capacitor box omits the lower plate.
This post-hoc finding does not change the retained values/connections, but these
coordinates must not directly target SAM or identify a part for a repair. The
current UI does not use them for either purpose.
