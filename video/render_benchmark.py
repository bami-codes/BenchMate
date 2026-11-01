import asyncio,json,subprocess
from pathlib import Path
from playwright.async_api import async_playwright
root=Path(__file__).resolve().parents[1]
async def main():
 async with async_playwright() as p:
  b=await p.chromium.launch();page=await b.new_page(viewport={'width':1920,'height':1080})
  await page.goto((root/'video/stage_tape.html').as_uri());await page.evaluate('document.fonts.ready')
  data=json.loads((root/'video/data/benchmark.json').read_text())
  await page.evaluate('data=>setupScene("numbers",{duration:9,cues:{}},{bench:data},{})',data)
  target=root/'video/out/benchmark-evaluation.mp4'
  ff=subprocess.Popen(['ffmpeg','-y','-loglevel','error','-f','image2pipe','-framerate','30','-i','-','-c:v','libx264','-preset','veryfast','-crf','18','-pix_fmt','yuv420p',str(target)],stdin=subprocess.PIPE)
  for frame in range(270):
   await page.evaluate('t=>window.frame(t)',frame/30);ff.stdin.write(await page.screenshot(type='jpeg',quality=92))
  ff.stdin.close();code=ff.wait()
  await page.screenshot(path=str(root/'video/out/benchmark-evaluation.png'))
  await b.close()
  if code:raise RuntimeError('Video encoder failed')
  print(json.dumps({'clip':str(target),'seconds':9,'data':'actual evaluation, synthetic bench, no physical claims'}))
asyncio.run(main())
