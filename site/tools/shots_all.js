// Every counted run, both viewports: play at 16× to the end, screenshot idle / reading / end, collect console errors and
// horizontal overflow; landing and every report at both viewports. Run with a local server on 8795:
//   python3 -m http.server --directory site 8795 &  node tools/shots_all.js
const { chromium } = require('playwright'); const fs = require('fs');
const base = process.env.BASE || 'http://127.0.0.1:8795'; const OUT = '_shots/all';
(async () => {
  const b = await chromium.launch(); fs.mkdirSync(OUT, { recursive: true });
  const errs = [], log = [];
  const mk = async (w, h) => { const p = await b.newPage({ viewport: { width: w, height: h }, deviceScaleFactor: 1 }); p.on('console', m => { if (m.type() === 'error') errs.push(`[${w}] ${p.url()} ${m.text()}`); }); p.on('pageerror', e => errs.push(`[${w}] ${p.url()} ${e.message}`)); p.on('requestfailed', r => errs.push(`[${w}] request failed ${r.url()}`)); p.on('response', r => { if (r.status() >= 400) errs.push(`[${w}] ${r.status()} ${r.url()}`); }); return p; };
  const overflow = async (p) => p.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth + 1);
  const idx = JSON.parse(fs.readFileSync('data/runs/index.json')).runs.filter(r => r.counted);
  const cases = JSON.parse(fs.readFileSync('data/cases.json')).cases;
  for (const [w, h] of [[1440, 900], [390, 844]]) {
    const p = await mk(w, h); await p.goto(base + '/index.html', { waitUntil: 'networkidle' }); await p.waitForTimeout(1500);
    await p.screenshot({ path: `${OUT}/landing-${w}-full.png`, fullPage: true }); if (await overflow(p)) errs.push(`[${w}] landing overflow`);
    fs.writeFileSync(`${OUT}/landing-${w}.txt`, await p.evaluate(() => document.body.innerText)); await p.close();
    for (const c of cases) { const q = await mk(w, h); await q.goto(`${base}/case.html?id=${c.id}`, { waitUntil: 'networkidle' }); await q.waitForTimeout(1200); await q.screenshot({ path: `${OUT}/report-${c.id}-${w}-full.png`, fullPage: true }); if (await overflow(q)) errs.push(`[${w}] report ${c.id} overflow`); fs.writeFileSync(`${OUT}/report-${c.id}-${w}.txt`, await q.evaluate(() => document.body.innerText)); await q.close(); }
  }
  for (const r of idx) for (const [w, h] of [[1440, 900], [390, 844]]) {
    const tag = `${r.case}-${r.label.replace(/\s+/g, '').toLowerCase()}-${w}`;
    const p = await mk(w, h); await p.goto(`${base}/run.html?run=${r.id}`, { waitUntil: 'networkidle' }); await p.waitForTimeout(1200);
    await p.screenshot({ path: `${OUT}/replay-${tag}-idle.png` });
    const speed = p.locator('button', { hasText: /^\d+×$/ }); for (let i = 0; i < 3; i++) { const t = (await speed.first().textContent()).trim(); if (t === '16×') break; await speed.first().click(); }
    await p.locator('button', { hasText: 'Play' }).first().click();
    let shotReading = false, t0 = Date.now();
    while (Date.now() - t0 < 150000) {
      await p.waitForTimeout(500);
      const txt = await p.evaluate(() => document.body.innerText);
      if (!shotReading && /reads one value|reads both bodies/.test(txt)) { shotReading = true; await p.waitForTimeout(2500); await p.evaluate(() => { const n = [...document.querySelectorAll('h3,h4')].find(x => /reads one value|reads both bodies/.test(x.textContent)); n && n.scrollIntoView({ block: 'center' }); }); await p.waitForTimeout(300); await p.screenshot({ path: `${OUT}/replay-${tag}-reading.png` }); }
      if (/Verdict · compared by code|End of the recording/.test(txt)) break;
    }
    await p.waitForTimeout(1500);
    await p.evaluate(() => { const n = [...document.querySelectorAll('h3,h4')].find(x => /Verdict · compared by code|End of the recording/.test(x.textContent)); n && n.scrollIntoView({ block: 'start' }); }); await p.waitForTimeout(600);
    await p.screenshot({ path: `${OUT}/replay-${tag}-end.png` }); await p.screenshot({ path: `${OUT}/replay-${tag}-full.png`, fullPage: true });
    const txt = await p.evaluate(() => document.body.innerText); fs.writeFileSync(`${OUT}/replay-${tag}.txt`, txt);
    const reached = /Verdict · compared by code/.test(txt);
    log.push(`${tag}: ${reached ? 'reached the verdict' : 'DID NOT reach the verdict'} in ${((Date.now() - t0) / 1000).toFixed(0)} s`);
    if (!reached) errs.push(`[${w}] ${r.id} replay did not reach the verdict`);
    if (await overflow(p)) errs.push(`[${w}] ${r.id} replay overflow`); await p.close();
  }
  fs.writeFileSync(`${OUT}/errors.txt`, errs.join('\n') || 'none'); fs.writeFileSync(`${OUT}/log.txt`, log.join('\n'));
  console.log(log.join('\n')); console.log('errors:', errs.length ? '\n' + errs.join('\n') : 'none');
  await b.close();
})();
