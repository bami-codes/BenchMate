# Recorded Spark physical RC demonstration

This read-only demonstration uses the completed October 30 physical D01 record.
It makes no new measurement or API request and does not change the original log.

```sh
uv run benchmate view examples/hardware-spark-rc/2026-10-30/20261029T174402-d3eaa8e612/execution --output runs/demo/physical-d01.html
```

Open `runs/demo/physical-d01.html` locally. It embeds the hash-verified event
record, interface and fonts and needs no internet connection. **Replay** and
**Physical observations · provisional** are separate labels. Replay advances
through key recorded actions; the elapsed time remains the original run time,
not the playback animation duration.

## A short demonstration

1. Select **Tau fitted**. The first new unloaded trace gives 21.384 ms. R and C
   are still ambiguous; this was a training fit, not independent verification.
2. Select **Load selected**. Spark chose a manual output-load intervention.
   The operator, instrument and numerical engine are identified separately.
3. Choose the loaded step in the condition selector. The recorded C-change
   prediction passes at 2.998 mV RMS; R change fails at 32.457 mV. No additional
   fitting is performed by the viewer.
4. Select **Models fixed**, then **Reserved check passed**. The first of these
   shows no future waveform: only parameters are fixed before acquisition.
   The voltage curves depend on the newly measured IN. The reserved 0.15 V,
   5 Hz sine supports C change at 3.043 mV RMS without refitting the scored OUT.
5. Open **Read original report** to inspect the unchanged Korean model report.
   The English reading aid is explicitly labelled; it is not a new model quote.

Scores show **whole / worst-region RMS**. Both must meet the common 9 mV
engineering allowance. The nominal model's reserved whole RMS is 8.539 mV,
but its worst region is 11.648 mV, so it remains failed. The nominal score and
full raw prediction remain available even though the main comparison plots
R-change and C-change curves.

The plots show voltage changes from each separately acquired HOLD origin.
The viewer subtracts those recorded origins for display; it does not refit a
curve or alter residual differences. It adds no reconstructed unloaded fit.
All 7,680 raw frames, the five original API requests and source records remain
in the evidence archive. The UI counts three scored waveform observations;
the remaining frames are independent stationary guards/origins.

This supports the limited measured-input conditional RC result. It does not
establish absolute voltage calibration, unique general topology, B5 discovery,
blinded reliability or a physical repair performed by Spark.

## Validation

The physical event reducer is checked against the real archived record for
future-result hiding, exact curve provenance, regional failures, failed
prefixes and source immutability. Browser checks cover 1440×900, 1280×900 and
390×844 layouts, model/condition selection, measured-IN toggling, original
report access, keyboard/replay operation and persistent connection errors.
The existing synthetic discovery screen is also regression checked.

`scripts/check_physical_viewer.mjs` expects a separately launched isolated
Chrome on local DevTools port 9338, never the user's browser profile. See
[validation result](physical-viewer-validation.json) for this build's checks.
