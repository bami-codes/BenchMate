# Case UI integration verification — 2026-11-02

Claude's handed-off `index.html`, `app.js` and `style.css` are integrated with the existing
case/replay/runner APIs. The user explicitly authorized Codex's corrections and commit.
No hardware or paid API was used. The frozen D01 protocol and its 17 source files are unchanged.

## Changes verified automatically

- All 512 plot points, including the output-channel delay, remain inside the time window.
  Paired hypotheses use the same axes.
- Failed regional checks remain failures even when overall RMS is below 9 mV.
- Mock command-input forecasts and measured-IN conditional verdicts have separate labels.
- A late run lookup or poll cannot overwrite another case; a stale confirmation card cannot POST.
- Reloading a lost launch does not start a replacement run; recovery requires an explicit click.
- A failed confirmation fetch restores the same checked card for an explicit retry.
- Confirmed designs, forecasts, operator requests and results retain backend hash/revision guards.
- Photo masks retain exact-image attribution. Original GPS photographs are never served.
- New local photo registration preserves originals and prior references; JPEG output has no EXIF.

Commands and results:

```sh
node --test tests/test_case_ui.cjs
# 7 passed (pure JS VM/state tests, not browser automation)
.venv/bin/python -m pytest -q tests/test_board_reference.py tests/test_photo_evidence.py tests/test_photo_bench_geometry.py tests/test_photo_bench_media.py tests/test_case_runner.py tests/test_case_conversation.py tests/test_case_review.py tests/test_design_replay.py tests/test_known_design.py tests/test_d01_repair.py
# 121 passed
```

## Visual verification and limits

The integrated server is `http://127.0.0.1:8774`, output `.private/case-review/integrated-ui-qa`.
Codex observed the final desktop replay: full loaded curves, 32.5/3.00 mV comparison,
nominal-R assumption below the headline, reference-photo caption, and source-labeled photo dialog.
This inspection does not establish a complete new button-through test.

The browser connector returned `browser access host unavailable`, and native Chrome input/state
updates became unreliable. Codex continued in a separate Safari tab and completed an actual
button-through on software QA case `102f4ed78f524a5a8dfcef709018bb5f`:

- Entered a new question; changing C to 2 µF blocked the archived run. Restoring 1 µF opened it.
- At event 49, the loaded check showed locked gain/tau numbers and “Not measured yet”, not
  pre-acquisition conditional curves.
- Started a scripted mock. The load button stayed disabled until all three checks were clicked.
- Confirmed the load, then observed 3 simulated waveforms and the frozen repair forecasts.
- The repair button stayed disabled until all five simulated checks were clicked.
- Confirmed repair and refreshed the page. It retained “Simulated repair verified”, 5 simulated
  waveforms, 0 API calls and 0 physical measurements.
- The step graph separately displayed 0.49 mV measured-IN conditional error and 0.56 mV
  plotted-forecast error; the unchanged model was rejected at 11.4 mV.
- Opened the historical board-photo dialog and inspected its state disclaimer and photograph.

Native screen capture later failed with `SCStreamErrorDomain -3811`. A new mobile-width pass,
mask-selector click-through and UI failure/cancel variants were not completed in this pass.
Those software paths have automatic coverage; Claude's earlier UI report applies to its handed-off
version. Do not describe this as exhaustive browser or mobile testing.

No new repair photo has been registered. Existing displayed board images are historical references,
not photographs asserted to match the replay. P2 automatic endpoint/component identification and
live hardware execution are still outside this completed software integration.
