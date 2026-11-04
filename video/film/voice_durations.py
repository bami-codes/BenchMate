#!/usr/bin/env python3
"""Measure the narration clips and write voice/durations.json, which the stage reads to stretch each scene.

  python3 voice_durations.py            # voice/s1.mp3 … s7.mp3 → voice/durations.json

Each scene gets its clip length plus 1.2 s of air (0.4 before, 0.8 after), never shorter than 60 % of the planned length.
"""
import json, pathlib, subprocess
V = pathlib.Path(__file__).resolve().parent; VO = V / 'voice'
PLANNED = {'s1': 11, 's2': 18, 's3': 52, 's4': 43, 's5': 15, 's6': 20.5, 's7': 13.5}  # must match PLANNED in shots.js
out = {}
for sid, planned in PLANNED.items():
    f = next((p for p in [VO / f'{sid}.mp3', VO / f'{sid}.wav', VO / f'{sid}.m4a'] if p.exists()), None)
    if not f: print(sid, 'no clip; planned', planned, 's'); continue
    d = float(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', str(f)], capture_output=True, text=True).stdout.strip())
    out[sid] = round(max(planned * 0.6, d + 1.2), 2); print(sid, f.name, f'{d:.2f}s → scene {out[sid]}s (planned {planned})')
(VO / 'durations.json').write_text(json.dumps(out, indent=1) + '\n')
print('total', round(sum(out.get(k, v) for k, v in PLANNED.items()), 1), 's')
