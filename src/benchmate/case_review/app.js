'use strict';
/* BenchMate case screen. Recorded replay of the Oct 30 physical run, plus a clearly labelled
   scripted mock on a simulated bench. No paid API, no hardware, no inline styles (CSP). */
const $ = id => document.getElementById(id);
const token = document.querySelector('meta[name="benchmate-session"]').content;
const NS = 'http://www.w3.org/2000/svg';
const reduce = matchMedia('(prefers-reduced-motion: reduce)').matches;
const NODES = ['IN', 'OUT', 'REF', 'N1', 'N2', 'UNKNOWN'];
const ACTIVE = ['running', 'awaiting_operator', 'cancelling'];

function E(tag, cls, text) { const n = document.createElement(tag); if (cls) n.className = cls; if (text !== undefined) n.textContent = text; return n; }
function S(tag, attrs, parent) { const n = document.createElementNS(NS, tag); for (const [k, v] of Object.entries(attrs)) n.setAttribute(k, String(v)); if (parent) parent.appendChild(n); return n; }
function button(text, handler, cls = 'linkish') { const b = E('button', cls, text); b.type = 'button'; b.addEventListener('click', handler); return b; }
const store = {
  get(k) { try { return JSON.parse(localStorage.getItem(k)); } catch { return null; } },
  set(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch { /* per-viewer convenience only */ } },
  del(k) { try { localStorage.removeItem(k); } catch { /* ignore */ } },
};
function notice(message) { $('notice').textContent = message || ''; $('notice').hidden = !message; }

async function api(path, body) {
  const controller = new AbortController(), timeout = setTimeout(() => controller.abort(), 15000);
  try {
    const init = body === undefined ? {} : { method: 'POST', headers: { 'Content-Type': 'application/json', 'X-BenchMate-Session': token }, body: JSON.stringify(body) };
    const response = await fetch(path, { signal: controller.signal, ...init });
    const result = await response.json().catch(() => ({}));
    if (!response.ok) { const e = new Error(result.error || 'The local request could not be completed.'); e.status = response.status; throw e; }
    return result;
  } catch (error) {
    if (error.name === 'AbortError') throw new Error('The local server did not answer in time. Nothing was retried automatically.');
    throw error;
  } finally { clearTimeout(timeout); }
}

/* ---------- formatting ---------- */
const clock = s => { s = Math.max(0, Math.floor(s)); return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`; };
const duration = s => { s = Math.floor(s); const m = Math.floor(s / 60), r = s % 60; return m ? `${m} min ${r} s` : `${r} s`; };
const mv = x => x < 10 ? x.toFixed(2) : x.toFixed(1);
const msOf = s => { const v = s * 1000; return v < 10 ? v.toFixed(2) : v.toFixed(1); };
const gain = g => g.toFixed(2);
const ts = iso => Date.parse(iso) / 1000;
function valueText(item) {
  if (item.value_si == null) return 'value unknown';
  if (item.kind === 'R') return item.value_si >= 1000 ? `${+(item.value_si / 1000).toPrecision(4)} kΩ` : `${+item.value_si.toPrecision(4)} Ω`;
  if (item.kind === 'C') return item.value_si >= 1e-6 ? `${+(item.value_si * 1e6).toPrecision(4)} µF` : `${+(item.value_si * 1e9).toPrecision(4)} nF`;
  return String(item.value_si);
}
const ONE = ['zero', 'one', 'two', 'three', 'four', 'five'];

/* ---------- glyphs ---------- */
const GLYPH = {
  pass: '<svg width="18" height="18" aria-hidden="true"><circle cx="9" cy="9" r="8"/></svg>',
  fail: '<svg width="18" height="18" aria-hidden="true"><circle cx="9" cy="9" r="8" fill="#d0302a"/><path d="M5.7 5.7l6.6 6.6M12.3 5.7l-6.6 6.6" stroke="#fff" stroke-width="2.2" stroke-linecap="round"/></svg>',
  open: '<svg width="18" height="18" aria-hidden="true"><circle cx="9" cy="9" r="7" fill="none" stroke="#4b504c" stroke-width="2"/></svg>',
  lock: '<svg width="15" height="17" aria-hidden="true"><rect x="1.5" y="7.5" width="12" height="8.5" fill="none" stroke="#000" stroke-width="1.7"/><path d="M4.3 7.5V5.2a3.2 3.2 0 0 1 6.4 0v2.3" fill="none" stroke="#000" stroke-width="1.7"/></svg>',
};
const SAMPLE = {
  a: '<svg width="22" height="8" aria-hidden="true"><path d="M2 4H20" stroke="#8f948e" stroke-width="2.8" stroke-dasharray="0.1 6" stroke-linecap="round"/></svg>',
  b: '<svg width="22" height="8" aria-hidden="true"><path d="M1 4H21" stroke="#2b58b0" stroke-width="2.4" stroke-dasharray="9 5"/></svg>',
  red: '<svg width="22" height="8" aria-hidden="true"><path d="M1 4H21" stroke="#d0302a" stroke-width="2.4"/></svg>',
};
const STYLE = {
  a: { stroke: '#8f948e', 'stroke-width': 2.8, 'stroke-dasharray': '0.1 6', 'stroke-linecap': 'round' },
  b: { stroke: '#2b58b0', 'stroke-width': 2.4, 'stroke-dasharray': '9 5' },
  red: { stroke: '#d0302a', 'stroke-width': 2.2, 'stroke-linejoin': 'round' },
};

/* ---------- oscilloscope ---------- */
const NICE_V = [.005, .01, .02, .025, .03, .04, .05, .06, .08, .1, .2, .25, .4, .5];
const NICE_T = [.05, .1, .2, .25, .3, .5, .6, 1, 1.2, 2, 4];
function scaleFor(series) {
  let tmax = 0;
  for (const s of series) for (const t of s.t) tmax = Math.max(tmax, t);
  const win = NICE_T.find(w => w >= tmax) || tmax || NICE_T[0];
  let lo = Infinity, hi = -Infinity;
  for (const s of series) s.v.forEach((v, i) => { if (s.t[i] <= win) { lo = Math.min(lo, v); hi = Math.max(hi, v); } });
  if (!Number.isFinite(lo)) { lo = -.1; hi = .1; }
  // fill about six of eight divisions and leave the top band free for the on-screen key
  const vdiv = NICE_V.find(n => (hi - lo) / n <= 6.6) || .5, q = vdiv / 5;
  return { win, vdiv, center: Math.round(((lo + hi) / 2 + .45 * vdiv) / q) * q };
}
function readout(sc) {
  const td = sc.win / 10;
  return `<span>${Math.round(sc.vdiv * 1000)} mV/div</span><span>${td >= 1 ? td + ' s' : +(td * 1000).toFixed(1) + ' ms'}/div</span>`;
}
function pathOf(s, sc) {
  const X = t => t / sc.win * 500, Y = v => 200 - (v - sc.center) / sc.vdiv * 50;
  let d = '';
  for (let i = 0; i < s.t.length; i++) {
    if (s.t[i] > sc.win) break;
    d += (d ? 'L' : 'M') + X(s.t[i]).toFixed(1) + ' ' + Math.max(-10, Math.min(410, Y(s.v[i]))).toFixed(1);
  }
  return d;
}
/* layers: [{t, v, style, sweep, fade}] ; sweep layers are revealed together by the beam */
function drawScope(svg, sc, layers, animate) {
  svg.replaceChildren();
  const g = S('g', { stroke: '#dde0d9', 'stroke-width': 1, 'vector-effect': 'non-scaling-stroke' }, svg);
  for (let i = 1; i < 10; i++) S('line', { x1: i * 50, x2: i * 50, y1: 0, y2: 400 }, g);
  for (let j = 1; j < 8; j++) S('line', { x1: 0, x2: 500, y1: j * 50, y2: j * 50 }, g);
  const ax = S('g', { stroke: '#b9beb5', 'stroke-width': 1, 'vector-effect': 'non-scaling-stroke' }, svg);
  S('line', { x1: 250, x2: 250, y1: 0, y2: 400 }, ax); S('line', { x1: 0, x2: 500, y1: 200, y2: 200 }, ax);
  for (let i = 1; i < 50; i++) S('line', { x1: i * 10, x2: i * 10, y1: 196, y2: 204 }, ax);
  for (let j = 1; j < 40; j++) S('line', { x1: 246, x2: 254, y1: j * 10, y2: j * 10 }, ax);
  if (!sc) return;
  const zy = 200 + sc.center / sc.vdiv * 50;
  if (zy > 8 && zy < 392) S('path', { d: `M0 ${zy - 6}L9 ${zy}L0 ${zy + 6}Z`, fill: '#4b504c' }, svg);
  const sweep = animate && !reduce;
  let clipGroup = null, rect = null;
  if (layers.some(l => l.sweep)) {
    const id = svg.id + '-clip', cp = S('clipPath', { id }, S('defs', {}, svg));
    rect = S('rect', { x: 0, y: -20, width: sweep ? 0 : 500, height: 440 }, cp);
    clipGroup = S('g', { 'clip-path': `url(#${id})` });
  }
  for (const l of layers) {
    const p = S('path', { d: pathOf(l, sc), fill: 'none', 'vector-effect': 'non-scaling-stroke', ...l.style }, l.sweep ? clipGroup : svg);
    if (l.fade && !reduce) { p.style.opacity = '0'; requestAnimationFrame(() => requestAnimationFrame(() => { p.style.transition = 'opacity .6s'; p.style.opacity = '1'; })); }
  }
  if (clipGroup) svg.appendChild(clipGroup);
  if (sweep && rect) {
    const beam = S('line', { x1: 0, x2: 0, y1: 0, y2: 400, stroke: '#d0302a', 'stroke-width': 1, opacity: .35, 'vector-effect': 'non-scaling-stroke' }, svg);
    const t0 = performance.now(), dur = 1400;
    const tick = now => {
      const k = Math.max(0, Math.min(1, (now - t0) / dur)), x = (500 * (1 - Math.pow(1 - k, 1.7))).toFixed(1);
      rect.setAttribute('width', x); beam.setAttribute('x1', x); beam.setAttribute('x2', x);
      if (k < 1) requestAnimationFrame(tick); else beam.remove();
    };
    requestAnimationFrame(tick);
  }
}
function overlay(el, html) { el.hidden = !html; el.innerHTML = html || ''; }
function verdictHTML(score, words) {
  if (!score) return '';
  const pass = score.passed, w = words || { pass: 'survives', fail: 'ruled out' };
  if (!pass && score.RMS_mV <= 9) return `${GLYPH.fail}<span><b>${mv(score.RMS_mV)} mV RMS</b> <span class="why">regional check failed</span></span>`;
  return pass ? `${GLYPH.pass}<span><b>Within ${mv(score.RMS_mV)} mV</b> <span class="why">${w.pass}</span></span>`
              : `${GLYPH.fail}<span><b>Misses by ${mv(score.RMS_mV)} mV</b> <span class="why">${w.fail}</span></span>`;
}
function setVerdict(el, html, delayed) {
  el.innerHTML = html;
  if (delayed && !reduce && html) { el.classList.add('hide'); setTimeout(() => el.classList.remove('hide'), 1300); }
  else el.classList.remove('hide');
}

/* ---------- state ---------- */
let current = null;           // case result
let snap = null, outline = null, cond = 'attach_output_load_step';
const cache = new Map();
let playing = false, timer = null, loading = false, caseEpoch = 0;

/* ---------- library and routing ---------- */
async function refreshLibrary() {
  const state = await api('/api/state');
  const picker = $('case-picker');
  picker.replaceChildren(new Option('Saved questions', ''));
  state.cases.forEach(c => picker.add(new Option(c.question.length > 60 ? c.question.slice(0, 58) + '…' : c.question, c.case_id)));
  picker.value = current?.manifest.case_id || '';
}
function showAsk() {
  caseEpoch++; stopPlay(); stopMock(); resetMockView(); loading = false;
  current = null; snap = null; outline = null; cache.clear();
  $('ask').hidden = false; $('case').hidden = true;
  history.replaceState(null, '', '/');
  $('case-picker').value = '';
  notice('');
  document.title = 'BenchMate';
}
async function guarded(fn) {
  document.body.setAttribute('aria-busy', 'true');
  try { notice(''); return await fn(); }
  catch (error) { stopPlay(); notice(error.message); return undefined; }
  finally { document.body.removeAttribute('aria-busy'); }
}

/* ---------- a case ---------- */
const linked = () => !!current?.manifest.experiment_link && current.replay_eligibility.allowed;
function design() {
  const d = current.manifest.intended_design;
  return (d.reviewed && d.reviewed.candidate) || d.draft_candidate;
}
async function openCase(id, cursor = 0) {
  const epoch = ++caseEpoch;
  stopPlay(); stopMock(); resetMockView(); loading = false;
  const result = await api(`/api/cases/${encodeURIComponent(id)}`);
  if (epoch !== caseEpoch) return;
  current = result;
  snap = null; outline = null; cache.clear();
  const m = current.manifest;
  $('ask').hidden = true; $('case').hidden = false;
  $('q').textContent = m.question.text;
  document.title = 'BenchMate: ' + m.question.text.slice(0, 60);
  $('case-picker').value = m.case_id;
  renderReview();
  renderProvenance(); loadBoardPhoto();
  $('replay').hidden = !linked();
  $('mock').hidden = !linked();
  if (linked()) {
    if (!await loadOutline(epoch)) return;
    await go(cursor, { initial: true });
    if (epoch === caseEpoch) await initMock();
  } else {
    renderAnswerLine(); renderSchematic();
    history.replaceState(null, '', `?case=${m.case_id}`);
  }
}

/* schematic drawn from the reviewed design (one R from IN to OUT, one C from OUT to REF) */
function renderSchematic() {
  const fig = $('schem'); fig.replaceChildren();
  const parts = design().components;
  const R = parts.find(p => p.kind === 'R' && p.a === 'IN' && p.b === 'OUT');
  const C = parts.find(p => p.kind === 'C' && p.a === 'OUT' && p.b === 'REF');
  if (!R || !C || parts.length !== 2) {
    const img = E('img'); img.src = '/schematic.png'; img.alt = 'The schematic'; fig.append(img, E('figcaption', null, 'The schematic file'));
    return;
  }
  const art = E('div', 'schem-art'); fig.append(art);
  const svg = S('svg', { viewBox: '0 0 400 156', role: 'img', 'aria-label': `${R.name} ${valueText(R)} from IN to OUT, ${C.name} ${valueText(C)} from OUT to REF` }, art);
  const glow = S('rect', { x: 198, y: 46, width: 56, height: 88, fill: '#f3c300', opacity: 0 }, svg);
  S('path', { d: 'M16 40H90M162 40H384M226 40V82M226 96V138H16', fill: 'none', stroke: '#000', 'stroke-width': 2 }, svg);
  S('rect', { x: 90, y: 29, width: 72, height: 22, fill: '#f8f9f5', stroke: '#000', 'stroke-width': 2 }, svg);
  S('path', { d: 'M202 82H250M202 96H250', stroke: '#000', 'stroke-width': 3.4 }, svg);
  S('circle', { cx: 226, cy: 40, r: 3.6 }, svg);
  const term = S('g', { fill: '#e8eae5', stroke: '#000', 'stroke-width': 2 }, svg);
  [[12, 40], [388, 40], [12, 138]].forEach(([cx, cy]) => S('circle', { cx, cy, r: 4 }, term));
  const lab = S('g', { 'font-size': 13, fill: '#4b504c' }, svg);
  S('text', { x: 10, y: 24 }, lab).textContent = 'IN';
  S('text', { x: 390, y: 24, 'text-anchor': 'end' }, lab).textContent = 'OUT';
  S('text', { x: 10, y: 122 }, lab).textContent = 'REF';
  const rt = S('text', { x: 126, y: 20, 'text-anchor': 'middle', 'font-size': 14 }, svg);
  S('tspan', { 'font-weight': 700 }, rt).textContent = R.name; rt.append(' ' + valueText(R));
  const ct = S('text', { x: 262, y: 87, 'font-size': 14 }, svg);
  S('tspan', { 'font-weight': 700 }, ct).textContent = C.name; ct.append(' ' + valueText(C));
  const markR = S('g', { 'font-size': 13 }, svg), markC = S('g', { 'font-size': 13 }, svg);
  const tape = E('span', 'tape'); tape.hidden = true;
  const tau = R.value_si && C.value_si ? R.value_si * C.value_si : null;
  art.append(tape);
  fig.append(E('figcaption', null, linked() ? `Your confirmed design: τ = ${R.name} × ${C.name} = ${tau ? msOf(tau) + ' ms' : 'unknown'}` : `Read from the schematic, not yet confirmed`));
  fig._parts = { glow, markR, markC, tape };
  updateSchematicMarks(false);
}
function mark(g, x, y, glyph, text) {
  g.replaceChildren(); if (!glyph) return;
  const G = {
    open: '<circle cx="7" cy="7" r="5.6" fill="none" stroke="#4b504c" stroke-width="1.8"/>',
    fail: '<circle cx="7" cy="7" r="7" fill="#d0302a"/><path d="M4.4 4.4l5.2 5.2M9.6 4.4l-5.2 5.2" stroke="#fff" stroke-width="1.9" stroke-linecap="round"/>',
    pass: '<circle cx="7" cy="7" r="7"/>',
  }[glyph];
  const s = S('g', { transform: `translate(${x} ${y})` }, g);
  s.innerHTML = G;
  S('text', { x: 20, y: 11.5, fill: glyph === 'open' ? '#4b504c' : '#000' }, s).textContent = text;
}
function updateSchematicMarks(animate) {
  const parts = $('schem')._parts; if (!parts) return;
  const { glow, markR, markC, tape } = parts;
  const h = snap ? Object.fromEntries(snap.hypotheses.map(x => [x.id, x.status])) : {};
  const started = snap && snap.messages.some(m => m.sequence >= 48);
  const word = { unresolved: 'open', rejected: 'fail', supported: 'pass' };
  const txt = (who, st) => st === 'rejected' ? `Bigger ${who} ruled out` : st === 'supported' ? `Bigger ${who} survives` : `Bigger ${who}?`;
  if (!started) { mark(markR); mark(markC); }
  else { mark(markR, 70, 60, word[h.r_changed], txt('R', h.r_changed)); mark(markC, 262, 96, word[h.c_changed], txt('C', h.c_changed)); }
  const done = !!snap?.answer;
  const cf = snap?.messages.find(m => m.sequence === 48)?.models?.c_changed?.C_f;
  tape.hidden = !done || !cf; glow.setAttribute('opacity', done ? .55 : 0);
  if (cf) tape.textContent = `acts like ${(cf * 1e6).toFixed(1)} µF`;
  if (done && animate && !reduce) { tape.classList.remove('stick'); void tape.offsetWidth; tape.classList.add('stick'); }
}

/* Historical references are separate from a case's measured specimen. */
const PHOTO = { catalog: null, selected: null, defaultId: null };
async function loadBoardPhoto() {
  const epoch = caseEpoch;
  $('board-photo').hidden = true; $('board-ph').hidden = false;
  $('board-open').disabled = true; $('boardslot').classList.add('empty');
  $('board-caption').textContent = 'No specimen photo linked';
  if (!current || current.manifest.scope !== 'recorded_walkthrough') return;
  try {
    if (!PHOTO.catalog) { const catalog = await api('/api/photo-evidence'); PHOTO.catalog = catalog.photos; PHOTO.defaultId = catalog.default_reference_id; }
    if (epoch !== caseEpoch) return;
    PHOTO.selected = PHOTO.catalog.find(p => p.id === PHOTO.defaultId && p.available) || PHOTO.catalog.find(p => p.id === 'img_8887' && p.available) || PHOTO.catalog.find(p => p.available);
    if (!PHOTO.selected) return;
    const p = PHOTO.selected, img = $('board-photo');
    img.onload = () => { if (epoch === caseEpoch) { img.hidden = false; $('board-ph').hidden = true; $('boardslot').classList.remove('empty'); $('board-open').disabled = false; } };
    img.onerror = () => { if (epoch === caseEpoch) { img.hidden = true; $('board-ph').hidden = false; } };
    img.alt = p.label + '. Reference only; specimen state unconfirmed.';
    // Use the verified source endpoint. /board.jpg is also available for registered photo IDs.
    img.src = p.image_url;
    $('board-caption').textContent = (p.role === 'operator_supplied_reference' ? 'Photo reference' : 'Historical reference') + ' · state unconfirmed';
  } catch { $('board-ph').textContent = 'Photo evidence is unavailable on this server.'; }
}
function renderPhotoEvidence() {
  const p = PHOTO.selected; if (!p) return;
  const image = $('photo-evidence-image'), select = $('photo-mask');
  image.src = p.image_url; image.alt = p.label;
  $('photo-state').textContent = p.notice;
  $('photo-full').href = p.master_url;
  $('photo-hash').textContent = p.photo_sha256;
  select.replaceChildren(new Option('Original photo', ''));
  for (const t of p.sam_trials) for (const mask of t.masks) select.add(new Option(`Recorded SAM: ${t.concept}`, mask.overlay_url));
  select.disabled = select.options.length === 1;
  const results = $('photo-trials'); results.replaceChildren();
  for (const t of p.sam_trials) results.append(E('li', null, `${t.concept}: ${t.match_count} ${t.match_count === 1 ? 'mask' : 'masks'} · recorded Nov 1`));
  $('photo-mask-note').textContent = p.sam_trials.length ? 'All five trials are retained. A mask is a visual pointer; a miss does not prove absence. No additional D01 capacitor has been identified.' : 'No SAM mask was recorded on this image. Photographs from different states are not combined.';
}
function openPhotoEvidence() {
  if (!PHOTO.catalog || !PHOTO.selected) return;
  const sel = $('photo-picker'); sel.replaceChildren();
  for (const p of PHOTO.catalog.filter(p => p.available)) sel.add(new Option(p.label, p.id));
  sel.value = PHOTO.selected.id; renderPhotoEvidence(); $('photo-dialog').showModal();
}

/* ---------- design review ---------- */
function renderReview() {
  const m = current.manifest, cand = m.intended_design.draft_candidate, sealed = !!m.experiment_link;
  $('review').hidden = linked();
  const list = $('components'); list.replaceChildren();
  cand.components.forEach((c, i) => {
    const box = E('div', 'component'), title = E('p', 'component-title');
    title.append(E('b', null, `${c.name}, ${c.kind === 'R' ? 'resistor' : c.kind === 'C' ? 'capacitor' : 'part'}`), E('span', null, `Read as “${c.marking || c.name}”`));
    const grid = E('div', 'cgrid');
    const unit = c.kind === 'R' ? 1000 : c.kind === 'C' ? 1e-6 : 1;
    const val = E('input'); Object.assign(val, { id: `value-${i}`, type: 'number', step: 'any', min: '0', placeholder: 'Unknown' });
    val.value = c.value_si == null ? '' : String(Number((c.value_si / unit).toPrecision(12)));
    const l1 = E('label', null, c.kind === 'R' ? 'Value in kΩ' : c.kind === 'C' ? 'Value in µF' : 'Value'); l1.append(val); grid.append(l1);
    for (const key of ['a', 'b']) {
      const sel = E('select'); sel.id = `${key}-${i}`; NODES.forEach(n => sel.add(new Option(n, n))); sel.value = c[key];
      const l = E('label', null, key === 'a' ? 'From' : 'To'); l.append(sel); grid.append(l);
    }
    box.append(title, grid); list.append(box);
  });
  $('review-fields').disabled = sealed;
  const gate = $('gate'), elig = current.replay_eligibility;
  gate.classList.toggle('bad', m.revision > 1 && !elig.allowed);
  gate.textContent = m.scope === 'different_specimen' ? 'A different circuit needs its own measurements. The recorded run cannot answer for it.'
    : m.revision === 1 ? 'Check each value and connection, then confirm.' : elig.message;
}
function candidateFromForm() {
  const cand = structuredClone(current.manifest.intended_design.draft_candidate);
  cand.components.forEach((c, i) => {
    const raw = $(`value-${i}`).value, unit = c.kind === 'R' ? 1000 : c.kind === 'C' ? 1e-6 : 1;
    c.value_si = raw === '' ? null : Number(raw) * unit;
    c.a = $(`a-${i}`).value; c.b = $(`b-${i}`).value;
    if (c.value_si !== null && (!Number.isFinite(c.value_si) || c.value_si <= 0)) throw new Error('Use a positive value, or leave it blank if unknown.');
  });
  const unknown = cand.components.some(x => x.value_si === null || [x.a, x.b].includes('UNKNOWN'));
  cand.status = unknown ? 'incomplete' : 'needs_review';
  cand.ambiguities = unknown ? ['Operator left a value or connection unresolved.'] : [];
  return cand;
}

/* ---------- recorded replay ---------- */
async function snapshotAt(cursor) {
  const id = current.manifest.case_id, key = `${id}:${cursor}`;
  if (!cache.has(key)) cache.set(key, await api(`/api/cases/${id}/timeline?cursor=${cursor}`));
  return cache.get(key);
}
function kindOf(actor) { return actor === 'Muse Spark' ? 'spark' : actor === 'Operator' ? 'op' : 'bench'; }
async function loadOutline(epoch) {
  const first = await snapshotAt(0);
  if (epoch !== caseEpoch) return false;
  const last = await snapshotAt(first.last_sequence);
  if (epoch !== caseEpoch) return false;
  const t0 = ts(first.timestamp), times = new Map(last.evidence.map(e => [e.sequence, ts(e.timestamp)]));
  times.set(0, t0); times.set(last.last_sequence, ts(last.timestamp));
  const actors = new Map(last.messages.map(m => [m.sequence, m.actor]));
  if (last.answer) actors.set(137, 'BenchMate');
  outline = {
    t0, end: ts(last.timestamp) - t0, last: first.last_sequence,
    steps: first.steps.map(seq => ({ seq, kind: kindOf(actors.get(seq)), t: (times.get(seq) ?? t0) - t0, actor: actors.get(seq) || 'Bench' })),
    times,
  };
  return true;
}
const timeOf = seq => (outline.times.get(seq) ?? outline.t0) - outline.t0;
function stateIn(s, id) {
  if (!s) return 'future';
  const p = s.plots.find(p => p.id === id);
  if (p) return Object.keys(p.scores).length ? 'scored' : 'captured';
  if (id !== 'unloaded_step' && s.messages.some(m => m.frozen_models)) return 'locked';
  return 'future';
}
function condForCursor(s) {
  const seqs = new Set(s.messages.map(m => m.sequence));
  if (s.answer) return 'attach_output_load_step';
  if (seqs.has(97)) return 'reserved_sine';
  if (seqs.has(49)) return 'attach_output_load_step';
  return 'unloaded_step';
}
async function go(target, { user = false, initial = false } = {}) {
  if (loading) return;
  const epoch = caseEpoch;
  loading = true;
  if (user) stopPlay();
  try {
    const prev = snap;
    const next = await snapshotAt(Math.max(0, Math.min(outline.last, target)));
    if (epoch !== caseEpoch) return;
    snap = next; cond = condForCursor(next);
    const forward = !prev || next.cursor > prev.cursor;
    const was = initial ? 'future' : stateIn(prev, cond), now = stateIn(next, cond);
    const measuredNow = now === 'captured' || now === 'scored', measuredBefore = was === 'captured' || was === 'scored';
    const sweep = forward && measuredNow && !measuredBefore;
    const fade = forward && !initial && now === 'scored' && was === 'captured';
    renderStage({ sweep, fade });
    renderLog(); renderRail();
    const newAnswer = !!next.answer && (initial || !prev?.answer);
    renderAnswerLine(newAnswer && forward);
    renderSchematic(); updateSchematicMarks(newAnswer && forward);
    renderMore();
    history.replaceState(null, '', `?case=${current.manifest.case_id}&event=${next.cursor}`);
  } finally { if (epoch === caseEpoch) loading = false; }
}
function stepAfter(dir) {
  const steps = snap.steps, c = snap.cursor;
  return dir > 0 ? (steps.find(n => n > c) ?? outline.last) : ([...steps].reverse().find(n => n < c) ?? 0);
}

const LOCK_NOTE = { attach_output_load_step: 'with the 9.99 kΩ load, before it was measured', reserved_sine: 'on the reserved sine, before it was measured' };
function renderStage({ sweep = false, fade = false } = {}) {
  const st = stateIn(snap, cond), plot = snap.plots.find(p => p.id === cond);
  const frozen = snap.messages.find(m => m.frozen_models);
  const tau = snap.messages.find(m => m.sequence === 48)?.metrics?.tau_ms;
  document.querySelectorAll('.cond[data-c]').forEach(b => b.setAttribute('aria-pressed', b.dataset.c === cond));
  const sharedScale = plot ? scaleFor([{t: plot.time_s, v: plot.observed_v},
    ...['r_changed', 'c_changed'].filter(k => plot.predictions[k]).map(k => ({t: plot.time_s, v: plot.predictions[k]}))]) : null;
  for (const [side, key] of [['A', 'r_changed'], ['B', 'c_changed']]) {
    const svg = $('scr' + side), ov = $('ov' + side), v = $('v' + side), ro = $('ro' + side), keyEl = $('key' + side);
    const label = key === 'r_changed' ? 'R about 21 kΩ, C 1 µF' : 'C about 2.1 µF, R 10 kΩ';
    const pm = snap.messages.find(m => m.sequence === 48)?.models?.[key];
    const exact = pm ? (key === 'r_changed' ? `R about ${(pm.R_ohm / 1000).toFixed(1)} kΩ, C ${valueText({ kind: 'C', value_si: pm.C_f })}` : `C about ${(pm.C_f * 1e6).toFixed(2)} µF, R ${valueText({ kind: 'R', value_si: pm.R_ohm })}`) : label;
    const sideStyle = side === 'A' ? 'a' : 'b';
    if (st === 'future') {
      drawScope(svg, null, [], false); ro.innerHTML = '';
      overlay(ov, snap.cursor < 48 ? 'Waiting for the first measurement' : 'Not measured yet at this point in the run');
      keyEl.innerHTML = ''; setVerdict(v, ''); continue;
    }
    if (st === 'locked') {
      const fm = frozen.frozen_models[key];
      drawScope(svg, null, [], false); ro.innerHTML = '';
      overlay(ov, `<div class="panel"><div class="when">${GLYPH.lock}Locked at ${clock(timeOf(frozen.sequence))}</div><div class="vals">Gain ${gain(fm.gain)}, τ ${msOf(fm.tau_s)} ms</div><div class="cond2">${LOCK_NOTE[cond]}</div></div>`);
      keyEl.innerHTML = `<span>${exact}</span>`;
      setVerdict(v, '<span class="why">Not measured yet</span>'); continue;
    }
    overlay(ov, '');
    const observed = { t: plot.time_s, v: plot.observed_v, style: STYLE.red, sweep: true };
    const pred = plot.predictions[key];
    const layers = [];
    if (pred) layers.push({ t: plot.time_s, v: pred, style: STYLE[sideStyle], sweep: sweep, fade: fade && !sweep });
    layers.push(observed);
    const sc = sharedScale;
    drawScope(svg, sc, layers, sweep);
    ro.innerHTML = readout(sc);
    keyEl.innerHTML = (pred ? `<span>${SAMPLE[sideStyle]}${exact}</span>` : `<span>${exact}</span>`) + `<span>${SAMPLE.red}Measured</span>`;
    if (cond === 'unloaded_step') setVerdict(v, `${GLYPH.open}<span><b>τ ${tau ? tau.toFixed(1) : ''} ms</b> <span class="why">this curve fits both explanations</span></span>`, sweep);
    else if (st === 'captured') setVerdict(v, '<span class="why">Measured. The recorded comparison comes next.</span>', sweep);
    else setVerdict(v, verdictHTML(plot.scores[key]), sweep || fade);
  }
}

function originalText(o) {
  if (o == null) return '';
  if (typeof o === 'string') return o;
  if (typeof o.instruction === 'string') return o.instruction;
  if (typeof o.verbatim === 'string') return o.verbatim;
  return Object.values(o).filter(v => typeof v === 'string').join('\n');
}
const CHOICE = { attach_output_load_step: 'the load test', repeat_unloaded_step: 'repeat the unloaded step' };
function logEntries() {
  const list = snap.messages.map(m => ({ ...m, kind: kindOf(m.actor) }));
  if (snap.answer) list.push({ sequence: 137, actor: 'BenchMate', kind: 'bench', title: 'Answer from the recorded result', text: `${snap.answer.title} ${snap.answer.assumption}`, source: 'summary', original: snap.answer.original, refs: [137] });
  return list;
}
const LOG_SUMMARIES = {
  7: 'Measure an unloaded step to find the time constant.',
  49: 'R and C both explain the first response. Freeze both models before the load test.',
  52: 'Repeating the step cannot separate R from C. A 9.99 kΩ load changes the gain and separates them.',
  54: 'The bench requested USB-off load connection and retained wiring. Historical instruction only.',
  97: 'Spark requested the reserved check. The protocol specified a 5 Hz sine.'
};
function renderLog() {
  const ol = $('entries'); ol.replaceChildren();
  const list = logEntries();
  if (!list.length) { ol.append(E('li', 'empty-log', 'The run is about to start. Press Play the run, or step through it.')); }
  let prevT = null, nowEl = null;
  list.forEach((m, i) => {
    const t = timeOf(m.sequence);
    if (prevT !== null && t - prevT > 60) ol.append(E('li', 'gap', `${duration(t - prevT)} ${m.kind === 'op' ? 'until the operator report' : 'between recorded steps'}`));
    prevT = t;
    const last = i === list.length - 1;
    const li = E('li', `entry k-${m.kind} ${last ? 'now' : 'past'} jump`);
    if (last) li.setAttribute('aria-current', 'step');
    const bd = E('div', 'bd');
    bd.append(E('span', 'who', m.actor));
    if (m.emphasis) { bd.append(E('br')); bd.append(E('span', 'tape small', m.title)); }
    else bd.append(E('div', 'ttl', m.title));
    const short = LOG_SUMMARIES[m.sequence], text = short || m.text;
    if (m.request) {
      const req = E('div', 'req', text);
      req.append(E('p', null, m.operator_confirmed ? 'Historical request. The operator reported it done.' : 'Historical request. Nothing to do now.'));
      bd.append(req);
    } else bd.append(E('div', 'txt', text));
    if (short) { const d = E('details'); d.append(E('summary', null, 'Full explanation'), E('p', null, m.text)); d.addEventListener('click', e => e.stopPropagation()); bd.append(d); }
    if (m.frozen_models) {
      const f = m.frozen_models;
      bd.append(E('div', 'txt', `More resistance: gain ${gain(f.r_changed.gain)}, τ ${msOf(f.r_changed.tau_s)} ms. More capacitance: gain ${gain(f.c_changed.gain)}, τ ${msOf(f.c_changed.tau_s)} ms.`));
    }
    if (m.choices) bd.append(E('div', 'txt', `Offered: ${m.choices.map(c => CHOICE[c] || c.replaceAll('_', ' ')).join(' or ')}.`));
    const src = E('div', 'src');
    if (short) src.append(E('span', null, 'Summarized for this screen.'));
    else if (m.source === 'screen_translation') src.append(E('span', null, 'Translated from Korean.'));
    if (m.source === 'runner_instruction_translation') src.append(E('span', null, 'Bench instruction, translated.'));
    src.append(E('span', null, 'Record'));
    (m.refs || [m.sequence]).forEach(seq => src.append(button(`event ${seq}`, e => { e.stopPropagation(); showEvent(seq); })));
    bd.append(src);
    const orig = originalText(m.original);
    if (orig && (m.source === 'screen_translation' || m.source === 'runner_instruction_translation' || m.actor === 'Operator')) {
      const d = E('details'); d.append(E('summary', null, 'Original'), E('p', null, orig)); d.addEventListener('click', e => e.stopPropagation()); bd.append(d);
    }
    li.append(E('span', 'tm', clock(t)), bd);
    li.addEventListener('click', () => { const target = snap.steps.find(n => n >= m.sequence) ?? m.sequence; if (target !== snap.cursor) go(target, { user: true }); });
    ol.append(li); if (last) nowEl = li;
  });
  const sc = $('logscroll');
  if (nowEl && sc.scrollHeight > sc.clientHeight) sc.scrollTo({ top: Math.max(0, nowEl.offsetTop - sc.clientHeight * .3), behavior: reduce ? 'auto' : 'smooth' });
}
function renderRail() {
  const r = $('rail'); r.replaceChildren();
  const steps = outline.steps, n = steps.length - 1;
  for (let i = 0; i < n; i++) {
    const gapS = steps[i + 1].t - steps[i].t, seg = E('div', 'seg' + (gapS > 60 ? ' wire' : ''));
    seg.style.left = (i / n * 100) + '%'; seg.style.width = (100 / n) + '%'; r.append(seg);
    if (gapS > 60) { const lab = E('div', 'seglabel', `${steps[i + 1].kind === 'op' ? 'operator interval' : 'interval'}, ${duration(gapS)}`); lab.style.left = ((i + .5) / n * 100) + '%'; r.append(lab); }
  }
  steps.forEach((s, i) => {
    const state = s.seq < snap.cursor ? 'done' : s.seq === snap.cursor ? 'now' : '';
    const b = E('button', `tick k-${s.kind} ${state}`); b.type = 'button';
    b.style.left = (i / n * 100) + '%'; b.title = `${clock(s.t)} ${s.actor}`; b.setAttribute('aria-label', `Go to ${clock(s.t)}, ${s.actor}`);
    b.addEventListener('click', () => go(s.seq, { user: true }));
    r.append(b);
  });
  $('clock').innerHTML = `${clock(timeOf(snap.cursor))} <span>of ${clock(outline.end)}</span>`;
  $('back').disabled = snap.cursor === 0; $('fwd').disabled = snap.cursor === outline.last;
}
function renderAnswerLine(animate = false) {
  const a = $('answerline'); a.replaceChildren();
  if (!linked()) { a.append(E('span', 'pending', current.manifest.scope === 'different_specimen' ? 'A different circuit needs its own measurements.' : 'Confirm the design to open the recorded experiment.')); return; }
  if (!snap?.answer) { a.append(E('span', 'pending', 'The answer appears when the run reaches it.')); return; }
  const tape = E('span', 'tape big' + (animate && !reduce ? ' stick' : ''), snap.answer.title);
  const changes = snap.messages.filter(m => m.request).length;
  a.append(tape, E('span', 'note', snap.answer.assumption), E('span', 'facts', `Muse Spark reported it after ${ONE[changes] || changes} wiring change${changes === 1 ? '' : 's'}, ${duration(timeOf(137))} into the run.`));
}
const LEDGER = { nominal_rc: 'Design unchanged', r_changed: 'More resistance', c_changed: 'More capacitance' };
function renderMore() {
  const holds = $('holds'); holds.replaceChildren();
  const a = snap.answer;
  if (!a) holds.append(E('p', 'pending', 'This fills in when the recorded run reaches its answer.'));
  else for (const [h, t] of [['Measured', a.observed], ['Assumed', a.assumption], ['Still unknown', a.unknown]]) { const d = E('div'); d.append(E('h4', null, h), E('p', null, t)); holds.append(d); }
  const led = $('ledger'); led.replaceChildren();
  snap.hypotheses.forEach(hy => {
    const li = E('li'), g = E('span'); g.innerHTML = { unresolved: GLYPH.open, rejected: GLYPH.fail, supported: GLYPH.pass }[hy.status];
    const parts = [];
    if (hy.scores.loaded_step !== undefined) parts.push(`load test ${mv(hy.scores.loaded_step)} mV`);
    if (hy.scores.reserved_sine !== undefined) parts.push(`reserved sine ${mv(hy.scores.reserved_sine)} mV`);
    li.append(g, E('span', null, `${LEDGER[hy.id] || hy.label}${hy.status === 'rejected' ? ', ruled out' : hy.status === 'supported' ? ', survives' : ', open'}`), E('span', 'sc', parts.join(', ')));
    led.append(li);
  });
  $('ask-more').hidden = !a;
  const asks = $('asks');
  if (a && asks.dataset.cursor !== String(snap.cursor)) {
    asks.dataset.cursor = String(snap.cursor); asks.replaceChildren(); $('reply').replaceChildren();
    snap.followups.forEach(f => {
      const b = E('button', 'askq', f.question); b.type = 'button'; b.setAttribute('aria-expanded', 'false');
      b.addEventListener('click', () => {
        asks.querySelectorAll('.askq').forEach(x => x.setAttribute('aria-expanded', x === b));
        const r = $('reply'); r.replaceChildren(E('div', 'from', 'Answered from this run’s record. Prepared question.'), E('p', null, f.text));
        const src = E('div', 'src');
        (f.refs || []).forEach(seq => src.append(button(`event ${seq}`, () => showEvent(seq))));
        if (f.plot) src.append(button('Show it on the scopes', () => { cond = f.plot; renderStage(); $('replay').scrollIntoView({ block: 'start', behavior: reduce ? 'auto' : 'smooth' }); }));
        r.append(src);
      });
      asks.append(b);
    });
  }
}

/* playback */
function stopPlay() { playing = false; if (timer) clearTimeout(timer); timer = null; $('playlabel').textContent = 'Play the run'; $('playicon').innerHTML = '<path d="M1 .5l9 5.5-9 5.5z"/>'; }
function schedule() {
  if (!playing) return;
  const epoch = caseEpoch, nextSeq = stepAfter(1);
  const reveals = [48, 93, 94, 132, 133].includes(nextSeq);
  timer = setTimeout(async () => {
    if (!playing) return;
    await guarded(() => go(nextSeq));
    if (epoch !== caseEpoch || !snap) return;
    if (snap.cursor >= outline.last) stopPlay(); else schedule();
  }, snap.cursor === 0 ? 900 : reveals ? 2000 : 2600);
}
async function togglePlay() {
  if (playing) { stopPlay(); return; }
  playing = true; $('playlabel').textContent = 'Pause'; $('playicon').innerHTML = '<path d="M1 .5h3v11H1zM7 .5h3v11H7z"/>';
  if (snap.cursor >= outline.last) await guarded(() => go(0));
  schedule();
}

/* ---------- records ---------- */
function renderProvenance() {
  const m = current.manifest, d = m.intended_design, dl = $('provenance'); dl.replaceChildren();
  const rows = {
    'Question': 'Entered here. Not sent to a model and not an input to the Oct 30 run.',
    'Schematic reading': 'Oct 31, recorded Muse Spark output on the example schematic',
    'Physical run': m.experiment_link ? 'Oct 30. Its protocol supplied the same nominal design; the board itself is not linked to this case.' : 'Not linked',
    'English text': 'Translated or summarized for this screen. Each Korean original is available.',
    'Physical record SHA-256': m.experiment_link?.record_sha256 || 'Not linked',
    'Schematic record SHA-256': d.vision_record_sha256,
    'Case revision': `${m.revision}, manifest ${current.manifest_sha256}`,
  };
  for (const [k, v] of Object.entries(rows)) dl.append(E('dt', null, k), E('dd', null, v));
  $('export').href = `/api/cases/${m.case_id}/export`;
  $('original-viewer').hidden = !m.experiment_link; $('original-viewer').href = `/api/cases/${m.case_id}/replay`;
  $('event-original').hidden = true; $('event-label').hidden = true;
}
async function showEvent(seq) {
  const epoch = caseEpoch, id = current.manifest.case_id, cursor = snap.cursor;
  await guarded(async () => {
    const event = await api(`/api/cases/${id}/event?cursor=${cursor}&sequence=${seq}`);
    if (epoch !== caseEpoch) return;
    $('evidence').open = true;
    $('event-label').hidden = false; $('event-label').textContent = `Event ${seq}, ${event.kind.replaceAll('_', ' ')}, recorded ${event.timestamp}`;
    const pre = $('event-original'); pre.hidden = false; pre.textContent = JSON.stringify(event, null, 2);
    pre.scrollIntoView({ block: 'center', behavior: reduce ? 'auto' : 'smooth' }); pre.focus({ preventScroll: true });
  });
}

/* ---------- scripted mock ---------- */
const M = { runs: [], run: null, events: [], after: -1, preds: null, poll: null, polling: false,
  view: 'repair_step', cardFor: null, sending: false, starting: false, generation: 0, caseId: null, prevStates: {} };
const PH = { unloaded_step: 'unloaded step', attach_output_load_step: 'loaded step', reserved_sine: 'reserved 5 Hz sine', repair_step: 'repaired step', repair_reserved_sine: 'unused 4 Hz sine' };
const CHECK_LABEL = {
  USB_connected: 'USB reconnected',
  USB_off_wiring_confirmed: 'Wiring changed with USB off',
  remaining_wiring_unchanged: 'Remaining wiring unchanged',
  additional_capacitor_removed: 'Extra capacitor removed',
  original_capacitor_and_load_retained: 'Original capacitor and load kept',
};
const randomId = () => [...crypto.getRandomValues(new Uint8Array(16))].map(b => b.toString(16).padStart(2, '0')).join('');
function stopMock() { if (M.poll) clearTimeout(M.poll); M.poll = null; }
function resetMockView() {
  M.generation++; M.caseId = current?.manifest.case_id || null;
  M.run = null; M.events = []; M.after = -1; M.preds = null; M.cardFor = null;
  M.prevStates = {}; M.polling = false; M.sending = false; M.starting = false;
  $('mock-card').replaceChildren();
}
const mockContext = () => ({ generation: M.generation, caseId: M.caseId, runId: M.run?.run_id });
const currentMock = c => c.generation === M.generation && c.caseId === current?.manifest.case_id && c.caseId === M.caseId && (!c.runId || c.runId === M.run?.run_id);
async function initMock() {
  stopMock(); resetMockView();
  const c = mockContext(), caseId = c.caseId;
  const runs = await api(`/api/cases/${caseId}/runs`);
  if (!currentMock(c)) return;
  M.runs = runs;
  const pending = store.get(`bm-launch-${caseId}`);
  if (pending && runs.some(r => r.run_id === pending.launch_id)) store.del(`bm-launch-${caseId}`);
  // Recover a lost response by reading. Creating a missing run still requires a click.
  const remembered = store.get(`bm-run-${caseId}`);
  const pick = runs.find(r => ACTIVE.includes(r.status)) || runs.find(r => r.run_id === remembered) || runs[runs.length - 1];
  renderRunPicker();
  if (pick) await selectRun(pick.run_id); else renderMock();
}
function renderRunPicker() {
  const sel = $('mock-runs'); sel.replaceChildren(); sel.hidden = M.runs.length < 2;
  M.runs.forEach((r, i) => sel.add(new Option(`Simulated run ${i + 1}: ${r.status.replaceAll('_', ' ')}`, r.run_id)));
  if (M.run) sel.value = M.run.run_id;
}
async function selectRun(runId) {
  stopMock(); resetMockView();
  const c = mockContext();
  const run = await api(`/api/runs/${runId}`);
  if (!currentMock(c)) return;
  if (run.case_id !== c.caseId) throw new Error('This run belongs to another case.');
  M.run = run; store.set(`bm-run-${c.caseId}`, runId);
  const selected = mockContext();
  await pullEvents(selected);
  if (!currentMock(selected)) return;
  renderRunPicker(); renderMock();
  if (ACTIVE.includes(M.run.status)) schedulePoll();
}
async function pullEvents(c = mockContext()) {
  if (!c.runId || !currentMock(c)) return;
  for (let i = 0; i < 40; i++) {
    const page = await api(`/api/runs/${c.runId}/events?after=${M.after}`);
    if (!currentMock(c)) return;
    if (!page.events.length) break;
    M.events.push(...page.events); M.after = page.next_after;
    if (M.events.length >= page.total) break;
  }
  if (M.run.publication && !M.preds) {
    const preds = await api(`/api/runs/${c.runId}/predictions`);
    if (currentMock(c)) M.preds = preds;
  }
}
function schedulePoll() {
  stopMock(); const c = mockContext();
  M.poll = setTimeout(async () => {
    if (!currentMock(c) || M.polling || !M.run) return;
    M.polling = true;
    try {
      const run = await api(`/api/runs/${c.runId}`);
      if (!currentMock(c)) return;
      M.run = run;
      await pullEvents(c);
      if (currentMock(c)) renderMock();
    } catch (e) { if (currentMock(c)) notice(e.message); }
    finally { if (currentMock(c)) M.polling = false; }
    if (!currentMock(c)) return;
    if (ACTIVE.includes(M.run.status)) schedulePoll();
    else {
      const runs = await api(`/api/cases/${c.caseId}/runs`).catch(() => null);
      if (currentMock(c) && runs) { M.runs = runs; renderRunPicker(); }
    }
  }, 600);
}
async function startRun() {
  if (M.starting) return;
  const c = mockContext(), caseId = c.caseId;
  const body = store.get(`bm-launch-${caseId}`) || { revision: current.manifest.revision, mode: 'scripted_mock', fault: $('fault').value, launch_id: randomId() };
  store.set(`bm-launch-${caseId}`, body); M.starting = true;
  $('mock-start').disabled = true; $('mock-error').hidden = true;
  try {
    const run = await api(`/api/cases/${caseId}/runs`, body);
    store.del(`bm-launch-${caseId}`);
    if (!currentMock(c)) return;
    const runs = await api(`/api/cases/${caseId}/runs`);
    if (!currentMock(c)) return;
    M.runs = runs; await selectRun(run.run_id);
  } catch (e) {
    if (e.status === 409 || e.status === 400) store.del(`bm-launch-${caseId}`);
    if (currentMock(c)) { $('mock-error').textContent = e.message; $('mock-error').hidden = false; }
  } finally {
    if (M.caseId === caseId && current?.manifest.case_id === caseId) { M.starting = false; renderMock(); }
  }
}
async function confirmRequest(card, checks) {
  if (M.sending || !checks.every(c => c.checked)) return;
  stopMock(); M.generation++; M.polling = false;
  const c = mockContext(), requestId = M.cardFor;
  M.sending = true; card.querySelector('.primary').disabled = true;
  try {
    const fresh = await api(`/api/runs/${c.runId}`);
    if (!currentMock(c)) return;
    const p = fresh.pending_request;
    if (!p || p.request_id !== requestId || M.cardFor !== requestId) {
      M.run = fresh; throw new Error('This simulated request is no longer current. Nothing was sent.');
    }
    const labels = p.required_checks.map(k => CHECK_LABEL[k] || k);
    const response = {
      request_id: p.request_id, action: p.action, fixture: p.fixture, prediction_sha256: p.prediction_sha256,
      expected_boot_id: p.expected_boot_id, wiring_revision: p.wiring_revision, request_sha256: p.request_sha256,
      simulated: true, verbatim: `Simulated confirmation entered in the BenchMate screen: ${labels.join('; ')}.`,
    };
    for (const key of p.required_checks) response[key] = checks.every(x => x.checked);
    const run = await api(`/api/runs/${c.runId}/respond`, response);
    if (currentMock(c)) M.run = run;
  } catch (e) { if (currentMock(c)) notice(e.message); }
  finally {
    if (currentMock(c)) {
      M.sending = false;
      if (card.isConnected) card.querySelector('.primary').disabled = !checks.every(x => x.checked);
      // The poll owns event pagination; acknowledgments never append a second copy of a page.
      renderMock(); if (ACTIVE.includes(M.run.status)) schedulePoll();
    }
  }
}
async function cancelRun() {
  stopMock(); M.generation++; M.polling = false;
  const c = mockContext();
  try {
    const run = await api(`/api/runs/${c.runId}/cancel`, { reason: 'User cancelled' });
    if (currentMock(c)) { M.run = run; renderMock(); schedulePoll(); }
  } catch (e) { if (currentMock(c)) notice(e.message); }
}

const cap = t => t ? t[0].toUpperCase() + t.slice(1) : t;
const clockFine = s => { s = Math.max(0, s); return s < 60 ? `${s.toFixed(1)} s` : clock(s); };
function mockStart() { const e = M.events.find(x => x.kind === 'run_started'); return e ? ts(e.timestamp) : null; }
const verb = s => s.passed ? `passes at ${mv(s.RMS_mV)} mV RMS` : `${mv(s.RMS_mV)} mV RMS; ${s.RMS_mV <= 9 ? 'regional check failed' : 'fails'}`;
function mockLine(e) {
  const p = e.payload;
  switch (e.kind) {
    case 'run_started': return { k: 'bench', who: 'Bench', ttl: 'Simulated run started', txt: 'A script drives a simulated circuit built from your confirmed design.' };
    case 'physical_measurement_selected': return { k: 'script', who: 'Script', ttl: `Chose the ${PH[p.phase] || p.phase}`, txt: cap(String(p.reason || '').replace(/^SOFTWARE SCRIPT:\s*/, '')) };
    case 'mock_rc_observation': return { k: 'bench', who: 'Bench', ttl: `Simulated capture: ${PH[p.phase] || p.phase}` };
    case 'unloaded_training_completed': return { k: 'bench', who: 'Bench', ttl: `Time constant ${msOf(p.tau_s)} ms`, txt: 'More resistance and more capacitance both draw this curve.' };
    case 'loaded_point_models_frozen': { const r = p.models.r_changed, c = p.models.c_changed; return { k: 'bench', who: 'Bench', ttl: 'Both explanations locked', txt: `More resistance: gain ${gain(r.gain)}, τ ${msOf(r.tau_s)} ms. More capacitance: gain ${gain(c.gain)}, τ ${msOf(c.tau_s)} ms.` }; }
    case 'operator_action_requested': return { k: 'you', who: 'You', ttl: p.action === 'attach_output_load' ? 'Asked to connect the load, simulated' : 'Asked to remove the extra capacitor, simulated' };
    case 'bridge_operator_response_consumed': return { k: 'you', who: 'You', ttl: 'Your simulated confirmation was used' };
    case 'physical_model_comparison': return { k: 'bench', who: 'Bench', ttl: 'Load test scored', txt: `More resistance ${verb(p.scores.r_changed)}. More capacitance ${verb(p.scores.c_changed)}.` };
    case 'physical_verification': return { k: 'bench', who: 'Bench', ttl: 'Reserved sine scored', txt: `More capacitance ${verb(p.scores.c_changed)}. More resistance ${verb(p.scores.r_changed)}.`, bad: !p.passed };
    case 'repair_prediction_frozen': return { k: 'script', who: 'Script', ttl: 'Repair forecast frozen before the repair', txt: 'Saved locally. Not published remotely.' };
    case 'repair_prediction_comparison': { const c = p.conditional, f = p.command_forecast; return { k: 'bench', who: 'Bench', ttl: `${p.settings.kind === 'sine' ? 'Unused 4 Hz sine' : 'Repaired step'} scored`, txt: `Restored design ${verb(c.restored_nominal)}. Unchanged circuit ${verb(c.unchanged)}. The frozen forecast ${verb(f.restored_nominal)}.`, bad: !c.restored_nominal.passed }; }
    case 'repair_verification_completed': return { k: 'bench', who: 'Bench', ttl: p.passed ? 'Repair verified on the simulated bench' : 'Repair not verified', bad: !p.passed };
    case 'run_completed': return { k: 'bench', who: 'Bench', ttl: 'Simulated run completed' };
    case 'run_failed': return { k: 'bench', who: 'Bench', ttl: `Run stopped: ${String(p.termination || 'failed').replaceAll('_', ' ')}`, txt: p.error || '', bad: true };
    default: return null;
  }
}
function renderMockLog() {
  const ol = $('mockentries'); ol.replaceChildren();
  const t0 = mockStart(); let nowEl = null;
  const lines = M.events.map(e => ({ e, l: mockLine(e) })).filter(x => x.l);
  lines.forEach(({ e, l }, i) => {
    const last = i === lines.length - 1;
    const li = E('li', `entry k-${l.k} ${last ? 'now' : 'past'}${l.bad ? ' bad' : ''}`), bd = E('div', 'bd');
    bd.append(E('span', 'who', l.who), E('div', 'ttl', l.ttl));
    if (l.txt) bd.append(E('div', 'txt', l.txt));
    const src = E('div', 'src'); src.append(E('span', null, `Simulated event ${e.sequence}`)); bd.append(src);
    li.append(E('span', 'tm', t0 ? clockFine(ts(e.timestamp) - t0) : ''), bd);
    ol.append(li); if (last) nowEl = li;
  });
  if (!lines.length) ol.append(E('li', 'empty-log', 'Starting the simulated run.'));
  const sc = $('mocklogscroll');
  if (nowEl && sc.scrollHeight > sc.clientHeight) sc.scrollTo({ top: Math.max(0, nowEl.offsetTop - sc.clientHeight * .4), behavior: reduce ? 'auto' : 'smooth' });
}
function renderMockStatus() {
  const box = $('mock-status'); box.replaceChildren();
  const r = M.run, res = r.result;
  let glyph = GLYPH.open, text = '';
  switch (r.status) {
    case 'running': text = 'Running the simulated protocol'; break;
    case 'awaiting_operator': text = 'Waiting for your simulated confirmation'; glyph = GLYPH.lock; break;
    case 'cancelling': text = 'Cancelling'; break;
    case 'completed': text = res?.repair_verified === true ? 'Simulated repair verified' : 'Completed. The simulated repair was not verified'; glyph = res?.repair_verified === true ? GLYPH.pass : GLYPH.fail; break;
    case 'failed': text = 'Stopped with an error'; glyph = GLYPH.fail; break;
    case 'timed_out': text = 'Stopped: no confirmation within 5 minutes'; glyph = GLYPH.fail; break;
    case 'cancelled': text = 'Cancelled'; glyph = GLYPH.fail; break;
    default: text = 'Interrupted. This run cannot resume'; glyph = GLYPH.fail;
  }
  const st = E('span', 'st'); st.innerHTML = glyph; st.append(E('b', null, text));
  box.append(st, E('span', 'note', `${r.mock_waveforms} simulated waveform${r.mock_waveforms === 1 ? '' : 's'}, ${r.paid_api_calls} API calls, ${r.physical_measurements} physical measurements`), E('span', 'spacer'));
  if (['running', 'awaiting_operator'].includes(r.status)) box.append(button('Cancel run', cancelRun, 'btn'));
}
function renderMockCard() {
  const holder = $('mock-card'), r = M.run, p = r.pending_request;
  if (p) {
    if (M.cardFor === p.request_id) return; // keep the person's ticks between polls
    M.cardFor = p.request_id;
    const card = E('div', 'card'), load = p.action === 'attach_output_load';
    card.append(E('h3', null, load ? 'Simulated: connect the output load' : 'Simulated: remove the extra capacitor'));
    card.append(E('p', 'instr', `${p.instruction} Nothing on a real board changes.`));
    const fs = E('fieldset', 'checks'); fs.append(E('legend', 'sr', 'Simulated checks'));
    const boxes = p.required_checks.map(k => { const l = E('label'), c = E('input'); c.type = 'checkbox'; l.append(c, document.createTextNode(`${CHECK_LABEL[k] || k}, simulated`)); fs.append(l); return c; });
    const row = E('div', 'row'), btn = E('button', 'primary', 'Confirm simulated step'); btn.type = 'button'; btn.disabled = true;
    boxes.forEach(c => c.addEventListener('change', () => { btn.disabled = M.sending || !boxes.every(x => x.checked); }));
    btn.addEventListener('click', () => confirmRequest(card, boxes));
    row.append(btn, E('span', 'note', 'Tick each step yourself. The run stops if it is not confirmed within 5 minutes.'));
    card.append(fs, row); holder.replaceChildren(card);
    return;
  }
  M.cardFor = null;
  holder.replaceChildren();
  const res = r.result;
  if (!res && !['cancelled', 'interrupted'].includes(r.status)) return;
  const good = r.status === 'completed' && res?.repair_verified === true;
  const card = E('div', `card result ${good ? 'good' : 'bad'}`);
  card.append(E('h3', null, good ? 'The simulated repair held' : r.status === 'completed' ? 'The simulated repair was not verified' : 'The simulated run stopped'));
  const lines = [];
  if (good) lines.push('Both repaired checks matched the restored design, and the unchanged circuit was ruled out. This is a software rehearsal, not a physical repair.');
  else if (r.status === 'completed') lines.push('The run finished, but the repair check did not pass. Nothing is relabelled as a success.');
  if (res?.error) lines.push(res.error);
  if (r.publication_label) lines.push(`Forecast: ${r.publication_label}.`);
  lines.forEach(t => card.append(E('p', null, t)));
  holder.append(card);
}
function repairData(view) {
  const idx = view === 'repair_step' ? 0 : 1, kind = view === 'repair_step' ? 'step' : 'sine';
  const fc = M.preds?.predictions?.forecasts?.[idx];
  const obsE = M.events.find(e => e.kind === 'mock_rc_observation' && e.payload.phase === view);
  const cmpE = M.events.find(e => e.kind === 'repair_prediction_comparison' && e.payload.settings.kind === kind);
  const series = {};
  if (fc) for (const key of ['restored_nominal', 'unchanged']) {
    const f = fc[key], per = (f.settings?.period_us ?? 500) / 1e6;
    series[key] = { t: f.predicted_output_relative_origin_v.map((_, i) => i * per + (f.nominal_output_delay_s || 0)), v: f.predicted_output_relative_origin_v };
  }
  let obs = null;
  if (obsE) { const d = obsE.payload.data, base = obsE.payload.baseline.output_v; obs = { t: d.frame_time_s.map((t, i) => t + d.output_delay_s[i]), v: d.output_v.map(v => v - base) }; }
  return { fc, series, obs, cmp: cmpE?.payload || null, frozenAt: M.events.find(e => e.kind === 'repair_prediction_frozen') };
}
function renderMockScopes() {
  document.querySelectorAll('.cond[data-m]').forEach(b => b.setAttribute('aria-pressed', b.dataset.m === M.view));
  const d = repairData(M.view), t0 = mockStart();
  const state = d.cmp ? 'scored' : d.obs ? 'captured' : d.fc ? 'locked' : 'future';
  const was = M.prevStates[M.view]; M.prevStates[M.view] = state;
  const sweep = !!was && was !== state && (state === 'captured' || (state === 'scored' && was === 'locked'));
  const pm = M.preds?.predictions?.point_models;
  const sharedScale = d.fc ? scaleFor([...Object.values(d.series), ...(d.obs ? [d.obs] : [])]) : null;
  for (const [side, key, sty] of [['R', 'restored_nominal', 'b'], ['U', 'unchanged', 'a']]) {
    const svg = $('scr' + side), ov = $('ov' + side), v = $('v' + side), ro = $('ro' + side), keyEl = $('key' + side), fcEl = v;
    if (state === 'future') {
      drawScope(svg, null, [], false); ro.innerHTML = ''; keyEl.innerHTML = '';
      overlay(ov, M.run && ['failed', 'cancelled', 'interrupted', 'timed_out'].includes(M.run.status) ? 'The run stopped before the repair forecast was frozen' : 'The repair forecast is frozen after the simulated diagnosis');
      setVerdict(v, ''); $('f' + side).textContent = ''; continue;
    }
    overlay(ov, ''); if (state !== 'scored') $('f' + side).textContent = '';
    const label = pm ? (key === 'restored_nominal' ? `Restored, C ${valueText({ kind: 'C', value_si: pm.restored_nominal.C_f })}` : `Unchanged, C ${(pm.unchanged.C_f * 1e6).toFixed(1)} µF`) : '';
    const layers = [{ ...d.series[key], style: STYLE[sty] }];
    if (d.obs) layers.push({ ...d.obs, style: STYLE.red, sweep: true });
    const sc = sharedScale;
    drawScope(svg, sc, layers, sweep); ro.innerHTML = readout(sc);
    keyEl.innerHTML = `<span>${SAMPLE[sty]}${label} · forecast</span>` + (d.obs ? `<span>${SAMPLE.red}Measured</span>` : '');
    if (state === 'locked') { setVerdict(fcEl, `${GLYPH.lock}<span>Frozen ${d.frozenAt && t0 ? 'at ' + clockFine(ts(d.frozenAt.timestamp) - t0) + ', ' : ''}before the repair</span>`); continue; }
    if (state === 'captured') { setVerdict(fcEl, '<span class="why">Captured. Scoring next.</span>', sweep); continue; }
    const words = key === 'restored_nominal' ? { pass: 'repair holds', fail: 'repair not confirmed' } : { pass: 'cannot tell them apart here', fail: 'ruled out' };
    const html = '<span class="metric-label">Using measured IN</span>' + verdictHTML(d.cmp.conditional[key], words);
    const f = d.cmp.command_forecast[key];
    setVerdict(fcEl, html, sweep);
    $('f' + side).textContent = f ? `Plotted forecast: ${verb(f)}.` : '';
  }
}
function renderMock() {
  const has = !!M.run;
  $('mock-stage').hidden = !has;
  const pending = current && store.get(`bm-launch-${current.manifest.case_id}`);
  $('mock-start').textContent = pending ? 'Recover requested simulated run' : 'Start a simulated run';
  $('mock-start').disabled = M.starting || (has && ACTIVE.includes(M.run.status));
  $('fault').disabled = M.starting || !!pending || (has && ACTIVE.includes(M.run.status));
  if (!has) return;
  renderMockStatus(); renderMockCard(); renderMockLog(); renderMockScopes();
}

/* ---------- wiring ---------- */
$('ask-form').addEventListener('submit', async e => {
  e.preventDefault();
  const btn = e.currentTarget.querySelector('button[type="submit"]'), epoch = caseEpoch;
  if (btn.disabled) return;
  btn.disabled = true;
  try {
    const scope = document.querySelector('input[name="scope"]:checked').value;
    const result = await api('/api/cases', { question: $('question').value, scope });
    await refreshLibrary();
    if (caseEpoch !== epoch) return;
    await openCase(result.manifest.case_id);
    if (current?.manifest.case_id === result.manifest.case_id) $('review').scrollIntoView({ block: 'start', behavior: reduce ? 'auto' : 'smooth' });
  } catch (err) { if (caseEpoch === epoch) notice(err.message); }
  finally { btn.disabled = false; }
});
$('review-form').addEventListener('submit', async e => {
  e.preventDefault();
  const btn = $('confirm-design'), epoch = caseEpoch, id = current?.manifest.case_id;
  if (btn.disabled || !id) return;
  btn.disabled = true;
  try {
    const result = await api(`/api/cases/${id}/confirm`, { revision: current.manifest.revision, candidate: candidateFromForm() });
    await refreshLibrary();
    if (caseEpoch !== epoch) return;
    await openCase(result.manifest.case_id, 0);
    if (current?.manifest.case_id === id && linked()) $('replay').scrollIntoView({ block: 'start', behavior: reduce ? 'auto' : 'smooth' });
  } catch (err) { if (caseEpoch === epoch) notice(err.message); }
  finally { btn.disabled = false; }
});
$('review-form').addEventListener('input', () => { $('gate').classList.remove('bad'); $('gate').textContent = 'Confirm these values and connections to continue.'; });
$('play').addEventListener('click', () => togglePlay());
$('back').addEventListener('click', () => guarded(() => go(stepAfter(-1), { user: true })));
$('fwd').addEventListener('click', () => guarded(() => go(stepAfter(1), { user: true })));
document.querySelectorAll('.cond[data-c]').forEach(b => b.addEventListener('click', () => { cond = b.dataset.c; renderStage(); }));
document.querySelectorAll('.cond[data-m]').forEach(b => b.addEventListener('click', () => { M.view = b.dataset.m; renderMockScopes(); }));
$('mock-start').addEventListener('click', startRun);
$('mock-runs').addEventListener('change', e => guarded(() => selectRun(e.target.value)));
$('new-case').addEventListener('click', showAsk);
$('case-picker').addEventListener('change', e => { const id = e.target.value; if (!id) showAsk(); else guarded(() => openCase(id)); });
document.addEventListener('keydown', e => {
  if (!snap || $('replay').hidden || e.target.closest('input,textarea,select,button,summary,[contenteditable]')) return;
  if (e.key === 'ArrowRight') guarded(() => go(stepAfter(1), { user: true }));
  if (e.key === 'ArrowLeft') guarded(() => go(stepAfter(-1), { user: true }));
});
document.addEventListener('visibilitychange', () => { if (document.hidden) stopPlay(); });

$('board-open').addEventListener('click', openPhotoEvidence);
$('photo-close').addEventListener('click', () => $('photo-dialog').close());
$('photo-picker').addEventListener('change', e => { PHOTO.selected = PHOTO.catalog.find(p => p.id === e.target.value); renderPhotoEvidence(); });
$('photo-mask').addEventListener('change', e => { $('photo-evidence-image').src = e.target.value || PHOTO.selected.image_url; });
guarded(async () => {
  await refreshLibrary();
  const query = new URLSearchParams(location.search), id = query.get('case');
  if (id) {
    const raw = query.get('event') || '0';
    await openCase(id, /^\d{1,3}$/.test(raw) ? Number(raw) : 0);
  }
});
