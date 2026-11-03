# Case 02 photo stage: SAM succeeded, ambiguous binding returned string null

Parent: `examples/reading-cohort/2026-11-03/records/20261103T165506-b6ad3e8cf7/`.
The completed fault diagnostic child still has native verdict `changed:C1` and
passed both reserved checks. The parent is now terminal `run_failed` at `bind`;
it remains counted and is not a completed repair pair. No automatic retry,
hardware command, component removal or restoration followed.

The operator supplied a newly captured corrected-state `case2-fixed.dng` in
response to the whole-board photo request. Existing pinned RAW conversion,
metadata-free sanitization and body decoding were used. The original DNG and
full conversion intermediates stay private. Published clean images and crops
contain no original phone metadata. No previous diagnosis, specimen assembly,
case map, file name or operator numeric value reached the photo models; the
binding request carried only the selected target ID C1 from the reading stage.

SAM3.1 received only the image and `electronic component`, once. Seven native
mask records survived body derivation, including both capacitor bodies. There
were zero accepted OpenCV fallback bodies. All original masks, derived masks,
candidate crops and rejected fallback contours are retained. The frozen decoder
used the existing cached OpenCV4.12.0, numpy2.2.6, Pillow12.3.0 and
meta-sam-parser0.1.0 environment. Resolving missing local imports added no paid
call, installation, algorithm change or rewritten native mask.

Spark received schematic, whole image, all seven retained body crops and geometry,
without a surface-value reader. It correctly stated the correspondence ambiguity:
both capacitors are parallel shunts between the same two nodes, so geometry and
wiring alone do not establish which is named C1 versus C2. It selected no body.
The returned arguments were:

```json
{"reason":"Both box-geometry capacitors are wired as identical parallel shunts to the same two nodes, so layout/wiring cannot distinguish C1 from C2.","sam_body":"null"}
```

The frozen validator permits JSON `null`, not the literal string `"null"`.
It therefore raised `Invalid body binding proposal retained; no retry.` The raw
reply and its completed child chain are preserved. This is an output-format
stop, not failed SAM localization, a new electrical failure, an assigned C1 body
or evidence that Spark could identify the two capacitors. Neither schema nor the
terminal event is changed retrospectively.

The existing operator fallback principle still applies, but the terminal chain
must not be reopened. A separately registered continuation can retain this failed
history and its valid diagnostic/forecast/photo artifacts, record the model's
abstention honestly, and accept an explicit operator-assigned existing mask.
No new diagnosis, photograph or model call is necessary just to assign that body.
The displayed upper capacitor is `sam-2`; operator confirmation/assignment is
pending. It must be labelled `chosen_by: operator`, never a successful Spark
correspondence. Numeric reading, seal reveal and restoration remain unperformed.

Photo-stage usage: **SAM1 + Spark1**, estimated **$0.01627945**
($0.0025 per-image SAM + $0.01377945 from Spark tokens). Attempt2 total:
**9 Spark,1 SAM,$0.11860230**. Case02 including miswired attempt1:
**17 Spark,1 SAM,$0.21665225**. Reading-cohort total:
**53 Spark,2 SAM,$0.52700335**. SDK dollar reservations are not invoices.

Full failed parent verification, with all bound child chains and photo artifacts:

```text
PASS events=292 forecasts=5 measurements=5 order_checks=22 prediction_files=2 run_status=run_failed head_sha256=0d0ec3edf91379cd43a017986d0c9ca5fd0feed67d3aea2cdbc04b771a9137f8 scope=internal_integrity+recorded_order creation_time=unproven
```

PASS describes retained integrity/order. The parent remains failed and the
unchanged numerical child remains a completed, reserved-validated fault diagnosis.
