# George s7 replacement — 5 November 2026

Applied the operator-approved closing paragraph to `video/film/narration.txt` and replaced **only George s7.mp3**. The other six MP3 hashes and their clip-relative word/sentence timing objects are unchanged. Brian alternatives were not modified.

George (`JBFqnCBsd6RMkjVDRZzb`), `eleven_multilingual_v2`, stability0.60, similarity0.80, style0, speaker boost enabled, speed1.0, **seed20261105**; MP3/44.1kHz/128kbps. No trim, gain, resampling or speed changes were applied to the source clip.

## Approved text

BenchMate turns an unexplained output into a concrete next check. Spark chooses the experiment. The simulator predicts. The operator acts. The real board tests the explanation. Shown on five circuits; a first step toward AI-guided experiments on physical systems.

Only paragraph breaks were added to the spoken copy before the four role statements and before the new “Shown…” sentence. The spoken words are unchanged.

## Measured result

- New s7 MP3: **18.204s**.
- “Shown on five circuits” starts at **12.434s** within the clip (about **169.704s** globally with this duration map).
- Total current scene duration: **177.77s (2:57.77)**. This uses the upstream longer-s7 hold policy already prepared in `809b9d9`.
- `voice_durations.py` and `plan_shots.py` were rerun. The resulting `s27_wide` entry is in the active `shot_plan.json`.
- All seven audio files are valid originals; only s7 has new bytes. Automated transcription matched the new words after case/punctuation normalization, including AI-guided experiments on physical systems. Human listening approval is not claimed.

## Provenance and actual usage

Narration source commit: `c17ada55af5752bc769b958834eb58822fa76867`. Source SHA-256: `6dc14bb549879f8601de471fc2b7dfee99e88b6f71b391f56c355599c01fe1bf`.
New MP3 SHA-256: `03f454c42f822ee6a5ff52226ad1ccdec53367b0cb6162a8b6b8cb3df0469a96`.
Initial batch usage and its original checks remain in the manifest. The replacement is a separate revision with the old s7 hash/timing retained; the original binary is also in Git history. The original all-seven transcription result refers to the old s7; the added `s7_revision_checks` applies to this replacement.

This revision used **1 TTS call (107 credits) +1 transcription call (6 credits) =113 credits**, with no retries or additional cash charge. Subscription delta matches the provider costs. Remaining credits: **37,948**.

## For the film owner

Read the new `voice/timings.json`, `voice/durations.json` and `voice/shot_plan.json`; rerender the current shots and remux using `audio.py`. Recheck the muxed duration remains at most180s. There is no need to regenerate s1–s6. Only narration text, audio/timing artifacts and this handoff were changed; renderer/site source code was not edited.
