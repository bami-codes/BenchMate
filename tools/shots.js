// Screenshots + checks for v3b. Usage: node tools/shots.js [base] [outdir]
const { chromium } = require('playwright');
const fs = require('fs');
const base = process.argv[2] || 'http://127.0.0.1:8793';
const out = process.argv[3] || '_shots/v3b';
fs.mkdirSync(out, { recursive: true });
const runA = '20261102T160841-eff2b65334';
(async () => {
  const b = await chromium.launch();
  const errors = [];
  const page = async (w, h, dpr = 1) => { const p = await b.newPage({ viewport: { width: w, height: h }, deviceScaleFactor: dpr }); p.on('pageerror', e => errors.push(`${w}px ${p.url()} ${e.message}`)); p.on('console', m => { if (m.type() === 'error') errors.push(`${w}px console ${p.url()} ${m.text()}`); }); return p; };
  const overflow = async (p, name) => { const o = await p.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth); if (o > 1) errors.push(`${name}: sideways overflow ${o}px`); };
  const fontsReady = async (p) => { await p.evaluate(() => document.fonts.ready); await p.waitForTimeout(400); };

  for (const [w, h, tag] of [[1440, 900, '1440'], [390, 844, '390']]) {
    const p = await page(w, h, tag === '390' ? 2 : 1);
    await p.goto(`${base}/index.html`, { waitUntil: 'networkidle' }); await fontsReady(p); await p.waitForTimeout(1200);
    await p.screenshot({ path: `${out}/landing-${tag}.png` }); await p.screenshot({ path: `${out}/landing-${tag}-full.png`, fullPage: true }); await overflow(p, `landing ${tag}`);
    // replay idle
    await p.goto(`${base}/run.html?run=${runA}`, { waitUntil: 'networkidle' }); await fontsReady(p); await p.waitForTimeout(600);
    await p.screenshot({ path: `${out}/replay-idle-${tag}.png` }); await overflow(p, `replay idle ${tag}`);
    // mid: seek into step 2 fit, then play a little at 1x for sweeps
    await p.evaluate(() => { document.querySelector('#scrub').value = 66; document.querySelector('#scrub').dispatchEvent(new Event('input')); });
    await p.waitForTimeout(1500);
    await p.screenshot({ path: `${out}/replay-mid-${tag}.png` }); await overflow(p, `replay mid ${tag}`);
    // end
    await p.evaluate(() => { const s = document.querySelector('#scrub'); s.value = s.max; s.dispatchEvent(new Event('input')); });
    await p.waitForTimeout(1800);
    await p.screenshot({ path: `${out}/replay-end-${tag}.png` }); await p.screenshot({ path: `${out}/replay-end-${tag}-full.png`, fullPage: true }); await overflow(p, `replay end ${tag}`);
    // evidence popover
    if (tag === '1440') { const n = await p.$('.fit-table .ev'); if (n) { await n.click(); await p.waitForTimeout(300); await p.screenshot({ path: `${out}/evidence-1440.png` }); } }
    // report
    await p.goto(`${base}/case.html?id=01&run=${runA}`, { waitUntil: 'networkidle' }); await fontsReady(p); await p.waitForTimeout(800);
    await p.screenshot({ path: `${out}/report-${tag}.png`, fullPage: true }); await overflow(p, `report ${tag}`);
    await p.goto(`${base}/case.html?id=04`, { waitUntil: 'networkidle' }); await fontsReady(p); await p.waitForTimeout(500); await overflow(p, `report04 ${tag}`);
    await p.close();
  }
  // play-through at 16x
  const p = await page(1440, 900);
  await p.goto(`${base}/run.html?run=${runA}`, { waitUntil: 'networkidle' }); await fontsReady(p);
  await p.evaluate(() => { const b = document.querySelector('#speed'); while (b.textContent !== '16×') b.click(); document.querySelector('#play').click(); });
  await p.waitForTimeout(12000);
  const done = await p.evaluate(() => ({ play: document.querySelector('#play').textContent, clock: document.querySelector('#clock').textContent, blocks: document.querySelectorAll('.entry').length, finale: !!document.querySelector('.finale.open') }));
  console.log('play-through', JSON.stringify(done));
  await p.screenshot({ path: `${out}/replay-played-1440.png`, fullPage: true });
  // DEV structure fixture
  if (fs.existsSync('tools/DEV-structure-run.json')) {
    await p.goto(`${base}/run.html?devsrc=tools/DEV-structure-run.json`, { waitUntil: 'networkidle' }); await fontsReady(p);
    await p.evaluate(() => { const s = document.querySelector('#scrub'); s.value = s.max; s.dispatchEvent(new Event('input')); });
    await p.waitForTimeout(1800);
    await p.screenshot({ path: `${out}/structure-scene-DEV-1440.png`, fullPage: true }); await overflow(p, 'structure DEV');
    const sc = await p.$('.propose'); if (sc) { await sc.scrollIntoViewIfNeeded(); await p.waitForTimeout(300); await p.screenshot({ path: `${out}/structure-card-DEV-1440.png` }); }
    const hb = await p.$('.entry.bench:has-text("held-back input 1")'); if (hb) { await hb.scrollIntoViewIfNeeded(); await p.waitForTimeout(300); await p.screenshot({ path: `${out}/verification-stage-DEV-1440.png` }); }
  }
  await p.close(); await b.close();
  console.log(errors.length ? 'ISSUES:\n' + errors.join('\n') : 'no console errors, no overflow');
})();
