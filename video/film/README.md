# The film: twenty-seven composed shots

`shots.html` + `shots.js` compose each 1920×1080 frame directly: the site's scope and meters are the instruments, everything
else is set at film scale. Every waveform, number, range, label, verdict and seal sentence is read from `site/data/runs/*.json`
and `cases.json`; `frame(t)` is a pure function of time (no one-shot state), so frames render one by one at 60 fps and a frame
rendered cold equals the same frame reached in sequence. Each shot fades in from the mat (0.4 s) and out to it (0.3 s); two shots are never on screen together. Burned-in captions are off by default (`shots.html?cap=1` turns them on, on their own line at the bottom); the caption text always goes out as `out/benchmate.srt` for closed captions.

Seven narration clips (`voice/s1.mp3 … s7.mp3`, text in `narration.txt`) drive the seven scenes: `voice_durations.py` writes
`voice/durations.json`, and each scene's shots stretch together to its clip (PLANNED in `shots.js` and `voice_durations.py`
must agree; today s1 9, s2 16, s3 47, s4 43, s5 17, s6 21, s7 13 = 166 s).

    python3 -m http.server --directory <repo root> 8796 &      # the stage reads site/data over http
    node render.js film 0 173 --fps 60 --jobs 3                # out/film.mp4 (about 6 min on 4 cores); t1 = filmTotal()
    node render.js film 0 0 --meta                             # out/captions.json, out/scenes.json, out/sfx.json
    node render.js chk 0 173 --stills 7.5,41,53                # review stills → frames/
    python3 voice_durations.py                                 # clips → voice/durations.json (scene lengths follow the clips)
    python3 audio.py                                           # out/benchmate.mp4 (bed, SFX from sfx.json, narration) + a shot-summary .srt
    python3 narration_srt.py                                   # overwrites out/benchmate.srt with the narration's own sentences (the CC to upload)

After adding voice clips: `voice_durations.py`, then `--meta` to read the new total, render again with that total, `--meta`
again, then `audio.py`. `stage.html` + `film.js` are the earlier one-camera version, kept for reference; `mux.py` is superseded by `audio.py`.
