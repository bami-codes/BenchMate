"""Scene timing from narration durations. Animations key off cue times; captions follow speech."""
import os
V=os.path.dirname(os.path.abspath(__file__)); ROOT=os.environ.get('BENCHMATE_ROOT',os.path.dirname(V))
import json, sys
voice=sys.argv[1] if len(sys.argv)>1 else 'am_michael'
lines=json.load(open(V+'/narration.json'))['lines']
dur=json.load(open(f'{V}/audio/{voice}/durations.json'))
# scene: lead-in, default gap, per-line pause after, tail
CFG={
 'hook':    dict(lead=0.5, gap=0.45, pause={'F1':0.6,'F2':0.5,'F3':0.6}, tail=2.2),
 'intro':   dict(lead=1.6, gap=0.6, pause={'L6':0.7,'L7':1.0}, tail=1.0),
 'diagnose':dict(lead=0.5, gap=0.45, pause={'L9':0.4,'L32':0.8,'L10':0.8,'L33':1.6,'L11':0.5,'L12':0.3,'L13':2.8,'L14':0.8,'L15':2.4,'L16':2.4,'L17':0.9}, tail=1.5),
 'app':     dict(lead=2.2, gap=0.6, pause={}, tail=1.0, fixed=9.0),
 'repair':  dict(lead=0.5, gap=0.6, pause={'L19':1.0,'L20':2.2,'L21':2.4}, tail=2.6),
 'discover':dict(lead=0.5, gap=0.5, pause={'L23':0.4,'L34':0.6,'L35':1.6,'L36':0.8,'L24':2.4,'L25':1.8}, tail=2.0),
 'trust':   dict(lead=0.4, gap=0.6, pause={'L27':2.2}, tail=1.4),
 'close':   dict(lead=0.6, gap=0.6, pause={'L29':1.2}, tail=2.2),
}
order=['hook','intro','diagnose','app','repair','discover','trust','close']
out={'voice':voice,'scenes':[]};T=0
for name in order:
    c=CFG[name];t=c['lead'];cues={}
    sl=[L for L in lines if L['scene']==name]
    for i,L in enumerate(sl):
        d=dur[L['id']];cues[L['id']]={'start':round(t,3),'end':round(t+d,3),'cap':L['cap']}
        t+=d+c['pause'].get(L['id'],c['gap'])
    t+=c['tail']-c['pause'].get(sl[-1]['id'],c['gap'])
    if 'fixed' in c: t=c['fixed']
    out['scenes'].append({'name':name,'start':round(T,3),'duration':round(t,3),'cues':cues});T+=t
out['total']=round(T,3)
json.dump(out,open(V+'/timeline.json','w'),indent=1)
for s in out['scenes']:print(f"{s['name']:9s} start {s['start']:6.1f}  dur {s['duration']:5.1f}")
print('TOTAL',out['total'])
