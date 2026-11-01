# Editing handoff — November 2

Ready locally:

- `out/d01-physical-highlight.mp4`: **51.359 s, 1920×1080, 30 fps**, English synthetic
  narration and burned-in captions. `out/d01-physical-highlight.srt` is the matching
  sidecar. This is one retained Oct 30 physical diagnosis, **not live footage** and
  not a repair. No separate vision/no-tool/B5 execution is spliced into its timeline.
- `out/benchmark-evaluation.mp4`: 9 s, 1920×1080, no audio. All completed first-attempt
  evaluation rows, including Spark Open interface failures; development probes excluded.
- `out/d01-spark-mock-replay.html`: actual Spark + simulated repair, clearly labelled.
- `audio/voice-audition/am_michael.wav` and `af_heart.wav`: two local voice options.

The physical highlight is also available in the public replay's Watch section.
Raw footage, generated speech and renders remain local apart from that explicitly
published, record-based clip. The source record and published clip hashes are retained.
Visual frames, timings, 1080p encoding and both audio/video streams were checked.
A final human listening pass is still appropriate before the submission edit.

Important for the full three-minute edit:

- Keep vision intake, the separate no-tool replies and Oct 30 diagnosis labelled as
  separate recorded examples. `narration.json` is an editing draft, not proof they
  happened in one continuous execution. The highlight uses its own reviewed script.
- Model parameters are locked before measurement. Measured-input conditional curves
  are drawn only after the measured trace appears. Repair command forecasts require
  their own score even if conditional verification passes.
- Physical repair, physical B5 and another operator's completion are not recorded yet.
  Never turn their placeholders into success claims. `extract_b5.py` and the full
  discovery scene currently target the original mock and contain that run's quote;
  a new physical run needs its own source/quote/score review before replacing them.
- Numbers use shape as well as colour; all fixed-plan rows remain. Unrun is not zero,
  incomplete is not a correct rejection, random repetitions are the same circuits.
- No final three-minute submission video has been exported or uploaded.

Rebuild the standalone highlight: generate local speech with `voice_highlight.py`,
then render with `render_highlight.py`. The former uses the versions and model revision
in `highlight-export.json`; the latter needs Playwright/Chromium and ffmpeg.
It checks both the physical-event hash and reviewed plot data before encoding.
Use `render_benchmark.py` for the numbers clip after `extract_benchmark.py`.
Fonts retain their OFL notices. Kokoro model code/weights are Apache-2.0.
