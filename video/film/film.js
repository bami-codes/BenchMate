// The film: one world, one camera, seven scenes. Every number, waveform, label and verdict is read from the public run
// records in site/data; the camera, the pacing and the captions are the only direction. frame(t) is a pure function of t.
const { $, el, Scope, Meter, stepTraces, stepTime, expName, menuChips, fmtMiss, netlistSVG, verdictWords } = BM;
const clamp = (x) => Math.max(0, Math.min(1, x));
const E = (x) => x < .5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2;          // the one easing
const back = (x) => { const c1 = 1.70158, c3 = c1 + 1; return 1 + c3 * Math.pow(x - 1, 3) + c1 * Math.pow(x - 1, 2); };
const ease = (t, a, b) => E(clamp((t - a) / (b - a)));
const lin = (t, a, b) => clamp((t - a) / (b - a));
const lerp = (a, b, u) => a + (b - a) * u;
const world = $('#world');
const ws = (id, x, y, cls = '') => { const d = el('div', { class: 'ws ' + cls, id }); d.style.left = x + 'px'; d.style.top = y + 'px'; world.append(d); return d; };
const kst = (iso) => iso ? new Date(iso).toLocaleTimeString('en-GB', { timeZone: 'Asia/Seoul', hour12: false }) : '';

// ---------- scenes: planned seconds; actual seconds come from voice/durations.json when the narration exists
const SCENES = [['s1', 11], ['s2', 16], ['s3', 58], ['s4', 38], ['s5', 22], ['s6', 14], ['s7', 11]].map(([id, planned]) => ({ id, planned, actual: planned }));
const sceneStart = (i) => SCENES.slice(0, i).reduce((a, s) => a + s.actual, 0);
const TOTAL = () => sceneStart(SCENES.length);
// a scene-local time `at` (planned seconds) → global seconds
const G = (i, at) => sceneStart(i) + at * SCENES[i].actual / SCENES[i].planned;
const L = (i, t) => (t - sceneStart(i)) * SCENES[i].planned / SCENES[i].actual;   // global → scene-local planned seconds

// ---------- camera
const CAM = [];   // {t, x, y, z} or {t, el, dx, dy, z}; equal t's hold
const anchor = (k) => { if (!k.el) return k; const e = k.el(); let x = e.offsetLeft, y = e.offsetTop, p = e.offsetParent; while (p && p !== world) { x += p.offsetLeft; y += p.offsetTop; p = p.offsetParent; } return { t: k.t, x: x + e.offsetWidth / 2 + (k.dx || 0), y: y + e.offsetHeight / 2 + (k.dy || 0), z: k.z }; };
function camAt(t) {
  if (t <= CAM[0].t) return anchor(CAM[0]); const last = CAM[CAM.length - 1]; if (t >= last.t) return anchor(last);
  let i = 0; while (CAM[i + 1].t <= t) i++; const a = anchor(CAM[i]), b = anchor(CAM[i + 1]); const u = E(clamp((t - a.t) / Math.max(1e-6, b.t - a.t)));
  const far = Math.hypot(b.x - a.x, b.y - a.y) > 1500;                                   // a long travel dips the zoom: a dolly out and in
  const z = lerp(a.z, b.z, u) * (far ? 1 - .32 * Math.sin(Math.PI * u) : 1);
  return { x: lerp(a.x, b.x, u), y: lerp(a.y, b.y, u), z };
}
const CAPS = [];  // {a, b, text} global seconds
const LOWER = []; // {a, b} lower third windows
const cue = (elm, t, a, d = .7) => { if (!elm) return; const e = ease(t, a, a + d); elm.style.opacity = e; elm.style.transform = `translateY(${14 * (1 - e)}px)`; return e; };
// a notebook card that grows the paper as it appears: height 0 → natural
const grow = (elm, t, a, d = .7) => { if (!elm) return 0; const e = ease(t, a, a + d); const h = elm._h || (elm._h = elm.scrollHeight); elm.style.height = (e >= 1 ? 'auto' : (h * e) + 'px'); elm.style.opacity = Math.min(1, e * 1.4); elm.style.transform = `translateY(${10 * (1 - e)}px)`; return e; };

// ---------- data
let R1, R1R, R4, R5, CASES, CENSUS, K1, K4, K5;
const Scn = {};   // per-scene update functions
window.filmReady = (async () => {
  [R1, R1R, R4, R5, CASES, CENSUS] = await Promise.all(['20261103T125924-bf8f64512b', '20261103T142003-2b176faa91', '20261103T150223-18d6f08ac9', '20261104T021333-c80ef3617e'].map(id => BM.json(`../../site/data/runs/${id}.json`)).concat([BM.json('../../site/data/cases.json'), BM.json('../../site/data/census.json')]));
  K1 = CASES.cases.find(c => c.id === '01'); K4 = CASES.cases.find(c => c.id === '04'); K5 = CASES.cases.find(c => c.id === '05');
  try { const d = await BM.json('voice/durations.json'); for (const s of SCENES) if (d[s.id]) s.actual = d[s.id]; } catch (e) { /* no voice yet: planned lengths */ }
  buildA(); buildB(); buildC(); buildD(); buildE(); buildF(); buildG();
})();

// ============ A. title (world x 0) ============
let A = {};
function buildA() {
  const photo = ws('photo', 0, 0); photo.append(el('img', { src: '../../examples/bench-photos/2026-11-04/full/camera-preview.png' }), el('div', { class: 'grade' }), el('div', { class: 'vig' }));
  A.img = photo.firstChild; A.photo = photo;
  A.lab = ws('photolab', 96, 980); A.lab.append(el('span', { class: 'tape2 white' }, 'The bench · 4 November 2026'));
  const lines = ws('lines', 96, 380); A.lines = [];
  ['The drawing is right.', 'The board is right.', 'The output is wrong.'].forEach((s, i) => { const ln = el('div', { class: 'ln' + (i === 2 ? ' wrong' : '') }, el('span', { class: 'txt' }, el('span', { class: 't' }), i === 2 ? el('span', { class: 'ul' }) : null), el('span', { class: 'caret' })); lines.append(ln); A.lines.push([ln, s]); });
  A.sub = ws('sub1', 96, 950); A.sub.append(el('b', {}, 'BenchMate'), ' — forecast-first experiments on a real circuit');
  const i = 0;
  CAM.push({ t: G(i, 0), x: 960, y: 540, z: 1 }, { t: G(i, 10.4), x: 960, y: 540, z: 1 });
  CAPS.push({ a: G(i, 5.8), b: G(i, 10.6), text: 'Every engineer meets this moment.' });
  Scn.s1 = (t) => {
    const z = 1 + .10 * ease(t, 0, 5.2); A.img.style.transform = `translate(-50%,-50%) translateY(${-120 + 40 * ease(t, 0, 5.2)}px) scale(${z})`;
    A.lab.style.opacity = ease(t, .8, 1.6) * (1 - ease(t, 4.4, 5.0));
    A.photo.style.opacity = 1 - ease(t, 4.8, 5.6);
    const typed = ([ln, s], t0, d) => { const n = Math.round(lin(t, t0, t0 + d) * s.length); ln.querySelector('.t').textContent = s.slice(0, n); const c = ln.querySelector('.caret'); const act = t >= t0 - .2 && t < t0 + d + .35; c.style.opacity = act ? ((Math.floor(t * 3) % 2) ? 1 : .25) : 0; };
    typed(A.lines[0], 5.6, .8); typed(A.lines[1], 6.9, .7); typed(A.lines[2], 8.1, .9);
    A.lines[2][0].querySelector('.ul').style.width = (ease(t, 9.05, 9.6) * 100) + '%';
    A.sub.style.opacity = ease(t, 9.7, 10.4) * (1 - ease(t, 11.0, 11.6));
    // the lines stay on the mat and recede as the camera leaves
    A.lines[0][0].parentElement.style.opacity = 1 - ease(t, 11.2, 12.4);
  };
}

// ============ B. setup (world x 2300) ============
let B = {};
function buildB() {
  B.drawn = ws('drawn', 2200, 350, 'fframe'); B.drawn.append(el('img', { src: 'assets-schem01.png' }));
  B.built = ws('built', 3180, 120, 'fframe'); B.built.append(el('img', { src: '../../examples/bench-photos/2026-11-04/full/camera-preview.png' }));
  B.pins = [['66%', '31%'], ['85%', '56.5%'], ['37%', '89%']].map(([x, y], i) => { const p = el('span', { class: 'pin' }, String(i + 1)); p.style.left = x; p.style.top = y; B.built.append(p); return p; });
  B.labd = ws('labdrawn', 2218, 322, 'flab'); B.labd.append(el('span', { class: 'tape2 white' }, 'Drawn · the schematic the model read'));
  B.labb = ws('labbuilt', 3198, 92, 'flab'); B.labb.append(el('span', { class: 'tape2 white' }, 'Built · a $40 bench'));
  B.key = ws('key', 3180, 966); B.key.append(el('span', {}, el('i', {}, '1'), el('b', {}, 'Arduino UNO R4'), ' runs each experiment'), el('span', {}, el('i', {}, '2'), el('b', {}, 'Instrument board')), el('span', {}, el('i', {}, '3'), el('b', {}, 'Mini board'), ' the circuit, plus one sealed fault'));
  B.front = ws('frontier', 2200, 150); B.front.append(el('span', { class: 'tape2' }, 'Meta Global AI Developer Hackathon · Push the Frontier'));
  B.seal = ws('seal', 3460, 745); B.seal.append('Sealed', el('small', {}, 'sha256 of the assembly, committed before the first measurement'));
  const i = 1;
  CAM.push({ t: G(i, .9), x: 3000, y: 560, z: .95 }, { t: G(i, 15.0), x: 3000, y: 560, z: .95 });
  CAPS.push({ a: G(i, 1.2), b: G(i, 6.0), text: 'One Arduino, one instrument board, one mini board with the circuit from the drawing' },
    { a: G(i, 6.4), b: G(i, 12.2), text: 'Spark reads the schematic and chooses its own experiments from a fixed menu' },
    { a: G(i, 12.6), b: G(i, 15.6), text: 'The fault was planted by us, hashed, and sealed. Spark never sees it.' });
  LOWER.push({ a: G(i, 6.2), b: G(i, 12.4) });
  Scn.s2 = (t) => {
    const d = ease(t, .2, 1.0); B.drawn.style.opacity = d; B.drawn.style.transform = `translateX(${-40 * (1 - d)}px)`; B.labd.style.opacity = ease(t, .9, 1.4);
    const b = ease(t, .9, 1.7); B.built.style.opacity = b; B.built.style.transform = `translateX(${40 * (1 - b)}px)`; B.labb.style.opacity = ease(t, 1.6, 2.1);
    B.pins.forEach((p, k) => { const x = clamp((t - (2.4 + k * .7)) / .45); p.style.transform = `translate(-50%,-50%) scale(${x <= 0 ? 0 : back(x)})`; });
    B.key.style.opacity = ease(t, 4.2, 4.9); B.front.style.opacity = ease(t, 9.4, 10.0);
    const s = clamp((t - 12.6) / .4); B.seal.style.transform = `rotate(-7deg) scale(${s <= 0 ? 0 : 0.9 + 0.1 * back(s)})`; B.seal.style.opacity = s <= 0 ? 0 : 1;
  };
}

// ============ shared: a case workspace ============
function workspace(id, x0, run) {
  const Wk = { x0 };
  const sc = ws(id + '-scope', x0, 0, 'case'); const scopeEl = el('div', { class: 'scope' }); sc.append(scopeEl); Wk.scope = new Scope(scopeEl, { fill: true });
  Wk.stripEl = el('div', { class: 'strip' }, el('b', {}, 'Experiment 1'), el('span', { class: 'fc' }, '– – forecast from the drawing'), el('span', { class: 'out' }, '— output, measured'), el('span', { class: 'in' }, '— input, measured')); scopeEl.append(Wk.stripEl);
  const mt = ws(id + '-meters', x0 + 1760, 0, 'case'); Wk.metersEl = el('div', { class: 'meters' }); mt.append(Wk.metersEl); Wk.meters = {}; Wk.metersWs = mt;
  const bk = ws(id + '-book', x0, 640, 'case'); Wk.book = el('div', { class: 'book' }); bk.append(Wk.book); Wk.bookWs = bk; bk.style.opacity = 0;
  Wk.meter = (fid, label, value) => { const m = new Meter(fid, label, { value }); m.root.classList.add('wait'); m.readout.firstChild.textContent = 'waiting'; m.readout.lastChild.textContent = ''; Wk.metersEl.append(m.root); Wk.meters[fid] = m; return m; };
  Wk.entry = (cls, who, lead, when, ...body) => { const e = el('div', { class: `entry ${cls} grow` }, el('div', { class: 't num' }, when || ''), el('div', {}, el('div', { class: 'who' }, el('i', { class: 'dot' }), who), lead ? el('p', { class: 'lead' }, lead) : null, el('div', { class: 'body' }, ...body))); e.style.height = '0px'; Wk.book.append(e); return e; };
  // scope phases: set once per key, then only progress changes
  Wk.phase = null;
  Wk.showStep = (key, step, title, { fcOnly = false } = {}) => { if (Wk.phase === key) return Wk.traces; Wk.phase = key; Wk.traces = stepTraces(step, { measuredProgress: 0 }); Wk.scope.set(stepTime(step), Wk.traces, title); return Wk.traces; };
  Wk.showCheck = (key, obs, fc, title) => { if (Wk.phase === key) return Wk.traces; Wk.phase = key; Wk.traces = []; for (const [fid, v] of Object.entries(fc || {})) Wk.traces.push({ id: fid, label: expName(fid) + ' forecast', kind: 'fc', v, dashed: true, progress: 1 }); Wk.traces.push({ id: 'in', label: 'IN', kind: 'in', v: obs.in_v, progress: 0 }, { id: 'out', label: 'OUT', kind: 'out', v: obs.out_v, progress: 0 }); Wk.scope.set(obs.t_s, Wk.traces, title); return Wk.traces; };
  Wk.sweep = (p, fcp = 1) => { for (const tr of Wk.traces || []) { if (tr.kind === 'fc') tr.progress = fcp; else if (tr.kind === 'in') tr.progress = p; else tr.progress = Math.max(0, p - .02); } Wk.scope.draw(); };
  Wk.needle = (m, miss, u, out, stepLab, worst, tagAt, t, tagText) => {
    if (u <= 0) { m.root.classList.add('wait'); m.root.classList.remove('bad', 'out', 'dead'); m.readout.firstChild.textContent = 'waiting'; m.readout.lastChild.textContent = ''; m.setAngle(0); m.root.querySelector('.tag')?.remove(); return; }
    m.root.classList.remove('wait'); m.setValue(miss * u, null, !(out && u > .6), stepLab, worst); m.root.classList.toggle('bad', out && u > .6);
    const on = out && tagAt != null && t >= tagAt;
    if (on && !m.root.querySelector('.tag')) { m.root.classList.add('out'); m.root.append(el('span', { class: 'tape red tag' }, tagText)); }
    if (!on) { m.root.classList.remove('out'); m.root.querySelector('.tag')?.remove(); }
    const tag = m.root.querySelector('.tag'); if (tag) { const s = ease(t, tagAt, tagAt + .45); tag.style.transform = `rotate(${-1.2 - 6 * (1 - s)}deg) scale(${.6 + .4 * s})`; tag.style.opacity = s; }
  };
  return Wk;
}
const stepTitle = (st) => st.label;
const missOf = (f, k = 0) => (f.decided_mV || f.miss_mV)[k];

// ============ C. case 01 (world x 4600) ============
let C;
function buildC() {
  C = workspace('c01', 4400, R1); const i = 2; const st = R1.steps, rd = R1.reading, ver = R1.verification;
  for (const f of st[0].fit) C.meter(f.id, expName(f.id), f.value != null ? BM.fmtFit(f.kind, f.value, f.at_bound) : 'drawn values');
  const EXT = 'external_equivalent:changed:R1'; C.ext = C.meter(EXT, expName(EXT), 'same waveforms'); C.ext.root.style.display = 'none'; C.ext.root.style.position = 'absolute'; C.ext.root.style.left = '350px'; C.ext.root.style.top = '244px'; C.ext.root.style.width = '330px'; C.ext.root.style.margin = '0';
  const cards = C.cards = {};
  cards.pick = C.entry('spark', 'Muse Spark 1.3 · chose the next experiment', null, kst(st[0].chosen_utc), el('div', { class: 'exp-title' }, el('span', { class: 'n' }, 1), st[0].label), el('p', { class: 'quote' }, st[0].reason.replace(/^["“]|["”]$/g, '')), menuChips(R1.menu, st[0].action));
  cards.frozen = C.entry('fit', 'Fit engine · forecasts frozen before measuring step 1', 'Before measuring, each standing explanation forecasts the output. Three dashed lines, frozen.', kst(st[0].chosen_utc), el('div', { class: 'chips' }, el('span', { class: 'chip sha' }, 'sha256 ' + st[0].forecast_sha), ...st[0].fit.map(f => el('span', { class: 'chip' }, el('i'), expName(f.id)))));
  cards.measure = C.entry('bench', 'Bench · measuring step 1', 'The bench measures experiment 1.', null, el('p', {}, `${st[0].settings.samples} frames captured. IN and OUT on the scope over the frozen forecasts; the forecast for the commanded input was frozen, the score drives that frozen model with the measured input.`));
  const fitRows = (s, n) => s.fit.map(f => { const out = f.status === 'inadequate'; const miss = missOf(f, n - 1); return el('tr', { class: out ? 'out' : '' }, el('td', {}, expName(f.id)), el('td', { class: 'muted' }, f.value != null ? 'fitted so far ' + BM.fmtFit(f.kind, f.value, f.at_bound) : 'drawn values'), el('td', {}, el('span', { class: `miss ${out ? 'bad' : 'good'}` }, fmtMiss(miss)), f.worst_region?.[n - 1] ? el('small', { class: 'muted' }, ` worst region: ${f.worst_region[n - 1].replace(/_/g, ' ')}`) : null), el('td', {}, out ? el('span', { class: 'tape red' }, `Ruled out after step ${n === 1 ? 1 : (f.id === 'changed:C1' ? 1 : 1)}`) : el('span', { class: 'muted' }, 'still fits'))); });
  cards.fit1 = C.entry('fit', 'Fit engine · ngspice, step 1', 'As drawn and C1 changed missed by too much and are crossed out. R1 changed still fits.', null, el('table', { class: 'fit-table' }, el('thead', {}, el('tr', {}, el('th', {}, 'Explanation'), el('th', {}, 'Value'), el('th', {}, 'Miss'), el('th', {}, ''))), el('tbody', {}, ...fitRows(st[0], 1))), el('p', { class: 'small muted' }, `Miss is the RMS difference between the forecast and the measured OUT; the frozen ${R1.allowance_mV} mV allowance applies to the whole step and to every region of it.`));
  cards.s2 = C.entry('spark', 'Muse Spark 1.3 · chose the next experiment', null, kst(st[1].chosen_utc), el('div', { class: 'exp-title' }, el('span', { class: 'n' }, 2), st[1].label), el('p', { class: 'quote' }, st[1].reason.replace(/^["“]|["”]$/g, '')), el('p', { class: 'small muted' }, `R1 changed still fits: ${fmtMiss(missOf(st[1].fit.find(f => f.id === 'changed:R1'), 1))}.`));
  cards.s3 = C.entry('spark', 'Muse Spark 1.3 · chose the next experiment', null, kst(st[2].chosen_utc), el('div', { class: 'exp-title' }, el('span', { class: 'n' }, 3), st[2].label), el('p', { class: 'quote' }, st[2].reason.replace(/^["“]|["”]$/g, '')), el('p', { class: 'small muted' }, `R1 changed still fits: ${fmtMiss(missOf(st[2].fit.find(f => f.id === 'changed:R1'), 2))}.`));
  const sc = ver.scored; cards.check = C.entry('fit', 'Fit engine · held-back inputs, forecast pushed first', 'The final forecast is pushed to GitHub; two inputs never used for fitting are measured.', null,
    el('div', { class: 'chips' }, el('span', { class: 'chip commit' }, 'commit ' + String(ver.commit || '').slice(0, 7)), ...sc.map(s => el('span', { class: 'chip' }, `held-back ${s.index}: ${fmtMiss(Object.values(s.conditional)[0].decided_mV)} · within ${R1.allowance_mV} mV`))));
  cards.equiv = C.entry('fit', 'Fit engine · electrically equivalent explanations', 'Two explanations give the same waveforms at the terminals.', null, el('p', {}, el('span', { class: 'chip' }, el('i'), 'engine rule — electrically equivalent'), ' ', `${expName('changed:R1')}, or ${expName(EXT)}. No experiment on the menu can separate them.`));
  const bands = rd.bands.filter(b => b.source === 'operator_dmm');
  cards.ask = C.entry('spark', 'Muse Spark 1.3 · asked for one reading', `Spark asks for one reading: ${BM.quantityWord(rd.quantity, rd.component)}.`, null, el('p', { class: 'quote' }, rd.reason.replace(/^["“]|["”]$/g, '')),
    el('p', { class: 'small muted', style: 'margin-top:6px' }, 'Before anyone reads, each explanation’s allowed range is frozen:'),
    el('table', { class: 'bands' }, el('thead', {}, el('tr', {}, el('th', {}, 'Explanation'), el('th', {}, `If read with a multimeter`))), el('tbody', {}, ...bands.map(b => el('tr', {}, el('td', {}, expName(b.explanation)), el('td', { class: 'b' }, `${b.low}–${b.high} ${b.unit}`))))));
  const ph = el('div', { class: 'photo' }, el('img', { src: '../../site/' + rd.binding.photo }), el('img', { class: 'mask', src: '../../site/' + rd.binding.overlay_file })); C.mask = ph.lastChild;
  cards.photo = C.entry('spark', 'Muse Spark 1.3 vision · pointed at the body', `Spark looks at the board photo with SAM 3.1’s outlines and points at the body that is ${rd.binding.component}.`, null, ph, el('p', { class: 'small muted' }, `“${rd.binding.reason}” ${rd.binding.operator_confirmed ? 'Confirmed by the operator.' : ''}`));
  C.typed = el('span', { class: 'typed' }, el('span', { class: 'v' }), el('span', { class: 'cr' }));
  cards.read = C.entry('bench', 'Operator · one multimeter reading', 'The operator reads R1, power off, both leads lifted.', null, C.typed, el('p', { class: 'small muted' }, `Inside ${bands.find(b => b.explanation === EXT).low}–${bands.find(b => b.explanation === EXT).high} ${bands[0].unit}: ${expName(EXT)} fits. ${expName('changed:R1')} is ruled out by the reading.`));
  const vcard = el('div', { class: 'verdict-card' }, el('div', { class: 'vs' }, el('span', { class: 'lab' }, 'Spark’s answer'), el('div', { class: 'big' }, verdictWords(R1.outcome, R1))), el('div', { class: 'vs planted cue' }, el('span', { class: 'lab' }, 'What was planted · opened only now'), el('div', { class: 'big' }, K1.hidden)), el('p', { class: 'small muted', style: 'margin-top:8px' }, 'The verdict is copied from the engine’s report; the seal’s digest is checked by code against the one committed before the first measurement. Spark never saw the lower line.'));
  C.planted = vcard.querySelector('.planted');
  cards.verdict = C.entry('guard', 'Verdict · from the engine’s report', null, null, vcard);
  cards.restored = C.entry('guard', 'Restored rerun · a fresh Spark, the fault repaired', null, null, el('div', { class: 'verdict-card quiet' }, el('div', { class: 'vs' }, el('span', { class: 'lab' }, 'Fixed, then rerun' ), el('div', { class: 'big' }, verdictWords(R1R.outcome, R1R))), el('p', { class: 'small muted', style: 'margin-top:8px' }, 'This says nothing about tests Spark did not run. On a restored board it is the expected result.')));
  // camera (planned-local seconds)
  const K = (at, obj) => Object.assign({ t: G(i, at) }, obj);
  const X = 4400;
  CAM.push(K(1.0, { el: () => cards.pick, dy: 40, z: 1.25 }), K(2.4, { el: () => cards.pick, dy: 40, z: 1.25 }),
    K(3.3, { x: X + 1045, y: 330, z: .88 }), K(9.9, { x: X + 1045, y: 330, z: .88 }),
    K(10.7, { x: X + 1500, y: 440, z: 1.1 }), K(13.2, { x: X + 1500, y: 440, z: 1.1 }),
    K(14.1, { el: () => cards.fit1, dy: 50, z: 1.15 }), K(15.6, { el: () => cards.fit1, dy: 50, z: 1.15 }),
    K(16.4, { x: X + 1045, y: 330, z: .88 }), K(20.0, { x: X + 1045, y: 330, z: .88 }),
    K(21.0, { el: () => cards.check, dy: 40, z: 1.15 }), K(24.0, { el: () => cards.check, dy: 40, z: 1.15 }),
    K(25.0, { x: X + 1960, y: 330, z: 1.15 }), K(27.0, { x: X + 1960, y: 330, z: 1.15 }),
    K(28.0, { el: () => cards.ask, dy: 60, z: 1.1 }), K(33.0, { el: () => cards.ask, dy: 60, z: 1.1 }),
    K(34.0, { el: () => cards.photo, dy: 40, z: 1.1 }), K(38.0, { el: () => cards.photo, dy: 40, z: 1.1 }),
    K(39.0, { el: () => cards.read, dy: 30, z: 1.2 }), K(41.5, { el: () => cards.read, dy: 30, z: 1.2 }),
    K(42.4, { x: X + 2100, y: 420, z: 1.2 }), K(44.6, { x: X + 2100, y: 420, z: 1.2 }),
    K(45.6, { el: () => cards.verdict, dy: 30, z: 1.1 }), K(53.0, { el: () => cards.verdict, dy: 30, z: 1.1 }),
    K(54.0, { el: () => cards.restored, dy: -40, z: 1.05 }), K(57.2, { el: () => cards.restored, dy: -40, z: 1.05 }));
  const m1 = missOf(st[0].fit.find(f => f.id === 'nominal'));
  CAPS.push({ a: G(i, .6), b: G(i, 2.8), text: 'Case 01 · Spark chooses experiment 1 and says why, in its own words' },
    { a: G(i, 3.0), b: G(i, 6.6), text: `Each explanation forecasts the output · frozen before the board is touched · sha256 ${st[0].forecast_sha}` },
    { a: G(i, 6.9), b: G(i, 10.5), text: 'The bench measures. The real output runs under the drawing’s forecast.' },
    { a: G(i, 10.9), b: G(i, 14.0), text: `${m1.toFixed(2)} mV against an allowance of ${R1.allowance_mV} mV: As drawn is crossed out` },
    { a: G(i, 16.6), b: G(i, 20.4), text: 'Experiments 2 and 3: R1 changed still fits' },
    { a: G(i, 21.2), b: G(i, 24.4), text: `Final forecast pushed to GitHub, then two held-back inputs: ${sc.map(s => fmtMiss(Object.values(s.conditional)[0].decided_mV)).join(' and ')}` },
    { a: G(i, 25.2), b: G(i, 27.6), text: 'Two explanations draw the same waveform. No experiment on the menu can separate them.' },
    { a: G(i, 28.4), b: G(i, 33.4), text: 'Spark asks for one multimeter reading; the allowed range under each explanation is frozen first' },
    { a: G(i, 34.4), b: G(i, 38.4), text: `Spark points at the body that is ${rd.binding.component}, with SAM 3.1’s outline` },
    { a: G(i, 39.4), b: G(i, 44.8), text: `The operator reads ${rd.observed.value} ${rd.observed.unit}: one explanation left` },
    { a: G(i, 46.0), b: G(i, 53.4), text: 'The seal opens. Spark had never seen the lower line.' },
    { a: G(i, 54.4), b: G(i, 58), text: 'Repaired, then run again by a fresh Spark: no mismatch in the tests it chose' });
  Scn.s3 = (t) => {
    C.bookWs.style.opacity = ease(t, .1, .6); const g = grow; g(cards.pick, t, .2); g(cards.frozen, t, 2.6); g(cards.measure, t, 6.6); g(cards.fit1, t, 13.4); g(cards.s2, t, 16.0); g(cards.s3, t, 18.0); g(cards.check, t, 20.6); g(cards.equiv, t, 24.6); g(cards.ask, t, 27.6); g(cards.photo, t, 33.6); g(cards.read, t, 38.6); g(cards.verdict, t, 45.4); g(cards.restored, t, 53.6);
    // scope phases
    if (t < 16.0) { C.showStep('s1', st[0], stepTitle(st[0])); let k = 0; for (const tr of C.traces) if (tr.kind === 'fc') { tr.progress = ease(t, 3.4 + k * .18, 5.4 + k * .18); k++; } const p = lin(t, 6.8, 10.2); for (const tr of C.traces) if (tr.kind === 'in') tr.progress = p; else if (tr.kind === 'out') tr.progress = Math.max(0, p - .02); C.scope.draw(); C.stripEl.firstChild.textContent = 'Experiment 1'; }
    else if (t < 18.0) { C.showStep('s2', st[1], stepTitle(st[1])); C.sweep(lin(t, 16.2, 17.6)); C.stripEl.firstChild.textContent = 'Experiment 2'; }
    else if (t < 20.6) { C.showStep('s3', st[2], stepTitle(st[2])); C.sweep(lin(t, 18.2, 19.6)); C.stripEl.firstChild.textContent = 'Experiment 3'; }
    else if (t < 24.6) { C.showCheck('v1', ver.observations[0], ver.forecasts[0], `Held-back input 1 · ${ver.reserved[0].kind} ${ver.reserved[0].amplitude_v} V`); C.sweep(lin(t, 20.8, 22.6)); C.stripEl.firstChild.textContent = 'Held-back check 1'; }
    else { C.showCheck('v2', ver.observations[1], ver.forecasts[1], `Held-back input 2 · ${ver.reserved[1].kind} ${ver.reserved[1].amplitude_v} V`); C.sweep(1); C.stripEl.firstChild.textContent = 'Held-back check 2'; }
    // meters by phase
    const f1 = st[0].fit, f2 = st[1].fit, f3 = st[2].fit;
    for (const f of f1) {
      const m = C.meters[f.id]; const out1 = f.status === 'inadequate';
      if (t < 16.0) C.needle(m, missOf(f, 0), ease(t, 10.6, 12.2), out1, 'step 1', f.worst_region?.[0], 12.3, t, 'Ruled out after step 1');
      else { const ff = (t < 18 ? f2 : f3).find(x => x.id === f.id); const k = t < 18 ? 1 : 2; if (out1) { m.root.classList.add('out', 'dead'); if (!m.root.querySelector('.tag')) m.root.append(el('span', { class: 'tape red tag' }, 'Ruled out after step 1')); } else { m.root.classList.remove('wait', 'dead'); m.setValue(missOf(ff, k), null, true, `step ${k + 1}`, ff.worst_region?.[k]); } }
    }
    // the fourth meter: the electrically equivalent explanation, from 24.6 s; the reading at 40.4 s decides between the two
    const r1m = C.meters['changed:R1'], ext = C.ext; const bEXT = bands.find(b => b.explanation === EXT), bR1 = bands.find(b => b.explanation === 'changed:R1');
    if (t >= 24.6) { ext.root.style.display = ''; ext.root.classList.remove('wait'); const e = ease(t, 24.6, 25.3); ext.root.style.opacity = e; ext.root.style.transform = `translateY(${12 * (1 - e)}px)`;
      if (t < 40.4) { if (!ext._tag) { ext.carry('Same waveforms as R1 changed'); ext._tag = true; } ext.setAngle(r1m.val || 0); ext.readout.firstChild.textContent = r1m.readout.firstChild.textContent; ext.readout.lastChild.textContent = 'same forecast'; ext.root.classList.remove('band'); }
      else { if (!ext._band) { ext.band(bEXT.low, bEXT.high, bEXT.unit, rd.observed.value); ext.setReading(rd.observed.value, rd.observed.unit, 'reading'); ext.root.querySelector('.tag')?.remove(); ext.root.append(el('span', { class: 'tape tag', style: 'background:var(--tape)' }, 'Fits the reading')); ext._band = true; }
        if (!r1m._dead) { r1m.band(bR1.low, bR1.high, bR1.unit, rd.observed.value); r1m.setReading(rd.observed.value, rd.observed.unit, 'reading'); r1m.ruleOutByReading(); r1m.die(); r1m._dead = true; } }
    } else { ext.root.style.display = 'none'; }
    // the typed reading 38.8 → 40.0
    const s = `${rd.observed.value} ${rd.observed.unit}`; const n = Math.round(lin(t, 38.8, 40.0) * s.length); C.typed.firstChild.textContent = s.slice(0, n); C.typed.lastChild.style.opacity = t > 38.6 && t < 40.6 ? ((Math.floor(t * 3) % 2) ? 1 : .2) : 0;
    C.mask.style.opacity = ease(t, 34.6, 35.4);
    cue(C.planted, t, 47.6);
  };
}

// ============ D. case 04 (world x 7600) ============
let D;
function buildD() {
  D = workspace('c04', 7100, R4); const i = 3; const st = R4.steps, ver = R4.verification, pr = R4.structure[0];
  for (const f of st[2].fit) D.meter(f.id, expName(f.id), f.value != null ? BM.fmtFit(f.kind, f.value, f.at_bound) : 'drawn values');
  const cards = D.cards = {};
  cards.fit3 = D.entry('fit', 'Fit engine · ngspice, step 3', 'No explanation fits any more. Every needle is in the red.', kst(st[2].chosen_utc), el('p', {}, `${st[2].label}. ${st[2].fit.map(f => `${expName(f.id)} ${fmtMiss(missOf(f, 2))}`).join(' · ')}; the allowance is ${R4.allowance_mV} mV.`));
  const added = (pr.diff?.added || []).map(x => x.name);
  const schem = el('div', { class: 'schem-wrap' }, netlistSVG(pr.elements, { highlight: added }));
  cards.propose = D.entry('spark', 'Muse Spark 1.3 · proposes a part the drawing does not show', `Spark proposes a part the drawing doesn’t show: ${BM.kindWord(pr.diff.added[0].kind)} between ${pr.diff.added[0].a} and ${pr.diff.added[0].b}.`, kst(pr.ev?.ts), el('p', { class: 'quote' }, pr.rationale.replace(/^["“]|["”]$/g, '')), el('div', { class: 'card violet propose' }, schem), el('p', { class: 'small muted' }, 'A new netlist, written by Spark; the engine fits it like any other explanation.'));
  D.schem = schem;
  cards.push = D.entry('fit', 'Fit engine · final forecast, pushed before the check', 'The forecast for the proposed circuit is pushed to GitHub. From here nothing can be re-fitted.', null, el('div', { class: 'chips' }, el('span', { class: 'chip commit' }, 'commit ' + String(ver.commit || '').slice(0, 7)), el('span', { class: 'chip sha' }, 'sha256 ' + String(ver.sha || '')), el('span', { class: 'chip' }, `${(ver.published_utc || '').slice(0, 16).replace('T', ' ')} UTC`)));
  const sc = ver.scored; const dec = sc.map(s => Object.values(s.conditional)[0]);
  cards.scores = D.entry('fit', 'Fit engine · held-back inputs scored against the frozen forecast', 'Two inputs Spark had never seen. Both within the allowance, in every region.', null,
    el('div', { class: 'scores' }, ...dec.map((d, k) => el('div', {}, el('b', {}, fmtMiss(d.decided_mV)), el('span', {}, `held-back ${k + 1} · worst region (${sc[k].settings.kind} ${sc[k].settings.amplitude_v} V)`))), el('div', { class: 'allow' }, el('b', {}, `${R4.allowance_mV} mV`), el('span', {}, 'the allowance, frozen before the first run'))));
  const vcard = el('div', { class: 'verdict-card' }, el('div', { class: 'vs' }, el('span', { class: 'lab' }, 'Spark’s answer'), el('div', { class: 'big' }, verdictWords(R4.outcome, R4))), el('div', { class: 'vs planted cue' }, el('span', { class: 'lab' }, 'What was planted · opened only now'), el('div', { class: 'big' }, K4.hidden)), el('p', { class: 'small muted', style: 'margin-top:8px' }, 'The connection Spark wrote. The verdict is copied from the engine’s report; the seal’s digest is checked by code. Spark never saw the lower line.'));
  D.planted = vcard.querySelector('.planted');
  cards.verdict = D.entry('guard', 'Verdict · from the engine’s report', null, null, vcard);
  // case 05 mini card to the right of the book
  const p5 = R5.structure[0], rd5 = R5.reading;
  D.mini = ws('c05-mini', 7100 + 1400, 660, 'case'); const mini = el('div', { class: 'mini' }, el('h3', {}, 'Case 05 · it happened twice'), el('p', {}, `${BM.diffWords ? '' : ''}Spark replaced a drawn wire with a resistor: ${p5.diff.added.map(x => `${BM.kindWord(x.kind)} between ${x.a} and ${x.b}`).join(', ')} in place of ${p5.diff.removed.map(x => x.name).join(', ')}. One reading placed it off the board.`), el('div', { class: 'photo' }, el('img', { src: '../../site/' + rd5.binding.photo }), el('img', { class: 'mask', src: '../../site/' + rd5.binding.overlay_file })), el('p', { class: 'small muted', style: 'margin-top:6px' }, `Sealed: ${K5.hidden}`)); D.mini.append(mini); D.mini.style.opacity = 0;
  const K = (at, obj) => Object.assign({ t: G(i, at) }, obj); const X = 7100;
  CAM.push(K(1.0, { x: X + 1045, y: 330, z: .88 }), K(4.4, { x: X + 1045, y: 330, z: .88 }),
    K(5.2, { x: X + 1925, y: 420, z: 1.25 }), K(7.2, { x: X + 1925, y: 420, z: 1.25 }),
    K(8.2, { el: () => cards.propose, dy: 60, z: 1.0 }), K(14.0, { el: () => cards.propose, dy: 60, z: 1.0 }),
    K(15.0, { el: () => cards.push, dy: 30, z: 1.15 }), K(17.4, { el: () => cards.push, dy: 30, z: 1.15 }),
    K(18.2, { x: X + 1045, y: 330, z: .88 }), K(24.4, { x: X + 1045, y: 330, z: .88 }),
    K(25.2, { el: () => cards.scores, dy: 40, z: 1.15 }), K(28.2, { el: () => cards.scores, dy: 40, z: 1.15 }),
    K(29.2, { el: () => cards.verdict, dy: 30, z: 1.1 }), K(34.2, { el: () => cards.verdict, dy: 30, z: 1.1 }),
    K(35.2, { el: () => D.mini, dy: 0, z: 1.05 }), K(37.4, { el: () => D.mini, dy: 0, z: 1.05 }));
  CAPS.push({ a: G(i, 1.2), b: G(i, 4.8), text: `Case 04 · ${st[2].label}: every value in the drawing fails` },
    { a: G(i, 5.4), b: G(i, 7.6), text: `${st[2].fit.map(f => fmtMiss(missOf(f, 2))).join(' · ')} · allowance ${R4.allowance_mV} mV` },
    { a: G(i, 8.6), b: G(i, 14.4), text: `Spark writes a new netlist: ${BM.kindWord(pr.diff.added[0].kind)} from ${pr.diff.added[0].a} to ${pr.diff.added[0].b}, which the drawing never had` },
    { a: G(i, 15.4), b: G(i, 17.8), text: `Forecast pushed to GitHub · commit ${String(ver.commit || '').slice(0, 7)}` },
    { a: G(i, 18.6), b: G(i, 24.8), text: 'Two inputs Spark has never seen are measured against the frozen forecast' },
    { a: G(i, 25.6), b: G(i, 28.6), text: `Worst regions ${dec.map(d => fmtMiss(d.decided_mV)).join(' and ')}, under the ${R4.allowance_mV} mV allowed` },
    { a: G(i, 29.6), b: G(i, 34.6), text: 'The seal opens: the connection Spark wrote.' },
    { a: G(i, 35.6), b: G(i, 38), text: 'Case 05: a plain wire became a resistor; one reading placed it off the board' });
  Scn.s4 = (t) => {
    D.bookWs.style.opacity = ease(t, 3.0, 3.6); grow(cards.fit3, t, 3.2); grow(cards.propose, t, 7.6); grow(cards.push, t, 14.6); grow(cards.scores, t, 24.8); grow(cards.verdict, t, 28.8);
    if (t < 18.2) { D.showStep('s3', st[2], stepTitle(st[2])); D.sweep(lin(t, .8, 3.0)); D.stripEl.firstChild.textContent = 'Experiment 3'; }
    else if (t < 21.6) { D.showCheck('v1', ver.observations[0], ver.forecasts[0], `Held-back input 1 · ${ver.reserved[0].kind} ${ver.reserved[0].amplitude_v} V`); D.sweep(lin(t, 18.4, 21.2)); D.stripEl.firstChild.textContent = 'Held-back check 1'; }
    else { D.showCheck('v2', ver.observations[1], ver.forecasts[1], `Held-back input 2 · ${ver.reserved[1].kind} ${ver.reserved[1].amplitude_v} V ${ver.reserved[1].frequency_hz || ''} Hz`); D.sweep(lin(t, 21.8, 24.4)); D.stripEl.firstChild.textContent = 'Held-back check 2'; }
    for (const f of st[2].fit) D.needle(D.meters[f.id], missOf(f, 2), ease(t, 3.0, 4.6), true, 'step 3', f.worst_region?.[2], 4.8, t, 'Ruled out after step 3');
    D.schem.style.opacity = ease(t, 8.4, 9.4);
    cue(D.planted, t, 31.6);
    const e = ease(t, 34.8, 35.6); D.mini.style.opacity = e; D.mini.style.transform = `translateX(${30 * (1 - e)}px)`;
  };
}

// ============ E. trust (world x 10600) ============
let Ev = {};
function buildE() {
  const i = 4; const X = 9800;
  const chain = ws('chain', X, 120); const evs = R1.timeline.filter(e => e.ev?.sha256).slice(0, 7);
  Ev.boxes = evs.map((e, k) => { const b = el('div', { class: 'hv cue' }, el('b', {}, e.ev.kind.replace(/_/g, ' ')), el('code', {}, 'sha256 ' + e.ev.sha256.slice(0, 12) + '…'), el('span', { class: 'prev' }, 'prev ' + (e.ev.prev || '').slice(0, 12) + '…')); if (k) chain.append(el('span', { class: 'link cue' })); chain.append(b); return b; });
  Ev.links = [...chain.querySelectorAll('.link')];
  Ev.chainTitle = ws('chaintitle', X, 40); Ev.chainTitle.append(el('div', { style: 'font:600 34px/1.2 var(--narrow);color:#fff' }, 'Every run is an append-only log. Each event carries its hash and the previous one.'));
  const cz = ws('census', X, 420); const c = CENSUS.counts; Ev.nums = [[c.registered_workflow_attempts, 'registered workflow attempts, five cases'], [c.diagnostic_starts, 'diagnostic runs started'], [c.stopped_before_verdict, 'stopped before a verdict · kept'], [c.abstained, 'abstained · kept'], [c.non_abstained_verdicts, 'verdicts, replayed on the site']].map(([n, l]) => { const k = el('div', { class: 'ck cue' }, el('b', {}, '0'), el('span', {}, l)); k._n = n; cz.append(k); return k; });
  Ev.censusTitle = ws('censustitle', X, 350); Ev.censusTitle.append(el('div', { style: 'font:600 30px/1.2 var(--narrow);color:#fff' }, 'Counts, not an accuracy rate.'));
  const term = ws('term', X, 700); term.style.width = '1680px'; term.append(el('div', { class: 'bar' }, el('b', {}, 'bash — BenchMate')), el('div', { class: 'm' }, '# a fresh clone. No packages, no API key, no network, no hardware.'), el('div', { class: 'c' }), el('div', { class: 'pass' }), el('div', { class: 'rows' }), el('div', { class: 'foot' }, el('b', {}, 'What this proves: '), 'every event hash-chained; every forecast hash matched to the event that froze it; forecast → capture → measurement order kept. ', el('b', {}, 'What it does not: '), 'when the files were written, or the physical truth itself. The forecast commits on GitHub carry the time.'));
  Ev.cmd = term.querySelector('.c'); Ev.out = term.querySelector('.pass'); Ev.rows = term.querySelector('.rows'); Ev.foot = term.querySelector('.foot');
  Ev.CMD = '$ python3 -S -m benchmate verify examples/reading-cohort/2026-11-03/records/20261103T125924-bf8f64512b/diagnosis-faulted/20261103T130826-26d83af2df';
  Ev.OUT = 'PASS events=247 forecasts=4 measurements=5 order_checks=19 prediction_files=1 run_status=run_completed head_sha256=390f8d0c…';
  [['case 04, the whole pair', 'benchmate.reading_terminal_pair verify … 20261103T150223-18d6f08ac9', 'events=607 · forecasts=10'], ['case 02, restored closeout', 'benchmate.reading_restored_sam_closeout verify … 20261103T182550-4ea22cc3a0', 'events=574 · forecasts=10'], ['case 05, the whole pair', 'benchmate.reading_wire_stage verify … 20261104T021333-c80ef3617e', 'events=484 · forecasts=8'], ['case 03, the whole chain', 'benchmate.reading_restored_after_photo_v5 verify … 20261104T051005-fac3d07c86', 'events=583 · forecasts=4'], ['case 05, restored attempt 2', 'benchmate.channel_timing_audit_v4 … 20261104T034748-10ab5af750', 'events=238 · forecasts=4']].forEach(([n, c2, v]) => Ev.rows.append(el('span', { class: 'k' }, 'PASS'), el('span', { class: 'n' }, n, el('small', {}, c2)), el('span', { class: 'v' }, v)));
  const K = (at, obj) => Object.assign({ t: G(i, at) }, obj);
  CAM.push(K(.9, { x: X + 760, y: 190, z: 1.0 }), K(3.0, { x: X + 760, y: 190, z: 1.0 }), K(7.2, { x: X + 1180, y: 190, z: 1.0 }), K(8.4, { x: X + 640, y: 520, z: 1.05 }), K(13.6, { x: X + 640, y: 520, z: 1.05 }), K(14.6, { x: X + 840, y: 1100, z: 1.0 }), K(21.4, { x: X + 840, y: 1100, z: 1.0 }));
  CAPS.push({ a: G(i, 1.2), b: G(i, 7.6), text: 'Every forecast is checked against the event that froze it' }, { a: G(i, 8.8), b: G(i, 13.8), text: 'The ledger keeps what went wrong: three runs stopped before a verdict, two abstained' }, { a: G(i, 15.0), b: G(i, 21.6), text: 'One command, no packages, no key, no network: it verifies any run' });
  Scn.s5 = (t) => {
    Ev.boxes.forEach((b, k) => cue(b, t, .6 + k * .5)); Ev.links.forEach((l, k) => { l.style.opacity = ease(t, 1.0 + k * .5, 1.4 + k * .5); });
    Ev.nums.forEach((k, j) => { cue(k, t, 8.6 + j * .35); k.firstChild.textContent = Math.round(k._n * ease(t, 8.8 + j * .35, 10.4 + j * .35)); });
    const n = Math.round(lin(t, 15.0, 17.6) * Ev.CMD.length); Ev.cmd.innerHTML = Ev.CMD.slice(0, n) + (t < 18.2 ? '<span class="cr" style="display:inline-block;width:12px;height:24px;background:#dfe9e3;vertical-align:-4px"></span>' : '');
    Ev.out.textContent = t >= 18.2 ? Ev.OUT : '';
    [...Ev.rows.children].forEach((e, k) => { e.style.opacity = lin(t, 19.0 + Math.floor(k / 3) * .4, 19.3 + Math.floor(k / 3) * .4); });
    Ev.foot.style.opacity = lin(t, 21.0, 21.6);
  };
}

// ============ F. loop (world x 13000) ============
let F = {};
function buildF() {
  const i = 5; const X = 11800; const sheet = ws('loopsheet', X, 92);
  sheet.append(el('div', { class: 'ltitle' }, 'The loop needs six things. None of them is electronic.', el('small', {}, 'Spark chose what to test next, and committed to what each explanation should predict.')), el('div', { class: 'ltag' }, el('span', { class: 'tape2' }, 'another bench · not built here')));
  const Xs = [430, 840, 1250], TOP = 300, BOT = 640, W = 340, H = 130;
  const stations = [[1, Xs[0], TOP, 'What was intended', 'here: the schematic image', 'schematic and layout of a PCB'], [2, Xs[1], TOP, 'Explanations to propose', 'a changed value, or a part the drawing lacks', 'a wrong part, a short, a missing pull-up'], [3, Xs[2], TOP, 'A simulator', 'here: ngspice', "SPICE with the board's models"], [4, Xs[2], BOT, 'An instrument with a menu', 'steps and sines, with or without a load', 'a bench supply and a scope'], [5, Xs[1], BOT, 'A person for the rest', 'move one jumper, read one part', "the probe in the operator's hand"], [6, Xs[0], BOT, 'A sealed truth', 'the assembly record, hashed first', 'the fix that worked, sealed first']];
  const ring = `M ${Xs[0]} ${TOP} L ${Xs[2]} ${TOP} L ${Xs[2] + W / 2 + 60} ${TOP} Q ${Xs[2] + W / 2 + 120} ${TOP} ${Xs[2] + W / 2 + 120} ${TOP + 60} L ${Xs[2] + W / 2 + 120} ${BOT - 60} Q ${Xs[2] + W / 2 + 120} ${BOT} ${Xs[2] + W / 2 + 60} ${BOT} L ${Xs[0]} ${BOT} L ${Xs[0] - W / 2 - 60} ${BOT} Q ${Xs[0] - W / 2 - 120} ${BOT} ${Xs[0] - W / 2 - 120} ${BOT - 60} L ${Xs[0] - W / 2 - 120} ${TOP + 60} Q ${Xs[0] - W / 2 - 120} ${TOP} ${Xs[0] - W / 2 - 60} ${TOP} L ${Xs[0] - W / 2 - 8} ${TOP}`;
  sheet.insertAdjacentHTML('beforeend', `<svg width="1680" height="896" viewBox="0 0 1680 896"><defs><marker id="ah" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="8" markerHeight="8" orient="auto-start-reverse"><path d="M0 0L10 5 0 10z" fill="#171b1e"/></marker></defs><path id="ring" class="arrow" d="${ring}" marker-end="url(#ah)"/>${stations.map(([n, x, y, h, here, alt]) => `<g class="st" transform="translate(${x} ${y})"><rect x="${-W / 2}" y="${-H / 2}" width="${W}" height="${H}" rx="8"/><text class="n" x="${-W / 2 + 16}" y="${-H / 2 + 26}">${n}</text><text class="h" x="0" y="-6" text-anchor="middle">${h}</text><text class="here" x="0" y="28" text-anchor="middle">${here}</text><text class="alt" x="0" y="28" text-anchor="middle">${alt}</text></g>`).join('')}</svg>`);
  sheet.append(el('div', { class: 'lline' }, 'The experiments were chosen by the model, and each forecast was frozen before the bench moved.', el('span', {}, 'A circuit was the cheapest real system where that could be done honestly in nine days.')));
  F.ring = sheet.querySelector('#ring'); F.L = F.ring.getTotalLength(); F.ring.style.strokeDasharray = F.L; F.sts = [...sheet.querySelectorAll('.st')]; F.title = sheet.querySelector('.ltitle'); F.tag = sheet.querySelector('.ltag'); F.line = sheet.querySelector('.lline'); F.sheet = sheet;
  const K = (at, obj) => Object.assign({ t: G(i, at) }, obj);
  CAM.push(K(.9, { x: X + 840, y: 92 + 448, z: 1.0 }), K(13.2, { x: X + 840, y: 92 + 448, z: 1.0 }));
  CAPS.push({ a: G(i, 1.0), b: G(i, 7.0), text: 'A description of what was intended · explanations · a simulator · an instrument with a menu · a person for the rest · a sealed truth' }, { a: G(i, 7.6), b: G(i, 11.2), text: 'The same loop, on another bench: not built here' });
  Scn.s6 = (t) => {
    F.title.style.opacity = ease(t, .2, .9); F.ring.style.strokeDashoffset = F.L * (1 - ease(t, .6, 5.2));
    F.sts.forEach((s, k) => { s.style.opacity = ease(t, 1.0 + k * .62, 1.5 + k * .62); });
    const sw = ease(t, 7.4, 7.9) * (1 - ease(t, 11.0, 11.5)); F.sheet.querySelectorAll('.here').forEach(e => e.style.opacity = 1 - sw); F.sheet.querySelectorAll('.alt').forEach(e => e.style.opacity = sw); F.tag.style.opacity = sw;
    F.line.style.opacity = ease(t, 11.6, 12.3);
  };
}

// ============ G. close (world x 15200) ============
let Gc = {};
function buildG() {
  const i = 6; const X = 13800; const c = ws('close', X + 96, 200); c.style.width = '1728px';
  c.append(el('p', { class: 'crow ch' }, 'The drawing is right. The board is right. ', el('span', { class: 'w' }, 'The output is wrong.')), el('p', { class: 'crow cname' }, 'BenchMate'), el('p', { class: 'crow ctag' }, 'forecast-first experiments on a real circuit'), el('p', { class: 'crow curl' }, 'bami-codes.github.io/BenchMate'),
    el('div', { class: 'crow cmeta' }, el('span', {}, 'Muse Spark 1.3 · Meta Model API'), el('i'), el('span', {}, 'SAM 3.1'), el('i'), el('span', {}, 'Arduino UNO R4'), el('i'), el('span', {}, 'ngspice'), el('i'), el('span', {}, 'MIT')),
    el('div', { class: 'crow cbuilt' }, el('span', { class: 'tape2' }, 'Built 27 Oct – 4 Nov 2026 · the first commit is the start of the project')),
    el('p', { class: 'crow cfine' }, 'Every number and waveform in this film is read from the public run records. The camera is the only thing we directed.'));
  Gc.rows = [...c.querySelectorAll('.crow')];
  const K = (at, obj) => Object.assign({ t: G(i, at) }, obj);
  CAM.push(K(.9, { x: X + 960, y: 540, z: 1.0 }), K(11, { x: X + 960, y: 540, z: 1.0 }));
  Scn.s7 = (t) => { Gc.rows.forEach((r, k) => { const e = ease(t, .3 + k * .4, 1.0 + k * .4); r.style.opacity = e; r.style.transform = `translateY(${14 * (1 - e)}px)`; }); };
}

// ---------- the frame
function applyCam(t) { const c = camAt(t); world.style.transform = `translate(${960 - c.x * c.z}px, ${540 - c.y * c.z}px) scale(${c.z})`; }
function applyCap(t) { const c = CAPS.find(c => t >= c.a && t < c.b); const s = $('#captxt'); s.textContent = c ? c.text : ''; $('#cap').style.opacity = c ? ease(t, c.a, c.a + .25) * (1 - ease(t, c.b - .25, c.b)) : 0; const l = LOWER.find(w => t >= w.a && t < w.b); $('#lower').style.opacity = l ? ease(t, l.a, l.a + .6) * (1 - ease(t, l.b - .4, l.b)) : 0; }
window.frame = (t) => {
  applyCam(t); applyCap(t);
  // every scene is updated with its own local time (clamped), so a scene's final state persists after it and its initial state precedes it
  SCENES.forEach((s, k) => { const fn = Scn[s.id]; if (!fn) return; const lt = L(k, t); fn(Math.max(-5, Math.min(s.planned + 30, lt))); });
};
window.filmTotal = () => TOTAL();
window.filmCaptions = () => CAPS.map(c => ({ a: c.a, b: c.b, text: c.text }));
window.filmScenes = () => SCENES.map((s, k) => ({ id: s.id, start: sceneStart(k), seconds: s.actual }));
