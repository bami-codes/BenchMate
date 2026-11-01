import os
V=os.path.dirname(os.path.abspath(__file__)); ROOT=os.environ.get('BENCHMATE_ROOT',os.path.dirname(V))
import asyncio, json, subprocess, sys, os
from playwright.async_api import async_playwright
def load_data():
    j=lambda f:json.load(open(f'{V}/data/{f}'))
    return {'d01':j('d01.json'),'b5':j('b5.json'),'repair':j('repair.json'),'trust':j('trust.json'),'vision':j('vision.json')}
async def main(mode, names, at=None):
    tl=json.load(open(f'{V}/timeline.json')); data=load_data()
    scenes={s['name']:s for s in tl['scenes']}
    async with async_playwright() as p:
        b=await p.chromium.launch(); pg=await b.new_page(viewport={'width':1920,'height':1080})
        errs=[]; pg.on('pageerror',lambda e:errs.append(str(e)))
        await pg.goto(f'file://{V}/stage.html'); await pg.evaluate('document.fonts.ready')
        for name in names:
            sc=scenes[name]
            order=[s['name'] for s in tl['scenes']]; i=order.index(name)
            BG={'hook':'#f7f8f5','intro':'#183d35','diagnose':'#f7f8f5','app':'#183d35','repair':'#f7f8f5','discover':'#f7f8f5','trust':'#f7f8f5','close':'#183d35'}
            opts={'inBg':BG[name] if i>0 else '#000000','outBg':BG[order[i+1]] if i+1<len(order) else '#000000'}
            await pg.evaluate('([n,s,d,o])=>setupScene(n,s,d,o)',[name,sc,data,opts]); await pg.wait_for_timeout(300)
            if mode=='stills':
                times=at or [sc['duration']*f for f in (0.25,0.5,0.75,0.98)]
                for t in times:
                    await pg.evaluate(f'frame({t})'); await pg.screenshot(path=f'{V}/frames/{name}_{t:05.1f}.jpg',type='jpeg',quality=85)
            else:
                n=int(round(sc['duration']*30)); tmp=f'{V}/out/{name}.tmp.mp4'
                ff=subprocess.Popen(['ffmpeg','-y','-loglevel','error','-f','image2pipe','-framerate','30','-i','-','-c:v','libx264','-preset','veryfast','-crf','18','-pix_fmt','yuv420p','-r','30',tmp],stdin=subprocess.PIPE)
                for i in range(n):
                    await pg.evaluate(f'frame({i/30})'); ff.stdin.write(await pg.screenshot(type='jpeg',quality=92))
                ff.stdin.close(); rc=ff.wait()
                if rc==0: os.replace(tmp,f'{V}/out/{name}.mp4')
                print(name,n,'frames rc',rc,flush=True)
        if errs: print('ERRORS',errs)
        await b.close()
if __name__=='__main__':
    mode=sys.argv[1]; names=sys.argv[2].split(','); at=[float(x) for x in sys.argv[3].split(',')] if len(sys.argv)>3 else None
    asyncio.run(main(mode,names,at))
