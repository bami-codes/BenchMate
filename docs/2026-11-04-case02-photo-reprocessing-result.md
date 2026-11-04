# Case02 photo stage reprocessed for the demo

At the operator's request, the existing case02 photograph and seven retained SAM
body crops were sent to Spark again using the candidate-set output contract.
This is an actual model call, with the request committed and pushed as `af3b1ca`
before execution. It is a **photo-stage reprocessing after the original bench
experiment**, not a new physical run or a new blind evaluation.

Record: `examples/photo-reprocess/2026-11-04/case02-candidates-v3/records/20261104T014142-817c2bdb8a/`.

Spark returned:

- `sam-2`, kind `C`: rectangular blue box body with two leads, capacitor form.
- `sam-3`, kind `C`: the same visible form.
- `mapping_status: ambiguous`, `sam_body: null`: the two bodies occupy parallel
  shunt positions on the same two nets, so layout cannot name C1 versus C2.

All seven IDs were supplied without preselection of the capacitor IDs. The model
received the intended schematic, complete clean photograph, body geometry and
baseline crops; no diagnostic result, prior operator reading, specimen truth or
private case mapping was supplied. Surface values were not requested or returned.
The raw string `"null"` was explicitly normalized to JSON null, preserving the
original arguments and normalization receipt; there was no retry.

Actual new usage: **Spark 1, SAM 0, hardware 0**, estimated **$0.01233995** from
the retained cohort tariff, not an invoice. Case02 cumulative including this demo
reprocessing: **29 Spark,2 SAM,$0.33548995**. Whole reading cohort plus the demo
reprocessing: **65 Spark,3 SAM,$0.64584105**. The website includes the additional
call and labels its photo stage as reprocessed.

The new overlay outlines only the model-returned IDs, using the unchanged native
masks and separate external green contours. The raw seven-mask output remains.
The demo displays this new candidate selection at its photo stage, then replays
the existing frozen forecast, isolated0.451/0.101uF observations and scores.
Its caption states that the photo stage was reprocessed on4Nov and the bench
readings come from the earlier experiment. Actual observation timestamps and
hashes stay intact. The original Codex-selected DMM group remains the historical
source of those readings; its authorship is not reassigned to Spark.

`historical_photo_stage` retains the old null-format stop and candidate-group
selection in the downloaded demo JSON. Neither original experiment chain nor its
classification was rewritten. New proposal and child chains pass integrity and
output-binding checks (5 parent events,5 Spark events). Existing case02 closeout
still passes its original574-event audit. Parser checks pass7/7.

For regenerating the site, first run Claude's historical extractor, then apply
the actual new model receipt with this offline command (no paid requests):

```sh
PYTHONPATH=src python scripts/apply_case02_photo_demo.py \
  examples/photo-reprocess/2026-11-04/case02-candidates-v3/records/20261104T014142-817c2bdb8a
```

The rendering helper requires Pillow, NumPy and OpenCV. It validates the model's
candidate IDs, both hash chains and proposal hash before applying the demo data.
It preserves every measured waveform, score, frozen interval and seal value.
It does not modify frontend source. The v3 binding adapter is implemented and
used for this photo reprocessing; wiring it into future physical-case commands
still requires the corresponding versioned registration/auditor integration.
