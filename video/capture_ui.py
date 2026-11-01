"""Film the real BenchMate viewer (exported replay HTML) with a scripted, deterministic camera."""
import asyncio, json, subprocess, sys, os
from playwright.async_api import async_playwright
V=os.path.dirname(os.path.abspath(__file__))
async def main(html, out, duration, script):
    async with async_playwright() as p:
        b=await p.chromium.launch(); pg=await b.new_page(viewport={'width':1600,'height':900},device_scale_factor=1.2)
        await pg.goto('file://'+html); await pg.wait_for_timeout(500)
        n=await pg.evaluate('state.events.length')
        ms=await pg.evaluate('state.milestones.length?state.milestones:[]')
        stages=await pg.evaluate("[...document.querySelectorAll('.story-stage')].length")
        tmp=out+'.tmp.mp4'
        ff=subprocess.Popen(['ffmpeg','-y','-loglevel','error','-f','image2pipe','-framerate','30','-i','-','-vf','scale=1920:1080','-c:v','libx264','-preset','veryfast','-crf','18','-pix_fmt','yuv420p',tmp],stdin=subprocess.PIPE)
        actions=sorted(script,key=lambda a:a[0]); ai=0
        for i in range(int(duration*30)):
            t=i/30
            while ai<len(actions) and actions[ai][0]<=t:
                await pg.evaluate(actions[ai][1]); ai+=1
            ff.stdin.write(await pg.screenshot(type='jpeg',quality=92))
        ff.stdin.close(); rc=ff.wait()
        if rc==0: os.replace(tmp,out)
        print(out,rc,'events',n)
        await b.close()
if __name__=='__main__':
    cfg=json.load(open(sys.argv[1])); asyncio.run(main(cfg['html'],cfg['out'],cfg['duration'],cfg['script']))
