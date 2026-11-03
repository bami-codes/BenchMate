const { chromium } = require('playwright'); const fs = require('fs');
const base = 'http://127.0.0.1:8795'; const RUN = '20261103T125924-bf8f64512b', RERUN = '20261103T142003-2b176faa91';
(async () => {
  const b = await chromium.launch(); fs.mkdirSync('_shots/v3h', { recursive: true });
  const errs = [];
  const mk = async (w, h, dsf = 1) => { const p = await b.newPage({ viewport: { width: w, height: h }, deviceScaleFactor: dsf }); p.on('console', m => { if (m.type() === 'error') errs.push(`[${w}] ${m.text()}`); }); p.on('pageerror', e => errs.push(`[${w}] ${e.message}`)); return p; };
  const overflow = async (p) => p.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth + 1);
  // landing
  for (const [w, h, name] of [[1440, 900, 'landing-1440'], [390, 844, 'landing-390']]) {
    const p = await mk(w, h); await p.goto(base + '/index.html', { waitUntil: 'networkidle' }); await p.waitForTimeout(1500);
    await p.screenshot({ path: `_shots/v3h/${name}.png` }); await p.screenshot({ path: `_shots/v3h/${name}-full.png`, fullPage: true });
    if (await overflow(p)) errs.push(`[${w}] landing overflow`); await p.close();
  }
  // replay: play at 16x to the end, shooting at the reading card and the end
  for (const [w, h] of [[1440, 900], [390, 844]]) {
    const p = await mk(w, h); await p.goto(`${base}/run.html?run=${RUN}`, { waitUntil: 'networkidle' }); await p.waitForTimeout(1200);
    await p.screenshot({ path: `_shots/v3h/replay-idle-${w}.png` });
    const speed = p.locator('button', { hasText: /^\d+×$/ }); for (let i = 0; i < 3; i++) { const t = (await speed.first().textContent()).trim(); if (t === '16×') break; await speed.first().click(); }
    await p.locator('button', { hasText: 'Play' }).first().click();
    let shotReading = false, shotBinding = false, t0 = Date.now();
    while (Date.now() - t0 < 120000) {
      await p.waitForTimeout(500);
      const txt = await p.evaluate(() => document.body.innerText);
      if (!shotBinding && /pointed at the body/.test(txt)) { shotBinding = true; await p.evaluate(() => { const n = [...document.querySelectorAll('.note h3,.note h4,h3,h4')].find(x => /pointed at the body/.test(x.textContent)); n && n.scrollIntoView({ block: 'center' }); }); await p.waitForTimeout(400); await p.screenshot({ path: `_shots/v3h/replay-binding-${w}.png` }); }
      if (!shotReading && /the operator reads one value/.test(txt)) { shotReading = true; await p.waitForTimeout(2500); await p.evaluate(() => { const n = [...document.querySelectorAll('h3,h4')].find(x => /reads one value/.test(x.textContent)); n && n.scrollIntoView({ block: 'center' }); }); await p.waitForTimeout(300); await p.screenshot({ path: `_shots/v3h/replay-reading-${w}.png` }); }
      if (/Verdict · compared by code/.test(txt)) break;
    }
    await p.waitForTimeout(1500);
    await p.evaluate(() => { const n = [...document.querySelectorAll('h3,h4')].find(x => /Verdict · compared by code/.test(x.textContent)); n && n.scrollIntoView({ block: 'start' }); }); await p.waitForTimeout(600);
    await p.screenshot({ path: `_shots/v3h/replay-end-${w}.png` }); await p.screenshot({ path: `_shots/v3h/replay-end-${w}-full.png`, fullPage: true });
    const txt = await p.evaluate(() => document.body.innerText); fs.writeFileSync(`_shots/v3h/replay-end-${w}.txt`, txt);
    if (!/Verdict · compared by code/.test(txt)) errs.push(`[${w}] replay did not reach the verdict`);
    if (await overflow(p)) errs.push(`[${w}] replay overflow`); await p.close();
  }
  // restored rerun, end only
  { const p = await mk(1440, 900); await p.goto(`${base}/run.html?run=${RERUN}`, { waitUntil: 'networkidle' }); await p.waitForTimeout(1000);
    const speed = p.locator('button', { hasText: /^\d+×$/ }); for (let i = 0; i < 3; i++) { const t = (await speed.first().textContent()).trim(); if (t === '16×') break; await speed.first().click(); }
    await p.locator('button', { hasText: 'Play' }).first().click(); const t0 = Date.now();
    while (Date.now() - t0 < 90000) { await p.waitForTimeout(600); if (/Verdict · compared by code/.test(await p.evaluate(() => document.body.innerText))) break; }
    await p.waitForTimeout(1500); await p.evaluate(() => { const n = [...document.querySelectorAll('h3,h4')].find(x => /Verdict · compared by code/.test(x.textContent)); n && n.scrollIntoView({ block: 'start' }); }); await p.waitForTimeout(500);
    await p.screenshot({ path: '_shots/v3h/rerun-end-1440.png' }); fs.writeFileSync('_shots/v3h/rerun-end.txt', await p.evaluate(() => document.body.innerText)); await p.close(); }
  // report
  { const p = await mk(1440, 900); await p.goto(`${base}/case.html?id=01`, { waitUntil: 'networkidle' }); await p.waitForTimeout(1200); await p.screenshot({ path: '_shots/v3h/report-1440-full.png', fullPage: true }); if (await overflow(p)) errs.push('report overflow'); await p.close(); }
  fs.writeFileSync('_shots/v3h/errors.txt', errs.join('\n') || 'none');
  console.log('errors:', errs.length ? errs.join('\n') : 'none');
  await b.close();
})();
