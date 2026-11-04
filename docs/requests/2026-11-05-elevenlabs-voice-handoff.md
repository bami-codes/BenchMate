# ElevenLabs narration handoff — 5 November 2026

Completed from adopted narration at main `0d4d544`.
Narration source SHA-256: `76a2b0c76d2b8f6b716ab768d225fa3e56348ab789ade37deaa7d46b525d5226`.

All seven original provider MP3s are in `video/film/voice/s1.mp3` through `s7.mp3`.
Voice: **George** (`JBFqnCBsd6RMkjVDRZzb`); model: **eleven_multilingual_v2**.
Settings: stability0.60, similarity0.80, style0, speaker boost enabled, speed1.0.
Format: MP3,44.1kHz,128kbps (available with the existing Starter subscription).
No trimming, normalization, resampling or time stretching was applied to the source MP3s.

## Clip and scene lengths

| Clip | Original MP3 seconds | Scheduled scene seconds |
|---|---:|---:|
| s1 | 5.805 | 7.00 |
| s2 | 14.629 | 15.83 |
| s3 | 44.071 | 45.27 |
| s4 | 44.536 | 45.74 |
| s5 | 17.276 | 18.48 |
| s6 | 16.347 | 17.55 |
| s7 | 11.981 | 13.18 |
| **Total** | **154.645** | **163.05** |

`voice_durations.py` has already been run. The current total is **163.05s**, including the existing0.4s before/0.8s after each clip. Re-read `filmTotal()` after loading the current shots before rendering; do not retain an old173s render end.

## Synchronization data

- [timings.json](../../video/film/voice/timings.json): clip-relative word/sentence times and named key cues. Global time is **scene start +0.4s +clip time**.
- [manifest.json](../../video/film/voice/manifest.json): exact spoken copy, source/audio hashes, source commit, settings, durations and credit totals.
- [quality-check.json](../../video/film/voice/quality-check.json): acoustic transcription checks and s7 silence measurements.
- [durations.json](../../video/film/voice/durations.json): actual scene lengths consumed by the film.

Use the original `narration.txt` for displayed spelling. Only the spoken copy changes `R1→R one`, `OUT→out`, `REF→ref`, `SAM→Sam`; s7 gets blank lines between its final four sentences. The canonical narration file was not edited.

## Key synchronization points

| Scene | Spoken cue | Clip start | Clip end |
|---|---|---:|---:|
| s3 | All three fail | 11.819 | 12.817 |
| s3 | writes a new circuit model | 17.032 | 18.367 |
| s3 | diode from out to ref | 18.785 | 20.178 |
| s3 | model is frozen | 27.725 | 28.584 |
| s3 | no refitting | 31.022 | 31.788 |
| s3 | five point one nine | 33.762 | 34.888 |
| s3 | four point zero five | 35.109 | 36.339 |
| s3 | The seal opens | 39.369 | 40.438 |
| s4 | two explanations remain | 5.909 | 7.338 |
| s4 | R one changed | 7.930 | 8.905 |
| s4 | expected range | 19.029 | 19.911 |
| s4 | Sam outlines | 22.721 | 23.557 |
| s4 | four point seven one kilohms | 27.550 | 29.280 |
| s4 | The seal reveals | 34.331 | 35.201 |
| s4 | After repair | 39.393 | 40.240 |
| s4 | no mismatch | 41.784 | 42.481 |
| s7 | Spark chooses the experiment. | 4.319 | 6.165 |
| s7 | The simulator predicts. | 6.490 | 7.895 |
| s7 | The operator acts. | 8.011 | 9.276 |
| s7 | The real board tests the explanation. | 9.555 | 11.738 |

Actual s7 gaps between the final four statements are about **0.527/0.301/0.468s** (detected below−35dBFS); the blank-line treatment already gives pauses. No additional silence was inserted into the MP3s.

## Verification and actual usage

s3 was generated first and reused. Its acoustic transcription contained the correct OUT→REF explanation and5.19/4.05/9mV statements. The remaining six clips were transcribed together afterwards. Neither transcription request included the reference transcript. After punctuation/case normalization and treating `R one`/`R1` as equivalent, the word sequences matched exactly (110 tokens for s3 and268 for the other six). All seven files decoded successfully and no sample clipping was detected in their unmodified originals.

These are automated checks, not a claim of human listening approval or proof of subjective delivery quality. Listen to s3, s4 and s7 when placing the final animation beats.

**7 TTS requests,2 transcription requests,0 retries.**2,299 input characters; actual TTS usage920 credits, transcription48 credits, total**968 credits**. Subscription usage moved0→968 and matches the response costs;**39,032 credits remain**. Calls used the existing Starter allowance with no incremental cash charge. This is a separate video-production cost, not an addition to the experimental Spark/SAM ledger.

## Next steps for the film owner

Run the current stage metadata export, render with its measured total, export metadata again, then `audio.py` and `narration_srt.py` as described in the current film README. Use the supplied cue times for the failure, diode proposal, reading and seal; stretching the whole scene alone does not guarantee word-level synchronization. Check final duration and sound after mux.

Only voice assets, generated timing/verification metadata and this handoff were added by Codex. Film/site code and the narration source remain with Claude.
