"""Local narration/timing for a bounded backup edit; no hosted speech API."""
from pathlib import Path
import json,hashlib,torch,numpy as np,soundfile as sf
from kokoro import KPipeline
V=Path(__file__).resolve().parent;R=V.parent
p=V/'backup-narration.json';script=json.loads(p.read_text());torch.set_num_threads(2)
for name,digest in script['source_sha256'].items():
 if hashlib.sha256((R/name).read_bytes()).hexdigest()!=digest:raise ValueError('Backup source changed: '+name)
pipe=KPipeline(lang_code='a',device='cpu',repo_id='hexgrad/Kokoro-82M');out=V/'audio/backup';out.mkdir(parents=True,exist_ok=True)
scenes=[];total=0
for name in ['hook','backup_intro','diagnose','backup_repair','discover','numbers','backup_close']:
 if name=='diagnose':
  scene=json.loads((V/'data/d01-highlight-timeline.json').read_text());scene={**scene,'reuse_video':'out/d01-physical-highlight.mp4'}
 else:
  t=.4;clips=[];cues={}
  for line in (x for x in script['lines'] if x['scene']==name):
   pieces=[a.numpy() if hasattr(a,'numpy') else a for _,_,a in pipe(line['say'],voice=script['voice'],speed=script['speed'])];a=np.concatenate(pieces);idx=np.where(np.abs(a)>.01)[0]
   if len(idx):a=a[max(0,idx[0]-900):idx[-1]+1800]
   dur=len(a)/24000;cues[line['id']]={'start':round(t,3),'end':round(t+dur,3),'cap':line['cap']};clips.append((t,a));sf.write(out/(line['id']+'.wav'),a,24000);t+=dur+line['gap']
  scene={'name':name,'duration':round(t,3),'cues':cues};track=np.zeros(int((t+.15)*24000),dtype=np.float32)
  for start,a in clips:i=int(start*24000);track[i:i+len(a)]+=a
  peak=np.max(np.abs(track));track*=.84/peak;sf.write(out/(name+'.wav'),track,24000)
 scene['start']=round(total,3);scenes.append(scene);total+=scene['duration'];print(json.dumps({'scene':name,'duration':scene['duration']}),flush=True)
if total>180:raise ValueError('Backup exceeds three minutes; review wording/timing instead of silently accelerating')
(V/'data/backup-timeline.json').write_text(json.dumps({'total':round(total,3),'narration_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'scenes':scenes},ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'total':total,'physical_diagnosis_reused':True}))
