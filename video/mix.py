"""Build the narration track from per-line wavs placed at timeline cue times."""
import os
V=os.path.dirname(os.path.abspath(__file__)); ROOT=os.environ.get('BENCHMATE_ROOT',os.path.dirname(V))
import json, sys, numpy as np, soundfile as sf
tl=json.load(open(f'{V}/timeline.json')); voice=tl['voice']; SR=24000
total=tl['total']; track=np.zeros(int((total+0.5)*SR),dtype=np.float32)
for sc in tl['scenes']:
    for lid,c in sc['cues'].items():
        a,sr=sf.read(f'{V}/audio/{voice}/{lid}.wav',dtype='float32'); assert sr==SR
        i=int((sc['start']+c['start'])*SR); track[i:i+len(a)]+=a
peak=np.abs(track).max(); track=track/peak*0.89
sf.write(f'{V}/out/narration.wav',track,SR); print('narration',round(len(track)/SR,2),'s, peak normalised from',round(float(peak),3))
