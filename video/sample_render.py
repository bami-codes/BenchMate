"""20-second motion sample in the label-tape direction: forum hook + 'only one survives'."""
import asyncio, json, subprocess, os, numpy as np, soundfile as sf
from scipy.signal import butter, sosfilt
from playwright.async_api import async_playwright
V=os.path.dirname(os.path.abspath(__file__))
tl=json.load(open(f'{V}/timeline.json')); dur=json.load(open(f'{V}/audio/am_michael/durations.json'))
caps={L['id']:L['cap'] for L in json.load(open(f'{V}/narration.json'))['lines']}
hook=next(s for s in tl['scenes'] if s['name']=='hook')
s14=0.4; s15=s14+dur['L14']+2.0
surv={'name':'survive','duration':round(s15+dur['L15']+3.4,3),'cues':{'L14':{'start':s14,'end':s14+dur['L14'],'cap':caps['L14']},'L15':{'start':s15,'end':s15+dur['L15'],'cap':caps['L15']}}}
data={'d01':json.load(open(f'{V}/data/d01.json'))}
scenes=[('hook',hook,{'inBg':'#000000','outBg':'#eef0ec'}),('survive',surv,{'inBg':'#eef0ec','outBg':'#000000'})]
async def main():
    sfx=[];offset=0;parts=[]
    async with async_playwright() as p:
        b=await p.chromium.launch(); pg=await b.new_page(viewport={'width':1920,'height':1080})
        await pg.goto(f'file://{V}/stage_tape.html'); await pg.evaluate('document.fonts.ready')
        for name,sc,opts in scenes:
            await pg.evaluate('([n,s,d,o])=>setupScene(n,s,d,o)',[name,sc,data,opts])
            n=int(round(sc['duration']*30)); out=f'{V}/out/sample_{name}.mp4'
            ff=subprocess.Popen(['ffmpeg','-y','-loglevel','error','-f','image2pipe','-framerate','30','-i','-','-c:v','libx264','-preset','veryfast','-crf','17','-pix_fmt','yuv420p',out],stdin=subprocess.PIPE)
            for i in range(n):
                await pg.evaluate(f'frame({i/30})'); ff.stdin.write(await pg.screenshot(type='jpeg',quality=92))
            ff.stdin.close(); ff.wait()
            sfx+= [offset+x for x in await pg.evaluate('sfx()')]
            parts.append((sc,offset)); offset+=n/30
        await b.close()
    return sfx,parts,offset
sfx,parts,total=asyncio.run(main())
SR=48000; tr=np.zeros(int((total+0.5)*SR))
import scipy.signal as ss
for sc,off in parts:
    for lid,c in sc['cues'].items():
        a,sr=sf.read(f'{V}/audio/am_michael/{lid}.wav',dtype='float32'); a=ss.resample_poly(a,2,1)
        i=int((off+c['start'])*SR); tr[i:i+len(a)]+=a*1.0
tr=tr/np.abs(tr).max()*0.85
# tape "stick" sound: band-passed noise click + low thump
rng=np.random.default_rng(3); fx=np.zeros_like(tr)
bp=butter(2,[1200,7000],btype='band',fs=SR,output='sos')
for s in sfx:
    n=int(0.09*SR); t=np.arange(n)/SR
    click=sosfilt(bp,rng.standard_normal(n))*np.exp(-t/0.018)*0.5
    thump=np.sin(2*np.pi*95*t)*np.exp(-t/0.03)*0.35
    i=int(s*SR); fx[i:i+n]+=(click+thump)[:max(0,len(fx)-i)]
# music bed: reuse generated bed, quiet, ducked under voice
m,msr=sf.read(f'{V}/out/music.wav',dtype='float32'); m=m[:len(tr)].mean(1) if m.ndim>1 else m[:len(tr)]
m=np.pad(m,(0,max(0,len(tr)-len(m))))
env=np.convolve(np.abs(tr),np.ones(int(0.25*SR))/(0.25*SR),mode='same'); duck=1-0.5*np.clip(env/0.02,0,1)
mix=tr+fx*0.9+m*duck*1.4
mix=mix/np.abs(mix).max()*0.95
sf.write(f'{V}/out/sample_audio.wav',np.stack([mix,mix],1),SR)
open(f'{V}/out/sample_list.txt','w').write("file 'sample_hook.mp4'\nfile 'sample_survive.mp4'\n")
subprocess.run(f"cd {V}/out && ffmpeg -y -loglevel error -f concat -safe 0 -i sample_list.txt -c copy sample_v.mp4 && ffmpeg -y -loglevel error -i sample_v.mp4 -i sample_audio.wav -map 0:v -map 1:a -c:v copy -af loudnorm=I=-14:TP=-1.5 -c:a aac -b:a 192k -shortest BenchMate_motion_sample.mp4",shell=True,check=True)
print('sample',round(total,1),'s; sfx',len(sfx))
