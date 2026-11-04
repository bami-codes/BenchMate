#!/usr/bin/env python3
"""Closed captions from the narration itself, not from the shot summaries.

  python3 narration_srt.py            # narration.txt + out/scenes.json (+ voice/durations.json) → out/benchmate.srt

Each scene's sentences are laid over that scene's clip span (scene start + 0.4 s, for the clip's length when a clip exists,
else the scene length minus 1.2 s), split in proportion to their character counts. With real clips this is close; the four
beats that must land (all explanations failed, the diode proposal, the 4.71 kΩ reading, the seal) are checked by ear after.
"""
import json, pathlib, re, subprocess
V = pathlib.Path(__file__).resolve().parent; OUT = V / 'out'; VO = V / 'voice'
scenes = {s['id']: s for s in json.loads((OUT / 'scenes.json').read_text())}
TIMED = json.loads((VO / 'timings.json').read_text())['scenes'] if (VO / 'timings.json').exists() else None
text = (V / 'narration.txt').read_text()
blocks = re.findall(r'^\[(s\d)\][^\n]*\n(.+?)(?=\n\s*\n|\Z)', text, flags=re.M | re.S)

def clip_len(sid):
    f = next((p for p in [VO / f'{sid}.mp3', VO / f'{sid}.wav', VO / f'{sid}.m4a'] if p.exists()), None)
    if not f: return None
    return float(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', str(f)], capture_output=True, text=True).stdout.strip())

def ts(x):
    h, r = divmod(max(0.0, x), 3600); m, s = divmod(r, 60)
    return f'{int(h):02d}:{int(m):02d}:{int(s):02d},{int(round((s - int(s)) * 1000)):03d}'

cues = []
for sid, body in blocks:
    sc = scenes.get(sid)
    if not sc: continue
    sentences = [x.strip() for x in re.split(r'(?<=[.!?])\s+', ' '.join(body.split())) if x.strip()]
    start = sc.get('voice_at', sc['start'] + 0.4); length = clip_len(sid) or max(1.0, sc['seconds'] - 1.2)
    timed = TIMED.get(sid, {}).get('sentences') if TIMED else None
    if timed and len(timed) == len(sentences):   # the clips' own alignment: exact sentence times
        for x, w in zip(sentences, timed): cues.append((start + w['start'], start + w['end'] - 0.05, x))
        continue
    total = sum(len(x) for x in sentences) or 1; t = start
    for x in sentences:
        d = length * len(x) / total
        cues.append((t, min(t + d, start + length) - 0.05, x)); t += d
with (OUT / 'benchmate.srt').open('w') as f:
    for i, (a, b, x) in enumerate(cues, 1): f.write(f'{i}\n{ts(a)} --> {ts(b)}\n{x}\n\n')
print(f'{len(cues)} cues from {len(blocks)} scenes → {OUT / "benchmate.srt"}', '(clip lengths used)' if any(clip_len(s) for s, _ in blocks) else '(no clips yet: scene lengths used)')
