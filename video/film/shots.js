// BenchMate film, shot by shot. Every number, waveform, range, label and verdict is read from the public run records in
// site/data. Each shot is a composed 1920×1080 frame; frame(t) sets every element from t alone (no one-shot state), so a frame
// rendered cold equals the same frame reached in sequence. The camera does not exist: continuity is in shared elements.
const { $, el, Scope, Meter, stepTraces, stepTime, expName, menuChips, fmtMiss, netlistSVG, verdictWords } = BM;
const clamp = (x) => Math.max(0, Math.min(1, x));
const E = (x) => x < .5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2;
const back = (x) => { const c1 = 1.70158, c3 = c1 + 1; return 1 + c3 * Math.pow(x - 1, 3) + c1 * Math.pow(x - 1, 2); };
const ease = (t, a, b) => E(clamp((t - a) / (b - a)));
const lin = (t, a, b) => clamp((t - a) / (b - a));
const kst = (iso) => iso ? new Date(iso).toLocaleTimeString('en-GB', { timeZone: 'Asia/Seoul', hour12: false }) : '';
const kstDate = (iso) => iso ? new Date(iso).toLocaleString('en-GB', { timeZone: 'Asia/Seoul', day: 'numeric', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit', hour12: false }).replace(',', '') + ' KST' : '';
const q = (s) => String(s || '').replace(/^["“]|["”]$/g, '');
const missOf = (f, k = 0) => (f.decided_mV || f.miss_mV)[k];
const rise = (elm, t, a, d = .6, dy = 18) => { if (!elm) return 0; const e = ease(t, a, a + d); elm.style.opacity = e; elm.style.transform = `translateY(${dy * (1 - e)}px)`; return e; };
const fade = (elm, t, a, d = .5) => { if (!elm) return 0; const e = ease(t, a, a + d); elm.style.opacity = e; return e; };
const typed = (elm, text, t, a, d) => { const n = Math.round(lin(t, a, a + d) * text.length); elm.textContent = text.slice(0, n); return n >= text.length; };

const SHOTS = []; const SFX = []; const CAPS = []; let VOICE = {};
// Seven narration clips (voice/s1…s7). Each scene's shots stretch together to its clip; ticks run in design time.
const SCENE_OF = { s1: ['s01','s02'], s2: ['s04','s05'], s3: ['s06','s07','s09','s10','s12','s13','s14'], s4: ['s15','s16','s18','s19','s20','s21','s22','s23'], s5: ['s24'], s6: ['s25','s26'], s7: ['s27'] };
const PLANNED = { s1: 9, s2: 16, s3: 47, s4: 43, s5: 17, s6: 21, s7: 13 };
const VOICE_LEAD = { s1: 2.2 };  // seconds of picture before the clip starts (the clip sits at scene start + 0.4 + lead)
let PLAN = {};  // voice/shot_plan.json: global start of each shot, computed by plan_shots.py from the clips' word timings
const sfx = (t, kind) => SFX.push({ t: +t.toFixed(3), kind });
const cap = (a, b, text) => CAPS.push({ a, b, text });
function shot(id, a, b, build, tick) { const root = el('div', { class: 'shot', id }); $('#shots').append(root); const s = { id, da: a, db: b, a, b, root, tick }; build(root, s); SHOTS.push(s); return s; }
function schedule() { let T = 0; const SC = []; for (const [sid, ids] of Object.entries(SCENE_OF)) { const sh = SHOTS.filter(x => ids.includes(x.id)); const design = sh.reduce((n, x) => n + (x.db - x.da), 0); const want = VOICE[sid] || PLANNED[sid]; const start = T, end = T + want; const planned = sh.every(x => PLAN[x.id] != null);
    if (planned) { sh.forEach((x, i) => { x.a = Math.max(start, PLAN[x.id]); x.b = i + 1 < sh.length ? Math.max(x.a + .5, PLAN[sh[i + 1].id]) : end; x.k = (x.b - x.a) / (x.db - x.da); }); T = end; }
    else { const k = want / design; for (const x of sh) { x.a = T; x.b = T + (x.db - x.da) * k; x.k = k; T = x.b; } }
    SC.push({ id: sid, start, seconds: T - start, voice_at: +(start + .4 + (VOICE_LEAD[sid] || 0)).toFixed(3), planned: PLANNED[sid], design }); } window.filmTotal = () => T; window.filmScenes = () => SC.map(x => ({ ...x })); }
const sched = (td) => { for (const x of SHOTS) if (td >= x.da && td < x.db + 1e-9) return x.a + (td - x.da) * x.k; const l = SHOTS[SHOTS.length - 1]; return l.b + (td - l.db) * l.k; };
const FIN = .4, FOUT = .3;  // each shot fades in from the mat and out to it; two shots are never on screen together

let R1, R1R, R4, R5, CASES, INDEX, SCH = {};
window.filmReady = (async () => {
  [R1, R1R, R4, R5, CASES, INDEX] = await Promise.all(['20261103T125924-bf8f64512b', '20261103T142003-2b176faa91', '20261103T150223-18d6f08ac9', '20261104T021333-c80ef3617e'].map(id => BM.json(`../../site/data/runs/${id}.json`)).concat([BM.json('../../site/data/cases.json'), BM.json('../../site/data/runs/index.json')]));
  for (const d of ['design-01', 'design-04']) SCH[d] = await fetch(`../../site/assets/schem/${d}.svg`).then(r => r.text());
  // names the site registers from the records: proposals and equivalence-group members
  for (const pr of R4.structure || []) BM.names[pr.id] = BM.proposalName(pr); for (const pr of R5.structure || []) BM.names[pr.id] = BM.proposalName(pr);
  for (const e of R1.timeline) if (e.kind === 'equivalence_group') for (const m of e.members || []) BM.names[m.id] = m.label || m.words;
  try { VOICE = await BM.json('voice/durations.json'); } catch (e) { VOICE = {}; }
  try { PLAN = await BM.json('voice/shot_plan.json'); } catch (e) { PLAN = {}; }
  buildAll(); schedule(); for (const c of CAPS) { c.a = sched(c.a); c.b = sched(c.b); } for (const e of SFX) e.t = +sched(e.t).toFixed(3);
})();
const schemSVG = (design) => { const doc = new DOMParser().parseFromString(SCH[design], 'image/svg+xml'); const svg = document.importNode(doc.documentElement, true); svg.removeAttribute('width'); svg.removeAttribute('height'); svg.querySelector('metadata')?.remove(); return svg; };
const K1 = () => CASES.cases.find(c => c.id === '01'), K4 = () => CASES.cases.find(c => c.id === '04'), K5 = () => CASES.cases.find(c => c.id === '05');
const EXT = 'external_equivalent:changed:R1';
const plain = (id) => id === 'changed:R1' ? 'R1 itself changed' : id === EXT ? 'Extra resistance before R1' : expName(id);

// ---------- instruments at film scale
function workspace(root) {
  const W = {};
  W.strip = el('div', { class: 'strip' }, el('b', {}, 'Experiment 1'), el('span', { class: 'fc' }, '– – forecast from the drawing'), el('span', { class: 'out' }, '— output, measured'), el('span', { class: 'in' }, '— input, measured'));
  W.replay = el('div', { class: 'replay' }, 'REPLAY OF A REAL HARDWARE RUN');
  const sc = el('div', { class: 'scope' }); W.scope = new Scope(sc, { fill: true });
  W.metersEl = el('div', { class: 'meters' }); W.meters = {}; W.note = el('div', { class: 'note' });
  root.classList.add('ws'); root.append(W.strip, W.replay, sc, W.metersEl, W.note);
  W.meter = (fid, label, value) => { const m = new Meter(fid, label, { value }); W.metersEl.append(m.root); W.meters[fid] = m; m._mode = null; return m; };
  W.phase = null;
  W.showStep = (key, step, title, fcLabel) => { if (W.phase !== key) { W.phase = key; W.traces = stepTraces(step, { measuredProgress: 0 }); W.scope.set(stepTime(step), W.traces, title); const ids = W.traces.filter(x => x.kind === 'fc').map(x => x.id); W.strip.children[1].textContent = fcLabel || (ids.every(i => i === 'nominal') ? '– – forecast from the drawing' : ids.length === 1 ? `– – frozen forecast · ${plain(ids[0])}` : '– – frozen forecasts · one per explanation'); } return W.traces; };
  W.showCheck = (key, obs, fc, title, fcLabel) => { if (W.phase !== key) { W.phase = key; W.traces = []; for (const [fid, v] of Object.entries(fc || {})) W.traces.push({ id: fid, label: expName(fid) + ' forecast', kind: 'fc', v, dashed: true, progress: 1 }); W.traces.push({ id: 'in', label: 'IN', kind: 'in', v: obs.in_v, progress: 0 }, { id: 'out', label: 'OUT', kind: 'out', v: obs.out_v, progress: 0 }); W.scope.set(obs.t_s, W.traces, title); W.strip.children[1].textContent = fcLabel || '– – frozen forecast'; } return W.traces; };
  W.draw = (p, fcp) => { let k = 0; for (const tr of W.traces || []) { if (tr.kind === 'fc') { tr.progress = typeof fcp === 'function' ? fcp(k++) : (fcp ?? 1); } else if (tr.kind === 'in') tr.progress = p; else tr.progress = Math.max(0, p - .02); } W.scope.draw(); };
  return W;
}
// a meter's whole state from a descriptor, every frame (idempotent)
function setMeter(m, d) {
  const mode = d.mode || 'mv';
  if (m._mode !== mode) { if (mode === 'mv') m.face({ fs: 15, redFrom: 9, unit: 'mV', ticks: [0, 3, 6, 9, 12, 15], major: [0, 9, 15] }); m._mode = mode; }
  m.root.classList.remove('wait', 'bad', 'out', 'dead', 'band'); m.root.querySelector('.tag')?.remove();
  if (d.wait) { m.root.classList.add('wait'); m.setAngle(0); m.readout.firstChild.textContent = 'waiting'; m.readout.lastChild.textContent = ''; return; }
  m.setAngle(d.value); m.readout.firstChild.textContent = `${d.value.toFixed(2)} mV${d.value > 15 ? ' (off scale)' : ''}`; m.readout.lastChild.textContent = d.sub || '';
  if (d.fitted) m.name.lastChild.textContent = d.fitted;
  if (d.bad) m.root.classList.add('bad');
  if (d.tag) { m.root.classList.add('out'); const tg = el('span', { class: 'tape red tag' }, d.tag); m.root.append(tg); const s = d.tagIn ?? 1; tg.style.transform = `rotate(${-1.2 - 6 * (1 - s)}deg) scale(${.6 + .4 * s})`; tg.style.opacity = s; }
  if (d.dead) m.root.classList.add('dead');
  if (d.carry) { const tg = el('span', { class: 'tape grey tag' }, d.carry); m.root.append(tg); }
}

// ---------- shots
function buildAll() {
  const st4 = R4.steps, ver4 = R4.verification, pr4 = R4.structure[0], st1 = R1.steps, rd1 = R1.reading, ver1 = R1.verification;
  const bands = rd1.bands.filter(b => b.source === 'operator_dmm'); const bEXT = bands.find(b => b.explanation === EXT), bR1 = bands.find(b => b.explanation === 'changed:R1');
  let T = 0; const span = (d) => { const a = T; T += d; return [a, T]; };

  // S01 0–5  the bench photo, pushing in
  { const [a, b] = span(3); shot('s01', a, b, (r) => {
      r.append(el('div', { class: 'abs', id: 'ph', style: 'inset:0;overflow:hidden;background:#2a3338' }, el('img', { id: 'phimg', src: '../../examples/bench-photos/2026-11-04/full/camera-preview.png', style: 'position:absolute;left:50%;top:50%;width:1920px;transform-origin:center' }), el('div', { class: 'abs', style: 'inset:0;background:linear-gradient(180deg,rgba(0,0,0,.10),rgba(0,0,0,0) 35%,rgba(0,0,0,.30))' })),
        el('div', { class: 'abs', id: 'phlab', style: 'left:96px;top:940px' }, el('span', { class: 'tape2 white' }, 'The bench · a real $40 setup · 4 November 2026')));
    }, (r, t) => { const lt = t; const z = 1 + .08 * ease(lt, 0, 3); r.querySelector('#phimg').style.transform = `translate(-50%,-50%) translateY(${-120 + 40 * ease(lt, 0, 3)}px) scale(${z})`; r.querySelector('#phlab').style.opacity = ease(lt, .4, 1.0) * (1 - ease(lt, 2.3, 2.8)); }); }
  // S02 5–11  the three sentences
  { const [a, b] = span(7); shot('s02', a, b, (r) => {
      const L = ['The drawing is right.', 'The board looks right.', 'The output is wrong.'];
      const box = el('div', { class: 'abs', style: 'left:96px;top:340px' }); L.forEach((s, i) => box.append(el('div', { class: 'h1 ln' + (i === 2 ? ' wrong' : ''), style: 'font-size:112px;line-height:1.08;height:122px;position:relative;white-space:nowrap' + (i === 2 ? ';color:var(--fault-soft)' : '') }, el('span', { class: 't' }), i === 2 ? el('span', { class: 'ul', style: 'position:absolute;left:0;bottom:-4px;height:9px;background:var(--fault);width:0;border-radius:2px' }) : null, el('span', { class: 'caret', style: 'display:inline-block;width:6px;height:96px;background:#fff;vertical-align:-10px;margin-left:8px;opacity:0' }))));
      r.append(box, el('div', { class: 'abs cue', id: 'ask', style: 'left:96px;top:760px;font:500 48px/1.2 var(--narrow);color:rgba(255,255,255,.9)' }, 'What do you measure next, and where do you look?'));
      r._L = L; for (let k = 0; k < 3; k++) { sfx(a + [.4, 1.5, 2.5][k], 'type'); }
    }, (r, t) => { const L = r._L; const lns = r.querySelectorAll('.ln'); [[.4, .75], [1.5, .65], [2.5, .85]].forEach(([t0, d], i) => { const ln = lns[i]; typed(ln.querySelector('.t'), L[i], t, t0, d); const c = ln.querySelector('.caret'); const act = t >= t0 - .2 && t < t0 + d + .35; c.style.opacity = act ? ((Math.floor(t * 3) % 2) ? 1 : .25) : 0; }); lns[2].querySelector('.ul').style.width = (ease(t, 3.4, 3.9) * 100) + '%'; rise(r.querySelector('#ask'), t, 4.1); }); }
  // S04 16–22  the bench: three boards
  { const [a, b] = span(9.5); shot('s04', a, b, (r) => {
      const ph = el('div', { class: 'photo2 abs', style: 'left:1070px;top:96px;width:754px;height:850px' }, el('img', { src: '../../examples/bench-photos/2026-11-04/full/camera-preview.png', style: 'position:absolute;inset:0;width:100%;height:100%;object-fit:cover' }));
      [['66%', '31%'], ['85%', '56.5%'], ['37%', '89%']].forEach(([x, y], i) => { const p = el('span', { class: 'pin' }, String(i + 1)); p.style.left = x; p.style.top = y; ph.append(p); });
      r.append(ph, el('div', { class: 'abs cue', id: 'hd', style: 'left:96px;top:96px;width:900px' }, el('div', { class: 'eyebrow' }, 'The bench'), el('div', { class: 'h2', style: 'margin-top:14px' }, 'One Arduino. One instrument board.', el('br'), 'One mini board with the circuit from the drawing.')),
        el('div', { class: 'rows abs', style: 'left:96px;top:420px;width:900px' },
          el('div', { class: 'row cue' }, el('i', {}, '1'), el('div', {}, el('b', {}, 'Arduino UNO R4'), el('span', {}, 'runs each experiment and records the answer'))),
          el('div', { class: 'row cue' }, el('i', {}, '2'), el('div', {}, el('b', {}, 'Instrument board'), el('span', {}, 'keeps the signal clean, holds the one jumper an operator moves'))),
          el('div', { class: 'row cue' }, el('i', {}, '3'), el('div', {}, el('b', {}, 'Mini board under test'), el('span', {}, 'the circuit the drawing shows, plus one sealed fault')))));
      cap(a + .8, b, 'About $40 of parts. The model never touches it.');
    }, (r, t) => { rise(r.querySelector('#hd'), t, .2); r.querySelectorAll('.row').forEach((row, k) => rise(row, t, 1.2 + k * .7)); r.querySelectorAll('.pin').forEach((p, k) => { const x = clamp((t - (1.4 + k * .7)) / .45); p.style.transform = `translate(-50%,-50%) scale(${x <= 0 ? 0 : back(x)})`; }); }); }
  // S05 22–28  Spark, and the seal
  { const [a, b] = span(8.5); shot('s05', a, b, (r) => {
      r.append(el('div', { class: 'abs cue', id: 'sp', style: 'left:96px;top:160px;width:1080px' }, el('div', { class: 'speaker spark', style: 'font-size:30px;color:#fff' }, el('i'), 'Meta’s Muse Spark 1.3 · Meta Model API'),
          el('div', { class: 'h2', style: 'margin-top:26px' }, 'Reads the schematic.', el('br'), 'Chooses its own experiments from a fixed menu.', el('br'), 'Says why.'),
          el('div', { class: 'body dim', style: 'margin-top:30px;font-size:30px' }, 'Before each measurement, its forecast is frozen and hashed. The engine scores; Spark decides what to test next.')),
        el('div', { class: 'abs', id: 'sealbox', style: 'left:1240px;top:200px;width:584px' }, el('div', { class: 'photo2' }, el('img', { src: '../../site/assets/photos/case04-faulted-crop.jpg', style: 'width:100%' })), el('div', { class: 'abs', id: 'seal', style: 'left:40px;top:240px;width:470px;transform:rotate(-7deg) scale(0);transform-origin:center;border:4px solid var(--fault);color:var(--fault);font:700 44px/1.1 var(--narrow);padding:16px 22px;border-radius:8px;letter-spacing:.06em;background:rgba(255,255,255,.92);text-transform:uppercase;box-shadow:0 8px 24px rgba(0,0,0,.35)' }, 'Sealed', el('small', { style: 'display:block;font:500 18px/1.3 var(--mono);letter-spacing:0;text-transform:none;color:#8a2a24;margin-top:6px' }, 'sha256 of the assembly, committed before the first measurement'))));
      cap(a + 4.5, b, 'The fault was planted by us, hashed, and sealed. Spark never sees it.'); sfx(a + 4.7, 'seal');
    }, (r, t) => { rise(r.querySelector('#sp'), t, .2); fade(r.querySelector('#sealbox'), t, 1.4); const s = clamp((t - 4.7) / .35); const se = r.querySelector('#seal'); se.style.transform = `rotate(-7deg) scale(${s <= 0 ? 0 : .9 + .1 * back(s)})`; se.style.opacity = s <= 0 ? 0 : 1; }); }

  // ===== Case 04 =====
  // S06 28–33  case title
  { const [a, b] = span(4); shot('s06', a, b, (r) => {
      const k = K4(); r.append(el('div', { class: 'abs cue', id: 'tt', style: 'left:96px;top:120px;width:860px' }, el('div', { class: 'eyebrow' }, `Case 04 · ${k.source.site} · ${k.source.date_label || ''}`), el('div', { class: 'h1', style: 'margin-top:18px' }, k.title), el('div', { class: 'body dim', style: 'margin-top:26px;font-size:32px' }, k.symptom)),
        el('div', { class: 'paper2 abs cue', id: 'sch', style: 'left:1000px;top:150px;width:824px;padding:26px 30px' }, el('div', { class: 'eyebrow' }, 'The drawing Spark read'), (() => { const s = schemSVG(k.design); s.style.width = '100%'; s.style.marginTop = '12px'; return s; })()),
        el('div', { class: 'abs cue', id: 'rp', style: 'left:96px;top:820px' }, el('span', { class: 'tape2 white' }, `Replay of a real hardware run · recorded ${kstDate(R4.started_utc)}`)));
    }, (r, t) => { rise(r.querySelector('#tt'), t, .2); rise(r.querySelector('#sch'), t, .9); rise(r.querySelector('#rp'), t, 2.0); }); }
  // S07 33–43  experiments 1 and 2: everything still fits
  { const [a, b] = span(9); shot('s07', a, b, (r, s) => {
      const W = workspace(r); s.W = W; for (const f of st4[0].fit) W.meter(f.id, expName(f.id), f.value != null ? BM.fmtFit(f.kind, f.value, f.at_bound) : 'drawn values');
      W.note.append(el('b', { id: 'n1' }, ''), ' ', el('span', { class: 'dim', id: 'n2' }, ''));
      cap(a + .5, a + 4.4, 'Experiment 1, Spark’s pick: the forecast frozen, then the bench measures'); cap(a + 4.8, b, 'Two small steps. Every explanation in the drawing still fits.');
      sfx(a + .7, 'forecast'); sfx(a + 1.8, 'sweep'); sfx(a + 4.9, 'forecast'); sfx(a + 5.8, 'sweep');
    }, (r, t, s) => { const W = s.W; const st = st4;
      if (t < 4.6) { W.showStep('s1', st[0], st[0].label); W.strip.firstChild.textContent = 'Experiment 1'; W.draw(lin(t, 1.8, 3.6), (k) => ease(t, .5 + k * .12, 1.5 + k * .12)); r.querySelector('#n1').textContent = `“${q(st[0].reason)}”`; r.querySelector('#n2').textContent = `— Muse Spark, choosing ${st[0].label}`; }
      else { W.showStep('s2', st[1], st[1].label); W.strip.firstChild.textContent = 'Experiment 2'; W.draw(lin(t, 5.8, 7.4), (k) => ease(t, 4.8 + k * .12, 5.6 + k * .12)); r.querySelector('#n1').textContent = `“${q(st[1].reason)}”`; r.querySelector('#n2').textContent = `— Muse Spark, choosing ${st[1].label}`; }
      for (const f of st[0].fit) { const m = W.meters[f.id]; const k = t < 4.6 ? 0 : 1; const ff = st[k].fit.find(x => x.id === f.id); const u = t < 4.6 ? ease(t, 3.6, 4.4) : ease(t, 7.4, 8.2); const prev = k === 1 ? missOf(f, 0) : 0; const v = k === 1 ? prev + (missOf(ff, 1) - prev) * u : missOf(ff, 0) * u; setMeter(m, u <= 0 && k === 0 ? { wait: true } : { value: v, sub: `step ${k + 1} · fits`, fitted: ff.value != null ? BM.fmtFit(ff.kind, ff.value, ff.at_bound) : 'drawn values' }); }
    }); }
  // S09 47–57  the large sine: every needle in the red
  { const [a, b] = span(8); shot('s09', a, b, (r, s) => {
      const W = workspace(r); s.W = W; for (const f of st4[2].fit) W.meter(f.id, expName(f.id), f.value != null ? BM.fmtFit(f.kind, f.value, f.at_bound) : 'drawn values');
      const big = el('div', { class: 'abs', id: 'bigwrap', style: 'inset:0;opacity:0' }, el('div', { class: 'abs', style: 'left:96px;top:130px' }, el('div', { class: 'eyebrow' }, 'Experiment 3 · scored'), el('div', { class: 'h1', id: 'bigh', style: 'margin-top:14px' }, 'All three explanations failed.')), el('div', { class: 'meters-big', id: 'mbig' }), el('div', { class: 'abs', id: 'bign', style: 'left:96px;top:840px;font:400 32px/1.35 var(--sans);color:rgba(255,255,255,.85)' }));
      r.append(big); s.big = big; s.bigMeters = {}; for (const f of st4[2].fit) { const m = new Meter(f.id + ':big', expName(f.id), { value: f.value != null ? BM.fmtFit(f.kind, f.value, f.at_bound) : 'drawn values' }); m._mode = null; big.querySelector('#mbig').append(m.root); s.bigMeters[f.id] = m; }
      big.querySelector('#bign').append(`${st4[2].fit.map(f => `${expName(f.id)} ${fmtMiss(missOf(f, 2))}`).join(' · ')} — the worst region of the sweep, against ${R4.allowance_mV} mV allowed.`);
      cap(a + .3, a + 2.6, 'Experiment 3: the bench measures the large sine'); cap(a + 4.2, b, `${st4[2].fit.map(f => fmtMiss(missOf(f, 2))).join(' · ')} against ${R4.allowance_mV} mV: every value explanation fails`);
      sfx(a + .3, 'sweep'); sfx(a + 3.4, 'needle_red'); sfx(a + 3.65, 'needle_red'); sfx(a + 3.9, 'needle_red'); sfx(a + 4.5, 'crossout');
    }, (r, t, s) => { const W = s.W; const st = st4[2];
      W.showStep('s3', st, st.label); W.strip.firstChild.textContent = 'Experiment 3'; W.draw(lin(t, .3, 2.3), 1);
      for (const f of st.fit) setMeter(W.meters[f.id], { value: missOf(f, 1), sub: 'step 2 · fits', fitted: f.value != null ? BM.fmtFit(f.kind, f.value, f.at_bound) : 'drawn values' });
      // cut to the big meters at 4.6 s: needles rise 5.0 → 6.4, tapes at 6.8
      const on = ease(t, 2.5, 2.9); s.big.style.opacity = on; [...r.children].forEach(c => { if (c !== s.big) c.style.opacity = 1 - on; });
      r.querySelector('#bigh').style.opacity = ease(t, 4.2, 4.6);
      for (const f of st.fit) { const m = s.bigMeters[f.id]; const u = ease(t, 3.0, 4.0); setMeter(m, u <= 0 ? { value: missOf(f, 1), sub: 'step 2 · fits' } : { value: missOf(f, 1) + (missOf(f, 2) - missOf(f, 1)) * u, bad: u > .45, sub: 'step 3 · worst region', tag: t >= 4.4 ? 'Ruled out after step 3' : null, tagIn: ease(t, 4.4, 4.85) }); }
    }); }
  // S10 57–65  the proposal
  { const [a, b] = span(6.5); shot('s10', a, b, (r) => {
      const added = (pr4.diff?.added || []).map(x => x.name); const svg = netlistSVG(pr4.elements, { highlight: added });
      r.append(el('div', { class: 'paper2 abs cue', id: 'nl', style: 'left:96px;top:150px;width:960px;padding:30px 34px' }, el('div', { class: 'eyebrow' }, 'The netlist Spark wrote'), el('div', { style: 'margin-top:14px' }, svg)),
        el('div', { class: 'abs cue', id: 'tx', style: 'left:1110px;top:150px;width:714px' }, el('div', { class: 'speaker spark', style: 'color:#fff' }, el('i'), 'Muse Spark 1.3', el('span', { class: 'ts', style: 'margin-left:auto;color:rgba(255,255,255,.6)' }, kst(pr4.ev?.ts))), el('div', { class: 'h2', style: 'margin-top:22px;font-size:50px' }, 'A part the drawing does not show.'), el('p', { class: 'quote white', style: 'margin-top:26px;font-size:38px' }, q(pr4.rationale)),
          el('div', { class: 'cue', id: 'diff', style: 'margin-top:34px' }, el('div', { class: 'chip2', style: 'border-color:var(--fault);color:#ffd1cd;font-size:32px' }, `+ ${pr4.diff.added[0].name} · ${BM.kindWord(pr4.diff.added[0].kind)} · ${pr4.diff.added[0].a} → ${pr4.diff.added[0].b}`), el('div', { class: 'small dim', style: 'margin-top:16px' }, 'A hypothesis, written as a circuit. The engine fits it like any other explanation, then freezes it.'))));
      r._svg = svg; const hl = [...svg.querySelectorAll('[stroke="#d5342c"],[fill="#d5342c"],[stroke="var(--fault)"]')]; r._hl = hl.length ? hl : [...svg.querySelectorAll('*')].filter(e => (e.getAttribute('stroke') || '').toLowerCase().includes('d5342c') || (e.getAttribute('fill') || '').toLowerCase().includes('d5342c'));
      cap(a + .8, b, 'Spark writes a new netlist: a diode from OUT to REF, which the drawing never had'); sfx(a + .2, 'card'); sfx(a + 2.2, 'forecast');
    }, (r, t) => { rise(r.querySelector('#nl'), t, .1); rise(r.querySelector('#tx'), t, .5); rise(r.querySelector('#diff'), t, 2.6); const e = ease(t, 2.0, 2.9); for (const h of r._hl) h.style.opacity = e; }); }
  // S12 69–78  the held-back checks against the frozen model
  { const [a, b] = span(8); shot('s12', a, b, (r, s) => {
      const W = workspace(r); s.W = W; const m = W.meter('proposal:1', BM.proposalName(pr4), 'frozen'); s.m = m; W.strip.children[1].textContent = '– – frozen forecast · proposed circuit';
      W.note.append(el('b', {}, 'Frozen-model check · measured IN. '), el('span', { class: 'dim' }, `Forecast frozen and pushed to GitHub (commit ${String(ver4.commit || '').slice(0, 7)}) before these inputs were measured; nothing is refitted, the frozen model is driven by the measured input and compared.`));
      const sc = ver4.scored; s.dec = sc.map(x => Object.values(x.conditional)[0]);
      cap(a + .4, a + 3.9, 'Held-back input 1: a step Spark never used, against the frozen forecast'); cap(a + 4.2, b, 'Held-back input 2: a sine Spark never used, against the frozen forecast');
      sfx(a + .5, 'sweep'); sfx(a + 3.2, 'pass'); sfx(a + 4.4, 'sweep'); sfx(a + 7.2, 'pass');
    }, (r, t, s) => { const W = s.W; const d = s.dec; const sc = ver4.scored;
      if (t < 4.0) { W.showCheck('v1', ver4.observations[0], ver4.forecasts[0], `Held-back input 1 · ${sc[0].settings.kind} ${sc[0].settings.amplitude_v} V`, '– – frozen forecast · proposed circuit'); W.strip.firstChild.textContent = 'Held-back check 1'; W.draw(lin(t, .5, 2.8), 1); setMeter(s.m, ease(t, 2.9, 3.7) <= 0 ? { wait: true } : { value: d[0].decided_mV * ease(t, 2.9, 3.7), sub: 'check 1 · worst region' }); }
      else { W.showCheck('v2', ver4.observations[1], ver4.forecasts[1], `Held-back input 2 · ${sc[1].settings.kind} ${sc[1].settings.amplitude_v} V ${sc[1].settings.frequency_hz || ''} Hz`, '– – frozen forecast · proposed circuit'); W.strip.firstChild.textContent = 'Held-back check 2'; W.draw(lin(t, 4.4, 6.8), 1); const u = ease(t, 6.9, 7.6); setMeter(s.m, { value: d[0].decided_mV + (d[1].decided_mV - d[0].decided_mV) * u, sub: u > 0 ? 'check 2 · worst region' : 'check 1 · worst region' }); }
    }); }
  // S13 78–83  the two numbers
  { const [a, b] = span(4); shot('s13', a, b, (r) => {
      const sc = ver4.scored; const d = sc.map(x => Object.values(x.conditional)[0]);
      const num = (v, lab) => el('div', { class: 'cue' }, el('div', { style: 'font:600 150px/1 var(--narrow);color:#6fe39a;letter-spacing:-.02em' }, fmtMiss(v)), el('div', { class: 'small dim', style: 'margin-top:14px;font-size:26px' }, lab));
      r.append(el('div', { class: 'abs', style: 'left:96px;top:160px' }, el('div', { class: 'eyebrow' }, 'Worst region of each held-back sweep'), el('div', { class: 'h2', style: 'margin-top:14px' }, 'Both within the allowance, in every region.')),
        el('div', { class: 'abs', id: 'nums', style: 'left:96px;top:400px;display:flex;gap:120px;align-items:flex-end' }, num(d[0].decided_mV, `held-back 1 · ${sc[0].settings.kind} ${sc[0].settings.amplitude_v} V`), num(d[1].decided_mV, `held-back 2 · ${sc[1].settings.kind} ${sc[1].settings.amplitude_v} V`), el('div', { class: 'cue' }, el('div', { style: 'font:600 150px/1 var(--narrow);color:#fff;letter-spacing:-.02em' }, `${R4.allowance_mV} mV`), el('div', { class: 'small dim', style: 'margin-top:14px;font-size:26px' }, 'the allowance, frozen before the first run'))),
        el('div', { class: 'abs', id: 'bar', style: 'left:96px;top:760px;width:1728px;height:14px;background:rgba(255,255,255,.18);border-radius:7px' }, el('div', { style: 'position:absolute;left:0;top:0;height:14px;width:100%;background:linear-gradient(90deg,rgba(111,227,154,.9) 0%,rgba(111,227,154,.9) 60%,rgba(213,52,44,.9) 60.1%,rgba(213,52,44,.9) 100%);border-radius:7px' }), ...d.map((x, i) => el('div', { class: 'cue mk', style: `position:absolute;left:${(x.decided_mV / 15) * 100}%;top:-14px;width:4px;height:42px;background:#fff;transform:translateX(-50%)` })), el('div', { style: 'position:absolute;left:60%;top:-46px;transform:translateX(-50%);font:600 24px/1 var(--narrow);color:#fff' }, `${R4.allowance_mV} mV`), el('div', { style: 'position:absolute;left:0;top:26px;font:500 22px/1 var(--narrow);color:rgba(255,255,255,.6)' }, '0'), el('div', { style: 'position:absolute;right:0;top:26px;font:500 22px/1 var(--narrow);color:rgba(255,255,255,.6)' }, '15 mV')));
      cap(a + .4, b, `Worst regions ${d.map(x => fmtMiss(x.decided_mV)).join(' and ')}, under the ${R4.allowance_mV} mV allowed`); sfx(a + .4, 'pass'); sfx(a + 1.0, 'pass');
    }, (r, t) => { [...r.querySelectorAll('#nums > .cue')].forEach((n, k) => rise(n, t, .2 + k * .45)); r.querySelectorAll('.mk').forEach((m, k) => fade(m, t, 1.5 + k * .4)); }); }
  // S14 83–91  the verdict
  { const [a, b] = span(6.5); shot('s14', a, b, (r) => {
      r.append(el('div', { class: 'vcard cue', id: 'vc', style: 'top:170px' }, el('div', { class: 'lab' }, 'BenchMate’s diagnosis · from the engine’s report'), el('div', { class: 'big' }, verdictWords(R4.outcome, R4)),
        el('div', { class: 'cue', id: 'pl' }, el('div', { class: 'sep' }), el('div', { class: 'lab' }, 'What was planted · the seal, opened only now'), el('div', { class: 'big2' }, K4().hidden)),
        el('div', { class: 'fine cue', id: 'fn' }, 'The connection Spark wrote; the part number is the seal’s. The verdict is copied from the engine’s report; the seal’s digest is checked by code against the one committed before the first measurement. Spark never saw the lower line.')));
      cap(a + .6, a + 1.8, 'Spark’s answer, from the record'); cap(a + 1.8, b, 'The seal opens: a diode, in the direction Spark wrote'); sfx(a + 1.5, 'seal');
    }, (r, t) => { rise(r.querySelector('#vc'), t, .1); rise(r.querySelector('#pl'), t, 1.6); fade(r.querySelector('#fn'), t, 3.0); }); }

  // ===== Case 01 =====
  // S15 91–95  case title
  { const [a, b] = span(3); shot('s15', a, b, (r) => {
      const k = K1(); r.append(el('div', { class: 'abs cue', id: 'tt', style: 'left:96px;top:120px;width:860px' }, el('div', { class: 'eyebrow' }, `Case 01 · ${k.source.site} · ${(k.source.date || '').slice(0, 7)}`), el('div', { class: 'h1', style: 'margin-top:18px' }, k.title), el('div', { class: 'body dim', style: 'margin-top:26px;font-size:32px' }, k.symptom)),
        el('div', { class: 'paper2 abs cue', id: 'sch', style: 'left:1000px;top:150px;width:824px;padding:26px 30px' }, el('div', { class: 'eyebrow' }, 'The drawing Spark read'), (() => { const s = schemSVG(k.design); s.style.width = '100%'; s.style.marginTop = '12px'; return s; })()),
        el('div', { class: 'abs cue', id: 'rp', style: 'left:96px;top:820px' }, el('span', { class: 'tape2 white' }, `Replay of a real hardware run · recorded ${kstDate(R1.started_utc)}`)));
    }, (r, t) => { rise(r.querySelector('#tt'), t, .2); rise(r.querySelector('#sch'), t, .7); rise(r.querySelector('#rp'), t, 1.6); }); }
  // S16 95–104  experiment 1: two explanations crossed out
  { const [a, b] = span(7.5); shot('s16', a, b, (r, s) => {
      const W = workspace(r); s.W = W; for (const f of st1[0].fit) W.meter(f.id, expName(f.id), f.value != null ? BM.fmtFit(f.kind, f.value, f.at_bound) : 'drawn values');
      W.note.append(el('b', {}, `“${q(st1[0].reason)}”`), ' ', el('span', { class: 'dim' }, `— Muse Spark, choosing ${st1[0].label}`));
      const m1 = missOf(st1[0].fit.find(f => f.id === 'nominal'));
      cap(a + .5, a + 4.0, 'Experiment 1: the forecast frozen, then the bench measures'); cap(a + 4.6, b, `${m1.toFixed(2)} mV against an allowance of ${R1.allowance_mV} mV: two explanations crossed out`);
      sfx(a + .7, 'forecast'); sfx(a + 1.8, 'sweep'); sfx(a + 4.6, 'needle_red'); sfx(a + 4.9, 'needle_red'); sfx(a + 5.5, 'crossout');
    }, (r, t, s) => { const W = s.W; const st = st1[0]; W.showStep('s1', st, st.label); W.strip.firstChild.textContent = 'Experiment 1'; W.draw(lin(t, 1.8, 4.0), (k) => ease(t, .5 + k * .15, 1.6 + k * .15));
      for (const f of st.fit) { const out = f.status === 'inadequate'; const u = ease(t, 4.1, 5.2); setMeter(W.meters[f.id], u <= 0 ? { wait: true } : { value: missOf(f, 0) * u, bad: out && u > .55, sub: 'step 1 · worst region', tag: out && t >= 5.5 ? 'Ruled out after step 1' : null, tagIn: ease(t, 5.5, 5.95) }); }
    }); }
  // S18 108–114  two explanations, one waveform
  { const [a, b] = span(5); shot('s18', a, b, (r, s) => {
      const W = workspace(r); s.W = W; W.metersEl.remove(); W.note.remove();
      const sc = el('div', { class: 'scope' }); sc.style.left = '96px'; sc.style.width = '1728px'; r.querySelector('.scope').replaceWith(sc); W.scope = new Scope(sc, { fill: true });
      r.append(el('div', { class: 'abs cue', id: 'two', style: 'left:96px;top:790px;width:1728px;display:flex;gap:40px;align-items:center' }, el('span', { class: 'chip2', style: 'font-size:32px;border-color:#c6a9ff;color:#c6a9ff' }, el('i'), plain('changed:R1')), el('span', { style: 'font:600 36px/1 var(--narrow);color:rgba(255,255,255,.6)' }, '='), el('span', { class: 'chip2', style: 'font-size:32px;border-color:#c6a9ff;color:#c6a9ff' }, el('i', { style: 'border-top-style:dotted' }), plain(EXT)), el('span', { class: 'small dim', style: 'margin-left:auto;max-width:700px;text-align:right' }, 'An engine rule: the same waveforms at the terminals. No experiment on the menu can separate them.')));
      cap(a + .6, b, 'Two explanations draw the same waveform. No experiment on the menu separates them.'); sfx(a + .4, 'sweep');
    }, (r, t, s) => { const W = s.W; const obs = ver1.observations[1], fc = ver1.forecasts[1].changed_R1 || Object.values(ver1.forecasts[1])[0];
      if (W.phase !== 'eq') { W.phase = 'eq'; W.traces = [{ id: 'a', label: plain('changed:R1') + ' forecast', kind: 'fc', v: fc, dashed: true, progress: 1, color: '#c6a9ff' }, { id: 'b', label: plain(EXT) + ' forecast', kind: 'fc', v: fc.map(x => x), dashed: true, progress: 1, color: '#e9dcff' }, { id: 'in', label: 'IN', kind: 'in', v: obs.in_v, progress: 0 }, { id: 'out', label: 'OUT', kind: 'out', v: obs.out_v, progress: 0 }]; W.scope.set(obs.t_s, W.traces, `Held-back input 2 · sine ${ver1.reserved[1].amplitude_v} V`); W.strip.children[1].textContent = '– – two forecasts, identical'; }
      W.strip.firstChild.textContent = 'After three experiments'; W.traces[0].progress = ease(t, .3, 1.3); W.traces[1].progress = ease(t, .9, 1.9); const p = lin(t, 2.1, 4.0); W.traces[2].progress = p; W.traces[3].progress = Math.max(0, p - .02); W.scope.draw(); rise(r.querySelector('#two'), t, .1);
    }); }
  // S19 114–121  Spark asks for one reading; the ranges are frozen
  { const [a, b] = span(6); shot('s19', a, b, (r) => {
      const lo = 0, hi = 30; const pct = (x) => `${((x - lo) / (hi - lo)) * 100}%`;
      const range = (id, lab, bnd, cls) => el('div', { class: 'range cue', id }, el('div', { class: 'lab' }, lab), el('div', { class: 'track' }), el('div', { class: `band ${cls}`, style: `left:${pct(bnd.low)};width:calc(${pct(bnd.high)} - ${pct(bnd.low)})` }), el('div', { class: 'val', style: `left:${pct(bnd.low)}` }, `${bnd.low}–${bnd.high} ${bnd.unit}`));
      r.append(el('div', { class: 'paper2 abs cue', id: 'ask', style: 'left:96px;top:120px;width:1728px;padding:40px 52px 36px' }, el('div', { class: 'speaker spark' }, el('i'), 'Muse Spark 1.3 · asked for one reading', el('span', { class: 'ts', style: 'margin-left:auto' }, kst(rd1.request_ev?.ts || rd1.frozen_ev?.ts))), el('div', { class: 'h2', style: 'margin:22px 0 10px' }, `Read ${rd1.component}, out of circuit, with a multimeter.`), el('p', { class: 'quote', style: 'font-size:34px' }, q(rd1.reason).split('; ')[0] + '.'),
        el('div', { class: 'eyebrow', style: 'margin-top:44px' }, 'Frozen before anyone touches the meter · the range each explanation allows'), el('div', { style: 'margin-top:60px;padding:0 10px' }, range('r1', plain('changed:R1'), bR1, ''), range('r2', plain(EXT), bEXT, '')), el('div', { style: 'position:relative;height:30px;margin-top:-20px;padding:0 10px' }, el('span', { class: 'ts' }, '0'), el('span', { class: 'ts', style: 'position:absolute;right:10px' }, `${hi} kΩ`))));
      cap(a + .6, a + 2.8, 'Spark asks for one multimeter reading of R1'); cap(a + 3.1, b, 'The range each explanation allows is frozen first, and pushed to GitHub'); sfx(a + .2, 'card'); sfx(a + 3.0, 'commit');
    }, (r, t) => { rise(r.querySelector('#ask'), t, .1); rise(r.querySelector('#r1'), t, 3.0); rise(r.querySelector('#r2'), t, 3.5); }); }
  // S20 121–127  the photo, SAM's outline, Spark points
  { const [a, b] = span(5); shot('s20', a, b, (r) => {
      r.append(el('div', { class: 'photo2 abs cue', id: 'ph', style: 'left:96px;top:96px;width:1060px' }, el('img', { src: '../../site/' + rd1.binding.photo }), el('img', { class: 'mask', id: 'mask', src: '../../site/' + rd1.binding.overlay_file })),
        el('div', { class: 'abs cue', id: 'tx', style: 'left:1220px;top:120px;width:604px' }, el('div', { class: 'speaker spark', style: 'color:#fff' }, el('i'), 'Muse Spark 1.3 vision · with SAM 3.1'), el('div', { class: 'h2', style: 'margin-top:22px' }, `Points at the body that is ${rd1.binding.component}.`), el('p', { class: 'quote white', style: 'margin-top:26px;font-size:32px' }, q(rd1.binding.reason)), el('div', { class: 'small dim', style: 'margin-top:26px' }, `SAM 3.1 segmented the board with one generic prompt; its native mask is the only outline. ${rd1.binding.operator_confirmed ? 'Confirmed by the operator.' : ''} No value is read from the photo.`)));
      cap(a + .6, b, `Spark points at the body that is ${rd1.binding.component}: the yellow outline is SAM 3.1’s`); sfx(a + 1.6, 'forecast');
    }, (r, t) => { rise(r.querySelector('#ph'), t, .1); fade(r.querySelector('#mask'), t, 1.4, .8); rise(r.querySelector('#tx'), t, .5); }); }
  // S21 127–134  the reading decides
  { const [a, b] = span(5.5); shot('s21', a, b, (r) => {
      const lo = 0, hi = 30; const pct = (x) => ((x - lo) / (hi - lo)) * 100;
      const range = (id, lab, bnd) => el('div', { class: 'range', id }, el('div', { class: 'lab' }, lab), el('div', { class: 'track' }), el('div', { class: 'band', style: `left:${pct(bnd.low)}%;width:${pct(bnd.high) - pct(bnd.low)}%` }), el('div', { class: 'val', style: `left:${pct(bnd.low)}%` }, `${bnd.low}–${bnd.high} ${bnd.unit}`), el('div', { class: 'strike' }));
      r.append(el('div', { class: 'paper2 abs', style: 'left:96px;top:120px;width:1728px;padding:40px 52px 36px' }, el('div', { class: 'speaker bench' }, el('i'), 'Operator · one multimeter reading', el('span', { class: 'ts', style: 'margin-left:auto' }, kst(rd1.observed?.ev?.ts || rd1.scored?.ev?.ts))), el('div', { class: 'h2', style: 'margin:22px 0 0' }, `${rd1.component}, power off, both leads lifted:`),
        el('div', { id: 'typed', style: 'font:600 150px/1 var(--narrow);color:var(--ink);margin:14px 0 30px;letter-spacing:-.02em;min-height:160px' }, el('span', { class: 'v' }), el('span', { class: 'cr', style: 'display:inline-block;width:6px;height:120px;background:var(--ink);vertical-align:-10px;margin-left:10px' })),
        el('div', { style: 'position:relative;padding:0 10px' }, range('r1', plain('changed:R1'), bR1), range('r2', plain(EXT), bEXT), el('div', { class: 'marker cue', id: 'mk', style: `left:calc(${pct(rd1.observed.value)}% + 10px);top:-6px;height:190px;position:absolute;width:4px;background:var(--ink);border-radius:2px;transform:translateX(-50%)` }, el('b', { style: 'position:absolute;left:50%;top:196px;transform:translateX(-50%);white-space:nowrap;font:600 32px/1 var(--narrow);color:var(--ink)' }, `${rd1.observed.value} ${rd1.observed.unit}`)))));
      cap(a + .5, a + 2.8, `The operator reads ${rd1.observed.value} ${rd1.observed.unit}`); cap(a + 3.1, b, `Inside one frozen range, outside the other: one explanation left`); sfx(a + .6, 'type'); sfx(a + 1.1, 'type'); sfx(a + 2.4, 'pass'); sfx(a + 3.4, 'crossout');
    }, (r, t) => { const s = `${rd1.observed.value} ${rd1.observed.unit}`; typed(r.querySelector('#typed .v'), s, t, .6, 1.2); r.querySelector('#typed .cr').style.opacity = t < 2.2 ? ((Math.floor(t * 3) % 2) ? 1 : .2) : 0; fade(r.querySelector('#mk'), t, 2.3, .5); r.querySelector('#r1 .strike').style.transform = `scaleX(${ease(t, 3.4, 4.1)})`; r.querySelector('#r1').style.opacity = 1 - .45 * ease(t, 3.4, 4.1); }); }
  // S22 134–141  the verdict
  { const [a, b] = span(6); shot('s22', a, b, (r) => {
      r.append(el('div', { class: 'vcard cue', id: 'vc', style: 'top:170px' }, el('div', { class: 'lab' }, 'BenchMate’s diagnosis · from the engine’s report'), el('div', { class: 'big' }, verdictWords(R1.outcome, R1)),
        el('div', { class: 'cue', id: 'pl' }, el('div', { class: 'sep' }), el('div', { class: 'lab' }, 'What was planted · the seal, opened only now'), el('div', { class: 'big2' }, K1().hidden)),
        el('div', { class: 'fine cue', id: 'fn' }, 'The verdict is copied from the engine’s report; the seal’s digest is checked by code against the one committed before the first measurement. Spark never saw the lower line.')));
      cap(a + .5, a + 1.2, 'Spark’s answer, from the record'); cap(a + 1.4, b, 'The seal opens: two resistors, hidden before R1'); sfx(a + 1.1, 'seal');
    }, (r, t) => { rise(r.querySelector('#vc'), t, .1); rise(r.querySelector('#pl'), t, 1.2); fade(r.querySelector('#fn'), t, 2.6); }); }
  // S23 141–145  the restored rerun
  { const [a, b] = span(3); shot('s23', a, b, (r) => {
      r.append(el('div', { class: 'vcard quiet cue', id: 'vc', style: 'top:400px' }, el('div', { class: 'lab' }, 'Repaired, then run again by a fresh Spark'), el('div', { class: 'big' }, verdictWords(R1R.outcome, R1R)), el('div', { class: 'fine' }, 'This says nothing about tests Spark did not run. On a restored board it is the expected result.')));
      cap(a + .5, b, 'Repaired, then run again by a fresh Spark: no mismatch in the tests it chose'); sfx(a + .2, 'card');
    }, (r, t) => { rise(r.querySelector('#vc'), t, .1); }); }

  // ===== the rest =====
  // S24 145–153  five cases
  { const [a, b] = span(15); shot('s24', a, b, (r) => {
      const counted = (INDEX.runs || []).filter(x => x.counted);
      const found = (x) => x.verdict === 'structure_supported' ? 'proposed a part the drawing does not show; held-back checks passed' : x.reading === 'group' ? 'one explanation left after two multimeter readings' : x.reading === 'one' ? 'one explanation left after one multimeter reading' : 'one explanation left after the tests';
      const list = el('div', { class: 'paper2 abs cue', id: 'list5', style: 'left:96px;top:90px;width:1060px;padding:28px 40px 12px' }, el('div', { class: 'h3', style: 'margin-bottom:10px' }, 'Five cases from real forum threads'));
      CASES.cases.forEach(c => { const f = counted.find(x => x.case === c.id && x.state === 'faulted'); list.append(el('div', { class: 'cue crow', style: 'display:grid;grid-template-columns:60px minmax(0,1fr);gap:0 20px;padding:11px 0;border-top:1px solid var(--rule)' }, el('div', { style: 'font:600 28px/1 var(--narrow);color:var(--ink-3)' }, c.id), el('div', {}, el('div', { style: 'font:600 28px/1.15 var(--narrow)' }, c.title), el('div', { class: 'small dim', style: 'margin-top:3px;font-size:21px' }, `Found it: ${found(f)}; the seal matched. ○ Fixed, then rerun: no mismatch.`)))); });
      const p5 = R5.structure[0]; r.append(list, el('div', { class: 'abs cue', id: 'm5', style: 'left:1200px;top:96px;width:624px' }, el('div', { class: 'photo2' }, el('img', { src: '../../site/' + R5.reading.binding.photo }), el('img', { class: 'mask', src: '../../site/' + R5.reading.binding.overlay_file })), el('div', { style: 'margin-top:22px' }, el('div', { class: 'h3' }, 'Case 05 · it happened twice'), el('div', { class: 'small dim', style: 'margin-top:8px' }, `Spark proposed ${BM.kindWord(p5.diff.added[0].kind)} where the drawing shows a wire; one reading of the isolated wire path placed it off the board. Sealed: ${K5().hidden}`))));
      cap(a + .6, a + 2.4, 'Five cases, five sealed faults; each ended with a repaired board and a rerun that reported no mismatch'); cap(a + 2.8, b, 'Case 05: resistance proposed where the drawing shows a wire; one reading placed it off the board'); sfx(a + .2, 'card'); sfx(a + 2.6, 'card');
    }, (r, t) => { rise(r.querySelector('#list5'), t, .1); r.querySelectorAll('.crow').forEach((row, k) => rise(row, t, .25 + k * .28, .45, 10)); rise(r.querySelector('#m5'), t, 2.6); }); }
  // S25 153–160  the records
  { const [a, b] = span(10.5); shot('s25', a, b, (r) => {
      const evs = R1.timeline.filter(e => e.ev?.sha256).slice(0, 4);
      const chain = el('div', { class: 'abs', style: 'left:96px;top:300px;width:1728px;display:flex;gap:26px;align-items:center' }); evs.forEach((e, k) => { if (k) chain.append(el('span', { class: 'cue lk', style: 'flex:none;width:60px;height:3px;background:#fff;opacity:0;position:relative' })); chain.append(el('div', { class: 'paper2 cue ev2', style: 'flex:1;padding:22px 24px' }, el('div', { style: 'font:600 26px/1.2 var(--narrow)' }, e.ev.kind.replace(/_/g, ' ')), el('div', { class: 'mono', style: 'font-size:19px;color:var(--ink-2);margin-top:8px' }, 'sha256 ' + e.ev.sha256.slice(0, 14) + '…'), el('div', { class: 'mono', style: 'font-size:17px;color:var(--ink-3);margin-top:4px' }, 'prev ' + (e.ev.prev || '').slice(0, 14) + '…'))); });
      r.append(el('div', { class: 'abs cue', id: 'h', style: 'left:96px;top:120px;width:1728px' }, el('div', { class: 'eyebrow' }, 'The records'), el('div', { class: 'h2', style: 'margin-top:14px' }, 'An append-only log. Each event carries its own hash and the one before it.')), chain,
        el('div', { class: 'abs cue', id: 'k', style: 'left:96px;top:560px;width:1728px' }, el('div', { class: 'body', style: 'font-size:34px;font-family:var(--narrow);font-weight:600' }, 'During the experiments, the candidates are refitted to each new measurement. The last two inputs test the frozen model, with no refitting.'), el('div', { class: 'body dim', style: 'margin-top:22px;font-size:30px' }, 'The ledger keeps every attempt: the runs that stopped before a verdict, the two that abstained, the miswired board. Counts, not an accuracy rate.')));
      cap(a + .6, a + 3.0, 'Every forecast is checked against the event that froze it'); cap(a + 3.3, b, 'Refitted during the experiments; frozen for the last two inputs; every attempt kept');
    }, (r, t) => { rise(r.querySelector('#h'), t, .1); r.querySelectorAll('.ev2').forEach((e, k) => rise(e, t, .6 + k * .45)); r.querySelectorAll('.lk').forEach((l, k) => { l.style.opacity = ease(t, 1.0 + k * .45, 1.4 + k * .45); }); rise(r.querySelector('#k'), t, 3.2); }); }
  // S26 160–168  one command
  { const [a, b] = span(10); shot('s26', a, b, (r) => {
      const term = el('div', { id: 'term' }, el('div', { class: 'bar' }, el('b', {}, 'bash — BenchMate')), el('div', { class: 'm' }, '# a fresh clone. No packages, no API key, no network, no hardware.'), el('div', { class: 'c' }), el('div', { class: 'pass' }), el('div', { class: 'rows2' }), el('div', { class: 'foot' }, el('b', {}, 'What this proves: '), 'every event hash-chained; every forecast hash matched to the event that froze it; forecast → capture → measurement order kept. ', el('b', {}, 'What it does not: '), 'when the files were written, or the physical truth itself. The forecast commits on GitHub carry the time.'));
      r.append(term); r._CMD = '$ python3 -S -m benchmate verify \\\n    examples/reading-cohort/2026-11-03/records/20261103T125924-bf8f64512b/diagnosis-faulted/20261103T130826-26d83af2df'; r._OUT = 'PASS events=247 forecasts=4 measurements=5 order_checks=19 prediction_files=1\n     run_status=run_completed head_sha256=390f8d0c…';
      [['case 04, the whole pair', 'benchmate.reading_terminal_pair verify … 20261103T150223-18d6f08ac9', 'events=607 · forecasts=10'], ['case 02, restored closeout', 'benchmate.reading_restored_sam_closeout verify … 20261103T182550-4ea22cc3a0', 'events=574 · forecasts=10'], ['case 05, the whole pair', 'benchmate.reading_wire_stage verify … 20261104T021333-c80ef3617e', 'events=484 · forecasts=8'], ['case 03, the whole chain', 'benchmate.reading_restored_after_photo_v5 verify … 20261104T051005-fac3d07c86', 'events=583 · forecasts=4'], ['case 05, restored attempt 2', 'benchmate.channel_timing_audit_v4 … 20261104T034748-10ab5af750', 'events=238 · forecasts=4']].forEach(([n, c2, v]) => term.querySelector('.rows2').append(el('span', { class: 'k' }, 'PASS'), el('span', { class: 'n' }, n, el('small', {}, c2)), el('span', { class: 'v' }, v)));
      cap(a + .6, b, 'One command, no packages, no key, no network: it verifies any run'); for (let k = 0; k < 10; k++) sfx(a + .4 + k * .22, 'type'); sfx(a + 3.4, 'pass');
    }, (r, t) => { const n = Math.round(lin(t, .3, 2.9) * r._CMD.length); r.querySelector('.c').textContent = r._CMD.slice(0, n); r.querySelector('.c').append(t < 3.4 ? el('span', { style: 'display:inline-block;width:13px;height:26px;background:#dfe9e3;vertical-align:-4px' }) : ''); r.querySelector('.pass').textContent = t >= 3.4 ? r._OUT : ''; [...r.querySelectorAll('.rows2 > *')].forEach((e, k) => { e.style.opacity = lin(t, 4.2 + Math.floor(k / 3) * .4, 4.5 + Math.floor(k / 3) * .4); }); r.querySelector('.foot').style.opacity = lin(t, 6.4, 7.0); }); }
  // S27 168–178  close
  { const [a, b] = span(13.5); shot('s27', a, b, (r) => {
      r.classList.add('close'); const rows = [el('div', { class: 'cue', style: 'font:500 40px/1.25 var(--narrow);color:rgba(255,255,255,.92);max-width:1500px' }, 'For the first power-on of a new board: what to measure next, and where to look.'),
        el('div', { class: 'cue ch', style: 'margin-top:34px' }, 'The drawing is right. The board looks right. ', el('span', { class: 'w' }, 'The output is wrong.')), el('div', { class: 'cue cname', style: 'margin-top:26px' }, 'BenchMate'), el('div', { class: 'cue ctag', style: 'margin-top:10px' }, 'forecast-first experiments on a real circuit'), el('div', { class: 'cue curl', style: 'margin-top:34px' }, 'bami-codes.github.io/BenchMate'),
        el('div', { class: 'cue cmeta', style: 'margin-top:28px' }, el('span', {}, 'Muse Spark 1.3 · Meta Model API'), el('i'), el('span', {}, 'SAM 3.1'), el('i'), el('span', {}, 'Arduino UNO R4'), el('i'), el('span', {}, 'ngspice'), el('i'), el('span', {}, 'MIT')),
        el('div', { class: 'cue', style: 'margin-top:28px' }, el('span', { class: 'tape2' }, 'Built 27 Oct – 4 Nov 2026 · the first commit is the start of the project')),
        el('div', { class: 'cue wide', style: 'margin-top:30px;max-width:1500px;font:500 34px/1.3 var(--narrow);color:rgba(255,255,255,.92)' }, 'Demonstrated on five circuits. A first step toward AI-guided experiments on physical systems.'),
        el('div', { class: 'cue cfine', style: 'margin-top:22px;max-width:1500px' }, 'Animated from the public run records: every waveform, number, range and verdict is read from them. Layout, camera and pace are ours.')];
      r.append(el('div', { class: 'abs', style: 'left:96px;top:120px;width:1728px' }, ...rows)); r._rows = rows;
      cap(a + 1.5, a + 8.5, 'Spark chose the experiments and committed to each forecast. The bench held it to them.'); sfx(a + .3, 'end');
    }, (r, t, sh) => { const wideAt = PLAN.s27_wide != null ? Math.max(.2, (PLAN.s27_wide - sh.a) / sh.k) : null; r._rows.forEach((x, k) => rise(x, t, x.classList.contains('wide') && wideAt != null ? wideAt : .2 + k * .4, .7, 14)); }); }
}

// ---------- the frame: shots crossfade over XF seconds; captions on their own line
const CAPTIONS_ON = new URLSearchParams(location.search).get('cap') === '1';  // burned-in captions are off by default; the SRT carries them
function applyCap(t) { if (!CAPTIONS_ON) { $('#cap').style.opacity = 0; return; } const c = CAPS.find(c => t >= c.a && t < c.b); const s = $('#captxt'); s.textContent = c ? c.text : ''; $('#cap').style.opacity = c ? ease(t, c.a, c.a + .3) * (1 - ease(t, c.b - .3, c.b)) : 0; }
window.frame = (t) => {
  for (const s of SHOTS) {
    const on = t >= s.a && t < s.b; s.root.classList.toggle('on', on); if (!on) continue;
    const lt = (t - s.a) / s.k; const fin = s.a === 0 ? 1 : ease(t, s.a, s.a + FIN); const o = fin * (1 - ease(t, s.b - FOUT, s.b));
    s.root.style.opacity = o; s.root.style.transform = `scale(${1 + .010 * (1 - fin)})`;
    s.tick(s.root, lt, s);
  }
  applyCap(t);
};
window.filmCaptions = () => CAPS.slice(); window.filmSfx = () => SFX.slice(); window.filmShots = () => SHOTS.map(s => ({ id: s.id, start: s.a, seconds: s.b - s.a }));
