"""Burn captions (and an optional label) onto a footage/UI clip using transparent PNGs drawn by stage.html."""
import asyncio, json, subprocess, sys, os
from playwright.async_api import async_playwright
V=os.path.dirname(os.path.abspath(__file__))
async def pngs(scene, label):
    out=[]
    async with async_playwright() as p:
        b=await p.chromium.launch(); pg=await b.new_page(viewport={'width':1920,'height':1080})
        await pg.goto(f'file://{V}/stage.html'); await pg.evaluate('document.fonts.ready')
        sc={'cues':{},'label':label}
        await pg.evaluate('([s])=>{setupScene("overlay",s,{})}',[sc]); await pg.evaluate('frame(0)')
        lp=f'{V}/frames/ov_{scene}_label.png'; await pg.screenshot(path=lp,omit_background=True); out.append((lp,0,1e9))
        for lid,c in scene_cues(scene).items():
            await pg.evaluate('([s])=>{setupScene("overlay",s,{})}',[{'cues':{lid:c}}]); await pg.evaluate(f'frame({c["start"]})')
            pth=f'{V}/frames/ov_{scene}_{lid}.png'; await pg.screenshot(path=pth,omit_background=True); out.append((pth,c['start']-0.05,c['end']+0.35))
        await b.close()
    return out
def scene_cues(name):
    tl=json.load(open(f'{V}/timeline.json')); return next(s for s in tl['scenes'] if s['name']==name)['cues']
def main(scene, base, label, offset=0.0):
    tl=json.load(open(f'{V}/timeline.json')); dur=next(s for s in tl['scenes'] if s['name']==scene)['duration']
    layers=asyncio.run(pngs(scene,label))
    cmd=['ffmpeg','-y','-loglevel','error','-ss',str(offset),'-t',str(dur),'-i',base]
    for pth,_,_ in layers: cmd+=['-loop','1','-t',str(dur),'-i',pth]
    fc=[f'color=c=0x183d35:s=1920x1080:r=30:d={dur}[bg]','[0:v]scale=1650:-2,fps=30,tpad=stop_mode=clone:stop_duration=30[w]',f'[bg][w]overlay=135:100:shortest=0,format=yuv420p,fade=t=in:st=0:d=0.45:color=0x183d35,fade=t=out:st={dur-0.45}:d=0.45:color=0xf7f8f5[b0]']
    for i,(_,a,z) in enumerate(layers,1):
        fc.append(f"[b{i-1}][{i}:v]overlay=0:0:enable='between(t,{a:.3f},{z:.3f})'[b{i}]")
    tmp=f'{V}/out/{scene}.tmp.mp4'
    cmd+=['-filter_complex',';'.join(fc),'-map',f'[b{len(layers)}]','-t',str(dur),'-c:v','libx264','-preset','veryfast','-crf','18','-pix_fmt','yuv420p','-r','30','-an',tmp]
    rc=subprocess.run(cmd).returncode
    if rc==0: os.replace(tmp,f'{V}/out/{scene}.mp4')
    print(scene,'rc',rc,'dur',dur)
if __name__=='__main__':
    main(sys.argv[1],sys.argv[2],sys.argv[3] if len(sys.argv)>3 else None,float(sys.argv[4]) if len(sys.argv)>4 else 0.0)
