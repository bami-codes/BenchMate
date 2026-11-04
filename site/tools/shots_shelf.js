// Shelf full/compact checks across the official runs. Usage: node tools/shots_shelf.js http://127.0.0.1:8791
const { chromium } = require('playwright');
const fs = require('fs');
const base = process.argv[2] || 'http://127.0.0.1:8791';
const RUNS = ['20261103T125924-bf8f64512b', '20261103T165506-b6ad3e8cf7', '20261103T150223-18d6f08ac9', '20261103T142003-2b176faa91'];
const out = 'tools/../_shots/v3k'; fs.mkdirSync(out, { recursive: true });
const report = {};
(async () => {
  const b = await chromium.launch();
  for (const [name, vp] of [['1440', { width: 1440, height: 900 }], ['390', { width: 390, height: 844 }]]) {
    for (const run of RUNS) {
      const ctx = await b.newContext({ viewport: vp, deviceScaleFactor: 1 });
      const p = await ctx.newPage(); const errs = [];
      p.on('console', m => { if (m.type() === 'error') errs.push(m.text()); }); p.on('pageerror', e => errs.push(String(e)));
      await p.goto(`${base}/run.html?run=${run}`, { waitUntil: 'networkidle' }); await p.waitForTimeout(800);
      const r = { errs };
      const shelfH = async () => p.evaluate(() => document.getElementById('shelf').getBoundingClientRect().height);
      const ovf = async () => p.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth);
      const mode = async () => p.evaluate(() => document.getElementById('shelf').classList.contains('compact') ? 'compact' : 'full');
      r.initialMode = await mode(); r.shelfInitial = await shelfH(); r.overflowIdle = await ovf();
      // speed 16x and play through
      const sp = await p.$('#speed'); for (let i = 0; i < 3; i++) { if ((await sp.innerText()).includes('16')) break; await sp.click(); }
      await p.click('#play');
      const END = await p.evaluate(() => Number(document.getElementById('scrub').max));
      await p.waitForTimeout(Math.min(60000, END / 16 * 1000 + 6000));
      r.clock = await p.evaluate(() => document.getElementById('clock').textContent);
      r.played = r.clock.split(' / ')[0] === r.clock.split(' / ')[1];
      r.meters = await p.evaluate(() => document.querySelectorAll('#meters .meter').length);
      r.many = await p.evaluate(() => document.getElementById('meters').classList.contains('many'));
      if (name === '1440') {
        // full mode at top
        await p.evaluate(() => scrollTo(0, 0)); await p.waitForTimeout(500); r.modeTop = await mode(); r.shelfFull = await shelfH(); r.full45vh = r.shelfFull <= 900 * 0.45 + 1;
        if (run === RUNS[1]) await p.screenshot({ path: `${out}/02-full-1440.png` });
        // auto-collapse on scroll
        await p.evaluate(() => scrollTo(0, 700)); await p.waitForTimeout(700); r.modeScrolled = await mode(); r.shelfCompact = await shelfH(); r.compact190 = r.shelfCompact <= 190;
        r.chips = await p.evaluate(() => [...document.querySelectorAll('#meter-chips .chip-m')].map(c => c.className.replace('chip-m ', '') + ':' + c.textContent.trim()));
        if (run === RUNS[1]) await p.screenshot({ path: `${out}/02-compact-1440.png` });
        // back to top expands
        await p.evaluate(() => scrollTo(0, 0)); await p.waitForTimeout(700); r.modeBackTop = await mode();
        // manual toggle pins
        await p.click('#shelf-toggle'); await p.waitForTimeout(500); r.afterToggle = await mode(); r.ariaExpanded = await p.getAttribute('#shelf-toggle', 'aria-expanded');
        await p.evaluate(() => scrollTo(0, 700)); await p.waitForTimeout(500); await p.evaluate(() => scrollTo(0, 0)); await p.waitForTimeout(600); r.pinnedStays = await mode();
        r.stored = await p.evaluate(() => localStorage.getItem('bm.shelf'));
        await p.click('#shelf-toggle'); await p.waitForTimeout(300); r.toggleBack = await mode();
      } else {
        r.overflowEnd = await ovf(); r.chipsVisible = await p.evaluate(() => getComputedStyle(document.getElementById('meter-chips')).display);
        r.gridHidden = await p.evaluate(() => getComputedStyle(document.getElementById('meters')).display === 'none');
        await p.evaluate(() => scrollTo(0, 0)); await p.waitForTimeout(300);
        if (run === RUNS[1]) await p.screenshot({ path: `${out}/02-compact-390.png` });
        await p.click('#shelf-toggle'); await p.waitForTimeout(300); r.afterToggleGrid = await p.evaluate(() => getComputedStyle(document.getElementById('meters')).display);
        r.overflowExpanded = await ovf();
      }
      report[`${name}:${run.slice(0, 15)}`] = r;
      await ctx.close();
    }
  }
  fs.writeFileSync(`${out}/report.json`, JSON.stringify(report, null, 1));
  console.log(JSON.stringify(report, null, 1));
  await b.close();
})();
