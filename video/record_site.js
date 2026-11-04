// Film the live site itself (served locally) scene by scene with Playwright's real-time recorder, 1920×1080.
// Nothing is staged: the replays are the recorded runs played back from their logs; the only direction is the
// playback speed and when the camera scrolls. Writes raw/<scene>.webm and raw/cues.json (first-appearance times of
// notebook markers, used to place captions). Run with the site served on 127.0.0.1:8795.
const { chromium } = require('playwright'); const fs = require('fs'); const path = require('path');
const base = process.env.BASE || 'http://127.0.0.1:8795'; const RAW = path.join(__dirname, 'raw');
const MARKERS = ['chose the next experiment', 'forecasts frozen before measuring step 1', 'measuring step 1', 'ngspice, step 1', 'measuring step 2', 'ngspice, step 2', 'measuring step 3', 'ngspice, step 3',
  'proposes a part the drawing does not show', 'ngspice, proposed circuit', 'asked for the check', 'forecast pushed before measuring', 'held-back input 1 of 2', 'held-back input 2 of 2', 'check complete', 'report after the measurements',
  'electrically equivalent explanations', 'asked for one reading', 'reading forecast, frozen before anyone reads', 'pointed at the body', 'asked which body', 'two capacitor bodies', 'reading forecast for both bodies',
  'the operator reads one value', 'the operator reads both bodies', 'scored by the frozen bands', 'both readings scored', 'Record · stopped', 'Verdict · compared by code'];
const sleep = ms => new Promise(r => setTimeout(r, ms));
// start points inside two replays: a second before the step-3 fit of case 05 (every needle in the red), and a second before Spark's
// report in case 02 (the reading stage follows). Read from the run files, never typed.
const tPlay = (rid, kind, step) => JSON.parse(fs.readFileSync(path.join(__dirname, '..', 'site', 'data', 'runs', rid + '.json'))).timeline.find(e => e.kind === kind && (step == null || e.step === step)).t_play;
const START05 = Math.max(0, tPlay('20261104T021333-c80ef3617e', 'fit_result', 3) - 1).toFixed(1);
const START02 = Math.max(0, tPlay('20261103T165506-b6ad3e8cf7', 'spark_report') - 1).toFixed(1);
(async () => {
  fs.mkdirSync(RAW, { recursive: true });
  const b = await chromium.launch();
  const ONLY = (process.env.SCENES || '').split(',').filter(Boolean); // re-record a subset; the others keep their files and cues
  const cues = fs.existsSync(path.join(RAW, 'cues.json')) ? JSON.parse(fs.readFileSync(path.join(RAW, 'cues.json'))) : {};
  async function scene(name, fn, { w = 1920, h = 1080 } = {}) {
    if (ONLY.length && !ONLY.includes(name)) { console.log(name, 'kept'); return; }
    const ctx = await b.newContext({ viewport: { width: w, height: h }, deviceScaleFactor: 1, recordVideo: { dir: RAW, size: { width: w, height: h } }, reducedMotion: 'no-preference' });
    const page = await ctx.newPage(); const t0 = Date.now(); const seen = {}; const log = (k, extra) => { if (seen[k] == null) { seen[k] = +((Date.now() - t0) / 1000).toFixed(2); if (extra) seen[k + ':note'] = extra; } };
    page.log = log; page.t0 = t0;
    await fn(page, log);
    const dur = +((Date.now() - t0) / 1000).toFixed(2);
    const vpath = await page.video().path(); await ctx.close();
    const out = path.join(RAW, name + '.webm'); fs.renameSync(vpath, out);
    cues[name] = { file: out, duration: dur, cues: seen }; console.log(name, dur + 's', JSON.stringify(seen));
  }
  // helpers for the replay page
  const pinFull = async (p) => { const t = p.locator('#shelf-toggle'); const txt = (await t.textContent()).trim(); if (/Collapse/.test(txt)) { await t.click(); await t.click(); } else { await t.click(); } };
  const setSpeed = async (p, s) => { const b = p.locator('#speed'); for (let i = 0; i < 4; i++) { const t = (await b.textContent()).trim(); if (t === `${s}×`) return; await b.click(); } };
  const watch = async (p, log, until, { onSee = {}, maxMs = 240000, poll = 200 } = {}) => {
    const t0 = Date.now();
    while (Date.now() - t0 < maxMs) {
      const txt = await p.evaluate(() => document.body.innerText);
      for (const m of MARKERS) if (txt.includes(m)) { const fresh = !p._seen?.[m]; (p._seen = p._seen || {})[m] = true; log(m); if (fresh && onSee[m]) await onSee[m](); }
      if (txt.includes(until)) return true;
      await sleep(poll);
    }
    return false;
  };
  const replay = async (name, run, plan) => scene(name, async (p, log) => {
    await p.goto(`${base}/run.html?run=${run}${plan.startAt ? '&t=' + plan.startAt : ''}`, { waitUntil: 'networkidle' }); await sleep(600);
    await pinFull(p); await setSpeed(p, plan.start || 4); await sleep(plan.idleMs ?? 1200); log('play');
    await p.locator('#play').click();
    await watch(p, log, 'Verdict · compared by code', { onSee: plan.onSee ? plan.onSee(p) : {} });
    await sleep(500);
    await p.evaluate(() => { const n = [...document.querySelectorAll('h3,h4')].find(x => /Verdict · compared by code/.test(x.textContent)); n && n.scrollIntoView({ block: 'start', behavior: 'smooth' }); });
    await sleep(plan.holdMs ?? 5000);
    if (plan.afterVerdict) await plan.afterVerdict(p, log);
  });
  const smoothScrollTo = async (p, sel, ms) => { await p.evaluate(([sel, ms]) => new Promise(res => { const el = document.querySelector(sel); const y1 = el.getBoundingClientRect().top + scrollY - 8, y0 = scrollY; const t0 = performance.now(); const step = (now) => { const k = Math.min(1, (now - t0) / ms); const e = k < .5 ? 2 * k * k : 1 - Math.pow(-2 * k + 2, 2) / 2; scrollTo(0, y0 + (y1 - y0) * e); if (k < 1) requestAnimationFrame(step); else res(); }; requestAnimationFrame(step); }), [sel, ms]); };

  // 1. landing: the claim and the scope, then down to the numbers
  await scene('s1-landing', async (p, log) => {
    await p.goto(`${base}/index.html`, { waitUntil: 'networkidle' }); await sleep(3800); log('scroll');
    await smoothScrollTo(p, '#score', 2400); await sleep(3200);
  });
  // 2. case 01: forecast, measurement, needles, the reading, the seal
  await replay('s2-case01', '20261103T125924-bf8f64512b', { start: 4, idleMs: 1200, onSee: (p) => ({ 'ngspice, step 1': async () => { await sleep(2500); await setSpeed(p, 16); }, 'asked for the check': async () => { await setSpeed(p, 4); }, 'held-back input 2 of 2': async () => { await setSpeed(p, 16); }, 'asked for one reading': async () => { await setSpeed(p, 4); }, 'pointed at the body': async () => { await setSpeed(p, 1); } }), holdMs: 4000 });
  // 3. case 04: every value explanation fails, Spark proposes the diode
  await replay('s3-case04', '20261103T150223-18d6f08ac9', { start: 16, idleMs: 800, onSee: (p) => ({ 'ngspice, step 3': async () => { await setSpeed(p, 4); }, 'ngspice, proposed circuit': async () => { await sleep(3000); await setSpeed(p, 16); } }), holdMs: 3500 });
  // 4. case 05: a proposal, two placements, one reading of the wire path, the seal; then the restored rerun's note
  await replay('s4-case05', '20261104T021333-c80ef3617e', { start: 4, startAt: START05, idleMs: 1500, onSee: (p) => ({ 'ngspice, proposed circuit': async () => { await sleep(2500); await setSpeed(p, 16); }, 'electrically equivalent explanations': async () => { await setSpeed(p, 4); }, 'pointed at the body': async () => { await setSpeed(p, 1); } }), holdMs: 4000 });
  // 5. case 02: Spark says the photo cannot tell the two capacitors apart; both are read; the bands decide
  await replay('s5-case02', '20261103T165506-b6ad3e8cf7', { start: 4, startAt: START02, idleMs: 1500, onSee: (p) => ({ 'two capacitor bodies': async () => { await setSpeed(p, 1); } }), holdMs: 4000 });
  // 6. landing again: the bench and what this is a prototype of
  await scene('s6-bench', async (p, log) => {
    await p.goto(`${base}/index.html#bench`, { waitUntil: 'networkidle' }); await p.evaluate(() => document.querySelector('#bench').scrollIntoView()); await sleep(4800); log('to-frontier');
    await smoothScrollTo(p, '#frontier', 1600); await sleep(4800);
  });
  // 7. the verifier, typed and answered (a local page that replays the real command lines and their recorded outputs)
  await scene('s7-verify', async (p, log) => {
    await p.goto('file://' + path.join(__dirname, 'verify-terminal.html'), { waitUntil: 'load' }); await sleep(12200);
  });
  // 8. closing card
  await scene('s8-close', async (p, log) => {
    await p.goto('file://' + path.join(__dirname, 'closing-card.html'), { waitUntil: 'load' }); await sleep(6000);
  });
  fs.writeFileSync(path.join(RAW, 'cues.json'), JSON.stringify(cues, null, 1));
  await b.close(); console.log('total', Object.values(cues).reduce((a, c) => a + c.duration, 0).toFixed(1), 's');
})();
