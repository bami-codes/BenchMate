# Brian narration comparison — 5 November 2026

Brian is an alternative to the existing George clips. **The active George files and their scene durations have not been replaced.**

Files: `video/film/voice/brian/s1.mp3` through `s7.mp3`.
Voice: Brian (`nPczCjzI2devNBz1zQrb`), model `eleven_multilingual_v2`.
Same adopted narration, spoken spelling, previous/next context, seed, output format and settings as George: stability0.60, similarity0.80, style0, speaker boost enabled, speed1.0;44.1kHz/128kbps MP3.
All seven spoken-text hashes match the George manifest. Original MP3s have not been trimmed, levelled, resampled or time-stretched.

## Length comparison

| Clip | Brian seconds | George seconds | Brian scene seconds |
|---|---:|---:|---:|
| s1 | 6.084 | 5.805 | 9.48 |
| s2 | 14.396 | 14.629 | 15.60 |
| s3 | 40.356 | 44.071 | 41.56 |
| s4 | 44.164 | 44.536 | 45.36 |
| s5 | 15.975 | 17.276 | 17.18 |
| s6 | 16.161 | 16.347 | 17.36 |
| s7 | 11.889 | 11.981 | 13.09 |
| **Total** | **149.026** | **154.645** | **159.63** |

Scene lengths include the newer2.2s cold-open lead adopted in `6dbd3f6`; only the Brian alternative duration map was recalculated here.

Brian is about5.62s shorter on the same script and speed setting. This is a duration observation, not a claim about subjective quality.

## Verification and listening checks

s3 passed the normalized word-sequence check, including OUT→REF and5.19/4.05/9mV. The other six clips were transcribed together; punctuation/case and `R one`/`R1` are normalized consistently with George.

The first transcript differed on **Muse Spark → MuSpark**, **it chose → it shows**, and **forum → form**. A third request transcribed only those three sentence excerpts without supplying the reference text. It returned **forum** correctly, but still wrote **MuSpark** and **it shows**. The first and follow-up transcripts and their differences are retained in `quality-check.json`.

**These are transcription disagreements, not proven speech errors. Human listening is needed for s2's first sentence (0–4.3s) and s4's last sentence (about39.1–43.8s).** No spelling changes or retakes were made merely to make a recognizer pass; the variant remains a controlled voice-only comparison. The same script and settings remain intact.

Actual s7 gaps between its final four statements are about0.573/0.512/0.496s. All seven audio files decoded successfully. Human listening approval is not claimed.

## Usage

7 TTS calls:920 credits.3 transcription calls:51 credits. **971 credits total,0 retries, no incremental cash charge** within the existing Starter allowance. The subscription counter changed968→1939, matching the provider response costs;38,061 credits remain. This cost is separate from the experimental Spark/SAM ledger.

## Files for the film owner

- [Brian manifest](../../video/film/voice/brian/manifest.json): settings, source/audio hashes, utterances and usage.
- [Brian timings](../../video/film/voice/brian/timings.json): clip-relative words/sentences and key cues.
- [Brian quality checks](../../video/film/voice/brian/quality-check.json): retained transcripts and unresolved listening checks.
- [Brian scene lengths](../../video/film/voice/brian/durations.json): alternative scene lengths; **not installed over the active George timeline**.

If Brian is selected, switch all seven clips as a set and recalculate the active scene durations before rendering/mixing. Do not combine Brian timings with George audio. Leave the currently active George clips alone until that choice is made.
