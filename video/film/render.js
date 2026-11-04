// Frame-step renderer for the film stage. The stage exposes window.filmReady (a promise) and window.frame(t).
//   node render.js <name> <t0> <t1> [--fps 60] [--jobs 3] [--stills t1,t2,...]
// Renders [t0, t1) in parallel chunks (one Chromium context each), JPEG q95 frames piped to ffmpeg, then concatenates.
const { chromium } = require('playwright'); const fs = require('fs'); const path = require('path'); const { spawn } = require('child_process');
const V = __dirname; const BASE = process.env.BASE || 'http://127.0.0.1:8796/video/film/shots.html';
const arg = (k, d) => { const i = process.argv.indexOf(k); return i > 0 ? process.argv[i + 1] : d; };
const [name, t0s, t1s] = process.argv.slice(2); const t0 = parseFloat(t0s), t1 = parseFloat(t1s);
const FPS = parseInt(arg('--fps', '60')), JOBS = parseInt(arg('--jobs', '3')); const stills = arg('--stills', null);
fs.mkdirSync(path.join(V, 'out'), { recursive: true }); fs.mkdirSync(path.join(V, 'frames'), { recursive: true });

async function openStage(browser) {
  const ctx = await browser.newContext({ viewport: { width: 1920, height: 1080 }, deviceScaleFactor: parseFloat(process.env.SCALE || '1'), reducedMotion: 'reduce' });  // SCALE=1.3333333 renders 2560×1440 from the same layout
  const pg = await ctx.newPage(); const errs = [];
  pg.on('pageerror', e => errs.push(String(e))); pg.on('console', m => { if (m.type() === 'error') errs.push(m.text()); });
  await pg.goto(BASE, { waitUntil: 'networkidle' }); await pg.evaluate(() => window.filmReady); await pg.evaluate(() => document.fonts.ready); await pg.waitForTimeout(300);
  return { ctx, pg, errs };
}

async function renderChunk(browser, idx, a, b) {
  const { ctx, pg, errs } = await openStage(browser);
  const n = Math.round((b - a) * FPS); const out = path.join(V, 'out', `_${name}_${idx}.mp4`);
  const ff = spawn('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', String(FPS), '-i', '-', '-c:v', 'libx264', '-preset', 'medium', '-crf', '15', '-pix_fmt', 'yuv420p', '-r', String(FPS), out]);
  const done = new Promise(res => ff.on('close', res)); const T = Date.now();
  for (let i = 0; i < n; i++) {
    const t = a + i / FPS; await pg.evaluate(t => { frame(t); return new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r))); }, t);
    const buf = await pg.screenshot({ type: 'jpeg', quality: 95 });
    if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r));
  }
  ff.stdin.end(); const rc = await done; await ctx.close();
  console.log(`chunk ${idx} [${a.toFixed(1)}, ${b.toFixed(1)}) ${n} frames in ${((Date.now() - T) / 1000).toFixed(0)} s (${(n / ((Date.now() - T) / 1000)).toFixed(1)} fps) rc ${rc}`);
  if (errs.length) console.log('  page errors:', errs.slice(0, 3));
  return out;
}

(async () => {
  const browser = await chromium.launch();
  if (process.argv.includes('--meta')) { const { pg } = await openStage(browser); fs.writeFileSync(path.join(V, 'out', 'captions.json'), JSON.stringify(await pg.evaluate(() => filmCaptions()), null, 1)); fs.writeFileSync(path.join(V, 'out', 'scenes.json'), JSON.stringify(await pg.evaluate(() => filmScenes()), null, 1)); if (await pg.evaluate(() => !!window.filmSfx)) fs.writeFileSync(path.join(V, 'out', 'sfx.json'), JSON.stringify(await pg.evaluate(() => filmSfx()), null, 1)); console.log('total', await pg.evaluate(() => filmTotal())); await browser.close(); return; }
  if (stills) {
    const { pg } = await openStage(browser);
    for (const t of stills.split(',').map(Number)) { await pg.evaluate(t => { frame(t); return new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r))); }, t); await pg.waitForTimeout(120); await pg.screenshot({ path: path.join(V, 'frames', `${name}_${t.toFixed(2).padStart(6, '0')}.png`) }); }
    console.log('stills', stills); await browser.close(); return;
  }
  const span = t1 - t0, per = span / JOBS; const chunks = Array.from({ length: JOBS }, (_, i) => [i, t0 + i * per, i === JOBS - 1 ? t1 : t0 + (i + 1) * per]);
  const outs = await Promise.all(chunks.map(([i, a, b]) => renderChunk(browser, i, a, b)));
  const lst = path.join(V, 'out', `_${name}.txt`); fs.writeFileSync(lst, outs.map(o => `file '${path.basename(o)}'`).join('\n') + '\n');
  await new Promise((res, rej) => { const p = spawn('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i', lst, '-c', 'copy', path.join(V, 'out', `${name}.mp4`)]); p.on('close', c => c ? rej(new Error('concat ' + c)) : res()); });
  console.log('wrote', path.join(V, 'out', `${name}.mp4`)); await browser.close();
})();
