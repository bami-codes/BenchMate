#!/usr/bin/env python3
"""Final assembly: out/film.mp4 (rendered frames) + narration clips + a quiet synthesized bed → out/benchmate.mp4 and .srt.

  python3 mux.py                        # uses voice/sN.mp3 where present, out/captions.json and out/scenes.json from render.js --meta

Narration starts 0.4 s into each scene (the scene lengths already come from the clips). The bed is a few sine chords,
synthesized here; nothing third-party. Captions are burned into the frames; the .srt repeats them for the player.
"""
import json, math, pathlib, subprocess, wave
import numpy as np
V = pathlib.Path(__file__).resolve().parent; OUT, VO = V / 'out', V / 'voice'
scenes = json.loads((OUT / 'scenes.json').read_text()); caps = json.loads((OUT / 'captions.json').read_text())
total = float(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', str(OUT / 'film.mp4')], capture_output=True, text=True).stdout.strip())


def bed(total_s, path):
    sr = 44100; t = np.arange(int(total_s * sr)) / sr; y = np.zeros_like(t)
    chords = [(110, 164.81, 196), (98, 146.83, 196), (87.31, 130.81, 174.61), (110, 164.81, 220)]
    for i, ch in enumerate(chords * int(math.ceil(total_s / 32))):
        a, b = i * 8, (i + 1) * 8; m = (t >= a) & (t < b); env = np.sin(np.pi * np.clip((t[m] - a) / 8, 0, 1)) ** 0.7
        for f in ch: y[m] += 0.07 * env * np.sin(2 * np.pi * f * t[m]) * (1 + 0.2 * np.sin(2 * np.pi * 0.13 * t[m]))
    y *= np.clip(t / 2, 0, 1) * np.clip((total_s - t) / 3, 0, 1)
    with wave.open(str(path), 'wb') as wf: wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(sr); wf.writeframes((np.clip(y, -1, 1) * 32767).astype('<i2').tobytes())


bedf = OUT / '_bed.wav'; bed(total + 1, bedf)
inputs = ['-i', OUT / 'film.mp4', '-i', bedf]; filters = ['[1:a]volume=0.45[bed]']; mix = ['[bed]']; n = 2
for sc in scenes:
    f = next((p for p in [VO / f"{sc['id']}.mp3", VO / f"{sc['id']}.wav", VO / f"{sc['id']}.m4a"] if p.exists()), None)
    if not f: continue
    ms = int((sc['start'] + 0.4) * 1000); inputs += ['-i', f]; filters.append(f'[{n}:a]adelay={ms}|{ms},volume=1.0[v{n}]'); mix.append(f'[v{n}]'); n += 1
filters.append(''.join(mix) + f'amix=inputs={len(mix)}:normalize=0,alimiter=limit=0.95[aout]')
subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', *map(str, inputs), '-filter_complex', ';'.join(filters), '-map', '0:v', '-map', '[aout]', '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', '-movflags', '+faststart', str(OUT / 'benchmate.mp4')], check=True)
fmt = lambda s: f'{int(s // 3600):02d}:{int(s % 3600 // 60):02d}:{int(s % 60):02d},{int((s % 1) * 1000):03d}'
(OUT / 'benchmate.srt').write_text(''.join(f"{i + 1}\n{fmt(c['a'])} --> {fmt(c['b'])}\n{c['text']}\n\n" for i, c in enumerate(caps)))
print('wrote', OUT / 'benchmate.mp4', f'{total:.1f}s', 'voice clips', n - 2)
