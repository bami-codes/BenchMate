# New case 01 — SAM and Spark correspondence

The operator supplied a new fault-state photograph after the reading forecast
publication. This case remains **known to developers, not blind**. The reading
forecast at `edec9d0` is unchanged; the photograph was not an input to terminal
fitting, reading selection or forecast generation.

Pair: `runs/reading-cohort/20261103T125924-bf8f64512b/`.
Photo artifacts: `photo-faulted/` inside the
[public pair folder](../examples/reading-cohort/2026-11-03/records/20261103T125924-bf8f64512b/).

The original DNG remains private. Pinned fixed RAW conversion retained a
3024×4032 metadata-free PNG; source GPS/EXIF was not copied. Both unsharpened
and fixed mild-sharpening derivatives and conversion settings are retained.
The full render SHA-256 is
`d5753b2ebc9ea48b2aca7368463691c31e08d164ef1a2dd79e465a376df3f5fe`.

SAM 3.1 received only generic `electronic component` plus the clean image.
It returned four native masks, all retained. Four geometric bodies survived,
including a large breadboard region and connector; this is **not four correctly
detected circuit components**. The pinned OpenCV fallback added no new bodies.
All its contour decisions remain in `decoded/body-manifest.json`.

Spark received the intended schematic, whole clean photo and four indexed body
crops, then selected **sam-1 → R1**. Its reason was the small axial two-lead
cylindrical body and series position, distinct from the box-shaped body. The
operator confirmed that correspondence and chose isolated DMM resistance as
the reading source. No operator reassignment was used: final `body_binding`
retains `chosen_by:muse_spark`, `operator_confirmed:true`.

The visible R1 highlight is an actual native SAM mask, not a manually painted
outline: `decoded/native-SAM/electronic component-object-1-record-1-overlay.png`.
Its original bounds are `[349,569,537,613]` in the 1200×1600 SAM input. Native
mask/confidence and the separately derived body mask are both retained; no
calibrated segmentation accuracy is claimed.

There was **no surface-value inference**: no resistor color-band vote, capacitor
code decoding, candidate-value tool or value-based selection. Model-authored
body correspondence is distinct from the operator's later numeric reading.

This photo stage used **SAM 1 + Spark 1**, estimated $0.01461420
($0.0025 SAM + $0.01211420 binding). New-cohort cumulative usage at this point is
**Spark 9 + SAM 1**, estimated **$0.08277320**. No hardware commands were sent
during photo processing. The operator has reported `4.71kΩ`; conditions and
reading-photo evidence are pending, so no formal score or repair conclusion
has yet been recorded. Values will not be refitted or changed to match a photo.
