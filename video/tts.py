import os
V=os.path.dirname(os.path.abspath(__file__)); ROOT=os.environ.get('BENCHMATE_ROOT',os.path.dirname(V))
import json, sys, soundfile as sf, numpy as np
from kokoro import KPipeline
voice=sys.argv[1]; speed=float(sys.argv[2]) if len(sys.argv)>2 else 1.0
pipe=KPipeline(lang_code='a' if voice[0]=='a' else 'b')
lines=json.load(open(V+'/narration.json'))['lines']
import os; os.makedirs(f'{V}/audio/{voice}',exist_ok=True)
only=set(sys.argv[3].split(',')) if len(sys.argv)>3 else None
dp=f'{V}/audio/{voice}/durations.json'
import os.path
dur=json.load(open(dp)) if only and os.path.exists(dp) else {}
for L in lines:
    if only and L['id'] not in only: continue
    audio=np.concatenate([a for _,_,a in pipe(L['say'],voice=voice,speed=speed)])
    # trim leading/trailing near-silence
    idx=np.where(np.abs(audio)>0.01)[0]; audio=audio[max(0,idx[0]-1200):idx[-1]+2400]
    sf.write(f'{V}/audio/{voice}/{L["id"]}.wav',audio,24000); dur[L['id']]=len(audio)/24000
json.dump(dur,open(f'{V}/audio/{voice}/durations.json','w'),indent=1)
print(voice, round(sum(dur.values()),1),'s total')
