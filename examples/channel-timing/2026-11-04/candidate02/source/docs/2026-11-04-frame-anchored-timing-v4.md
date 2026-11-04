# Frame-anchored measured-IN model, v4

This is an engineering revision before new data, not a replacement verdict for
an old experiment. The rejected v3 source,70 synthetic controls and adverse
regression results remain in commit `ba95743` and candidate01. Original107-source
and wire-reading freezes, all original official results and counted failures
remain unchanged. A new physical diagnostic uses a separate numbered attempt.

## One fixed rule for every passive topology

The input-only solver uses recorded frame times and recorded A1/A2 completion
delays. Firmware records a frame immediately after writing the DAC, then reads
A1, A2, A3 and A4. A frame is therefore a recorded post-write marker, not an
independently calibrated DAC-switching/aperture timestamp. No fitted delay,
gain, offset or other timing nuisance is introduced.

For a step, the only declared level transition is frame `samples//10`. For a
sine, firmware writes the next rounded DAC code every frame; each write is
conservatively treated as a possible level transition, including rounded equal
codes. The rule does not inspect OUT or infer edges from output residuals:

1. Keep the preceding measured IN level through the transition frame.
2. From that frame, interpolate to its actual A1 completion sample.
3. Where the command level does not change, interpolate between the successive
   A1 samples, retaining the measured slow IN response.
4. Evaluate the circuit at actual A2 completion times. Hold endpoints where
   there is no measured history; retain the declared repeated-first-cycle sine
   initialization and its numerical settling check.

Thus a measured input jump cannot be smeared backwards across a known command
transition. Neither the IN ramp length nor the IN–OUT skew is hardcoded as52/53µs.
The same function handles R/C/D/W models and their literal proposed structures;
it does not branch on case ID, old verdict, hidden assembly or a chosen component.
Pre-measurement command forecasts retain their existing ideal buffered DAC and
declared1kΩ instrument path; measured-IN conditional and command checks stay
separate. No996Ω calibration is introduced: the historical fixture notes contain
996Ω readings, while this cohort's declared instrument remains1kΩ. The fallback
driver-reconstruction model was not needed or activated.

## Engineering checks before new hardware

`candidate02` retains the complete qualification artifacts and hashes.

- Independent analytic truth:70 checks across seven normal/fault R/C/W controls,
  with a1kΩ source path and53µs channel skew. For05-type direct input capacitance,
  reserved-step worst RMS goes **13.206→2.749mV** (old fails/new passes).
  Other-design pass/fail changes: **0**. These are simulation controls, not hardware.
- Original-record regression:17 unique diagnostic logs,60 captured waveforms,
  including all current01/04/02/05 attempts, failures and restored followups,
  plus the five assigned previous-protocol official logs as a separate
  development group. Same-action final verdict changes: **0**.
- The only other-case internal change is02 attempt1 `proposal:1` from a source-
  current `fit_error` to computed `inadequate`; it remains an abstention with
  no held-back pair. This is reported, not hidden as “zero changes everywhere”.
- In the old05 restored log, nominal/R1/C1 training fits become adequate.
  Nominal worst RMS changes **9.303→3.805mV**, **10.167→6.460mV**; sine stays
  **5.986mV**. No old reserved data exists; this is training support only.
- Fourteen focused software checks pass, including independent physical controls,
  no pre-write input rise, real timestamp use, no OUT/timing fit fields,
  reserved-output exclusion, unchanged command forecasts and a complete mock
  tool loop freezing before holdout. Mock source/actor are explicitly recorded.

All regional and whole-waveform thresholds remain9mV. Raw A3 primary3mV,
A4 auxiliary-only behavior, trusted-channel voltage/rail/settling checks, current
and voltage bounds, acquisition timing limits,1kΩ instrument configuration and
new-boot10second wait remain. No firmware or electrical guard is changed.
This revision is not a calibration certificate or proof of a unique physical
cause. Live guards and new reserved measurements still determine the result.

## Common runtime and case05 restored attempt2

`channel_timing_session_v4.Session` reuses the original menu, tools, hypothesis
families, component-value optimizer and outcome rules, substituting only the
qualified input reconstruction. Spark still chooses each training experiment;
the runner does not schedule a winning order. Only existing R/C/diode parameters
are fitted on training OUT; reserved OUT is never fitted. No case truth, earlier
reading, earlier waveform, photo or verdict is supplied to the new model context.

`channel_timing_followup_v4` registers a counted, non-selected restored-only
followup before any new API request or stimulus. Case05's next ordinal is2.
It binds the unchanged measurement protocol, new model/session/runner source
hashes, qualification, reviewed intended design and original terminal record.
Its original abstention remains counted and first-selected. No previous chain
is reopened. The new run requires an actual unchanged-board USB reconnect,
fresh unarmed PING-only preflight and the preserved10second startup wait.

The physical engine keeps W1 B3-B8,10kΩ E8-E13,105 C8-C13, green IN at large A35,
original OUT/REF, the1kΩ instrument path and no output load as its initial setup.
The external20kΩ stays removed. Additional photo/SAM/value requests are0 because
the operator confirmed unchanged mini-board layout and an external-only repair.
No old photograph is relabelled as a new restored capture.

At most8 Spark requests are planned, estimated$0.06–0.12; standing operator
authorization applies, and actual usage is reported. No automatic retry after a
failed guard, firmware/transport error or completed abstention. The model and
training parameters are frozen and pushed before fresh reserved acquisitions.
A consistent result is labelled **No mismatch in the tests Spark chose**;
native `physical_repair_demonstrated:false` is never overwritten.

The qualification artifact, code and registration must be committed/pushed
before execution. Numerical audit remains available with `python -m benchmate
verify <run>`. The added compound audit also verifies the registered source,
qualification and preserved original pair, with no key/network dependency:

```sh
PYTHONPATH=src .venv/bin/python -S -m benchmate.channel_timing_followup_v4 verify <run>
```

Both audits establish internal integrity and recorded order, not original
creation time, physical wiring truth or calibrated meter accuracy. Recorded
times are backed by prospective protocol/registration and prediction commits.
