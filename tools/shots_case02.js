// case 02: the two-reading stage. Checks: no console errors, no sideways overflow at 390 px, 16× play-through to the verdict
// for both the fault run and the restored rerun; screenshots to _shots/v3j/.
const { chromium } = require('playwright'); const fs = require('fs');
const base = 'http://127.0.0.1:8795'; const RUN = '20261103T165506-b6ad3e8cf7', RERUN = '20261103T182550-4ea22cc3a0'; const OUT = '_shots/v3j';
(async () => {
  const b = await chromium.launch(); fs.mkdirSync(OUT, { recursive: true });
  const errs = [];
  const mk = async (w, h, dsf = 1) => { const p = await b.newPage({ viewport: { width: w, height: h }, deviceScaleFactor: dsf }); p.on('console', m => { if (m.type() === 'error') errs.push(`[${w}] ${m.text()}`); }); p.on('pageerror', e => errs.push(`[${w}] ${e.message}`)); p.on('response', r => { if (r.status() >= 400) errs.push(`[${w}] HTTP ${r.status()} ${r.url()}`); }); return p; };
  const overflow = async (p) => p.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth + 1);
  // scroll a stage heading to just below the sticky bench panel (the panel is the element holding the counters)
  const scrollTo = async (p, re, block = 'center') => { await p.evaluate(([src, block]) => { const re = new RegExp(src); const n = [...document.querySelectorAll('h3,h4,p.lead,.who')].find(x => re.test(x.textContent)); if (!n) return; let bar = document.querySelector('#c-calls'); while (bar && getComputedStyle(bar).position !== 'sticky' && getComputedStyle(bar).position !== 'fixed') bar = bar.parentElement; const top = bar ? bar.getBoundingClientRect().bottom : 0; window.scrollBy(0, n.getBoundingClientRect().top - top - 14); }, [re.source, block]); await p.waitForTimeout(400); };
  const to16 = async (p) => { const speed = p.locator('button', { hasText: /^\d+×$/ }); for (let i = 0; i < 4; i++) { const t = (await speed.first().textContent()).trim(); if (t === '16×') break; await speed.first().click(); } };
  // landing: cases list
  for (const [w, h, name] of [[1440, 900, 'cases-list-1440'], [390, 844, 'cases-list-390']]) {
    const p = await mk(w, h); await p.goto(base + '/index.html', { waitUntil: 'networkidle' }); await p.waitForTimeout(1200);
    await p.evaluate(() => { const n = document.querySelector('#cases, .case-row'); n && n.scrollIntoView({ block: 'start' }); }); await p.waitForTimeout(300);
    await p.screenshot({ path: `${OUT}/${name}.png` }); await p.screenshot({ path: `${OUT}/${name}-full.png`, fullPage: true });
    fs.writeFileSync(`${OUT}/landing-${w}.txt`, await p.evaluate(() => document.body.innerText));
    if (await overflow(p)) errs.push(`[${w}] landing overflow`); await p.close();
  }
  // fault run replay at 16×
  for (const [w, h] of [[1440, 900], [390, 844]]) {
    const p = await mk(w, h); await p.goto(`${base}/run.html?run=${RUN}`, { waitUntil: 'networkidle' }); await p.waitForTimeout(1200);
    await to16(p); await p.locator('button', { hasText: 'Play' }).first().click();
    let shot = {}; const t0 = Date.now();
    while (Date.now() - t0 < 150000) {
      await p.waitForTimeout(500);
      const txt = await p.evaluate(() => document.body.innerText);
      if (!shot.abst && /asked which body is C1/.test(txt)) { shot.abst = 1; await scrollTo(p, /asked which body is C1/); await p.screenshot({ path: `${OUT}/02-binding-abstained-${w}.png` }); }
      if (!shot.group && /which is which unknown/.test(txt)) { shot.group = 1; await p.waitForTimeout(600); await scrollTo(p, /which is which unknown/); await p.screenshot({ path: `${OUT}/02-body-group-${w}.png` }); }
      if (!shot.fc && /reading forecast for both bodies/.test(txt)) { shot.fc = 1; await scrollTo(p, /reading forecast for both bodies/); await p.screenshot({ path: `${OUT}/02-group-forecast-${w}.png` }); }
      if (!shot.read && /reads both bodies/.test(txt)) { shot.read = 1; await p.waitForTimeout(3200); await scrollTo(p, /reads both bodies/); await p.screenshot({ path: `${OUT}/02-reading-card-${w}.png` }); }
      if (!shot.score && /both readings scored/.test(txt)) { shot.score = 1; await p.waitForTimeout(400); await scrollTo(p, /both readings scored/); await p.screenshot({ path: `${OUT}/02-assignment-block-${w}.png` }); }
      if (/Verdict · from the engine’s report/.test(txt)) break;
    }
    await p.waitForTimeout(1800);
    // settled shots of each stage, after the play-through (the live shots above catch the typing mid-way)
    for (const [re, name] of [[/asked which body is C1/, '02-binding-abstained'], [/which is which unknown/, '02-body-group'], [/reading forecast for both bodies/, '02-group-forecast'], [/reads both bodies/, '02-reading-card'], [/both readings scored/, '02-assignment-block']]) { await scrollTo(p, re, 'center'); await p.screenshot({ path: `${OUT}/${name}-${w}.png` }); }
    await scrollTo(p, /Verdict · from the engine’s report/, 'start');
    await p.screenshot({ path: `${OUT}/02-end-${w}.png` }); await p.screenshot({ path: `${OUT}/02-end-${w}-full.png`, fullPage: true });
    const txt = await p.evaluate(() => document.body.innerText); fs.writeFileSync(`${OUT}/02-end-${w}.txt`, txt);
    if (!/Verdict · from the engine’s report/.test(txt)) errs.push(`[${w}] fault replay did not reach the verdict`);
    for (const k of ['abst', 'group', 'fc', 'read', 'score']) if (!shot[k]) errs.push(`[${w}] stage not seen: ${k}`);
    if (await overflow(p)) errs.push(`[${w}] fault replay overflow`); await p.close();
  }
  // restored rerun at 16×
  for (const [w, h] of [[1440, 900], [390, 844]]) {
    const p = await mk(w, h); await p.goto(`${base}/run.html?run=${RERUN}`, { waitUntil: 'networkidle' }); await p.waitForTimeout(1000);
    await to16(p); await p.locator('button', { hasText: 'Play' }).first().click(); const t0 = Date.now();
    while (Date.now() - t0 < 120000) { await p.waitForTimeout(600); if (/Verdict · from the engine’s report/.test(await p.evaluate(() => document.body.innerText))) break; }
    await p.waitForTimeout(1800); await scrollTo(p, /Verdict · from the engine’s report/, 'start');
    await p.screenshot({ path: `${OUT}/02-restored-end-${w}.png` }); await p.screenshot({ path: `${OUT}/02-restored-end-${w}-full.png`, fullPage: true });
    const txt = await p.evaluate(() => document.body.innerText); fs.writeFileSync(`${OUT}/02-restored-end-${w}.txt`, txt);
    if (!/Verdict · from the engine’s report/.test(txt)) errs.push(`[${w}] restored replay did not reach the verdict`);
    if (await overflow(p)) errs.push(`[${w}] restored replay overflow`); await p.close();
  }
  // reports
  for (const [id, run, name] of [['02', RUN, '02-report'], ['02', RERUN, '02-restored-report']]) for (const [w, h] of [[1440, 900], [390, 844]]) {
    const p = await mk(w, h); await p.goto(`${base}/case.html?id=${id}&run=${run}`, { waitUntil: 'networkidle' }); await p.waitForTimeout(1500);
    await p.screenshot({ path: `${OUT}/${name}-${w}-full.png`, fullPage: true }); fs.writeFileSync(`${OUT}/${name}-${w}.txt`, await p.evaluate(() => document.body.innerText));
    if (await overflow(p)) errs.push(`[${w}] ${name} overflow`); await p.close();
  }
  fs.writeFileSync(`${OUT}/errors.txt`, errs.join('\n') || 'none');
  console.log('errors:', errs.length ? errs.join('\n') : 'none');
  await b.close();
})();
