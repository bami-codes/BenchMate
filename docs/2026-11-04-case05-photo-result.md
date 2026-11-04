# Case05: Spark selected sam-1 as W1 before the operator resistance reading

Pair: `examples/reading-cohort/2026-11-03/records/20261104T021333-c80ef3617e/`.
The physical pair is still in progress. No path resistance reading, seal reveal,
restoration or restored diagnosis has yet occurred at this point in the record.

The uploaded actual fault-state photo was converted with the existing fixed
camera-WB/no-auto-brightness/mild-sharpening RAW converter. The private DNG was
not committed or sent to a model. The clean full image is3024x4032; the full-frame
SAM input is1200x1600, SHA256
`08e61dd3f569ae5329ce083281a732c92c8dd31079dfa847f8e504fd29226fbe`.
PNG chunk checks found only image chunks; original GPS/EXIF was not copied.
Conversion provenance is bound separately in `photo-faulted/raw-conversion.json`.

Generic SAM3.1, `electronic component`, returned **7 native regions**. All7 exact
rasters and derived body crops are retained; this count includes connectors and
background geometry, not seven verified circuit components. Accepted OpenCV
fallback bodies:0. All7 retained IDs/crops were passed to the one Spark call;
Codex did not preselect the orange jumper ID.

Actual Spark output:

```json
{
  "candidate_bodies": [{
    "sam_body": "sam-1",
    "kind": "wire",
    "reason": "short orange insulated jumper with exposed ends seated in breadboard holes, wire body shape"
  }],
  "mapping_status": "unique",
  "sam_body": "sam-1",
  "reason": "orange jumper bridges the IN-side row to the OUT-side row matching intended W1 IN-OUT, other bodies are capacitor, resistor and connectors"
}
```

No surface value or prior operator reading was supplied or returned. The operator
then confirmed **“맞음 · W1과 IN/OUT 포트 확인”**. Model selection and operator
confirmation are separate records. The selected native contour alone is drawn
in `photo-faulted/candidate-display/Spark-selected-overview.png`; the context crop
is a display derivative, not a new model input or a new capture. All raw masks
remain unchanged. The named W1 is operator-added intended schematic topology;
its actual body selection is `chosen_by:muse_spark`.

The DMM observable is the **isolated mini-board IN-OUT path with W1 and contacts
retained**, not the orange jumper removed from its sockets. Disconnect all three
fixture-side lead ends, leave mini-board ends and W1/R1/C1 installed, float REF,
and measure across the free IN/OUT metal ends after USB-off/discharge wait.
This avoids silently excluding socket/contact resistance from the observation.
The operator is asked for a free numeric reading, range, unit and display format;
the prepublished source/range intervals, not a model value guess, determine fit.

New usage: **SAM1 + Spark1**, estimated **$0.01732470**
($0.0025 retained per-image SAM estimate plus$0.01482470 from Spark tokens).
Case05 so far: **10 Spark,1 SAM,$0.10775610**. Reading cohort plus the separately
labelled case02 demo reprocessing: **75 Spark,4 SAM,$0.75359715**. These are
estimates, not invoices or SDK reservation amounts. No hardware operation was
performed in the photo stage.

The original241-event physical diagnostic audit remains valid. The new compound
auditor's current-prefix path was also exercised in a temporary offline clone,
with a test-only terminal marker excluded from the actual record; it checked305
events successfully. This is an auditor integration test, **not** a claim the
actual pair is terminal, failed or completed. Original events were not modified.

Next is the operator's already-forecast path resistance reading. The fault
assembly remains sealed and the expected repair/rerun remains unperformed.
