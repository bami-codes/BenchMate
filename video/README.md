# Video pipeline

The 3-minute demo video is generated from the recorded runs, not drawn by hand.

- `extract_*.py` read the hash-chained event logs in `examples/` and write `data/*.json`.
  Curves are the recorded predictions or the engine's own `conditional_curve`.
- `narration.json` holds the script; `tts.py` (Kokoro, local) voices it; `timeline.py` derives
  scene timing from the narration so animations and captions follow the speech.
- `stage.html` draws each scene at time *t*; `render.py` steps it frame by frame in Chromium
  and encodes one MP4 per scene. `music.py` synthesizes the background bed (no third-party audio);
  `mix.py` places the narration.

Generated audio, frames and renders (`audio/`, `frames/`, `out/`) and raw footage (`raw/`) are not committed.
