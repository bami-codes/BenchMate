"""Render an honest complete backup edit from retained records; no live bench/model."""
import asyncio,hashlib,json,subprocess
from pathlib import Path
from playwright.async_api import async_playwright
V=Path(__file__).resolve().parent;R=V.parent

def stamp(seconds):
    ms=round(seconds*1000);h,ms=divmod(ms,3600000);m,ms=divmod(ms,60000);s,ms=divmod(ms,1000)
    return f'{h:02}:{m:02}:{s:02},{ms:03}'

async def main():
    plan=json.loads((V/'backup-narration.json').read_text());tl=json.loads((V/'data/backup-timeline.json').read_text())
    if tl['narration_sha256']!=hashlib.sha256((V/'backup-narration.json').read_bytes()).hexdigest():raise ValueError('Narration changed')
    for name,digest in plan['source_sha256'].items():
        if hashlib.sha256((R/name).read_bytes()).hexdigest()!=digest:raise ValueError('Backup source changed: '+name)
    proof=json.loads((V/'highlight-export.json').read_text())
    physical=V/'out/d01-physical-highlight.mp4'
    if hashlib.sha256(physical.read_bytes()).hexdigest()!=proof['sha256']:raise ValueError('Physical clip differs')
    data={name:json.loads((V/'data'/f'{name}.json').read_text()) for name in ('d01','repair','trust','vision','benchmark')}
    data.update(b5=json.loads((V/'data/backup-b5.json').read_text()),backupRepair=json.loads((V/'data/backup-repair.json').read_text()),backup={'photo':(R/plan['photo']).as_uri()});data['bench']=data['benchmark']
    out=V/'out/backup';out.mkdir(exist_ok=True);stills=out/'stills';stills.mkdir(exist_ok=True);errors=[];parts=[]
    async with async_playwright() as p:
        browser=await p.chromium.launch();page=await browser.new_page(viewport={'width':1920,'height':1080})
        page.on('pageerror',lambda e:errors.append(str(e)))
        for scene in tl['scenes']:
            name=scene['name']
            if scene.get('reuse_video'):
                parts.append(V/scene['reuse_video']);continue
            await page.goto((V/('stage_tape.html' if name=='numbers' else 'stage.html')).as_uri())
            if name!='numbers':await page.add_script_tag(path=str(V/'backup-scenes.js'))
            await page.evaluate('document.fonts.ready')
            await page.evaluate('([s,d])=>setupScene(s.name,s,d,{})',[scene,data])
            if name=='discover':
                await page.evaluate('d=>{const e=document.createElement("div");e.style.cssText="position:absolute;left:72px;top:870px;width:1776px;font-size:20px;color:#55635e";e.textContent="Conditional curves use measured IN. Command-forecast errors: "+d.ver_scores.map(x=>x.cmd.toFixed(2)).join(" / ")+" mV. Physical B5 remains pending.";document.getElementById("stage").append(e);}',data['b5'])
            for frac in (.25,.6,.88):
                await page.evaluate('(t)=>frame(t)',scene['duration']*frac)
                await page.screenshot(path=str(stills/f'{name}-{int(frac*100)}.png'))
            if errors:raise RuntimeError(errors)
            silent=out/(name+'-silent.mp4');part=out/(name+'.mp4');frames=round(scene['duration']*30)
            enc=subprocess.Popen(['ffmpeg','-y','-loglevel','error','-f','image2pipe','-framerate','30','-i','-',
                '-an','-c:v','libx264','-preset','veryfast','-crf','18','-pix_fmt','yuv420p','-movflags','+faststart',str(silent)],stdin=subprocess.PIPE)
            try:
                for i in range(frames):
                    await page.evaluate('(t)=>frame(t)',i/30);enc.stdin.write(await page.screenshot(type='jpeg',quality=92))
            finally:enc.stdin.close()
            if enc.wait():raise RuntimeError('Scene encoding failed')
            subprocess.run(['ffmpeg','-y','-loglevel','error','-i',str(silent),'-i',str(V/'audio/backup'/(name+'.wav')),
                '-map','0:v:0','-map','1:a:0','-c:v','copy','-c:a','aac','-b:a','192k','-ar','24000','-t',str(scene['duration']),'-movflags','+faststart',str(part)],check=True)
            parts.append(part);print(json.dumps({'scene':name,'duration':scene['duration'],'finished':True}),flush=True)
        await browser.close()
    if errors:raise RuntimeError(errors)
    concat=out/'parts.txt';concat.write_text('\n'.join("file '"+str(p)+"'" for p in parts)+'\n')
    final=V/'out/benchmate-backup-cut.mp4'
    subprocess.run(['ffmpeg','-y','-loglevel','error','-f','concat','-safe','0','-i',str(concat),'-c:v','copy',
        '-af','loudnorm=I=-16:TP=-1.5:LRA=11','-ar','48000','-c:a','aac','-b:a','192k','-movflags','+faststart',str(final)],check=True)
    srt=[];n=0
    for scene in tl['scenes']:
        for c in scene['cues'].values():
            n+=1;srt.append(f"{n}\n{stamp(scene['start']+c['start'])} --> {stamp(scene['start']+c['end'])}\n{c['cap']}\n")
    final.with_suffix('.srt').write_text('\n'.join(srt))
    info=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration,size:stream=codec_name,width,height','-of','json',str(final)]))
    if float(info['format']['duration'])>180:raise ValueError('Encoded clip exceeds limit')
    manifest={'file':final.name,'sha256':hashlib.sha256(final.read_bytes()).hexdigest(),'duration_s':float(info['format']['duration']),
        'size_bytes':final.stat().st_size,'streams':info['streams'],'javascript_errors':errors,
        'scope':'backup edit: one physical D01 diagnosis, separately labelled actual-Spark mock repair and mock B5; no physical repair/B5/participant result',
        'sources':plan['source_sha256'],'narration_sha256':tl['narration_sha256'],'voice_generated_locally':True,'human_audio_review':False,
        'scenes':[{'name':s['name'],'start':s['start'],'duration':s['duration']} for s in tl['scenes']]}
    (V/'backup-export.json').write_text(json.dumps(manifest,indent=2)+'\n');print(json.dumps(manifest))

if __name__=='__main__':asyncio.run(main())
