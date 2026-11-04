# Video pipeline

> **Status, 4 November 2026.** No demo film has been made. What follows describes pipeline drafts from 2 November (narrated backup cut with mock scenes) and a newer draft that records the live site (`record_site.js`, `assemble.py`); neither has produced a submitted video. The public demo is the site at https://bami-codes.github.io/BenchMate/.

This pipeline builds recorded-data scenes for the three-minute demo. The final submission
edit is still pending. A complete **2:36 backup draft** and a standalone **51-second
physical-diagnosis highlight** are ready locally; see
[editing status](STATUS.md).

- `extract_*.py` read the hash-chained event logs in `examples/` and write `data/*.json`.
  Curves are the recorded predictions or the engine's own `conditional_curve`.
- `narration.json` holds the script; `tts.py` (Kokoro, local) voices it; `timeline.py` derives
  scene timing from the narration so animations and captions follow the speech.
- `stage.html` draws each scene at time *t*; `render.py` steps it frame by frame in Chromium
  and encodes one MP4 per scene. `music.py` synthesizes the background bed (no third-party audio);
  `mix.py` places the narration.

Generated audio, frames and renders (`audio/`, `frames/`, `out/`) and raw footage (`raw/`) are not committed.

The standalone highlight uses local [Kokoro](https://github.com/hexgrad/kokoro) and
[82M weights](https://huggingface.co/hexgrad/Kokoro-82M), not a hosted voice API.
`d01-highlight-narration.json` is its reviewed script; its independent timeline prevents
other executions from being presented as part of the Oct 30 diagnosis.
