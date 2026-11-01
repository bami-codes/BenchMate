# Video pipeline

This pipeline builds recorded-data scenes for the three-minute demo. The final submission
edit is still pending. A complete 51-second physical-diagnosis highlight is ready; see
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
