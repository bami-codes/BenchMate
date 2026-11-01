# Codex to Claude: repair execution and filming

November 1 evening: D01 repair first, then B5. No new physical run has started;
actual hookup and intended-design review are pending. The available repair
rehearsal is scripted mock data, not a Spark-controlled physical repair.

The runner now verifies its complete local experiment import closure: 16 modules
plus the runner. Read-only viewer changes no longer invalidate readiness.
Acquisition, model and scoring policy is unchanged. The closure is tested.
Protocol: `examples/d01-repair-protocol/2026-11-01-repair-first/protocol.json`.

The current `benchmate watch` shows all five conditions, repair/operator steps,
recorded conditional curves and Scripted/Mock labels. Eleven viewer tests pass.
Read-only preview: http://127.0.0.1:8769 (mock, not the upcoming physical run).
Actual run directory will be added when one exists.

## Presentation points before filming

- The main success text must distinguish conditional model verification from
  command-input forecast agreement. `repair_verification_completed` records
  `passed` and `command_forecasts_pass` separately. A failed command forecast
  with passing conditional checks needs a visible explanation, not only raw data.
- Current plotted curves are `conditional`, available after measured IN exists.
  The actual prior command curves are `repair_prediction_frozen.forecasts`.
  Never animate conditional curves as if they existed before acquisition.
- In the final mock, the unchanged model fails the step but passes the small
  sine. Only the restored model passes the complete two-check suite. Do not
  imply every individual waveform separates both models.
- Keep the actual new model reason and publication event in the video. Precise
  component/hole coordinates come from the local operator guide, not Spark.
- Lead README with supported outcome and user benefit. Keep physical/mock labels
  by their examples; detailed limitations can move into one section. A working
  development fixture alone does not establish time saved or general accuracy.
- EE305's reported 14.1% discrepancy is motivation, not a real coursework case
  already measured and solved by BenchMate.
- TTS rough cut followed by a short same-script human reading comparison is
  sensible. Clarity, pacing and synchronization with actual decisions matter.

Codex is leaving the in-progress viewer and README files to Claude. Measurement
sources and original event records remain independently frozen and preserved.
