// BenchMate v3 shared pieces: data, formatting, the scope (canvas), the meters (SVG), schematics.
// Every number shown comes from data/*.json. Nothing here invents values.
window.BM = (() => {
  const REDUCED = matchMedia('(prefers-reduced-motion: reduce)').matches;
  const $ = (s, r = document) => r.querySelector(s);
  const el = (tag, attrs = {}, ...kids) => {
    const n = document.createElement(tag);
    for (const [k, v] of Object.entries(attrs)) {
      if (k === 'class') n.className = v; else if (k === 'html') n.innerHTML = v;
      else if (k.startsWith('on')) n.addEventListener(k.slice(2), v); else if (v != null) n.setAttribute(k, v);
    }
    for (const k of kids.flat()) if (k != null) n.append(k.nodeType ? k : document.createTextNode(String(k)));
    return n;
  };
  const json = async (p) => { const r = await fetch(p, { cache: 'no-cache' }); if (!r.ok) throw new Error(p + ' ' + r.status); return r.json(); };
  const loadCases = () => json('data/cases.json');
  const loadRuns = () => json('data/runs/index.json');
  const loadRun = (id) => json(`data/runs/${id}.json`);
  const loadNotes = () => json('data/notes.json').catch(() => ({}));
  const loadResults = () => json('data/results.json').catch(() => null);

  // ---- names and units
  const names = {}; // proposal ids → their plain names, registered when the proposal appears
  const expName = (id) => names[id] ? names[id] : id === 'nominal' ? 'As drawn' : id.startsWith('changed:') ? `${id.slice(8)} changed`
    : id.startsWith('added:') ? `Added ${id.slice(6)}` : id;
  const fmtR = (v) => v >= 1e6 ? `${(v / 1e6).toFixed(2)} MΩ` : v >= 1e3 ? `${(v / 1e3).toFixed(2)} kΩ` : `${v.toFixed(0)} Ω`;
  const fmtC = (v) => v >= 1e-6 ? `${(v * 1e6).toFixed(2)} µF` : v >= 1e-9 ? `${(v * 1e9).toFixed(0)} nF` : `${(v * 1e12).toFixed(0)} pF`;
  const fmtVal = (kind, v) => v == null ? '' : kind === 'R' ? fmtR(v) : kind === 'C' ? fmtC(v) : String(v);
  // SI prefixes everywhere a value is shown: 20.5 kΩ, 0.47 µF, 3.02 nA — never 2.05e+4
  const SI = [[1e9, 'G'], [1e6, 'M'], [1e3, 'k'], [1, ''], [1e-3, 'm'], [1e-6, 'µ'], [1e-9, 'n'], [1e-12, 'p']];
  const fmtSI = (v, unit = '') => { if (v == null || !Number.isFinite(Number(v))) return v == null ? '' : String(v); v = Number(v); if (v === 0) return `0 ${unit}`.trim();
    const a = Math.abs(v); const [m, pre] = SI.find(([m]) => a >= m * 0.9995) || SI[SI.length - 1]; const x = v / m; const d = Math.abs(x) >= 100 ? 0 : Math.abs(x) >= 10 ? 1 : 2;
    return `${x.toFixed(d).replace(/\.0+$/, '').replace(/(\.\d*[1-9])0+$/, '$1')} ${pre}${unit}`.trim(); };
  const unitOf = (name) => /^(R|res)/i.test(name) ? 'Ω' : /^(C|cap)/i.test(name) ? 'F' : /_IS$/i.test(name) ? 'A' : /^L/i.test(name) ? 'H' : '';
  const fmtParam = (name, v) => `${name} ${fmtSI(v, unitOf(name))}`;
  const fmtUSD = (x) => '$' + (x < 0.1 ? x.toFixed(3) : x.toFixed(2));
  const fmtClock = (s) => { s = Math.max(0, Math.round(s)); const m = Math.floor(s / 60); return `${m}:${String(s % 60).padStart(2, '0')}`; };
  const fmtDur = (s) => s >= 60 ? `${Math.floor(s / 60)} min ${Math.round(s % 60)} s` : `${Math.round(s)} s`;
  const fmtLog = (iso, offsetS) => { // KST wall clock of the log
    const d = new Date(new Date(iso).getTime() + offsetS * 1000);
    return d.toLocaleTimeString('en-GB', { hour12: false, timeZone: 'Asia/Seoul' });
  };
  // "3 Nov 2026, 01:08 KST" everywhere; no dd/mm/yyyy
  const fmtDate = (iso, seconds = false) => { const d = new Date(iso); const z = { timeZone: 'Asia/Seoul' };
    return `${d.toLocaleString('en-GB', { day: 'numeric', month: 'short', year: 'numeric', ...z })}, ${d.toLocaleString('en-GB', { hour: '2-digit', minute: '2-digit', ...(seconds ? { second: '2-digit' } : {}), hour12: false, ...z })} KST`; };
  const menuLabel = (a) => ({
    unloaded_step_small: ['Step ±0.2 V', 'no load'], loaded_step_small: ['Step ±0.2 V', '9.99 kΩ load'],
    unloaded_step_large: ['Step ±0.5 V', 'no load'], loaded_step_large: ['Step ±0.5 V', '9.99 kΩ load'],
    unloaded_sine_1hz_small: ['Sine 1 Hz, 0.2 V', 'no load'], unloaded_sine_1hz_large: ['Sine 1 Hz, 0.8 V', 'no load'],
    unloaded_sine_5hz_small: ['Sine 5 Hz, 0.15 V', 'no load'], loaded_sine_5hz_small: ['Sine 5 Hz, 0.15 V', '9.99 kΩ load'],
  })[a] || [a, ''];

  // ---- schematics: the model's file untouched, margins cropped on screen only
  const svgCache = {};
  async function schematic(design, { crop = true } = {}) {
    if (!svgCache[design]) svgCache[design] = fetch(`assets/schem/${design}.svg`).then(r => r.text());
    const txt = await svgCache[design];
    const doc = new DOMParser().parseFromString(txt, 'image/svg+xml');
    const svg = document.importNode(doc.documentElement, true);
    svg.removeAttribute('width'); svg.removeAttribute('height');
    svg.setAttribute('role', 'img'); svg.setAttribute('aria-label', `Schematic ${design}, as given to the model`);
    if (crop) {
      // the generator draws inside a 1200×650 page; tighten to the drawing with a margin
      const probe = svg.cloneNode(true); probe.style.cssText = 'position:absolute;left:-9999px;width:1200px;height:650px';
      document.body.append(probe);
      let x0 = 1e9, y0 = 1e9, x1 = -1e9, y1 = -1e9;
      probe.querySelectorAll('line,rect,circle,polygon,text').forEach(n => {
        if (n.getAttribute('width') === '100%') return;
        const b = n.getBBox(); if (!b.width && !b.height) return;
        x0 = Math.min(x0, b.x); y0 = Math.min(y0, b.y); x1 = Math.max(x1, b.x + b.width); y1 = Math.max(y1, b.y + b.height);
      });
      probe.remove();
      const m = 28;
      svg.setAttribute('viewBox', `${x0 - m} ${y0 - m} ${x1 - x0 + 2 * m} ${y1 - y0 + 2 * m}`);
    }
    return svg;
  }
  // red overlay from cases.json (drawn only after the seal opens; never part of the model input)
  function overlaySVG(ov, viewBox = '0 0 1200 650') {
    const NS = 'http://www.w3.org/2000/svg';
    const s = document.createElementNS(NS, 'svg'); s.setAttribute('viewBox', viewBox); s.setAttribute('preserveAspectRatio', 'xMidYMid meet');
    const add = (t, a, txt) => { const n = document.createElementNS(NS, t); for (const [k, v] of Object.entries(a)) n.setAttribute(k, v); if (txt) n.textContent = txt; s.append(n); return n; };
    for (const o of ov || []) {
      const st = { stroke: '#d5342c', fill: 'none', 'stroke-width': 4 };
      if (o.type === 'resistor') add('rect', { x: o.x, y: o.y - o.h / 2, width: o.w, height: o.h, 'stroke-dasharray': '10 8', ...st });
      else if (o.type === 'box') add('rect', { x: o.x, y: o.y, width: o.w, height: o.h, rx: 6, 'stroke-dasharray': '10 8', ...st });
      else if (o.type === 'dashed') add('polyline', { points: o.points.map(p => p.join(',')).join(' '), 'stroke-dasharray': '10 8', ...st });
      else if (o.type === 'dot') add('circle', { cx: o.x, cy: o.y, r: 7, fill: '#d5342c' });
      else if (o.type === 'diode') { add('polygon', { points: `${o.x - 26},${o.y} ${o.x + 26},${o.y} ${o.x},${o.y + 42}`, 'stroke-dasharray': '8 6', ...st }); add('line', { x1: o.x - 26, y1: o.y + 42, x2: o.x + 26, y2: o.y + 42, ...st }); }
      else if (o.type === 'text') add('text', { x: o.x, y: o.y, 'text-anchor': o.anchor || 'start', 'font-size': o.size || 26, 'font-family': 'Archivo Narrow, Arial, sans-serif', 'font-weight': 600, fill: '#d5342c' }, o.text);
    }
    return s;
  }

  // after mounting: widen the schematic and overlay viewBoxes so red overlay text is never clipped
  function fitOverlay(svg, ovsvg) {
    try {
      const vb = svg.getAttribute('viewBox').split(' ').map(Number); let [x0, y0, w, h] = vb; let x1 = x0 + w, y1 = y0 + h;
      ovsvg.querySelectorAll('*').forEach(n => { if (!n.getBBox) return; const b = n.getBBox(); if (!b.width && !b.height) return; x0 = Math.min(x0, b.x - 12); y0 = Math.min(y0, b.y - 12); x1 = Math.max(x1, b.x + b.width + 12); y1 = Math.max(y1, b.y + b.height + 12); });
      const nv = `${x0} ${y0} ${x1 - x0} ${y1 - y0}`; svg.setAttribute('viewBox', nv); ovsvg.setAttribute('viewBox', nv);
    } catch {}
  }

  // ---- the scope
  class Scope {
    constructor(root, { ratio = 0.42, fill = false } = {}) {
      this.root = root; this.ratio = ratio; this.fill = fill;
      this.canvas = el('canvas'); root.append(this.canvas);
      this.hud = el('div', { class: 'hud' }); this.title = el('div', { class: 'title' });
      this.read = el('div', { class: 'read' }); this.sweepLab = el('div', { class: 'sweep' });
      root.append(this.hud, this.title, this.read, this.sweepLab);
      this.state = { t: [], traces: [], vdiv: 0.1, title: '', progress: 1, cursor: null };
      this.ro = new ResizeObserver(() => this.draw()); this.ro.observe(root);
      this.canvas.addEventListener('pointermove', e => this.hover(e)); this.canvas.addEventListener('pointerleave', () => { this.state.cursor = null; this.draw(); });
      this.draw();
    }
    // traces: [{id,label,kind:'in'|'out'|'fc'|'meas', v:[...], dashed, color, progress}]
    set(t, traces, title) {
      const s = this.state; s.t = t || []; s.traces = traces || []; s.title = title || '';
      const amp = Math.max(0.05, ...s.traces.flatMap(tr => tr.v.map(Math.abs)));
      const cands = [0.02, 0.05, 0.1, 0.2, 0.25, 0.5];
      s.vdiv = cands.find(c => c * 4 >= amp * 1.08) || 0.5;
      this.title.textContent = s.title;
      this.hud.innerHTML = '';
      const seen = new Set();
      for (const tr of s.traces) { if (seen.has(tr.kind)) continue; seen.add(tr.kind);
        this.hud.append(el('span', { class: tr.kind === 'in' ? 'in' : tr.kind === 'out' ? 'out' : 'fc' }, el('b', {}, tr.kind === 'in' ? 'IN' : tr.kind === 'out' ? 'OUT' : 'forecast'), ` ${Math.round(s.vdiv * 1000)} mV/div`)); }
      const span = s.t.length ? s.t[s.t.length - 1] - s.t[0] : 0;
      this.sweepLab.textContent = span ? `${(span * 1000 / 10).toFixed(1)} ms/div` : '';
      this.draw();
    }
    setProgress(tr, p) { tr.progress = p; this.draw(); }
    hover(e) {
      const r = this.canvas.getBoundingClientRect(); const x = (e.clientX - r.left) / r.width;
      const s = this.state; if (!s.t.length) return;
      const i = Math.max(0, Math.min(s.t.length - 1, Math.round(x * (s.t.length - 1))));
      s.cursor = i; this.draw();
      const parts = [`t ${(s.t[i] * 1000).toFixed(1)} ms`];
      for (const tr of s.traces) if ((tr.progress ?? 1) * (s.t.length - 1) >= i) parts.push(`${tr.label} ${(tr.v[i] * 1000).toFixed(0)} mV`);
      this.read.textContent = parts.join(' · ');
    }
    draw() {
      const c = this.canvas, dpr = devicePixelRatio || 1, W = this.root.clientWidth, H = this.fill ? this.root.clientHeight : Math.round(W * this.ratio);
      if (!W) return;
      if (c.width !== W * dpr || c.height !== H * dpr) { c.width = W * dpr; c.height = H * dpr; c.style.height = H + 'px'; }
      const g = c.getContext('2d'); g.setTransform(dpr, 0, 0, dpr, 0, 0);
      g.fillStyle = '#0e1315'; g.fillRect(0, 0, W, H);
      const L = 10, R = W - 10, T = 30, B = H - 26, w = R - L, h = B - T;
      g.strokeStyle = '#1a2528'; g.lineWidth = 1;
      for (let i = 0; i <= 10; i++) { const x = L + w * i / 10; g.beginPath(); g.moveTo(x, T); g.lineTo(x, B); g.stroke(); }
      for (let i = 0; i <= 8; i++) { const y = T + h * i / 8; g.beginPath(); g.moveTo(L, y); g.lineTo(R, y); g.stroke(); }
      g.strokeStyle = '#27343a'; g.lineWidth = 1.2;
      g.beginPath(); g.moveTo(L, T + h / 2); g.lineTo(R, T + h / 2); g.stroke();
      g.beginPath(); g.moveTo(L + w / 2, T); g.lineTo(L + w / 2, B); g.stroke();
      const s = this.state; if (!s.t.length) { g.fillStyle = '#4a5a60'; g.font = '13px Archivo Narrow, sans-serif'; g.fillText('no trace yet', L + 12, T + 20); return; }
      const t0 = s.t[0], t1 = s.t[s.t.length - 1];
      const X = t => L + w * (t - t0) / (t1 - t0), Y = v => T + h / 2 - v / (s.vdiv * 4) * (h / 2);
      const col = { in: '#5fdc8c', out: '#6ea6ff', fc: '#c6a9ff', meas: '#ffffff' };
      const order = [...s.traces].sort((a, b) => (a.kind === 'fc') - (b.kind === 'fc'));
      for (const tr of order) {
        const n = Math.floor((tr.progress ?? 1) * (s.t.length - 1));
        if (n < 1) continue;
        g.strokeStyle = tr.color || col[tr.kind] || '#fff'; g.lineWidth = tr.kind === 'fc' ? 2 : 2.2;
        g.setLineDash(tr.dashed ? [7, 6] : []); g.lineJoin = 'round';
        g.shadowColor = tr.kind === 'fc' ? 'transparent' : g.strokeStyle; g.shadowBlur = tr.kind === 'fc' ? 0 : 6;
        g.beginPath();
        for (let i = 0; i <= n; i++) { const x = X(s.t[i]), y = Y(tr.v[i]); i ? g.lineTo(x, y) : g.moveTo(x, y); }
        g.stroke(); g.shadowBlur = 0; g.setLineDash([]);
        if (n < s.t.length - 1) { g.fillStyle = '#fff'; g.beginPath(); g.arc(X(s.t[n]), Y(tr.v[n]), 3, 0, 7); g.fill(); }
      }
      if (s.cursor != null) { g.strokeStyle = 'rgba(255,255,255,.35)'; g.setLineDash([3, 3]); g.beginPath(); const x = X(s.t[s.cursor]); g.moveTo(x, T); g.lineTo(x, B); g.stroke(); g.setLineDash([]); }
    }
  }

  // ---- analog meters: 0–15 mV face, red from the 9 mV allowance; values past 15 pin at the stop
  const FS = 15;
  class Meter {
    constructor(id, label, { value } = {}) {
      this.id = id; this.val = null; this.fs = FS;
      this.root = el('div', { class: 'meter new', 'data-id': id });
      const NS = 'http://www.w3.org/2000/svg';
      this.svg = document.createElementNS(NS, 'svg'); this.svg.setAttribute('viewBox', '0 0 160 92'); this.svg.setAttribute('aria-hidden', 'true');
      this.face({ fs: FS, redFrom: 9, unit: 'mV', ticks: [0, 3, 6, 9, 12, 15], major: [0, 9, 15] });
      this.name = el('div', { class: 'name' }, el('span', {}, label), el('span', { class: 'v' }, value || ''));
      this.readout = el('div', { class: 'read' }, el('span', { class: 'miss' }, 'no reading'), el('span', { class: 'st' }, ''));
      this.root.append(this.svg, this.name, this.readout);
      this.setAngle(0);
    }
    // the face: mV with red above the allowance (default), or a value scale with one green window (a reading's band)
    face({ fs, redFrom, band, unit, ticks, major, bandLabel }) {
      this.fs = fs;
      const arc = (r, a0, a1) => { const p = a => [80 + r * Math.cos(a), 84 - r * Math.sin(a)]; const [x0, y0] = p(a0), [x1, y1] = p(a1); return `M${x0} ${y0}A${r} ${r} 0 0 1 ${x1} ${y1}`; };
      const ang = v => Math.PI - Math.PI * Math.max(0, Math.min(v, fs)) / fs;
      const fmtTick = v => fs >= 100 ? String(Math.round(v)) : fs >= 10 ? String(Math.round(v * 10) / 10) : String(Math.round(v * 100) / 100);
      const zones = band
        ? `<path d="${arc(62, ang(0), ang(fs))}" stroke="#d9c9c1" stroke-width="7" fill="none"/><path d="${arc(62, ang(band[0]), ang(band[1]))}" stroke="#2f9e5b" stroke-width="7" fill="none"/>`
        : `<path d="${arc(62, ang(0), ang(redFrom))}" stroke="#bdb59c" stroke-width="7" fill="none"/><path d="${arc(62, ang(redFrom), ang(fs))}" stroke="#d5342c" stroke-width="7" fill="none"/>`;
      const prev = this.needle ? this.needle.style.transform : '';
      this.svg.innerHTML = `<path d="${arc(66, Math.PI, 0)}" stroke="#8d8878" stroke-width="2" fill="none"/>${zones}
        ${ticks.map(v => { const a = ang(v), c = Math.cos(a), s = Math.sin(a); const lab = band ? major.includes(v) : true; return `<line x1="${80 + 54 * c}" y1="${84 - 54 * s}" x2="${80 + 48 * c}" y2="${84 - 48 * s}" stroke="#2b2a26" stroke-width="1.5"/>${lab ? `<text class="${major.includes(v) ? 'tk' : 'tk minor'}" x="${80 + 40 * c}" y="${86 - 40 * s}" font-size="9" text-anchor="middle" font-family="Archivo Narrow,sans-serif" fill="#2b2a26">${fmtTick(v)}</text>` : ''}`; }).join('')}
        ${band ? (() => { const a = ang((band[0] + band[1]) / 2), c = Math.cos(a), s = Math.sin(a); return `<text x="${80 + 38 * c}" y="${86 - 38 * s}" font-size="8.5" text-anchor="middle" font-family="Archivo Narrow,sans-serif" font-weight="600" fill="#1f7a45">${bandLabel}</text>`; })() : ''}
        <text x="80" y="62" font-size="9" text-anchor="middle" font-family="Archivo Narrow,sans-serif" fill="#5a584f">${unit}</text>
        <g class="needle" style="transform-origin:80px 84px;transition:transform ${REDUCED ? 0 : 1.2}s cubic-bezier(.2,.8,.3,1.1)"><line x1="80" y1="84" x2="80" y2="22" stroke="#1b1a17" stroke-width="2"/><circle cx="80" cy="84" r="5" fill="#1b1a17"/></g>`;
      this.needle = this.svg.querySelector('.needle'); if (prev) this.needle.style.transform = prev;
    }
    // a reading's band: the face becomes a value scale in the reading's unit, green only inside this explanation's frozen band
    band(low, high, unit, upto) {
      const top = Math.max(high * 1.25, upto || 0, low * 1.1);
      const step = Math.pow(10, Math.floor(Math.log10(top))); const fs = Math.ceil(top / (step / 2)) * (step / 2);
      this.face({ fs, band: [low, high], unit, ticks: [0, low, high, fs], major: [0, fs], bandLabel: `${low}–${high}` });
      this.root.classList.add('band'); this.bandOf = { low, high, unit };
    }
    setReading(value, unit, label) {
      this.val = value; this.setAngle(value);
      const inBand = this.bandOf && value >= this.bandOf.low && value <= this.bandOf.high;
      this.readout.firstChild.textContent = `${value} ${unit}${value > this.fs ? ' (off scale)' : ''}`;
      this.readout.lastChild.textContent = label || 'reading'; this.readout.lastChild.title = this.bandOf ? `Frozen band ${this.bandOf.low}–${this.bandOf.high} ${this.bandOf.unit}` : '';
      if (this.root.classList.contains('out')) { this.die(); return; }
      this.root.classList.toggle('bad', !inBand);
    }
    setAngle(v) { const deg = -90 + 180 * Math.max(0, Math.min(v, this.fs)) / this.fs; this.needle.style.transform = `rotate(${deg}deg)`; }
    setValue(mV, fitted, passed, stepN, worstRegion) {
      this.val = mV; this.setAngle(mV);
      this.readout.firstChild.textContent = `${mV.toFixed(2)} mV${mV > FS ? ' (off scale)' : ''}`;
      const lab = stepN == null ? '' : /^(step|check|all|the)\b/.test(String(stepN)) ? String(stepN) : `step ${stepN}`;
      this.readout.lastChild.textContent = lab + (worstRegion ? ` · worst region` : '');
      this.readout.lastChild.title = worstRegion ? `Decided by the worst region: ${worstRegion}` : '';
      if (this.root.classList.contains('out')) { this.die(); return; }
      if (fitted) this.name.lastChild.textContent = fitted;
      this.root.classList.toggle('bad', passed === false);
    }
    ruleOut(stepN) { this.root.classList.add('out'); this.root.querySelector('.tag')?.remove(); this.root.append(el('span', { class: 'tape red tag' }, `Ruled out after step ${stepN}`)); this.deadAfter = stepN; }
    // ruled out by the operator's one reading: a different tape from the bench's
    ruleOutByReading() { this.root.classList.add('out'); this.root.querySelector('.tag')?.remove(); this.root.append(el('span', { class: 'tape read tag' }, 'Ruled out by one reading')); this.deadAfter = 'reading'; }
    // a ruled-out explanation's meter goes dead: no more live readings on a struck explanation
    die() { this.root.classList.add('dead'); }
    carry(text) { this.root.querySelector('.tag')?.remove(); this.root.append(el('span', { class: 'tape grey tag' }, text)); }
  }

  // reusable step → scope traces (forecasts first, the measurement on top)
  function stepTraces(step, { measuredProgress = 1, forecasts = true } = {}) {
    const obs = step.observation; const traces = [];
    if (forecasts) for (const f of step.forecasts || []) traces.push({ id: f.id, label: expName(f.id) + ' forecast', kind: 'fc', v: f.v, dashed: true, progress: 1 });
    if (obs) { traces.push({ id: 'in', label: 'IN', kind: 'in', v: obs.in_v, progress: measuredProgress }); traces.push({ id: 'out', label: 'OUT', kind: 'out', v: obs.out_v, progress: measuredProgress }); }
    return traces;
  }
  const stepTime = (step) => step.observation ? step.observation.t_s : (step.forecasts?.[0] ? step.forecasts[0].v.map((_, i) => i * (step.settings?.period_us || 500) * 2e-6) : []);


  // ---- plain headlines: one voice, one template per state, numbers from data
  const fmtMiss = (x) => x == null ? '—' : `${Number(x).toFixed(2)} mV`;
  const words = {
    choice: (e) => `Spark chose experiment ${e.step}: ${e.label}.`,
    forecast: (e) => e.final ? 'Before the check, the surviving explanation’s forecast is frozen and pushed to GitHub.' : (e.ids.length === 1 ? `Before measuring, the drawing’s forecast is frozen: the dashed line is what the output should do.` : `Before measuring, each standing explanation forecasts the output. ${e.ids.length} dashed lines, frozen.`),
    bench: (e) => `The bench has to change: ${e.text}.`,
    capture: (e) => e.verification ? 'The bench measures the first held-back input.' : `The bench measures experiment ${e.step}.`,
    fit: (e, allow) => { const out = e.results.filter(r => !r.adequate), ok = e.results.filter(r => r.adequate);
      if (e.all_inadequate) return 'No explanation fits any more. Every needle is in the red.';
      if (!out.length) return ok.length === 1 ? `${expName(ok[0].id)} still fits, within ${allow} mV.` : `${ok.map(r => expName(r.id)).join(' and ')} both still fit.`;
      return `${out.map(r => expName(r.id)).join(' and ')} missed by too much and ${out.length === 1 ? 'is' : 'are'} crossed out. ${ok.length ? (ok.length === 1 ? `${expName(ok[0].id)} still fits.` : `${ok.map(r => expName(r.id)).join(' and ')} still fit.`) : ''}`; },
    structure: (e) => { const a = e.diff?.added || []; return a.length ? `Spark proposes a part the drawing doesn’t show: ${a.map(x => `${kindWord(x.kind)} between ${x.a} and ${x.b}`).join(', ')}.` : 'Spark proposes a different circuit.'; },
    structureFit: (e) => e.status === 'adequate' ? `The proposed circuit fits every measurement so far, within ${fmtMiss(e.miss_mV)}.` : e.status === 'fit_error' ? 'The proposed circuit could not be fitted.' : `The proposed circuit misses by ${fmtMiss(e.miss_mV)}. Crossed out.`,
    verifyReq: () => 'Spark asks for the check: two inputs it never saw will be measured.',
    heldBack: (k, n) => `The bench measures held-back input ${k} of ${n}.`,
    published: () => 'The forecast is on GitHub. From here nothing can be re-fitted.',
    scored: (e) => { const vals = Object.values(e.conditional || {}); const ok = vals.every(v => v.passed); return `Held-back input ${e.index ?? ''}: ${ok ? 'within' : 'outside'} the frozen allowance.`; },
    // the reading stage: one operator reading, forecast per explanation before it is taken
    readingReq: (e, live) => `${live === 2 ? 'Two explanations' : live > 2 ? `${live} explanations` : 'The explanations'} still fit. Spark asks for one reading.`,
    readingForecast: (e) => `Before the reading, each explanation says what ${e.component || 'the part'} should read.`,
    binding: (e) => `Spark says this body is ${e.component} — ${e.operator_confirmed ? 'confirmed by the operator' : e.chosen_by === 'operator' ? 'assigned by the operator' : 'not yet confirmed'}.`,
    readingObs: (e) => `${e.component} reads ${e.value} ${e.unit}, ${sourceWord(e.source)}.`,
    readingScored: (e, bands) => e.outcome === 'one' ? `Only ${expName(e.fits[0])} fits this reading. The rest are crossed out.` : e.outcome === 'none' ? 'No explanation fits this reading. All are crossed out.' : `The reading does not separate ${e.fits.map(expName).join(' and ')}.`,
    equivalence: (e) => `Same waveform: ${(e.members || []).map(m => m.words || m.label).join('; ')}.`,
    guard: () => 'The bench’s own reference moved too much. The run stops here.',
    stopped: () => 'The recording ends here. No verdict.',
    report: (e, run) => verdictWords(e, run),
  };
  const kindWord = (k) => ({ R: 'a resistor', C: 'a capacitor', D: 'a diode', W: 'a wire' })[k] || k;
  const sourceWord = (s) => ({ operator_dmm: 'measured with a multimeter', operator_marking: 'read from the marking on the part' })[s] || (s || 'source not recorded').replace(/_/g, ' ');
  const sourceShort = (s) => ({ operator_dmm: 'multimeter', operator_marking: 'marking' })[s] || s;
  const quantityWord = (q, comp) => ({ resistance: `${comp}’s resistance, measured out of circuit`, capacitance: `${comp}’s capacitance, measured out of circuit`,
    marking: `the marking printed on ${comp}`, continuity: `whether ${comp} conducts end to end`, presence: `whether ${comp} is on the board at all` })[q] || `${q} of ${comp}`;
  const chosenWord = (by) => by === 'muse_spark' ? 'chosen by Muse Spark 1.3' : by === 'engine' ? 'chosen by the engine' : by === 'operator' ? 'assigned by the operator' : `chosen by ${by || 'an unrecorded party'}`;
  // which frozen bands a value falls in, for one source: the same rule the engine applied, replayed in the browser
  // a band with a null bound is open on that side (a marking cannot rule out a damaged part keeping its old label)
  const bandFits = (bands, source, value) => bands.filter(b => b.source === source && (b.low == null || value >= b.low) && (b.high == null || value <= b.high)).map(b => b.explanation);
  // fit range of the engine (R 1 kΩ–100 kΩ, C 1 nF–10 µF); a value at a bound is a limit, not a measurement
  const FIT_BOUNDS = { R: [1000, 100000], C: [1e-9, 1e-5] };
  function fmtFit(kind, value, atBound) {
    if (value == null) return null;
    const b = FIT_BOUNDS[kind]; const tol = 1e-6;
    const atHi = b && Math.abs(value - b[1]) <= b[1] * tol, atLo = b && Math.abs(value - b[0]) <= b[0] * tol;
    if (atBound || atHi || atLo) return `${atLo ? '≤' : '≥'} ${fmtVal(kind, atLo ? b[0] : atHi ? b[1] : value)} (fit limit)`;
    return fmtVal(kind, value);
  }
  const bandText = (b) => b.low == null && b.high == null ? 'any value' : b.high == null ? `${b.low} ${b.unit} and up (open)` : b.low == null ? `up to ${b.high} ${b.unit}` : `${b.low}–${b.high} ${b.unit}`;
  const nodeWord = (x) => x.kind === 'W' ? `the wire ${x.a}–${x.b}` : `${kindWord(x.kind)} from ${x.a} to ${x.b}`;
  const diffWords = (diff) => { const d = diff || {}; const parts = [];
    if (d.added?.length) parts.push('Added: ' + d.added.map(nodeWord).join(', '));
    if (d.removed?.length) parts.push('Removed: ' + d.removed.map(nodeWord).join(', '));
    if (d.reconnected?.length) parts.push('Reconnected: ' + d.reconnected.map(nodeWord).join(', '));
    return parts.length ? parts.join(' · ') + '.' : 'The proposed circuit has the same parts, reconnected.'; };
  const proposerWords = (by) => by === 'muse_spark' ? 'Proposed by Muse Spark 1.3' : by === 'scripted_controller' ? 'Proposed by a scripted controller (development only)' : `Proposed by ${by || 'an unrecorded controller'}`;
  const proposalName = (p) => { const a = (p.diff?.added || [])[0]; return a ? `Spark’s proposal: ${({ R: 'resistor', C: 'capacitor', D: 'diode', W: 'wire' })[a.kind] || a.kind}, ${a.a}→${a.b}` : 'Spark’s proposal'; };
  function verdictWords(e, run) {
    const v = e.verdict || ''; const surv = e.survivors || [];
    if (v === 'nominal_consistent' || (surv.length === 1 && surv[0] === 'nominal')) return 'No mismatch in the tests Spark chose.';
    if (surv.length > 1) return `${surv.length === 2 ? 'Two' : surv.length} explanations still fit: ${surv.map(expName).join(' and ')}. One reading at the bench decides.`;
    if (surv.length === 1 && names[surv[0]] && !surv[0].startsWith('proposal')) return `Found: ${names[surv[0]]}, not what the drawing says.`;
    if (surv.length === 1 && surv[0].startsWith('proposal')) { const pr = (run.structure || []).find(x => x.id === surv[0]); const a = pr?.diff?.added || []; return `Found: a part the drawing doesn’t show${a.length ? ', ' + a.map(x => `${kindWord(x.kind)} between ${x.a} and ${x.b}`).join(', ') : ''}.`; }
    if (surv.length === 1 && surv[0].startsWith('changed:')) { const m = (run.verification?.models || []).find(x => x.id === surv[0]); return `Found: ${surv[0].slice(8)} behaves like ${m ? fmtVal(m.kind, m.value) : 'a different value'}, not what the drawing says.`; }
    if (v === 'abstained') return 'Spark abstained: no explanation survived the tests it chose.';
    return v ? `Verdict: ${v.replace(/_/g, ' ')}.` : 'Verdict recorded.';
  }

  // ---- which run a page shows by default: first official attempt (counted, earliest) for the case; else the earliest pilot
  const defaultRun = (runs, caseId) => { const of = runs.filter(r => r.case === caseId).sort((a, b) => a.started_utc < b.started_utc ? -1 : 1); return of.find(r => r.counted) || of[0] || runs.find(r => r.counted) || runs[0]; };
  // ---- the hero line, one template per end state, numbers from the run
  function heroLine(run) {
    const n = run.steps.length, e = `${n} experiment${n === 1 ? '' : 's'}`;
    const surv = run.outcome?.survivors || run.verification?.survivors || [];
    const scored = run.verification?.scored || [], need = run.reserved?.length || 0;
    if (run.outcome?.kind === 'stopped') return `Spark narrowed it to one explanation in ${e}, then the bench’s own guard stopped the run. Watch how.`;
    if (run.outcome?.kind === 'report' && need && scored.length >= need) {
      const passed = scored.every(s => Object.values(s.conditional || {}).every(v => v.passed));
      const rd = run.reading;
      if (rd?.scored) {
        const o = rd.outcome;
        if (o === 'one') return `In ${e}, the held-back checks ${passed ? 'passed' : 'failed'}; one reading at the bench settled it. Watch how.`;
        if (o === 'none') return `In ${e}, the held-back checks ${passed ? 'passed' : 'failed'}; the reading fit no explanation. Watch how.`;
        return `In ${e}, the held-back checks ${passed ? 'passed' : 'failed'}; the reading did not separate the explanations. Watch how.`;
      }
      if (surv.length === 1 && surv[0] === 'nominal') return `In ${e}, nothing disagreed with the drawing, and the held-back check passed. Watch how.`;
      if (surv.length === 1) return `Spark narrowed it to one explanation in ${e}, and the held-back check ${passed ? 'passed' : 'failed'}. Watch how.`;
      if (surv.length > 1) return `Spark narrowed it to ${surv.length} explanations in ${e}; one reading at the bench decides. Watch how.`;
      return `After ${e}, no explanation survived the held-back check. Watch how.`;
    }
    return `Spark ran ${e}. Watch how.`;
  }

  // ---- menu chips: the whole fixed menu, the chosen one solid
  function menuChips(menu, chosen) {
    return el('div', { class: 'menu-chips', 'aria-label': 'Fixed test menu' }, ...menu.map(a => { const [l, s] = menuLabel(a); return el('span', { class: 'mchip' + (a === chosen ? ' on' : '') }, l, el('small', {}, s)); }));
  }

  // ---- evidence popover: any number can show the log event it came from
  // popover values: scalars as text, arrays of records as a compact table, anything else as pretty JSON
  function evValue(v) {
    if (v == null || typeof v !== 'object') return document.createTextNode(String(v));
    if (Array.isArray(v) && v.length && v.every(x => x && typeof x === 'object' && !Array.isArray(x))) {
      const cols = [...new Set(v.flatMap(x => Object.keys(x)))];
      const cell = (x) => x == null ? '—' : typeof x === 'number' ? (Number.isInteger(x) ? String(x) : x.toFixed(2)) : typeof x === 'object' ? JSON.stringify(x) : String(x);
      return el('table', { class: 'evtab' }, el('thead', {}, el('tr', {}, ...cols.map(c => el('th', {}, c)))), el('tbody', {}, ...v.map(x => el('tr', {}, ...cols.map(c => el('td', {}, cell(x[c])))))));
    }
    if (Array.isArray(v) && v.every(x => typeof x !== 'object')) return document.createTextNode(v.join(', '));
    return el('pre', { class: 'evjson' }, JSON.stringify(v, null, 1));
  }
  let pop = null;
  function evidence(anchor, ev, extra = {}) {
    if (pop) pop.remove();
    if (!ev) return;
    const rows = [['run', extra.run], ['sequence', ev.seq], ['kind', ev.kind], ['time UTC', ev.ts], ['time KST', fmtDate(ev.ts, true)], ['sha256', ev.sha256], ['previous_sha256', ev.prev], ...Object.entries(extra.fields || {})];
    pop = el('div', { class: 'evpop', role: 'dialog', 'aria-label': 'Evidence: the log event behind this value' },
      el('div', { class: 'evhead' }, el('b', {}, 'Evidence'), el('span', { class: 'small muted' }, extra.what || ''), el('button', { class: 'x', 'aria-label': 'Close', onclick: () => { pop.remove(); pop = null; } }, '×')),
      el('dl', {}, ...rows.filter(([, v]) => v != null && v !== '').flatMap(([k, v]) => [el('dt', {}, k), el('dd', { class: /sha|previous/.test(k) ? 'mono' : '' }, evValue(v))])),
      el('div', { class: 'evfoot' }, el('button', { class: 'btn sm', onclick: (x) => { navigator.clipboard?.writeText(JSON.stringify({ run: extra.run, event: ev, ...extra.fields }, null, 2)); x.currentTarget.textContent = 'Copied'; } }, 'Copy JSON'),
        el('span', { class: 'small muted' }, `events.jsonl, line ${ev.seq + 1}. Each event carries its own sha256 and the previous one.`)));
    document.body.append(pop);
    const r = anchor.getBoundingClientRect(); const w = Math.min(420, innerWidth - 20);
    pop.style.left = Math.max(10, Math.min(innerWidth - w - 10, r.left)) + 'px'; pop.style.top = (r.bottom + scrollY + 8) + 'px'; pop.style.width = w + 'px';
    const close = (x) => { if (pop && !pop.contains(x.target) && x.target !== anchor) { pop.remove(); pop = null; document.removeEventListener('pointerdown', close); } };
    setTimeout(() => document.addEventListener('pointerdown', close), 0);
  }
  // wrap a node so a click shows its evidence
  function ev(node, evd, extra) { if (!evd) return node; node.classList.add('ev'); node.setAttribute('tabindex', '0'); node.setAttribute('title', 'Show the log event behind this'); const f = (x) => { x.stopPropagation(); evidence(node, evd, extra); }; node.addEventListener('click', f); node.addEventListener('keydown', (x) => { if (x.key === 'Enter' || x.key === ' ') { x.preventDefault(); f(x); } }); return node; }

  // ---- mini breadboard diagram from the wiring record (shown until a photo exists)
  function boardSVG(board, { crop = false } = {}) {
    const NS = 'http://www.w3.org/2000/svg';
    const s = (t, a = {}, txt) => { const n = document.createElementNS(NS, t); for (const [k, v] of Object.entries(a)) n.setAttribute(k, v); if (txt != null) n.textContent = txt; return n; };
    const p = 24, left = 44, top = 62;
    const rowIdx = { A: 0, B: 1, C: 2, D: 3, E: 4, F: 6, G: 7, H: 8, I: 9, J: 10 };
    const X = col => left + (col - 1) * p, Y = row => top + rowIdx[row] * p;
    const hole = id => ({ x: X(+id.slice(1)), y: Y(id[0]) });
    const W = left + 16 * p + 34, H = top + 10 * p + 44;
    const vb = crop ? `${left - 30} ${top - 52} ${X(15) - left + 48} ${Y('E') - top + 70}` : `0 0 ${W} ${H}`;
    const svg = s('svg', { viewBox: vb, role: 'img', 'aria-label': `Mini breadboard diagram: ${board.record}${crop ? ', rows A–E, columns 1–15' : ''}` });
    svg.append(s('rect', { x: 18, y: top - 20, width: W - 30, height: 10 * p + 56, rx: 10, fill: '#f6f7f4', stroke: '#c9cec7', 'stroke-width': 1.5 }));
    svg.append(s('rect', { x: 18, y: Y('E') + p * 0.62, width: W - 30, height: p * 0.76, fill: '#e3e6e1' }));
    for (const r of Object.keys(rowIdx)) { svg.append(s('text', { x: 30, y: Y(r) + 4, 'text-anchor': 'middle', 'font-size': 11, fill: '#8c939a', 'font-family': 'Archivo Narrow, Arial, sans-serif' }, r)); for (let c = 1; c <= 17; c++) svg.append(s('rect', { x: X(c) - 3.5, y: Y(r) - 3.5, width: 7, height: 7, rx: 1.5, fill: '#b9bfb7' })); }
    for (const c of [1, 5, 10, 15]) svg.append(s('text', { x: X(c), y: Y('J') + 24, 'text-anchor': 'middle', 'font-size': 11, fill: '#8c939a', 'font-family': 'Archivo Narrow, Arial, sans-serif' }, c));
    const netColor = { IN: '#1f9a52', OUT: '#2b6bdc', REF: '#8b949b' };
    for (const ld of board.leads || []) { const a = hole(ld.hole); svg.append(s('path', { d: `M${a.x},${a.y} L${a.x},${top - 34}`, stroke: netColor[ld.net], 'stroke-width': 5, 'stroke-linecap': 'round', fill: 'none' })); svg.append(s('text', { x: a.x, y: top - 40, 'text-anchor': 'middle', 'font-size': 14, 'font-weight': 600, fill: netColor[ld.net], 'font-family': 'Archivo Narrow, Arial, sans-serif' }, ld.net)); }
    for (const part of board.parts || []) {
      const a = hole(part.from), b = hole(part.to); const mid = (a.x + b.x) / 2, len = (b.x - a.x) * 0.56;
      svg.append(s('line', { x1: a.x, y1: a.y, x2: b.x, y2: b.y, stroke: '#8c939a', 'stroke-width': 2 }));
      const halo = { 'paint-order': 'stroke', stroke: '#f6f7f4', 'stroke-width': 4, 'stroke-linejoin': 'round' };
      if (part.kind === 'R') { svg.append(s('rect', { x: mid - len / 2, y: a.y - 6, width: len, height: 12, rx: 6, fill: '#e6d7b3', stroke: '#9a8b6a', 'stroke-width': 1.5 })); svg.append(s('text', { x: mid, y: a.y - 12, 'text-anchor': 'middle', 'font-size': 13, 'font-weight': 600, fill: '#22272e', 'font-family': 'Archivo Narrow, Arial, sans-serif', ...halo }, part.label)); }
      else { svg.append(s('rect', { x: mid - len / 2, y: a.y - 9, width: len, height: 18, rx: 3, fill: '#f0e2a2', stroke: '#a08a2e', 'stroke-width': 1.5 })); svg.append(s('text', { x: mid, y: a.y + 26, 'text-anchor': 'middle', 'font-size': 13, 'font-weight': 600, fill: '#22272e', 'font-family': 'Archivo Narrow, Arial, sans-serif', ...halo }, part.label)); }
      for (const q of [a, b]) svg.append(s('circle', { cx: q.x, cy: q.y, r: 3.5, fill: '#5f6670' }));
    }
    return svg;
  }

  // ---- a netlist drawn as a schematic (for proposed circuits: the FULL proposed netlist, redrawn)
  function netlistSVG(elements, { highlight = [] } = {}) {
    const NS = 'http://www.w3.org/2000/svg';
    const s = (t, a = {}, txt) => { const n = document.createElementNS(NS, t); for (const [k, v] of Object.entries(a)) n.setAttribute(k, v); if (txt != null) n.textContent = txt; return n; };
    const W = 760, TOP = 120, BOT = 300; const nodes = ['IN', 'N1', 'N2', 'OUT'];
    const used = nodes.filter(n => elements.some(e => e.a === n || e.b === n)); const xs = {}; used.forEach((n, i) => xs[n] = 90 + i * ((W - 180) / Math.max(1, used.length - 1)));
    const svg = s('svg', { viewBox: `0 0 ${W} ${BOT + 60}`, role: 'img', 'aria-label': 'Proposed circuit' });
    svg.append(s('rect', { width: '100%', height: '100%', fill: '#fff' }));
    const hi = new Set(highlight); const col = (e) => hi.has(e.name) ? '#d5342c' : '#000';
    const series = elements.filter(e => e.a !== 'REF' && e.b !== 'REF'), shunt = elements.filter(e => e.a === 'REF' || e.b === 'REF');
    const label = (e) => `${e.name}  ${e.kind === 'R' ? fmtR(e.value) : e.kind === 'C' ? fmtC(e.value) : e.kind === 'D' ? 'diode' : ''}`;
    for (const e of series) { const x0 = Math.min(xs[e.a], xs[e.b]), x1 = Math.max(xs[e.a], xs[e.b]); const m = (x0 + x1) / 2;
      svg.append(s('line', { x1: x0, y1: TOP, x2: x1, y2: TOP, stroke: col(e), 'stroke-width': 4 }));
      if (e.kind === 'W') continue;
      svg.append(s('rect', { x: m - 60, y: TOP - 18, width: 120, height: 36, fill: '#fff', stroke: col(e), 'stroke-width': 4, 'stroke-dasharray': hi.has(e.name) ? '10 7' : 'none' }));
      svg.append(s('text', { x: m, y: TOP - 30, 'text-anchor': 'middle', 'font-size': 20, 'font-family': 'Archivo Narrow, Arial, sans-serif', fill: col(e) }, label(e))); }
    const byNode = {}; for (const e of shunt) { const n = e.a === 'REF' ? e.b : e.a; (byNode[n] = byNode[n] || []).push(e); }
    for (const [n, list] of Object.entries(byNode)) list.forEach((e, i) => { const x = xs[n] + (i - (list.length - 1) / 2) * 120; svg.append(s('circle', { cx: xs[n], cy: TOP, r: 5, fill: '#000' }));
      svg.append(s('line', { x1: xs[n], y1: TOP, x2: x, y2: TOP + 30, stroke: col(e), 'stroke-width': 4 })); svg.append(s('line', { x1: x, y1: TOP + 30, x2: x, y2: BOT, stroke: col(e), 'stroke-width': 4 }));
      const mid = (TOP + 30 + BOT) / 2; const dash = hi.has(e.name) ? '10 7' : 'none';
      if (e.kind === 'R') svg.append(s('rect', { x: x - 16, y: mid - 40, width: 32, height: 80, fill: '#fff', stroke: col(e), 'stroke-width': 4, 'stroke-dasharray': dash }));
      else if (e.kind === 'C') { svg.append(s('rect', { x: x - 36, y: mid - 14, width: 72, height: 28, fill: '#fff', stroke: 'none' })); svg.append(s('line', { x1: x - 32, y1: mid - 8, x2: x + 32, y2: mid - 8, stroke: col(e), 'stroke-width': 4 })); svg.append(s('line', { x1: x - 32, y1: mid + 8, x2: x + 32, y2: mid + 8, stroke: col(e), 'stroke-width': 4 })); }
      else if (e.kind === 'D') { const down = e.a !== 'REF'; svg.append(s('rect', { x: x - 26, y: mid - 26, width: 52, height: 52, fill: '#fff', stroke: 'none' })); svg.append(s('polygon', { points: down ? `${x - 22},${mid - 22} ${x + 22},${mid - 22} ${x},${mid + 18}` : `${x - 22},${mid + 22} ${x + 22},${mid + 22} ${x},${mid - 18}`, fill: '#fff', stroke: col(e), 'stroke-width': 4, 'stroke-dasharray': dash })); svg.append(s('line', { x1: x - 22, y1: down ? mid + 18 : mid - 18, x2: x + 22, y2: down ? mid + 18 : mid - 18, stroke: col(e), 'stroke-width': 4 })); }
      const leftSide = list.length > 1 && i === 0;
      svg.append(s('text', { x: leftSide ? x - 44 : x + 44, y: mid + 7, 'text-anchor': leftSide ? 'end' : 'start', 'font-size': 20, 'font-family': 'Archivo Narrow, Arial, sans-serif', fill: col(e) }, label(e))); });
    svg.append(s('line', { x1: 60, y1: BOT, x2: W - 60, y2: BOT, stroke: '#000', 'stroke-width': 4 }));
    for (const n of used) svg.append(s('text', { x: xs[n], y: TOP - 60, 'text-anchor': 'middle', 'font-size': 22, 'font-family': 'Archivo Narrow, Arial, sans-serif' }, n));
    svg.append(s('text', { x: 60, y: BOT + 36, 'font-size': 22, 'font-family': 'Archivo Narrow, Arial, sans-serif' }, 'REF'));
    return svg;
  }

  return { names, fmtSI, fmtParam, fmtFit, FIT_BOUNDS, sourceWord, sourceShort, quantityWord, chosenWord, bandFits, bandText, defaultRun, heroLine, proposalName, diffWords, proposerWords, fitOverlay, words, verdictWords, kindWord, menuChips, evidence, ev, boardSVG, netlistSVG, fmtMiss, REDUCED, $, el, json, loadCases, loadRuns, loadRun, loadNotes, loadResults, expName, fmtVal, fmtR, fmtC, fmtUSD, fmtClock, fmtDur, fmtLog, fmtDate, menuLabel, schematic, overlaySVG, Scope, Meter, stepTraces, stepTime };
})();
