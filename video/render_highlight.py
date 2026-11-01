"""Export the reviewed, single-record physical D01 highlight and caption sidecar.

Needs Playwright/Chromium and ffmpeg; no hardware, model API or curve fitting.
Narration must already exist. A separate scene timeline leaves the full edit intact.
"""
from pathlib import Path
import asyncio,hashlib,json,subprocess
from playwright.async_api import async_playwright
V=Path(__file__).resolve().parent

def stamp(seconds):
    ms=round(seconds*1000);h,ms=divmod(ms,3600000);m,ms=divmod(ms,60000);s,ms=divmod(ms,1000)
    return f'{h:02}:{m:02}:{s:02},{ms:03}'

async def main():
    scene=json.loads((V/'data/d01-highlight-timeline.json').read_text())
    narration=V/'out/d01-physical-highlight-narration.wav'
    if not narration.is_file():raise ValueError('Generate the retained highlight narration first')
    if hashlib.sha256((V/'d01-highlight-narration.json').read_bytes()).hexdigest()!=scene['narration_sha256']:
        raise ValueError('Narration changed after the voice/timing export')
    declared=json.loads((V/'d01-highlight-narration.json').read_text())
    raw_record=V.parent/declared['record']/'events.jsonl'
    if hashlib.sha256(raw_record.read_bytes()).hexdigest()!=declared['events_sha256']:
        raise ValueError('Retained physical record differs from the reviewed source')
    if hashlib.sha256((V/'data/d01.json').read_bytes()).hexdigest()!=declared['plot_data_sha256']:
        raise ValueError('Plot data changed after narration/source review')
    data={name:json.loads((V/'data'/f'{name}.json').read_text()) for name in ('d01','b5','repair','trust','vision')}
    # Do not splice the later schematic read or separate no-tool exchanges into this run.
    assert 'L32' not in scene['cues'] and 'L33' not in scene['cues']
    raw=V/'out/d01-physical-highlight-silent.mp4';final=V/'out/d01-physical-highlight.mp4'
    frames=round(scene['duration']*30);stills=V/'out/d01-highlight-stills';stills.mkdir(exist_ok=True)
    errors=[]
    async with async_playwright() as p:
        browser=await p.chromium.launch();page=await browser.new_page(viewport={'width':1920,'height':1080})
        page.on('pageerror',lambda e:errors.append(str(e)))
        await page.goto((V/'stage.html').as_uri());await page.evaluate('document.fonts.ready')
        await page.evaluate('([s,d])=>setupScene("diagnose",s,d,{inBg:"#f7f8f5",outBg:"#f7f8f5"})',[scene,data])
        for key in ('L10','L11','L13','L15','L16','L17'):
            await page.evaluate('(t)=>frame(t)',scene['cues'][key]['start']+2.8)
            await page.screenshot(path=str(stills/(key+'.png')))
        if errors:raise RuntimeError(errors)
        encoder=subprocess.Popen(['ffmpeg','-y','-loglevel','error','-f','image2pipe','-framerate','30','-i','-',
            '-an','-c:v','libx264','-preset','veryfast','-crf','18','-pix_fmt','yuv420p','-movflags','+faststart',str(raw)],stdin=subprocess.PIPE)
        try:
            for frame in range(frames):
                await page.evaluate('(t)=>frame(t)',frame/30)
                encoder.stdin.write(await page.screenshot(type='jpeg',quality=92))
                if frame%300==0:print(json.dumps({'frame':frame,'total':frames}),flush=True)
        finally:
            encoder.stdin.close()
        if encoder.wait()!=0:raise RuntimeError('Video encode failed')
        await browser.close()
    if errors:raise RuntimeError(errors)
    subprocess.run(['ffmpeg','-y','-loglevel','error','-i',str(raw),'-i',str(narration),'-map','0:v:0','-map','1:a:0',
       '-c:v','copy','-c:a','aac','-b:a','192k','-t',str(scene['duration']),'-movflags','+faststart',str(final)],check=True)
    srt=[]
    for i,cue in enumerate(scene['cues'].values(),1):srt.append(f"{i}\n{stamp(cue['start'])} --> {stamp(cue['end'])}\n{cue['cap']}\n")
    (V/'out/d01-physical-highlight.srt').write_text('\n'.join(srt))
    (V/'out/d01-physical-highlight-manifest.json').write_text(json.dumps({'file':final.name,'sha256':hashlib.sha256(final.read_bytes()).hexdigest(),
        'physical_record_sha256':scene['physical_record_sha256'],'narration_sha256':scene['narration_sha256'],'plot_data_sha256':declared['plot_data_sha256'],'timeline_sha256':hashlib.sha256((V/'data/d01-highlight-timeline.json').read_bytes()).hexdigest(),'duration_s':scene['duration'],'size_bytes':final.stat().st_size,
        'javascript_errors':errors,'scope':'single retained physical diagnosis; no repair or B5 result; local synthetic narration'},indent=2)+'\n')
    print(json.dumps({'finished':str(final),'duration':scene['duration']}))

if __name__=='__main__':asyncio.run(main())
