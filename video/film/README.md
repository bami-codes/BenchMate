# The film (v3): one stage, one camera

`stage.html` + `film.js` place the site's own parts (scope, meters, notebook cards, schematic, tape) on one large sheet and
move a virtual camera over it for about 2:50. Every waveform, number, band, verdict and seal sentence is read from
`site/data/runs/*.json`, `cases.json` and `census.json`; `frame(t)` is a pure function of time, so frames are rendered
one by one (60 fps) and the result is deterministic.

    python3 -m http.server --directory <repo root> 8796 &      # the stage reads site/data over http
    node render.js film 0 170 --fps 60 --jobs 3                # out/film.mp4 (about 5.5 min on 4 cores)
    node render.js film 0 170 --stills 9.5,24.5,70.5           # review stills → frames/
    node render.js film 0 0 --meta                             # out/captions.json, out/scenes.json
    python3 voice_durations.py                                 # voice/s1.mp3 … s7.mp3 → voice/durations.json (scene lengths follow the clips)
    python3 mux.py                                             # out/benchmate.mp4 + out/benchmate.srt (narration + bed)

After adding voice clips: run `voice_durations.py`, then render again (the timeline stretches to the clips), then `--meta` and `mux.py`.
The narration text is `../v2/narration.txt`; the shot list is `../v2/script.json`.
