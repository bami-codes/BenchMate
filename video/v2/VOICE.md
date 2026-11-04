# Narration: how to generate the voice (ElevenLabs, on your machine)

The container cannot reach ElevenLabs or any TTS API, so the voice is generated outside and committed here.

1. Open ElevenLabs → Text to Speech. Voice: a calm documentary narrator (Daniel, Brian or Adam work; pick
   the one that reads "ngspice" and "kilohms" cleanly). Model: Eleven Multilingual v2 (or Turbo v2.5).
   Settings: Stability 0.55 · Similarity 0.75 · Style 0.15 · Speaker boost on · Speed 0.98.
2. Generate **one clip per scene** from `script.json` (`scenes[].vo`), exactly the text there. Seven clips.
3. Download as MP3 (44.1 kHz) and save them as `video/v2/voice/s1.mp3 … s7.mp3`. Commit and push to `main`.
4. Listen once to s3 and s4: the numbers must be read as "eighty-seven millivolts", "four point seven one kilohms",
   "five point one nine", "one N four one four eight". If a number is swallowed, regenerate that scene only.

Fallback inside the container: Kokoro ONNX (`pip install kokoro-onnx soundfile` plus the model files from the
kokoro-onnx GitHub release), voice `am_michael`, speed 1.0. Lower quality; use only if ElevenLabs is not possible.
