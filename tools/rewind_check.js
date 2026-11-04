// Rewind check, every counted run: a seek (scrubber, Jump-to, ?t=) must leave the replay exactly as a forward play to that
// time would. For each run: seek to the end, back to 0, and compare the whole derived state (seal chip, bench-state rows,
// counters, meters and chips, scope, drawing card, notebook headlines, play label) with the state at load; then play forward
// at 16× to a time inside the longest quiet gap, pause, and compare with a forward seek, a backward seek from the end, a
// fresh page opened with ?t=, and a Jump-to button whose target sits in a quiet gap. Run with a local server on 8795:
//   python3 -m http.server --directory site 8795 &  node tools/rewind_check.js
const { chromium } = require('playwright'); const fs = require('fs');
const base = process.env.BASE || 'http://127.0.0.1:8795'; const OUT = '_shots/rewind';
const snap = () => {
  const $ = s => document.querySelector(s); const txt = n => (n ? n.textContent.trim() : null);
  const cls = n => [...n.classList].sort().join(' ');
  return {
    seal: txt($('#seal')), sealClass: cls($('#seal')), bsSeal: txt($('#bs-seal')), bsLoad: txt($('#bs-load')), bsLast: txt($('#bs-last')),
    exp: txt($('#c-exp')), calls: txt($('#c-calls')), cost: txt($('#c-cost')),
    railHidden: $('#rail-schem').closest('.rail-card').hidden, railNote: txt($('#rail-schem-note')),
    scopeTitle: txt($('#scope .title')), scopeClass: cls($('#scope')), scopeHud: txt($('#scope .hud')), idleOff: $('#scope-idle').classList.contains('off'),
    play: txt($('#play')), clock: txt($('#clock')),
    meters: [...document.querySelectorAll('#meters .meter')].map(m => [m.dataset.id, cls(m), txt(m.querySelector('.name')), txt(m.querySelector('.read')), txt(m.querySelector('.tag'))].join(' | ')),
    chips: [...document.querySelectorAll('#meter-chips .chip-m')].map(c => cls(c) + ' ' + txt(c)),
    entries: [...document.querySelectorAll('#book .entry')].map(e => [txt(e.querySelector('.who')), txt(e.querySelector('.lead'))].join(' | ')),
    finale: document.querySelectorAll('#book .finale').length, verdict: txt($('#book .verdict-card .big')),
  };
};
const seekTo = t => { const s = document.querySelector('#scrub'); s.value = String(t); s.dispatchEvent(new Event('input', { bubbles: true })); };
const scrubAt = () => Number(document.querySelector('#scrub').value);
const noClock = s => { const { clock, ...rest } = s; return rest; };
const diff = (a, b) => Object.keys(a).filter(k => JSON.stringify(a[k]) !== JSON.stringify(b[k])).map(k => `${k}: ${JSON.stringify(a[k]).slice(0, 160)} ≠ ${JSON.stringify(b[k]).slice(0, 160)}`);
(async () => {
  const b = await chromium.launch(); fs.mkdirSync(OUT, { recursive: true });
  const errs = [], log = [];
  const idx = JSON.parse(fs.readFileSync('data/runs/index.json')).runs.filter(r => r.counted);
  const open = async (url) => { const p = await b.newPage({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 1 });
    p.on('console', m => { if (m.type() === 'error') errs.push(`${url} console: ${m.text()}`); }); p.on('pageerror', e => errs.push(`${url} pageerror: ${e.message}`));
    await p.goto(`${base}/${url}`, { waitUntil: 'networkidle' }); await p.waitForTimeout(900); return p; };
  const setSpeed = async (p, want) => { const sp = p.locator('#speed'); for (let i = 0; i < 3; i++) { if ((await sp.textContent()).trim() === want) return; await sp.click(); } };
  for (const r of idx) {
    const tag = `${r.case}-${r.label.replace(/\s+/g, '').toLowerCase()}`;
    const run = JSON.parse(fs.readFileSync(`data/runs/${r.id}.json`)); const tl = run.timeline;
    const END = Math.max(run.play_length_s, tl[tl.length - 1].t_play + 0.5);
    const fail = (what, d) => { errs.push(`${tag}: ${what}${d && d.length ? '\n    ' + d.join('\n    ') : ''}`); };
    const A = await open(`run.html?run=${r.id}`);
    const s0 = await A.evaluate(snap);
    if (s0.seal !== 'Hidden fault sealed' || s0.exp !== '0' || s0.calls !== '0' || s0.cost !== '$0' || s0.bsSeal !== 'hidden fault sealed') fail('initial header is not the sealed zero state', [JSON.stringify([s0.seal, s0.exp, s0.calls, s0.cost, s0.bsSeal])]);
    // 1. end, then back to 0: everything derived returns to the initial state
    await A.evaluate(seekTo, END + 1); await A.waitForTimeout(1800);
    const sEnd = await A.evaluate(snap);
    if (!/^Seal opened|^Stopped/.test(sEnd.seal) || !sEnd.finale) fail('end state did not open the seal', [JSON.stringify([sEnd.seal, sEnd.finale])]);
    await A.evaluate(seekTo, 0); await A.waitForTimeout(700);
    const sBack = await A.evaluate(snap);
    const d0 = diff(s0, sBack); if (d0.length) fail('after end → 0 the state differs from the initial one', d0);
    await A.screenshot({ path: `${OUT}/${tag}-back-to-0.png` });
    // 2. a time inside the longest quiet gap (no event within it): forward play there, then every way of seeking there
    let gap = null; for (let i = 0; i + 1 < tl.length; i++) { const g = tl[i + 1].t_play - tl[i].t_play; if (!gap || g > gap.len) gap = { a: tl[i].t_play, b: tl[i + 1].t_play, len: g }; }
    const T = gap.a + Math.min(2, gap.len / 3);
    const B = await open(`run.html?run=${r.id}`); await setSpeed(B, '16×'); await B.locator('#play').click();
    let v = 0; const t0 = Date.now(); while (Date.now() - t0 < 60000) { v = await B.evaluate(scrubAt); if (v >= T) break; await B.waitForTimeout(40); }
    await B.locator('#play').click(); await B.waitForTimeout(300); v = await B.evaluate(scrubAt);
    if (!(v > gap.a + 0.1 && v < gap.b - 0.1)) { fail(`forward play paused at ${v}, outside the quiet gap ${gap.a}–${gap.b}; mid check inconclusive`); }
    else {
      const sFwd = noClock(await B.evaluate(snap)); // the clock rounds pos to the second; a forward play's pos sits within the scrubber's 0.1 s step of v
      await A.evaluate(seekTo, v); await A.waitForTimeout(700); const sSeekFwd = noClock(await A.evaluate(snap));
      const d1 = diff(sFwd, sSeekFwd); if (d1.length) fail(`forward seek 0 → ${v} differs from forward play to ${v}`, d1);
      await A.evaluate(seekTo, END + 1); await A.waitForTimeout(1500); await A.evaluate(seekTo, v); await A.waitForTimeout(700); const sSeekBack = noClock(await A.evaluate(snap));
      const d2 = diff(sFwd, sSeekBack); if (d2.length) fail(`backward seek end → ${v} differs from forward play to ${v}`, d2);
      const C = await open(`run.html?run=${r.id}&t=${v}`); const sT = noClock(await C.evaluate(snap)); await C.close();
      const d3 = diff(sFwd, sT); if (d3.length) fail(`?t=${v} differs from forward play to ${v}`, d3);
      await A.screenshot({ path: `${OUT}/${tag}-mid.png` });
      log.push(`${tag}: end→0 restores the initial state; forward play to ${v} s = forward seek = backward seek = ?t=`);
    }
    await B.close();
    // 3. Jump-to, from the end state: a button whose target (0.4 s before the moment) has no event within 0.11 s of it. The jump
    // and the pause run in one task, so pos is exactly the target; the result must equal a fresh page seeked there with the scrubber
    const jumps = await A.evaluate(() => [...document.querySelectorAll('#jumps button')].map((b, i) => ({ i, name: b.firstChild.textContent, t: Number(document.querySelectorAll('#jump-ticks option')[i].value) })));
    const quiet = jumps.filter(j => j.t - 0.4 > 0 && !tl.some(e => Math.abs(e.t_play - (j.t - 0.4)) < 0.11));
    if (!jumps.length) log.push(`${tag}: no Jump-to row`);
    else if (!quiet.length) log.push(`${tag}: no Jump-to target in a quiet gap; jump check skipped`);
    else { const j = quiet[quiet.length - 1];
      await A.evaluate(seekTo, END + 1); await A.waitForTimeout(1500);
      await A.evaluate(i => { document.querySelectorAll('#jumps button')[i].click(); document.querySelector('#play').click(); }, j.i); await A.waitForTimeout(700);
      const w = await A.evaluate(scrubAt);
      if (Math.abs(w - (j.t - 0.4)) > 0.06) fail(`Jump-to "${j.name}" left the scrubber at ${w}, not at its target ${j.t - 0.4}`);
      else { const sJ = await A.evaluate(snap); const D = await open(`run.html?run=${r.id}`); await D.evaluate(seekTo, w); await D.waitForTimeout(700); const sD = await D.evaluate(snap); await D.close();
        const d4 = diff(sJ, sD); if (d4.length) fail(`Jump-to "${j.name}" from the end (${w} s) differs from a fresh seek to ${w}`, d4); else log.push(`${tag}: Jump-to "${j.name}" from the end = fresh seek to ${w} s`); } }
    await A.close();
  }
  fs.writeFileSync(`${OUT}/errors.txt`, errs.join('\n') || 'none'); fs.writeFileSync(`${OUT}/log.txt`, log.join('\n'));
  console.log(log.join('\n')); console.log('errors:', errs.length ? '\n' + errs.join('\n') : 'none');
  await b.close(); process.exitCode = errs.length ? 1 : 0;
})();
