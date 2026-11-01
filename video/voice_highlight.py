from pathlib import Path
import torch,numpy as np,soundfile as sf,json,hashlib
from kokoro import KPipeline
r=Path(__file__).resolve().parents[1];textfile=r/'video/d01-highlight-narration.json';d=json.loads(textfile.read_text())
out=r/'video/audio/d01-highlight';out.mkdir(parents=True,exist_ok=True);torch.set_num_threads(2)
pipe=KPipeline(lang_code='a',device='cpu',repo_id='hexgrad/Kokoro-82M')
t=.6;cues={};segments=[];pauses={'L9':.7,'L10':1.,'L11':1.2,'L12':.6,'L13':3.2,'L14':1.1,'L15':3.5,'L16':3.5,'L17':1.0,'L18':2.8}
for row in d['lines']:
 pieces=[a.numpy() if hasattr(a,'numpy') else a for _,_,a in pipe(row['say'],voice=d['voice'],speed=d['speed'])];audio=np.concatenate(pieces)
 idx=np.where(np.abs(audio)>.01)[0]
 if len(idx):audio=audio[max(0,idx[0]-900):idx[-1]+1800]
 sec=len(audio)/24000;cues[row['id']]={'start':round(t,3),'end':round(t+sec,3),'cap':row['cap']};segments.append((t,audio))
 sf.write(out/(row['id']+'.wav'),audio,24000);t+=sec+pauses[row['id']]
 print(json.dumps({'line':row['id'],'seconds':sec}),flush=True)
track=np.zeros(int((t+.2)*24000),dtype=np.float32)
for start,a in segments:
 i=int(start*24000);track[i:i+len(a)]+=a
peak=np.max(np.abs(track));track*=.84/peak
sf.write(r/'video/out/d01-physical-highlight-narration.wav',track,24000)
manifest={'name':'diagnose','duration':round(t,3),'cues':cues,'narration_sha256':hashlib.sha256(textfile.read_bytes()).hexdigest(),
 'voice':d['voice'],'model':'hexgrad/Kokoro-82M','voice_generated_locally':True,'physical_record_sha256':d['events_sha256'],'speech_seconds':round(sum(len(a)/24000 for _,a in segments),3)}
(r/'video/data/d01-highlight-timeline.json').write_text(json.dumps(manifest,indent=2)+'\n');print(json.dumps({'duration':t,'speech':manifest['speech_seconds']}))
