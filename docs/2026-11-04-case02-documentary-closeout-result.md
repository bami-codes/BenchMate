# Case02 complete under the explicitly amended documentary-photo scope

Completed parent: `examples/reading-restored-v2/2026-11-04/records/20261103T182550-4ea22cc3a0/`.
Result: `result.json`; final status `run_completed`, restored verdict `consistent`,
caption **No mismatch in the tests Spark chose**. This combines the retained
validated fault diagnosis, isolated unordered0.451uF/0.101uF observations, actual
operator restoration, fresh-context consistent rerun and documentary restored
photo/SAM visualization. Every preceding failure and first selection is preserved.
It is not a first-attempt success, a blind test or proof all components are correct.

The operator explicitly requested skipping the restored Spark correspondence.
Scope/source freeze **dff609d6258aa0ad61851882759481d180ab825f** was committed,
pushed and remotely confirmed **before opening/converting/hashing the restored
DNG**. The scope was after diagnostic results and after upload/capture, which is
stated honestly. The old diagnostic prefix was archived byte-for-byte and verified
with its original auditor; immutable live files still match that snapshot. No
frozen numerical/guard source or old event was rewritten.

Actual new photo usage: **1 SAM3.1,0 Spark,$0.0025 estimated** at the retained
per-image estimate, not a billing invoice. SAM received the clean1600px image and
only `electronic component`. It returned **8 mask regions**, all retained. Those
include non-part/background geometry;8 is not a component count or coverage score.
All8 masks have exact native raster mapping and were drawn without stretching.
No OpenCV fallback, manual mask edit, body classifier, value reader, reference-name
assignment or operator body confirmation was used in this restored stage.

Artifacts:

- `photo-restored/prepared/`: clean image/full-frame input, scoped plan and the
  one SAM child with original response text and hash chain.
- `photo-restored/raw-conversion.json`: fixed original RAW conversion plus the
  explicit full-frame1600px compatibility-resize provenance.
- `photo-restored/native-SAM/`: all native rasters, exact-size masks, individual
  overlays, unassigned crops, parser diagnostics and crop manifest.
- `photo-restored/documentary/before-after-SAM.png`: both actual photos with all
  exact native mask outlines; no spatial registration or identity match implied.
- `photo-restored/documentary/manifest.json`: visualization-only scope, empty
  component assignments/values and both input hashes. The earlier fault photo
  retains its original capture state and prior7 native masks.

The original pinned RAW converter produced3024x4032 clean output privately, using
as-shot camera WB, no auto brightness/WB and the fixed mild sharpening. A local
preflight rejected its size before any SAM request or photo artifact was created.
The existing `known_design.sanitize_image` full-frame1600px resize was moved before
that check; the adapter manifest embeds the unchanged original RAW manifest and
source/render hashes. No crop, local visual tuning or changed selection rule was
introduced. This was an offline input compatibility correction, not an API retry.
The public documentary input/full PNG is1200x1600. Original DNG/full RAW derivatives
stay private. All37 produced PNGs were checked for absent EXIF/GPS/XMP/comment
metadata; original DNG is ignored and is not committed or sent to a model.

Binding omission is recorded as **waived, not satisfied**. Result flags:
`restored_binding_performed:false`, `restored_component_identity_verified:false`,
`SAM_used_as_identification_evidence:false`,
`prior_restored_binding_requirement_waived:true`,
`prior_restored_binding_requirement_satisfied:false`.
The native diagnostic `physical_repair_demonstrated:false` is never overwritten.
No physical action or further reading was requested in this documentary stage.

Current restored follow-up total: **6 Spark,1 SAM,estimated$0.05562755**.
Case02 including previous attempts: **28 Spark,2 SAM,estimated$0.32315000**.
Whole reading cohort: **64 Spark,3 SAM,estimated$0.63350110**. SDK dollar
reservations are retained separately and are not actual charges.

Keyless/network-free standard-library closeout audit:

```text
PASS events=574 forecasts=10 measurements=12 order_checks=43 prediction_files=4 run_status=run_completed head_sha256=ad05d5914d22d2333f9eddf8be546e0c2ec207ba094d0d81dc54ea5972a16ed8 scope=internal_integrity+recorded_order creation_time=unproven
```

Command: `python -m benchmate.reading_restored_sam_closeout verify <parent>`.
The old full-binding parent auditor is not used for this expressly waived branch;
the original diagnostic child/prefix still pass their original audits. PASS checks
retained integrity/order, not creation time, physical truth, authenticity or stable
instrument behavior on future boots.
