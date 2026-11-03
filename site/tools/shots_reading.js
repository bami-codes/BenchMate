// Screenshots + checks for the reading stage (DEV fixture). Usage: node tools/shots_reading.js [base] [outdir]
const { chromium } = require('playwright');
const fs = require('fs');
const base = process.argv[2] || 'http://127.0.0.1:8793';
const out = process.argv[3] || '_shots/v3g';
fs.mkdirSync(out, { recursive: true });
const src = 'tools/DEV-reading-run.json';
(async () => {
  const b = await chromium.launch();
  const errors = [];
  const page = async (w, h, dpr = 1) => { const p = await b.newPage({ viewport: { width: w, height: h }, deviceScaleFactor: dpr }); p.on('pageerror', e => errors.push(`${w}px ${p.url()} ${e.message}`)); p.on('console', m => { if (m.type() === 'error') errors.push(`${w}px console ${p.url()} ${m.text()}`); }); return p; };
  const overflow = async (p, name) => { const o = await p.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth); if (o > 1) errors.push(`${name}: sideways overflow ${o}px`); };
  const fontsReady = async (p) => { await p.evaluate(() => document.fonts.ready); await p.waitForTimeout(400); };
  const run = JSON.parse(fs.readFileSync(src));
  const tAt = (kind, off = 0.2) => run.timeline.find(e => e.kind === kind).t_play + off;
  const seek = async (p, t) => { await p.evaluate(t => { const s = document.querySelector('#scrub'); s.value = t; s.dispatchEvent(new Event('input')); }, t); await p.waitForTimeout(1500); };
  const shotBlock = async (p, sel, name) => { const n = await p.$(sel); if (n) { await n.evaluate(x => x.scrollIntoView({ block: 'center' })); await p.waitForTimeout(400); await n.screenshot({ path: `${out}/${name}.png` }); } else errors.push(`missing ${sel}`); };

  for (const [w, h, tag] of [[1440, 900, '1440'], [390, 844, '390']]) {
    const p = await page(w, h, tag === '390' ? 2 : 1);
    await p.goto(`${base}/run.html?devsrc=${src}`, { waitUntil: 'networkidle' }); await fontsReady(p);
    await seek(p, tAt('reading_requested')); await p.screenshot({ path: `${out}/reading-request-${tag}.png` }); await overflow(p, `request ${tag}`);
    await seek(p, tAt('reading_forecast_frozen')); await shotBlock(p, '#book .entry:last-child', `reading-forecast-${tag}`);
    await seek(p, tAt('body_binding')); await shotBlock(p, '#book .entry:last-child', `reading-binding-${tag}`);
    // typed reading: seek just before, then play 1x so the field types
    await seek(p, tAt('reading_observed', -0.3));
    await p.evaluate(() => { const b = document.querySelector('#speed'); while (b.textContent !== '1×') b.click(); document.querySelector('#play').click(); });
    await p.waitForTimeout(1300); await p.screenshot({ path: `${out}/reading-typed-${tag}.png` });
    await p.waitForTimeout(1400); await p.screenshot({ path: `${out}/reading-meters-${tag}.png` });
    await p.evaluate(() => document.querySelector('#play').click());
    await seek(p, tAt('reading_scored')); await p.screenshot({ path: `${out}/reading-scored-${tag}.png` }); await overflow(p, `scored ${tag}`);
    await p.evaluate(() => { const s = document.querySelector('#scrub'); s.value = s.max; s.dispatchEvent(new Event('input')); }); await p.waitForTimeout(1800);
    await p.screenshot({ path: `${out}/reading-end-${tag}.png` }); await p.screenshot({ path: `${out}/reading-end-${tag}-full.png`, fullPage: true }); await overflow(p, `end ${tag}`);
    // try any value: 40 → none; 25 → R1 changed; 4.8 → proposal
    await shotBlock(p, '.tryit', `reading-tryit-closed-${tag}`);
    const closed = await p.$eval('.tryit', d => !d.open); if (!closed) errors.push('try-it not collapsed by default');
    await p.$eval('.tryit', d => { d.open = true; });
    const tr = await p.$('.tryit input');
    if (tr) { for (const v of ['40', '25', '4.8']) { await tr.fill(v); await p.waitForTimeout(150); const txt = await p.$eval('.tryout', n => n.textContent); fs.appendFileSync(`${out}/tryit-${tag}.txt`, v + ' → ' + txt + '\n'); } await shotBlock(p, '.tryit', `reading-tryit-${tag}`); } else errors.push('no tryit');
    if (tag === '1440') { await p.goto(`${base}/case.html?id=01&devsrc=${src}`, { waitUntil: 'networkidle' }); await fontsReady(p); await p.screenshot({ path: `${out}/report-reading-1440-full.png`, fullPage: true }); await overflow(p, 'report'); }
    await p.close();
  }
  // play-through at 16x on the fixture
  const p = await page(1440, 900);
  await p.goto(`${base}/run.html?devsrc=${src}`, { waitUntil: 'networkidle' }); await fontsReady(p);
  await p.evaluate(() => { const b = document.querySelector('#speed'); while (b.textContent !== '16×') b.click(); document.querySelector('#play').click(); });
  await p.waitForTimeout((run.play_length_s / 16 + 4) * 1000);
  const done = await p.$eval('#play', n => n.textContent);
  fs.writeFileSync(`${out}/playthrough.txt`, `play button after run: ${done}\n`);
  // older runs unaffected: Pilot A has no reading stage
  await p.goto(`${base}/run.html?run=20261102T160841-eff2b65334`, { waitUntil: 'networkidle' }); await fontsReady(p);
  await p.evaluate(() => { const s = document.querySelector('#scrub'); s.value = s.max; s.dispatchEvent(new Event('input')); }); await p.waitForTimeout(1500);
  const leak = await p.evaluate(() => /Try any value|one reading/.test(document.body.innerText));
  if (leak) errors.push('reading stage text leaked into Pilot A');
  await b.close();
  fs.writeFileSync(`${out}/errors.txt`, errors.join('\n') || 'no errors\n');
  console.log(errors.length ? errors.join('\n') : 'no errors');
})();
