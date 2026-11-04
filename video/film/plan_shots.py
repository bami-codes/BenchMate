#!/usr/bin/env python3
"""Where each shot starts, from the words of the recorded narration.

  python3 plan_shots.py      # voice/timings.json + voice/durations.json → voice/shot_plan.json (global seconds)

An anchor is (scene, text, lead): the shot starts `lead` seconds before that sentence or key cue is spoken (a negative
lead starts it after). Shots without an anchor start at their scene's start. Scene starts come from durations.json in
scene order; a clip plays at scene start + 0.4 + VOICE_LEAD (shots.js and voice_durations.py carry the same lead).
"""
import json, pathlib
V = pathlib.Path(__file__).resolve().parent; VO = V / 'voice'
T = json.load((VO / 'timings.json').open())['scenes']; D = json.load((VO / 'durations.json').open())
ORDER = ['s1', 's2', 's3', 's4', 's5', 's6', 's7']; LEAD = {'s1': 2.2}
start = {}; t = 0.0
for s in ORDER: start[s] = t; t += D[s]
voice_at = {s: start[s] + 0.4 + LEAD.get(s, 0) for s in ORDER}

def spoken(scene, text):
    sc = T[scene]
    for s in sc['sentences'] + sc['key_cues']:
        if s['text'].lower().startswith(text.lower()): return voice_at[scene] + s['start']
    raise SystemExit(f'no sentence or cue in {scene} starts with {text!r}')

ANCHORS = {
  's01': ('s1', None, 0), 's02': ('s1', '+2.3', 0),
  's04': ('s2', None, 0), 's05': ('s2', 'Spark reads the schematic', .3),
  's06': ('s3', None, 0), 's07': ('s3', 'Two small step tests', .3), 's09': ('s3', 'All three fail', 1.7),
  's10': ('s3', 'Spark writes a new circuit model', .2), 's12': ('s3', 'The fitted model is frozen', .2),
  's13': ('s3', 'five point one nine', .2), 's14': ('s3', 'The seal opens', .4),
  's15': ('s4', None, 0), 's16': ('s4', "The drawing's model fails", .5), 's18': ('s4', 'R one changed', .4),
  's19': ('s4', 'Spark asks for a measurement', .2), 's20': ('s4', 'Sam outlines', .3), 's21': ('s4', 'The operator reads', .3), 's22': ('s4', 'The seal reveals', .3), 's23': ('s4', 'After repair', .3),
  's24': ('s5', None, 0), 's25': ('s6', None, 0), 's26': ('s6', 'Stopped and abstained', -1.5), 's27': ('s7', None, 0),
}
plan = {}
for shot, (scene, text, lead) in ANCHORS.items():
    if text is None: g = start[scene]
    elif text.startswith('+'): g = start[scene] + float(text[1:])
    else: g = spoken(scene, text) - lead
    plan[shot] = round(g, 3)
# the close card's wide line rises when the narration reaches it (if the s7 clip has that sentence)
try: plan['s27_wide'] = round(spoken('s7', 'Shown on five circuits') - 0.2, 3)
except SystemExit: pass
(VO / 'shot_plan.json').write_text(json.dumps(plan, indent=1) + '\n')
prev = None
for k, v in plan.items():
    if k == 's27_wide': continue
    if prev is not None and v < prev: raise SystemExit(f'{k} starts before the shot before it ({v} < {prev})')
    prev = v
print(json.dumps(plan)); print('total', round(t, 2))
