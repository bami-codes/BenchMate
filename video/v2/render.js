// Frame-step renderer for the v2 motion scenes (Node + the pre-installed Playwright/Chromium).
// Each scene HTML exposes window.frame(t) (seconds) and sets the whole DOM for that instant, so frames are deterministic.
//   node render.js s1 title.html 11 --at 2.5 5 9.4     stills → frames/s1_*.png
//   node render.js s1 title.html 11 --stills            stills at 25/50/75/98 %
//   node render.js s1 title.html 11                     out/s1.mp4 (1920×1080, 30 fps, H.264, no audio)
const { chromium } = require('playwright'); const fs = require('fs'); const path = require('path'); const { spawn } = require('child_process');
const V = __dirname, FPS = 30;
(async () => {
  const a = process.argv.slice(2); const [name, html, durS] = a; const duration = parseFloat(durS);
  const stills = a.includes('--stills'); const at = a.includes('--at') ? a.slice(a.indexOf('--at') + 1).map(Number) : null;
  fs.mkdirSync(path.join(V, 'frames'), { recursive: true }); fs.mkdirSync(path.join(V, 'out'), { recursive: true });
  const b = await chromium.launch(); const pg = await b.newPage({ viewport: { width: 1920, height: 1080 }, deviceScaleFactor: 1 });
  const errs = []; pg.on('pageerror', e => errs.push(String(e))); pg.on('console', m => { if (m.type() === 'error') errs.push(m.text()); });
  await pg.goto('file://' + path.join(V, html)); await pg.evaluate(() => document.fonts.ready); await pg.waitForTimeout(500);
  if (stills || at) {
    const times = at || [0.25, 0.5, 0.75, 0.98].map(f => duration * f);
    for (const t of times) { await pg.evaluate(t => frame(t), t); await pg.waitForTimeout(40); await pg.screenshot({ path: path.join(V, 'frames', `${name}_${t.toFixed(1).padStart(5, '0')}.png`) }); }
    console.log(name, 'stills', times.map(t => t.toFixed(1)).join(' '));
  } else {
    const n = Math.round(duration * FPS); const out = path.join(V, 'out', `${name}.mp4`);
    const ff = spawn('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', String(FPS), '-i', '-', '-c:v', 'libx264', '-preset', 'slow', '-crf', '16', '-pix_fmt', 'yuv420p', '-r', String(FPS), out]);
    const done = new Promise(res => ff.on('close', res));
    for (let i = 0; i < n; i++) { await pg.evaluate(t => frame(t), i / FPS); const png = await pg.screenshot({ type: 'png' }); if (!ff.stdin.write(png)) await new Promise(r => ff.stdin.once('drain', r)); }
    ff.stdin.end(); const rc = await done; console.log(name, n, 'frames', 'rc', rc, out);
  }
  await b.close(); if (errs.length) { console.log('PAGE ERRORS:', errs.slice(0, 5)); process.exit(2); }
})();
