// The replay: one recorded diagnosis, played back from its log in order. Forecasts are drawn before the
// measurement that tests them, because that is the order they happened in. Needles move only to misses the
// fit engine logged. Every block's headline is one plain sentence; the numbers under it come from the log,
// and clicking any of them shows the log event (sequence, hashes) it came from.
(async () => {
  const { $, el, expName, fmtVal, fmtUSD, fmtClock, fmtDur, fmtLog, fmtDate, menuLabel, menuChips, words, schematic, overlaySVG, fitOverlay, netlistSVG, Scope, Meter, stepTraces, stepTime, ev, fmtMiss, REDUCED } = BM;
  const q = new URLSearchParams(location.search);
  const [index, cases, notes] = await Promise.all([BM.loadRuns(), BM.loadCases(), BM.loadNotes()]);
  const runId = q.get('run') || BM.defaultRun(index.runs || [], '01')?.id;
  if (!runId && !q.get('devsrc')) { $('#book').textContent = 'No recorded runs yet.'; return; }
  const run = q.get('devsrc') ? await BM.json(q.get('devsrc')) : await BM.loadRun(runId); // devsrc: tools/ fixtures only, never linked
  const kase = cases.cases.find(c => c.id === run.case);
  for (const pr of run.structure || []) BM.names[pr.id] = BM.proposalName(pr);
  for (const g of run.reading?.groups || []) for (const m of g.members || []) BM.names[m.id] = m.label || m.words;
  const note = notes.runs?.[run.id] || {};
  const SWEEP_MS = REDUCED ? 1 : 1700;
  const EV = (node, evd, what, fields) => ev(node, evd, { run: run.id, what, fields });
  document.title = `Case ${run.case} · ${run.label} replay · BenchMate`;
  if (run.dev) document.body.classList.add('dev');

  // ---------- header / shelf / rail
  $('#case-title').textContent = kase.title;
  $('#case-n').textContent = `Case ${run.case} · ${run.label}`;
  $('#shelf-title').textContent = `Case ${run.case} · ${kase.title}`;
  const modelName = String(run.model || '').replace(/^muse-spark-(\S+)$/, 'Muse Spark $1');
  const whatRun = run.pilot ? 'Pilot run' : run.state === 'restored' || /restored/i.test(run.label || '') ? 'Rerun after the fault was repaired' : 'Diagnosis on the faulted board';
  $('#replay-of').textContent = `${whatRun}, recorded ${fmtDate(run.started_utc)}${modelName ? ' · ' + modelName : ''}`;
  $('#meters-head').textContent = `Explanations on trial · how far each one’s forecast misses the board; red past the ${run.allowance_mV ?? 9} mV allowance`;
  const cls = run.classification || { label: run.pilot ? 'Pilot run — not counted' : 'Counted run' };
  $('#badge').replaceWith(el('span', { class: 'badge ' + (run.counted ? 'live' : run.pilot ? 'pilot' : 'pending'), id: 'badge', title: (cls.label || '') + (cls.basis ? ' — ' + cls.basis : '') }, cls.public_label || cls.label));
  $('#report-link').href = `case.html?id=${run.case}&run=${run.id}`;
  const scope = new Scope($('#scope'), { fill: true }); // the wrap's CSS height sets the scope; the shelf never passes 45vh
  const idle = $('#scope-idle');
  const railSchem = await schematic(kase.design); $('#rail-schem').append(railSchem);
  const railDrawing = $('#rail-schem').closest('.rail-card'); railDrawing.hidden = true; // the drawing shows once: in the scope area until the scope has traces
  const showRailDrawing = () => { railDrawing.hidden = false; };
  idle.append(el('div', { class: 'frame-in' }, await schematic(kase.design)),
    el('p', {}, 'The drawing Spark read. Press Play below: every forecast is drawn before the bench measures.'));
  if (run.design_amendment) idle.append(el('p', { class: 'small muted amend' }, run.design_amendment.text));
  if (run.design_amendment) $('#rail-schem-note').append(' ', el('span', { class: 'amend' }, run.design_amendment.text));
  const metersBox = $('#meters');
  const meters = {}; let meterOrder = [];
  const ensureMeter = (id, value) => {
    if (meters[id]) return meters[id];
    const m = new Meter(id, expName(id), { value });
    meters[id] = m; meterOrder.push(id);
    $('#meters-empty')?.remove();
    metersBox.append(m.root); return m;
  };
  const waitingMeters = () => { metersBox.innerHTML = ''; for (const k in meters) delete meters[k]; meterOrder = [];
    for (const id of ['nominal', ...(run.design || []).filter(d => d.kind !== 'W').map(d => 'changed:' + d.name)]) { const m = ensureMeter(id); m.readout.firstChild.textContent = 'waiting'; m.readout.lastChild.textContent = ''; m.root.classList.add('wait'); } };

  // ---------- shelf: full / compact. Compact keeps a 110 px scope strip and one row of chips that mirror the meters,
  // so a verdict is never missed while collapsed. Auto-collapses on scroll unless the viewer toggled it by hand.
  const shelf = $('#shelf'), chips = $('#meter-chips'), toggle = $('#shelf-toggle');
  const phone = () => matchMedia('(max-width: 900px)').matches;
  { const shelfEl = $('#shelf'); const setH = () => document.documentElement.style.setProperty('--shelf-h', shelfEl.offsetHeight + 'px'); new ResizeObserver(setH).observe(shelfEl); setH(); } // the sticky rail sits under the shelf, whatever its height
  let pinned = false, mode = 'full';
  const chipStatus = m => m.root.classList.contains('out') || m.root.classList.contains('dead') ? 'out' : m.root.classList.contains('wait') ? 'wait' : m.root.classList.contains('bad') ? 'bad' : m.val == null ? 'wait' : 'fit';
  const renderChips = () => {
    chips.replaceChildren(...meterOrder.map(id => { const m = meters[id]; if (!m) return null;
      const st = chipStatus(m), val = m.readout.firstChild.textContent;
      return el('span', { class: 'chip-m ' + st + (m.root.classList.contains('dead') ? ' dead' : ''), title: `${m.name.firstChild.textContent}: ${val}` }, el('i'), el('span', { class: 'cn' }, m.name.firstChild.textContent), el('span', { class: 'cv' }, val)); }).filter(Boolean));
    metersBox.classList.toggle('many', meterOrder.length > 4); metersBox.dataset.n = String(meterOrder.length);
  };
  new MutationObserver(renderChips).observe(metersBox, { subtree: true, childList: true, characterData: true, attributes: true, attributeFilter: ['class'] });
  const setMode = (m, byUser) => {
    mode = m; shelf.classList.toggle('compact', m === 'compact'); shelf.classList.toggle('full', m !== 'compact');
    toggle.textContent = m === 'compact' ? 'Full player ▾' : 'Compact player ▴'; toggle.setAttribute('aria-expanded', String(m !== 'compact'));
    if (byUser) { pinned = true; try { localStorage.setItem('bm.shelf', m); } catch {} }
    requestAnimationFrame(() => scope.draw());
  };
  toggle.addEventListener('click', () => setMode(mode === 'compact' ? 'full' : 'compact', true));
  let stored = null; try { stored = localStorage.getItem('bm.shelf'); } catch {}
  setMode(stored === 'compact' || stored === 'full' ? stored : phone() ? 'compact' : 'full');
  let scrollTick = 0;
  addEventListener('scroll', () => { if (pinned || phone() || scrollTick) return; scrollTick = requestAnimationFrame(() => { scrollTick = 0;
    const y = scrollY; if (y > 320 && mode !== 'compact') setMode('compact'); else if (y < 40 && mode !== 'full') setMode('full'); }); }, { passive: true });
  addEventListener('resize', () => requestAnimationFrame(() => scope.draw()));

  // ---------- replay clock
  const tl = run.timeline;
  const END = Math.max(run.play_length_s, tl[tl.length - 1].t_play + 0.5);
  const SPEEDS = [1, 4, 16];
  let pos = 0, playing = false, speed = Number(sessionStorage.getItem('bm.speed')) || 4, next = 0, lastWall = 0, raf = 0;
  if (!SPEEDS.includes(speed)) speed = 4;
  const sweeps = [];
  const scrub = $('#scrub'); scrub.max = END.toFixed(2);
  const speedBtn = $('#speed');
  const setSpeed = s => { speed = s; try { sessionStorage.setItem('bm.speed', s); } catch {} speedBtn.textContent = `${s}×`; speedBtn.setAttribute('aria-label', `Replay speed: ${s}×`); };
  speedBtn.addEventListener('click', () => setSpeed(SPEEDS[(SPEEDS.indexOf(speed) + 1) % SPEEDS.length])); setSpeed(speed);
  const playBtn = $('#play');
  const clock = () => { $('#clock').textContent = `${fmtClock(Math.min(pos, END))} / ${fmtClock(END)}`; };
  const setPlaying = p => { playing = p; playBtn.textContent = p ? 'Pause' : (pos >= END ? 'Replay again' : 'Play'); playBtn.setAttribute('aria-pressed', String(p)); if (p) { idle.classList.add('off'); lastWall = performance.now(); raf = requestAnimationFrame(tick); } };
  playBtn.addEventListener('click', () => { if (pos >= END) seek(0); setPlaying(!playing); });
  scrub.addEventListener('input', () => { seek(Number(scrub.value)); if (Number(scrub.value) > 0) idle.classList.add('off'); });

  function tick(now) {
    if (!playing) return;
    pos = Math.min(END, pos + (now - lastWall) / 1000 * speed);
    while (next < tl.length && tl[next].t_play <= pos) dispatch(tl[next++], false);
    lastWall = now;
    for (const s of [...sweeps]) { const p = Math.min(1, (now - s.startWall) / SWEEP_MS); for (const tr of s.traces) tr.progress = p; if (p >= 1) { sweeps.splice(sweeps.indexOf(s), 1); s.done?.(); } }
    if (sweeps.length) scope.draw();
    scrub.value = pos; clock();
    if (pos >= END && next >= tl.length) { setPlaying(false); return; }
    raf = requestAnimationFrame(tick);
  }
  function seek(t) {
    cancelAnimationFrame(raf); sweeps.length = 0;
    book.innerHTML = ''; waitingMeters();
    scope.set([], [], ''); state = freshState(); benchState(); railDrawing.hidden = true; intro(); if (t === 0) idle.classList.remove('off');
    pos = t; next = 0;
    while (next < tl.length && tl[next].t_play <= pos) dispatch(tl[next++], true);
    scrub.value = pos; clock();
    if (playing) { lastWall = performance.now(); raf = requestAnimationFrame(tick); }
  }

  // ---------- notebook
  const book = $('#book');
  const freshState = () => ({ thinking: null, pending: null, steps: {}, seal: 'sealed', totals: null, dead: {}, load: false, last: '—', proposals: {}, scored: 0, said: {} });
  let state = freshState();
  const stepOf = n => run.steps.find(s => s.n === n);
  const logT = e => fmtLog(run.started_utc, e.t_log);
  function block(e, cls, who, headline, ...body) {
    const n = el('div', { class: `entry ${cls}` }, el('div', { class: 't num' }, logT(e)),
      el('div', {}, el('div', { class: 'who' }, el('i', { class: 'dot' }), who), headline ? el('p', { class: 'lead' }, headline) : null, el('div', { class: 'body' }, ...body)));
    book.append(n); if (!REDUCED) n.scrollIntoView({ block: 'nearest', behavior: 'smooth' }); return n;
  }
  const callLine = (calls, role) => calls?.length ? el('p', { class: 'calls small muted' }, ...calls.map((c, i) => EV(el('span', {}, `${role}${calls.length > 1 ? ' · call ' + (i + 1) : ''}: ${c.seconds != null ? c.seconds + ' s, ' : ''}${fmtUSD(c.cost)}, ${c.out_tokens} output tokens`), c.ev, role, { seconds: c.seconds, cost_usd: c.cost, output_tokens: c.out_tokens, input_tokens: c.in_tokens, reasoning_tokens: c.reasoning_tokens })).flatMap((x, i) => i ? [' · ', x] : [x])) : null;
  const counters = t => { if (!t) return; $('#c-calls').textContent = t.spark_calls; $('#c-cost').textContent = fmtUSD(t.spark_cost); $('#c-exp').textContent = Object.keys(state.steps).length; };
  const setSeal = (s, text) => { const b = $('#seal'); b.className = 'seal ' + s; b.textContent = text; $('#bs-seal').textContent = text.toLowerCase(); };
  const benchState = () => { $('#bs-load').textContent = state.load ? '9.99 kΩ load connected' : 'no load'; $('#bs-last').textContent = state.last; };
  const num = (txt, evd, what, fields) => EV(el('span', { class: 'num' }, txt), evd, what, fields);

  function dispatch(e, instant) {
    state.totals = e.totals; counters(e.totals);
    const H = handlers[e.kind]; if (H) H(e, instant);
  }
  const handlers = {
    spark_choice(e) {
      if (state.thinking) { state.thinking.remove(); state.thinking = null; }
      const st = stepOf(e.step); state.steps[e.step] = st; counters(e.totals);
      block(e, 'spark', 'Muse Spark 1.3 · chose the next experiment', null,
        el('div', { class: 'exp-title' }, el('span', { class: 'n' }, e.step), e.label),
        el('p', { class: 'quote' }, e.reason || '(no reason logged)'),
        menuChips(run.menu, e.action),
        state.said.menu ? null : (state.said.menu = true, el('p', { class: 'small muted' }, 'The whole fixed menu, the same for every case; the solid chip is Spark’s pick. The runner never chooses.')),
        callLine(e.calls, 'Muse Spark chose the next experiment'));
    },
    forecast_frozen(e) {
      const st = e.step === 'verification' ? null : stepOf(e.step);
      const sha = EV(el('span', { class: 'chip sha' }, ' sha256 ' + e.sha), e.ev, 'frozen forecast', { sha256_full: e.sha_full });
      const chips = el('div', { class: 'chips' }, sha, ...e.ids.map(id => el('span', { class: 'chip' }, el('i'), expName(id))));
      block(e, 'fit', e.final ? 'Fit engine · final forecast, frozen before the check' : `Fit engine · forecasts frozen before measuring step ${e.step}`, words.forecast(e), chips);
      for (const id of e.ids) { const m = ensureMeter(id); m.root.classList.remove('wait'); }
      showRailDrawing();
      if (st) { scope.set(stepTime(st), stepTraces(st, { measuredProgress: 0 }), `Step ${st.n} · ${st.label}`); scope.root.classList.add('idle'); }
      else if (run.verification?.forecasts?.[0]) {
        const f = run.verification.forecasts[0]; const id = Object.keys(f)[0]; const v = f[id]; const t = v.map((_, i) => i * 1e-3);
        const r0 = run.reserved?.[0]; scope.set(t, [{ id, label: expName(id) + ' forecast', kind: 'fc', v, dashed: true, progress: 1 }], `Reserved ${r0 ? r0.kind + ' ' + r0.amplitude_v + ' V' : 'input'} · forecast only`);
      }
    },
    bench_request(e) {
      const tape = el('div', { class: 'note-tape' }, el('b', {}, 'Bench: ' + e.text), el('span', { class: 'wait' }, 'Waiting for the operator. USB off while wiring.'));
      state.pending = tape; block(e, 'bench', 'Bench · operator asked to rewire', null, tape);
    },
    operator_confirm(e) {
      const tape = state.pending;
      if (e.fixture === 'output_load' || /connect|load/i.test(e.choice || '') && !/remove|disconnect|unloaded/i.test(e.choice || '')) state.load = e.fixture === 'output_load';
      else if (e.fixture) state.load = e.fixture === 'output_load';
      state.last = e.gap_real_s ? `${e.fixture === 'output_load' ? 'load connected' : 'load removed'} · ${fmtDur(e.gap_real_s)}` : (e.fixture === 'unloaded' ? 'initial wiring checked' : e.fixture || '—'); benchState();
      const wait = e.gap_real_s ? `Done · ${fmtDur(e.gap_real_s)} at the bench, shortened here.` : 'Done.';
      const det = el('details', { class: 'small' }, el('summary', {}, 'Operator’s words'), el('p', { class: 'quote' }, e.text));
      if (tape) { const w = tape.querySelector('.wait'); w.textContent = wait; EV(w, e.ev, 'operator confirmation', { fixture: e.fixture, real_wait_s: e.gap_real_s }); tape.append(det); state.pending = null; }
      else block(e, 'bench', 'Bench · operator confirmed the wiring', null, el('div', { class: 'note-tape' }, EV(el('b', {}, 'Bench: initial wiring checked, no load'), e.ev, 'operator confirmation', { fixture: e.fixture }), det));
    },
    capture(e, instant) {
      const st = stepOf(e.step);
      if (e.verification) { const k = (state.vcap = (state.vcap || 0) + 1); const n = run.reserved?.length || 2;
        state.pendingCap = block(e, 'bench', `Bench · held-back input ${k} of ${n}`, words.heldBack(k, n), el('span', { class: 'thinking' }, el('i'), 'Acquiring 512 frames, IN and OUT… the guard checks the reference first.')); return; }
      const n = block(e, 'bench', `Bench · measuring step ${e.step}`, words.capture(e), el('span', { class: 'thinking' }, el('i'), 'Acquiring 512 frames, IN and OUT…'));
      const traces = stepTraces(st, { measuredProgress: instant ? 1 : 0 });
      scope.set(stepTime(st), traces, `Step ${st.n} · ${st.label}`); scope.root.classList.remove('idle');
      const done = () => { n.querySelector('.body').replaceChildren(EV(el('span', { class: 'small muted' }, `512 frames captured. IN and OUT now on the scope over the frozen forecast${(st.forecasts || []).length > 1 ? 's' : ''}.`), st.observation?.ev, 'measurement')); };
      if (instant) done(); else sweeps.push({ traces: traces.filter(t => t.kind !== 'fc'), startWall: performance.now(), done });
    },
    fit_result(e) {
      const st = stepOf(e.step); const allow = run.allowance_mV;
      for (const r of e.results) if (!r.adequate && state.dead[r.id] == null) state.dead[r.id] = e.step;
      const rows = e.results.map(r => { const out = !r.adequate; const bad = r.passed_this_step === false; return el('tr', { 'data-id': r.id, class: out ? 'out' : '' },
        el('td', {}, expName(r.id)), el('td', { class: 'muted' }, r.value != null ? ['fitted so far ', num(BM.fmtFit(r.kind, r.value, r.at_bound), e.ev, `fitted value of ${expName(r.id)} on step ${e.step}`, { explanation: r.id, raw_value: r.value, kind: r.kind, parameter_at_bound: r.at_bound, fit_range: BM.FIT_BOUNDS[r.kind] })] : 'drawn values'),
        el('td', {}, num(fmtMiss(r.decided_mV ?? r.miss_mV), st.fit_ev, `miss of ${expName(r.id)} on step ${e.step}`, { explanation: r.id, step: e.step, decided_by: r.worst_region ? `worst region ${r.worst_region}` : 'whole step', decided_mV: r.decided_mV, whole_step_RMS_mV: r.miss_mV, regions: r.regions, passed: r.passed_this_step, status: r.status }), r.worst_region ? el('small', { class: 'muted' }, ` worst region: ${r.worst_region.replace(/_/g, ' ')}`) : null),
        el('td', {}, out ? el('span', { class: 'tape red' }, `Ruled out after step ${state.dead[r.id]}`) : el('span', { class: 'muted' }, 'still fits'))); });
      const fresh = e.results.filter(r => !meters[r.id]).map(r => expName(r.id));
      block(e, 'fit', `Fit engine · ngspice, step ${e.step}`, words.fit({ ...e, already_out: e.results.filter(r => state.dead[r.id] != null && state.dead[r.id] < e.step).map(r => r.id) }, allow),
        el('div', { class: 'tscroll' }, el('table', { class: 'fit-table' }, el('thead', {}, el('tr', {}, el('th', {}, 'Explanation'), el('th', {}, 'Value'), el('th', {}, 'Miss'), el('th', {}, ''))), el('tbody', {}, ...rows))),
        el('p', { class: 'small muted' }, `${state.said.miss ? '' : (state.said.miss = true, `Miss is the RMS difference between the forecast and the measured OUT; the frozen ${allow} mV allowance applies to the whole step and to every region of it, so the number shown is the worst of those.`)}${fresh.length ? ` New from this measurement: ${fresh.join(', ')} (fitted to it, so not forecast for it).` : ''}${e.sim_calls ? ` ${e.sim_calls} ngspice runs.` : ''}`.trim()));
      for (const r of e.results) { const m = ensureMeter(r.id); m.root.classList.remove('wait'); if (state.dead[r.id] != null && state.dead[r.id] < e.step) { m.die(); continue; } m.setValue(r.decided_mV ?? r.miss_mV ?? 0, r.value != null ? BM.fmtFit(r.kind, r.value, r.at_bound) : 'drawn values', r.passed_this_step, `step ${e.step}`, r.worst_region); }
      state.thinking = block({ t_log: e.t_log + 0.5 }, 'spark', 'Muse Spark 1.3', null, el('span', { class: 'thinking' }, el('i'), 'Reading the results, deciding the next step…'));
    },
    ruled_out(e) { meters[e.id]?.ruleOut(e.step); },
    structure_proposed(e) { // all needles red → a new explanation, drawn as the full proposed circuit
      if (state.thinking) { state.thinking.remove(); state.thinking = null; }
      const added = (e.diff?.added || []).map(x => x.name), recon = (e.diff?.reconnected || []).map(x => x.name);
      const card = el('div', { class: 'card violet propose' }, el('div', { class: 'schem-wrap' }, netlistSVG(e.elements, { highlight: added.concat(recon) })),
        el('p', { class: 'small muted' }, BM.diffWords(e.diff) + ' Drawn as the whole proposed circuit, not as an overlay.'),
        e.rationale ? el('p', { class: 'quote' }, e.rationale) : null,
        el('p', { class: 'small muted' }, `${BM.proposerWords(e.selected_by)}. A proposal is a hypothesis: it is fitted and checked like the others.`));
      block(e, 'spark', 'Muse Spark 1.3 · proposes a part the drawing does not show', words.structure(e), card);
      const m = ensureMeter(e.id); m.root.classList.remove('wait'); m.root.classList.add('proposal'); state.proposals[e.id] = e;
      m.name.firstChild.textContent = BM.proposalName(e); BM.names[e.id] = BM.proposalName(e);
    },
    structure_fit(e) {
      const m = ensureMeter(e.id); m.root.classList.remove('wait');
      if (e.status === 'fit_error') { m.readout.firstChild.textContent = 'fit error'; m.root.classList.add('bad'); }
      else m.setValue(e.miss_mV ?? 0, e.fitted_parameters ? Object.entries(e.fitted_parameters).map(([k, v]) => BM.fmtParam(k, v)).join(', ') : '', e.passed?.every(Boolean), 'all steps');
      if (e.status === 'inadequate') { m.ruleOut('the proposal'); m.die(); }
      block(e, 'fit', `Fit engine · ngspice, proposed circuit`, words.structureFit(e),
        el('p', { class: 'small muted' }, [e.status ? `Status: ${e.status}` : null, e.misses?.length ? `misses per step: ${e.misses.map(fmtMiss).join(', ')}` : null, e.simulator_calls ? `${e.simulator_calls} ngspice runs` : null, e.error ? `error: ${e.error}` : null].filter(Boolean).join(' · ')),
        el('p', { class: 'small muted' }, '“Fits” means fits the training measurements. The check on held-back inputs is still ahead; the site never promotes a fit to a verdict.'));
    },
    verification_requested(e) {
      if (state.thinking) { state.thinking.remove(); state.thinking = null; }
      block(e, 'spark', 'Muse Spark 1.3 · asked for the check', words.verifyReq(), el('p', { class: 'small muted' }, 'Two reserved inputs, never used for fitting, will be measured next. The surviving explanation must forecast them first.'), callLine(e.calls, 'Muse Spark asked for the check'));
      for (const id of meterOrder) if (!meters[id].root.classList.contains('out') && !meters[id].root.classList.contains('wait')) meters[id].carry('Carried to the check');
    },
    verification_published(e) { block(e, 'fit', 'GitHub · forecast pushed before measuring', words.published(), el('p', { class: 'small' }, 'Commit ', EV(el('a', { class: 'linkish', href: e.url, target: '_blank', rel: 'noopener' }, e.commit), e.ev, 'publication', { commit: e.commit_full, url: e.url }), '. From here the bench cannot be re-fitted to the reserved inputs.')); },
    verification_observed(e, instant) { // the bench measures a held-back input: measured trace over the frozen forecast
      const obs = run.verification?.observations?.[e.index - 1]; const fc = run.verification?.forecasts?.[e.index - 1] || {}; const rs = run.reserved?.[e.index - 1];
      const label = rs ? `Held-back ${rs.kind} ${rs.amplitude_v} V${rs.frequency_hz ? ', ' + rs.frequency_hz + ' Hz' : ''}${rs.load_ohm ? ', load' : ', no load'}` : `Held-back input ${e.index}`;
      const traces = Object.entries(fc).map(([id, v]) => ({ id, label: expName(id) + ' forecast', kind: 'fc', v, dashed: true, progress: 1 }));
      if (obs) { traces.push({ id: 'in', label: 'IN', kind: 'in', v: obs.in_v, progress: instant ? 1 : 0 }, { id: 'out', label: 'OUT', kind: 'out', v: obs.out_v, progress: instant ? 1 : 0 }); scope.set(obs.t_s, traces, `${label} · check ${e.index} of ${run.reserved?.length || 2}`); scope.root.classList.remove('idle'); }
      const n = state.pendingCap || block(e, 'bench', `Bench · held-back input ${e.index} of ${run.reserved?.length || 2}`, words.heldBack(e.index, run.reserved?.length || 2), el('span', { class: 'thinking' }, el('i'), 'Acquiring 512 frames, IN and OUT…')); state.pendingCap = null;
      const done = () => n.querySelector('.body').replaceChildren(EV(el('span', { class: 'small muted' }, '512 frames captured. The forecast for this input was frozen and published before it.'), obs?.ev, 'held-back measurement'));
      if (instant || !obs) done(); else sweeps.push({ traces: traces.filter(t => t.kind !== 'fc'), startWall: performance.now(), done });
    },
    verification_scored(e) {
      state.scored = (state.scored || 0) + 1;
      const rows = Object.entries(e.conditional || {}).map(([id, v]) => el('tr', {}, el('td', {}, expName(id)), el('td', {}, num(fmtMiss(v.decided_mV ?? v.RMS_mV), e.ev, `held-back input ${e.index}`, { explanation: id, decided_by: v.worst_region ? `worst region ${v.worst_region}` : 'whole input', decided_mV: v.decided_mV, whole_RMS_mV: v.RMS_mV, regions: v.regions, passed: v.passed, OUT_refitted: e.OUT_refitted }), v.worst_region ? el('small', { class: 'muted' }, ` worst region: ${v.worst_region.replace(/_/g, ' ')}`) : null), el('td', {}, v.passed ? el('span', { class: 'tape grey' }, 'within allowance') : el('span', { class: 'tape red' }, 'outside allowance'))));
      block(e, 'fit', `Fit engine · held-back input ${e.index ?? ''} scored against the frozen forecast`, words.scored(e), el('table', { class: 'fit-table' }, el('tbody', {}, ...rows)), el('p', { class: 'small muted' }, e.dev_placeholder ? 'DEV PLACEHOLDER: numbers copied from a training fit to exercise this stage. Not a measurement.' : 'Scored against the frozen forecast with the measured input; nothing was re-fitted.'));
      for (const [id, v] of Object.entries(e.conditional || {})) if (meters[id] && (v.decided_mV ?? v.RMS_mV) != null) meters[id].setValue(v.decided_mV ?? v.RMS_mV, undefined, v.passed, `check ${e.index ?? ''}`, v.worst_region);
    },
    verification_completed(e) { block(e, 'fit', 'Fit engine · check complete', null, el('p', { class: 'small muted' }, `Survivors after the check: ${(e.survivors || []).map(expName).join(', ') || 'none'}.`)); },
    guard_stop(e) { if (state.thinking) { state.thinking.remove(); state.thinking = null; } if (state.pendingCap) { state.pendingCap.querySelector('.body').replaceChildren(el('span', { class: 'small muted' }, '512 frames captured; the guard check that follows failed, so this input was never scored.')); state.pendingCap = null; } setSeal('stopped', 'Stopped by the guard'); block(e, 'guard', 'Guard · reference check failed', words.guard(), EV(el('div', { class: 'card red' }, el('h4', {}, `Reference guard tripped on ${e.label.replace(/_/g, ' ')}`), el('p', {}, note.guard_detail || e.failed.join(', ')), el('p', { class: 'small muted', style: 'margin-top:4px' }, 'The guard watches the bench’s own reference voltage. No result was scored and no input was retried.')), e.ev, 'guard failure', { label: e.label, failed_checks: e.failed })); },
    stopped(e) { finale(e, 'stopped'); },
    report(e) {
      const need = run.reserved?.length || 0, got = state.scored || 0;
      if (need && got < need) block(e, 'guard', 'Check · incomplete in this recording', null, el('div', { class: 'card red' }, el('h4', {}, `Only ${got} of ${need} held-back inputs were scored.`), el('p', { class: 'small muted' }, 'A verdict is shown only after every held-back input is scored. The engine’s report is kept below as recorded.')));
      finale(e, 'verdict');
    },
    probe_path(e) { block(e, 'bench', 'Bench · probe path declared', null, el('p', {}, e.text)); },
    spark_report(e) { // the engine's report after the measurements; the seal stays closed until the reading is scored
      const surv = e.survivors || [];
      block(e, 'spark', 'Muse Spark 1.3 · report after the measurements', surv.length === 1 ? `Spark reports: ${expName(surv[0])}. The seal stays closed; one reading at the bench comes next.` : words.report(e, run),
        el('p', { class: 'small muted' }, e.verdict === 'indistinguishable' ? `Verdict ${e.verdict}: ${(e.components || []).join(' and ')} give the same terminal waveforms. The seal stays closed until one of them is read.`
          : e.verdict === 'structure_supported' ? `Verdict ${e.verdict}: the proposed circuit passed the held-back checks. Terminal measurements say what the series resistance is, not where it sits, so the engine does not open the seal yet.`
          : e.components?.length ? `Verdict ${e.verdict}: ${e.components.join(', ')}. ${run.reading?.group ? 'The part itself has not been read yet; the seal stays closed until it has.' : 'Terminal measurements alone cannot tell the visible part from an extra series path, so the engine does not open the seal yet.'}` : ''));
    },
    seal_opened(e) { finale(e, 'verdict'); },

    // ---------- the reading stage: Spark asks for one reading; bands are frozen per explanation and per
    // source before anyone reads; the operator types one value; the same rule rules explanations out
    equivalence_group(e) { // an engine rule splits one surviving explanation into electrically equivalent members
      if (state.thinking) { state.thinking.remove(); state.thinking = null; }
      const base = meters[e.base_explanation];
      for (const m of e.members || []) { BM.names[m.id] = m.label || m.words; const mm = ensureMeter(m.id, base?.name.lastChild.textContent || ''); mm.root.classList.remove('wait'); mm.name.firstChild.textContent = m.label || m.words; if (base?.val != null) { mm.setValue(base.val, undefined, true, base.readout.lastChild.textContent); } }
      if (e.split_base && base) { base.root.classList.add('split'); base.carry('Where it sits: one reading decides'); } // the base survives as its two placements; the bands belong to them
      block(e, 'fit', 'Fit engine · electrically equivalent explanations', words.equivalence(e),
        el('p', { class: 'small' }, el('span', { class: 'chip' }, el('i'), 'engine rule — electrically equivalent'), ' ', el('span', { class: 'muted' }, e.split_base ? `${expName(e.base_explanation)} passed the checks as a terminal model; it says nothing about where the resistance sits. Two placements, same waveforms: ${(e.members || []).map(m => m.words || m.label).join('; or ')}.` : `${expName(e.base_explanation)} cannot be told from ${(e.members || []).map(m => m.words || m.label).join(' or ')} by any terminal measurement: they give the same waveforms.`)),
        e.reason ? el('p', { class: 'small muted' }, e.reason) : null);
    },
    binding_stopped(e) { // the pair record stopped on a local error before Spark's body call; the chain continues in linked records
      if (state.thinking) { state.thinking.remove(); state.thinking = null; }
      block(e, 'guard', 'Record · stopped on a local input error', 'This record stops here; the chain continues in a linked record, registered first.',
        EV(el('div', { class: 'card' }, el('p', { class: 'small' }, e.line)), e.ev, 'run_failed', { stage: e.stage, error: e.error, counted_failure: true }));
    },
    reading_requested(e) {
      if (state.thinking) { state.thinking.remove(); state.thinking = null; }
      const live = meterOrder.filter(id => !meters[id].root.classList.contains('out') && !meters[id].root.classList.contains('wait') && !meters[id].root.classList.contains('split')).length;
      state.reading = { component: e.component, quantity: e.quantity, live };
      block(e, 'spark', 'Muse Spark 1.3 · asked for one reading', words.readingReq(e, live),
        el('p', { class: 'quote' }, e.reason || '(no reason logged)'),
        el('p', { class: 'small' }, el('span', { class: 'chip' }, el('i'), BM.chosenWord(e.chosen_by)), ' ', el('span', { class: 'muted' }, `What to read: ${BM.quantityWord(e.quantity, e.component)}. The operator chooses how (multimeter or marking) and reports which.`)),
        callLine(e.calls, 'Muse Spark asked for one reading'));
    },
    reading_forecast_frozen(e) {
      const bands = e.bands || []; const srcs = [...new Set(bands.map(b => b.source))]; const exps = [...new Set(bands.map(b => b.explanation))];
      const sha = EV(el('span', { class: 'chip sha' }, ' sha256 ' + e.sha), e.ev, 'frozen reading forecast', { sha256_full: e.sha_full, bands });
      const cell = (x, b) => b ? num(BM.bandText(b), e.ev, `frozen band for ${expName(x)}, ${BM.sourceShort(b.source)}`, { explanation: x, source: b.source, low: b.low, high: b.high, unit: b.unit, rule: b.rule, note: b.note }) : el('span', { class: 'muted' }, '—');
      const rows = exps.map(x => el('tr', {}, el('td', {}, expName(x)), ...srcs.map(s => { const b = bands.find(q => q.explanation === x && q.source === s); return el('td', {}, cell(x, b), b?.rule ? el('small', { class: 'muted', style: 'display:block' }, b.rule) : null); })));
      const notes = [...new Set(bands.filter(b => b.note).map(b => `${BM.sourceShort(b.source)}: ${b.note}`))];
      block(e, 'fit', 'Fit engine · reading forecast, frozen before anyone reads', words.readingForecast({ component: state.reading?.component }),
        el('div', { class: 'chips' }, sha, e.commit ? el('span', { class: 'chip' }, el('i'), 'pushed ', EV(el('a', { class: 'linkish', href: e.url || '#', target: '_blank', rel: 'noopener' }, String(e.commit).slice(0, 7)), e.ev, 'publication', { commit: e.commit, url: e.url })) : null),
        el('div', { class: 'tscroll' }, el('table', { class: 'fit-table' }, el('thead', {}, el('tr', {}, el('th', {}, 'Explanation'), ...srcs.map(s => el('th', {}, `If read by ${BM.sourceShort(s)}`)))), el('tbody', {}, ...rows))),
        el('p', { class: 'small muted' }, `Same rule as the scope: a reading inside an explanation’s band keeps it; outside, it is crossed out. Any value is allowed; it can fit one band, none, or several.${notes.length ? ' ' + notes.map(n => n.endsWith('.') ? n : n + '.').join(' ') : ''}`));
      state.bands = bands;
    },
    body_binding(e) {
      const card = el('div', { class: 'card' });
      if (e.photo) { const box = el('div', { class: 'photo', style: 'max-width:420px' }, el('img', { src: e.photo, alt: `Board photo, ${e.component} outlined by SAM 3.1` })); if (e.overlay_file) box.append(el('img', { class: 'mask', src: e.overlay_file, alt: 'SAM 3.1 outline' })); card.append(box); }
      else card.append(el('p', { class: 'small muted' }, 'Photo and SAM outline: not in this record.'));
      card.append(el('p', { class: 'small' }, EV(el('b', {}, `${e.sam_body || 'SAM body'} → ${e.component}`), e.ev, 'body binding', { sam_body: e.sam_body, component: e.component, chosen_by: e.chosen_by, operator_confirmed: e.operator_confirmed, localizer: e.localizer, mask_bounds_in_sam_input: e.bounds, sam_confidence: e.confidence, sam_input_sha256: e.input_image_sha256, bodies_retained: e.bodies }), ` · ${BM.chosenWord(e.chosen_by)}${e.operator_confirmed ? ' · confirmed by the operator' : ''}${e.bodies ? ` · SAM 3.1 returned ${e.bodies} bodies` : ''}`), e.reason ? el('p', { class: 'quote' }, e.reason) : null,
        el('p', { class: 'small muted' }, 'The outline is SAM 3.1’s. Which body is which part is Spark’s call, confirmed by a person; the site never pairs them itself.'));
      block(e, 'spark', 'Muse Spark vision · pointed at the body', words.binding(e), card);
    },
    reading_observed(e, instant) {
      const unit = e.unit || ''; const txt = String(e.value);
      const field = el('span', { class: 'readfield', 'aria-label': `${e.component} reading` }, el('span', { class: 'typed' }, instant ? txt : ''), el('span', { class: 'caret' }));
      const tape = el('div', { class: 'note-tape white' }, el('b', {}, `Reading: ${e.component} = `, field, ` ${unit}`), el('span', { class: 'src' }, `${BM.sourceWord(e.source)}${e.note ? ', ' + e.note : ''}`),
        e.gap_real_s ? el('span', { class: 'wait' }, `${e.note ? 'USB off, leads lifted, read, leads back' : 'At the bench'} · ${fmtDur(e.gap_real_s)}, shortened here.`) : null);
      EV(tape.querySelector('b'), e.ev, 'operator reading', { component: e.component, value: e.value, unit: e.unit, source: e.source, meter_range: e.meter_range, power_off: e.power_off, isolated: e.isolated, evidence_image: e.evidence_link, evidence_sha256: e.evidence_sha256 });
      block(e, 'bench', 'Bench · the operator reads one value', words.readingObs(e), tape);
      state.observed = e;
      const bands = state.bands || run.reading?.bands || [];
      const apply = () => { for (const id of meterOrder) { const m = meters[id]; if (m.root.classList.contains('out') || m.root.classList.contains('wait')) continue; const b = bands.find(q => q.explanation === id && q.source === e.source); if (!b) continue; m.band(b.low, b.high, b.unit, Number(e.value)); m.setReading(Number(e.value), unit, 'reading'); } };
      if (instant || REDUCED) { field.querySelector('.typed').textContent = txt; apply(); return; }
      let i = 0; const typed = field.querySelector('.typed'); const tick = () => { typed.textContent = txt.slice(0, ++i); if (i < txt.length) setTimeout(tick, 160); else { field.classList.add('done'); setTimeout(apply, 300); } }; setTimeout(tick, 400);
    },
    reading_scored(e) {
      const bands = state.bands || run.reading?.bands || []; const src = state.observed?.source;
      const rows = bands.filter(b => b.source === src).map(b => { const fit = (e.fits || []).includes(b.explanation); return el('tr', { class: fit ? '' : 'out' }, el('td', {}, expName(b.explanation)), el('td', {}, num(BM.bandText(b), e.ev, `band for ${expName(b.explanation)}`, { explanation: b.explanation, source: b.source, low: b.low, high: b.high, unit: b.unit, rule: b.rule })), el('td', {}, fit ? el('span', { class: 'tape grey' }, 'inside the band') : el('span', { class: 'tape read' }, 'Ruled out by one reading'))); });
      block(e, 'fit', 'Fit engine · the reading scored by the frozen bands', words.readingScored(e, bands),
        el('table', { class: 'fit-table' }, el('thead', {}, el('tr', {}, el('th', {}, 'Explanation'), el('th', {}, `Band, ${BM.sourceShort(src)}`), el('th', {}, ''))), el('tbody', {}, ...rows)),
        el('p', { class: 'small muted' }, 'Scored by code against the bands frozen before the reading. The site shows the engine’s list of fits as written.'));
      for (const id of e.fits || []) if (meters[id]) meters[id].carry(e.outcome === 'one' ? 'Fits the reading' : 'Not separated');
    },
    ruled_out_by_reading(e) { const m = meters[e.id]; if (m) { m.ruleOutByReading(); m.die(); } },

    // ---------- the unordered reading stage (case 02): Spark, asked which body is C1, named none; two bodies were read out of
    // circuit and every assignment of bodies to parts was tested against bands frozen first. No model paired a body with a part.
    binding_abstained(e) {
      if (state.thinking) { state.thinking.remove(); state.thinking = null; }
      block(e, 'spark', `Muse Spark vision · asked which body is ${e.component}`, words.bindingAbstained(e),
        EV(el('p', { class: 'quote' }, e.reason || '(no reason logged)'), e.ev, 'Spark named no body', { component: e.component, sam_bodies: e.bodies }),
        e.bodies ? el('p', { class: 'small muted' }, `SAM 3.1 had returned ${e.bodies} bodies; none is paired with a drawing part.`) : null,
        callLine(e.calls, `Muse Spark asked which body is ${e.component}`));
    },
    body_group(e) {
      const ph = run.photo || {}; const cb = e.crop_box || ph.crop_box || [0, 0, ph.image?.width || 1200, ph.image?.height || 1600];
      const box = el('div', { class: 'photo', style: 'max-width:420px' }, el('img', { src: e.photo || ph.image?.file, alt: 'Board photo with the outlines of the SAM 3.1 masks' }));
      if (e.overlay_file) box.append(el('img', { class: 'mask', src: e.overlay_file, alt: 'SAM 3.1 outlines of the two bodies' }));
      for (const [id, bb] of Object.entries(e.boxes || {})) box.append(maskLabel(id, bb, cb, [], true));
      state.group = { bodies: e.bodies, components: e.components, boxes: e.boxes };
      block(e, 'bench', 'Bench · two capacitor bodies, which is which unknown', words.bodyGroup(e),
        el('div', { class: 'card' }, box, el('p', { class: 'small', style: 'margin:6px 0 0' }, EV(el('span', {}, e.provenance || ph.provenance || ''), e.ev, 'body group', { bodies: e.bodies, components: e.components, chosen_by: e.chosen_by, spark_chose_group: e.spark_chose_group, boxes_in_sam_input: e.boxes, already_received: e.already_received })), ph.note ? el('p', { class: 'small faint', style: 'margin:4px 0 0' }, ph.note) : null),
        el('p', { class: 'small muted' }, `${(e.bodies || []).join(' and ')} are the two bodies to be read. ${e.topology || ''}`),
        el('p', { class: 'small muted' }, `Neither body is paired with ${(e.components || []).join(' or ')} here. Both will be read out of circuit, and every way of assigning the two bodies to the two parts will be tested against bands frozen before the readings.`));
    },
    group_reading_forecast(e) {
      const bands = e.bands || []; const comps = e.components || [...new Set(bands.map(b => b.component))]; const exps = [...new Set(bands.map(b => b.explanation))];
      const sha = EV(el('span', { class: 'chip sha' }, ' sha256 ' + e.sha), e.ev, 'frozen group reading forecast', { sha256_full: e.sha_full, bands, meter: e.meter, matching: e.matching });
      const cell = (x, c) => { const b = bands.find(q => q.explanation === x && q.component === c); return b ? el('td', {}, num(BM.bandText(b), e.ev, `frozen band for ${c} under ${expName(x)}`, { explanation: x, component: c, low: b.low, high: b.high, unit: b.unit, rule: b.rule }), el('small', { class: 'muted', style: 'display:block' }, b.rule)) : el('td', {}, el('span', { class: 'muted' }, '—')); };
      const rows = exps.map(x => { const role = bands.find(b => b.explanation === x)?.role; return el('tr', { class: role === 'reference' ? 'out' : '' }, el('td', {}, expName(x), el('small', { class: 'muted', style: 'display:block' }, role === 'reference' ? 'reference: already ruled out by the bench tests' : 'the surviving explanation')), ...comps.map(c => cell(x, c))); });
      const m = e.meter || {};
      block(e, 'fit', 'Fit engine · reading forecast for both bodies, frozen before anyone reads', words.groupForecast(e),
        el('div', { class: 'chips' }, sha),
        el('div', { class: 'tscroll' }, el('table', { class: 'fit-table' }, el('thead', {}, el('tr', {}, el('th', {}, 'Explanation'), ...comps.map(c => el('th', {}, `${c}, by ${BM.sourceShort(e.source)}`)))), el('tbody', {}, ...rows))),
        el('p', { class: 'small muted' }, `Multimeter on the ${m.range_uF} µF range, ${m.resolution_uF} µF resolution; allowance ${Math.round((m.relative_allowance || 0) * 100)} % + ${m.digits_allowance} digits, an engineering acceptance, not a manufacturer accuracy${m.calibrated === false ? ' (meter not calibrated)' : ''}.${m.basis ? ' ' + m.basis : ''}`),
        el('p', { class: 'small muted' }, `The bodies are not yet paired with ${comps.join(' and ')}. Rule, written down now: ${e.matching || 'every assignment of bodies to parts is tested against these bands; the nearest value is never used.'}`));
      state.gbands = bands; state.group = { ...(state.group || {}), bodies: e.bodies, components: comps, bands, meter: m, source: e.source };
      for (const x of exps) { const mt = meters[x]; const b = bands.find(q => q.explanation === x && q.component === comps[0]); if (mt && b && !mt.root.classList.contains('out')) { mt.root.classList.remove('wait'); mt.band(b.low, b.high, b.unit); } }
    },
    group_reading_observed(e, instant) {
      const g = state.group || {}; const boxes = g.boxes || {}; const unit = (e.readings || [])[0]?.unit || 'µF';
      const posWord = (body) => { const ids = Object.keys(boxes); if (ids.length !== 2 || !boxes[body]) return ''; const other = ids.find(i => i !== body); return boxes[body][1] < boxes[other][1] ? 'C-top ' : 'C-bottom '; };
      const fields = (e.readings || []).map(r => ({ r, field: el('span', { class: 'readfield', 'aria-label': `${r.body} reading` }, el('span', { class: 'typed' }, instant ? String(r.value) : ''), el('span', { class: 'caret' })) }));
      const line = el('b', {}, 'Readings: ');
      fields.forEach((f, i) => { if (i) line.append(' · '); line.append(`${posWord(f.r.body)}(${f.r.body}) = `, f.field, ` ${f.r.unit || unit}`); });
      const first = (e.readings || [])[0] || {};
      const tape = el('div', { class: 'note-tape white' }, line, el('span', { class: 'src' }, `${BM.sourceShort(e.source)}, ${first.range_uF} µF range, each capacitor removed from the board${e.power_off ? ', USB off' : ''}${e.discharge_wait ? ', discharged first' : ''}`),
        e.gap_real_s ? el('span', { class: 'wait' }, `At the bench · ${fmtDur(e.gap_real_s)}, shortened here.`) : null);
      EV(line, e.ev, 'operator readings', { source: e.source, readings: e.readings, power_off: e.power_off, discharge_wait: e.discharge_wait });
      block(e, 'bench', 'Bench · the operator reads both bodies, out of circuit', words.groupObs(e), tape,
        el('p', { class: 'small muted' }, 'Two values, by body. Which body is which part is not decided here: that is the next step, by the frozen bands.'));
      state.gobserved = e;
      if (instant || REDUCED) { for (const f of fields) { f.field.querySelector('.typed').textContent = String(f.r.value); f.field.classList.add('done'); } return; }
      let k = 0; const typeNext = () => { const f = fields[k]; if (!f) return; const txt = String(f.r.value); let i = 0; const typed = f.field.querySelector('.typed'); const tick = () => { typed.textContent = txt.slice(0, ++i); if (i < txt.length) setTimeout(tick, 160); else { f.field.classList.add('done'); k++; setTimeout(typeNext, 350); } }; tick(); }; setTimeout(typeNext, 400);
    },
    group_reading_scored(e) {
      const g = state.group || {}; const bands = state.gbands || g.bands || []; const obs = state.gobserved || {}; const vals = Object.fromEntries((obs.readings || []).map(r => [r.body, r.value]));
      const bodies = g.bodies || Object.keys(vals); const comps = g.components || [...new Set(bands.map(b => b.component))]; const unit = (obs.readings || [])[0]?.unit || 'µF';
      const perms = (arr) => arr.length <= 1 ? [arr] : arr.flatMap((x, i) => perms([...arr.slice(0, i), ...arr.slice(i + 1)]).map(r => [x, ...r]));
      const assigns = perms(bodies).map(order => Object.fromEntries(comps.map((c, i) => [c, order[i]])));
      const inBand = (x, c, v) => { const b = bands.find(q => q.explanation === x && q.component === c); return b ? (b.low == null || v >= b.low) && (b.high == null || v <= b.high) : null; };
      const exps = [...new Set(bands.map(b => b.explanation))].sort((a, b) => (bands.find(q => q.explanation === a)?.role === 'reference') - (bands.find(q => q.explanation === b)?.role === 'reference'));
      const engineFits = (x, a) => ((e.matches || []).find(mm => mm.explanation === x)?.assignments || []).some(as => comps.every(c => as[c] === a[c]));
      const rows = [];
      for (const x of exps) for (const a of assigns) {
        const cells = comps.map(c => { const v = vals[a[c]]; const ok = inBand(x, c, v); const b = bands.find(q => q.explanation === x && q.component === c); return el('td', {}, el('span', { class: 'mono' }, `${c} = ${a[c]}: ${v} ${unit}`), el('small', { class: 'muted', style: 'display:block' }, `band ${b ? BM.bandText(b) : '—'} · ${ok ? 'inside' : 'outside'}`)); });
        const fits = engineFits(x, a); const role = bands.find(q => q.explanation === x)?.role;
        rows.push(el('tr', { class: fits ? '' : 'out' }, el('td', {}, expName(x), role === 'reference' ? el('small', { class: 'muted', style: 'display:block' }, 'reference') : null), ...cells, el('td', {}, fits ? el('span', { class: 'tape grey' }, 'fits') : el('span', { class: 'tape read' }, 'misses'))));
      }
      const bind = e.binding || {};
      block(e, 'fit', 'Fit engine · both readings scored by the frozen bands', words.groupScored(e, assigns.length),
        el('div', { class: 'tscroll' }, el('table', { class: 'fit-table assign-table' }, el('thead', {}, el('tr', {}, el('th', {}, 'Explanation'), ...comps.map((c, i) => el('th', {}, `Assignment, part ${i + 1}`)), el('th', {}, ''))), el('tbody', {}, ...rows))),
        el('p', { class: 'small' }, EV(el('b', {}, Object.keys(bind).length ? `Assignment that fits: ${comps.map(c => `${c} = ${bind[c]}`).join(', ')}.` : 'No assignment fits.'), e.ev, 'group reading score', { fits: e.fits, ruled_out: e.ruled_out, matches: e.matches, binding: e.binding, outcome: e.outcome, body_identity_status: e.body_identity_status, nearest_value_assignment: e.nearest_value_assignment, refitted: e.refitted }),
          ` Surviving explanation${(e.fits || []).length === 1 ? '' : 's'}: ${(e.fits || []).map(expName).join(', ') || 'none'}. Body identity: ${String(e.body_identity_status || '').replace(/_/g, ' ')}.`),
        el('p', { class: 'small muted' }, `Scored by code against the bands frozen before the readings; ${e.nearest_value_assignment ? 'nearest-value assignment was used' : 'no nearest-value assignment'}, ${e.refitted ? 'models were re-fitted' : 'nothing was re-fitted'}. The ‘fits’/‘misses’ column is the engine’s list as written; the in/out notes beside each value are the same bands re-read in your browser.`));
      for (const x of e.fits || []) { const mt = meters[x]; if (!mt) continue; const c0 = comps[0]; const b = bands.find(q => q.explanation === x && q.component === c0); const v = vals[bind[c0]]; if (b && v != null) { mt.band(b.low, b.high, b.unit, v); mt.setReading(v, unit, `${c0} = ${bind[c0]}`); } mt.carry(e.outcome === 'one' ? 'Fits both readings' : 'Not separated'); }
    },
    ended() {},
  };
  // a label on a photo, placed under a mask's bounding box (bounds in SAM-input pixels, relative to the crop box)
  // `others`: the other labelled boxes; when one sits just below this box, the label goes above it instead
  function maskLabel(text, bb, cb, others = [], side = false) {
    const iw = cb[2] - cb[0], ih = cb[3] - cb[1];
    if (side) return el('span', { class: 'masklabel side', style: `left:${((bb[2] - cb[0]) / iw * 100 + 1.5).toFixed(1)}%;top:${((bb[1] + bb[3]) / 2 - cb[1]) / ih * 100}%` }, text);
    const up = others.some(o => o !== bb && o[1] >= bb[3] - 4 && o[1] < bb[3] + 0.09 * ih && o[0] < bb[2] && o[2] > bb[0]);
    const style = up ? `left:${((bb[0] + bb[2]) / 2 - cb[0]) / iw * 100}%;bottom:${(100 - (bb[1] - cb[1]) / ih * 100 + 1.5).toFixed(1)}%` : `left:${((bb[0] + bb[2]) / 2 - cb[0]) / iw * 100}%;top:${((bb[3] - cb[1]) / ih * 100 + 2).toFixed(1)}%`;
    return el('span', { class: 'masklabel' + (up ? ' up' : ''), style }, text);
  }

  const truthText = (t) => { const m = t.measured_ohm || {}; const parts = Object.entries(m).map(([k, v]) => `${k.replace('hidden_', 'hidden ')} ${BM.fmtR(v)}`); return `Measured on the bench: ${parts.join(', ')}${t.series_total_ohm ? `; series total ${BM.fmtR(t.series_total_ohm)}` : ''}. ${t.source || ''}`; };

  // ---------- the end: for a pilot, the stop and the fix; for a counted run, the seal opens
  async function finale(e, kind) {
    const wrap = el('div', { class: 'finale' });
    const inner = el('div', { class: 'inner' });
    const schemWrap = el('div', { class: 'schem-wrap' });
    const svg = await schematic(kase.design); schemWrap.append(svg);
    const ovs = overlaySVG(kase.overlay, svg.getAttribute('viewBox')); const ov = el('div', { class: 'ov' }); ov.append(ovs); schemWrap.append(ov);
    const right = el('div', {});
    const headline = kind === 'verdict' ? words.report(e, run) : words.stopped();
    if (kind === 'verdict') {
      const surv = e.survivors || []; const noMismatch = run.outcome?.verdict === 'consistent' || (surv.length === 1 && surv[0] === 'nominal');
      const restoredHere = run.pair?.state === 'restored';
      right.append(el('div', { class: 'verdict-card' + (noMismatch ? ' quiet' : '') },
        el('div', { class: 'vs' }, el('span', { class: 'lab' }, 'Spark’s answer'), el('div', { class: 'big' }, headline)),
        e.text ? el('p', {}, e.text) : null,
        noMismatch ? null : el('div', { class: 'vs planted' }, el('span', { class: 'lab' }, restoredHere ? 'What had been planted, now repaired' : 'What was planted · opened only now'), el('div', { class: 'big' }, kase.hidden)),
        el('p', { class: 'small muted', style: 'margin-top:8px' }, noMismatch ? 'This says nothing about tests Spark did not run. On a restored board it is the expected result.' : 'The verdict is copied from the engine’s report; the seal’s digest is checked by code against the one committed before the first measurement. Spark never saw the lower line.')));
      if (surv.length > 1 && !noMismatch) right.append(el('div', { class: 'card', style: 'margin-top:10px' }, el('h4', {}, 'Limits of the chosen tests'), el('p', {}, 'Two explanations behave the same at the terminals. One reading at the bench, forecast before it is taken, is what separates them.')));
      if (noMismatch && surv.length > 1) right.append(el('div', { class: 'card', style: 'margin-top:10px' }, el('h4', {}, 'What this does not say'), el('p', { class: 'small muted' }, `Nearby value-change models (${surv.filter(x => x !== 'nominal').map(expName).join(', ')}) also fit these tests. The verdict is that nothing disagreed with the drawing, not that every part is proven correct.`)));
      setSeal('open', 'Seal opened after the run');
    } else {
      right.append(el('div', { class: 'card' }, el('h4', {}, run.outcome?.kind === 'stopped' ? 'Run stopped. No verdict.' : 'Run ended'), el('p', {}, run.outcome?.reason || ''), el('p', { class: 'small muted', style: 'margin-top:6px' }, run.pilot ? 'This pilot is not counted. The seal is opened here only so you can compare.' : '')));
      if (run.note_after) right.append(el('div', { class: 'card', style: 'margin-top:10px' }, el('h4', {}, 'What was wrong with the bench'), el('p', {}, run.note_after), notes.ground_fix?.source ? el('p', { class: 'small faint', style: 'margin-top:4px' }, 'Source: ' + notes.ground_fix.source) : null));
      setSeal('stopped', 'Stopped · seal opened to compare');
    }
    const sealTruth = run.seal?.truth ? el('p', { class: 'small muted', style: 'margin-top:4px' }, EV(el('span', {}, 'Sealed before the diagnosis: ' + run.seal.truth.map(t => `${t.component.replace('external_', 'hidden ')} ${t.value_nominal_ohm != null ? BM.fmtR(t.value_nominal_ohm) : t.value_nominal_F != null ? BM.fmtC(t.value_nominal_F) : ''}${t.marking ? ' (marked ' + t.marking + ')' : ''} at ${t.location}`).join('; ') + (run.seal.matches_commitment ? '. The opened record matches the digest committed before the first measurement.' : '.')), run.seal.opened_ev, 'seal opened', { sealed_sha256: run.seal.sealed_sha256, sealed_event: run.seal.sealed_ev, matches_commitment: run.seal.matches_commitment, truth: run.seal.truth })) : (kase.truth ? el('p', { class: 'small muted', style: 'margin-top:4px' }, truthText(kase.truth)) : null);
    const restored = run.pair?.state === 'restored';
    const prev = run.pair?.previous_attempt;
    right.append(el('div', { class: 'card', style: 'margin-top:10px' }, el('h4', {}, restored ? 'The fault, restored before this rerun' : 'The sealed record, in detail'), restored ? el('p', {}, `Was: ${kase.hidden}`) : null, sealTruth,
      restored && run.pair?.restored_what ? el('p', { class: 'small muted', style: 'margin-top:4px' }, 'Restoration, in the operator’s words: ', EV(el('q', {}, run.pair.restored_what), run.pair.restore_ev, 'operator restoration confirmed', { closeout: run.pair.closeout, external_only: run.pair.external_only })) : null,
      prev ? el('p', { class: 'small muted', style: 'margin-top:4px' }, EV(el('span', {}, `Restored attempt ${prev.attempt} ended ${prev.verdict} and is counted; this is attempt ${run.pair.attempt}. `), prev.ev, 'restored attempt 1, engine report', { verdict: prev.verdict, record: prev.record, engine_report: prev.text }), prev.note) : null,
      el('p', { class: 'small muted', style: 'margin-top:4px' }, kase.limits)));
    right.append(el('div', { class: 'card', style: 'margin-top:10px' }, el('h4', {}, 'What the forum thread found'), kase.title_after_reveal ? el('p', { class: 'small muted' }, `Case ${run.case} — ${kase.title_after_reveal.toLowerCase()}`) : null, el('p', {}, kase.cause),
      el('dl', { class: 'kv small', style: 'margin-top:6px' }, el('dt', {}, 'Kept'), el('dd', {}, kase.kept), el('dt', {}, 'Changed'), el('dd', {}, kase.changed),
        el('dt', {}, 'Source'), el('dd', {}, el('a', { href: kase.source.url, target: '_blank', rel: 'noopener' }, `${kase.source.site}: ${kase.source.title}`))),
      el('p', { class: 'small faint', style: 'margin-top:4px' }, 'Same principle, reproduced on our bench. We did not repair the original poster’s board.')));
    const photo = run.photo?.image?.file ? photoCard(run.photo) : null;
    const rd = run.reading;
    if (run.seal) setSeal('open', run.reading?.observed ? 'Seal opened after the reading' : 'Seal opened after the run');
    if (rd?.group?.observed) right.append(el('div', { class: 'card', style: 'margin-top:10px' }, el('h4', {}, 'The two readings'), el('p', {}, readingLine(rd)), el('p', { class: 'small muted' }, `${BM.sourceWord(rd.group.observed.source)}, each body out of circuit; bands for both parts frozen before the readings${rd.group.sha ? ', sha256 ' + rd.group.sha : ''}. Which body is which part followed from the readings, by the engine’s assignment test; no model paired them.`)));
    else if (rd?.observed) right.append(el('div', { class: 'card', style: 'margin-top:10px' }, el('h4', {}, 'The one reading'), el('p', {}, readingLine(rd)), el('p', { class: 'small muted' }, `${BM.sourceWord(rd.observed.source)}; bands frozen before it, ${rd.sha ? 'sha256 ' + rd.sha : ''}.`)));
    inner.append(el('div', {}, schemWrap, el('p', { class: 'small muted', style: 'margin-top:6px' }, run.pair?.state === 'restored' ? 'The drawing the model read, with the fault that was restored before this rerun overlaid in red. The overlay was never part of the model input.' : 'The drawing the model read, with the hidden fault overlaid in red. The overlay was never part of the model input.'), photo ? el('div', { style: 'margin-top:10px' }, photo) : null, rd?.binding?.photo && !photo ? el('div', { class: 'photo', style: 'margin-top:10px;max-width:420px' }, el('img', { src: rd.binding.photo, alt: 'Board photo' }), rd.binding.overlay_file ? el('img', { class: 'mask', src: rd.binding.overlay_file, alt: 'SAM 3.1 outline' }) : null) : null), right);
    if (rd?.group?.bands?.length) wrap.append(tryAnyPair(rd)); else if (rd?.bands?.length) wrap.append(tryAnyValue(rd));
    wrap.append(el('span', { class: 'tape seal-tape' }, 'SEALED · hidden fault'), inner);
    block(e, 'guard', kind === 'verdict' ? 'Verdict · from the engine’s report' : 'End of the recording', kind === 'verdict' ? null : headline, wrap,
      el('p', { style: 'margin-top:10px' }, el('a', { class: 'btn sm', href: `case.html?id=${run.case}&run=${run.id}` }, 'Open the report')));
    requestAnimationFrame(() => { fitOverlay(svg, ovs); setTimeout(() => wrap.classList.add('open'), REDUCED ? 0 : 500); });
  }
  // the end-scene line for the reading, from data: a value against the drawing, or a presence/continuity answer
  function readingLine(rd) {
    if (rd.group?.observed) {
      const g = rd.group; const bind = g.scored?.binding || {}; const fits = g.scored?.fits || [];
      const reads = (g.observed.readings || []).map(r => `${r.body} read ${r.value} ${r.unit}`).join(', ');
      const drawnOf = (c) => { const d = (run.design || []).find(x => x.name === c); return d && d.value != null ? `${c} drawn ${fmtVal(d.kind, d.value)}` : null; };
      const drawn = Object.keys(bind).map(drawnOf).filter(Boolean).join(', ');
      const which = Object.keys(bind).length ? `by the frozen bands ${Object.entries(bind).map(([c, b]) => `${c} is ${b}`).join(' and ')}` : 'no assignment fit the bands';
      const verdict = fits.length === 1 && fits[0].startsWith('changed:') ? ` · ${fits[0].slice(8)} is not what the drawing says` : fits.length === 1 ? ' · the board is right' : '';
      return `${reads}${drawn ? ' · ' + drawn : ''} · ${which}${verdict}.`;
    }
    const o = rd.observed; const drawn = (run.design || []).find(d => d.name === o.component);
    if (rd.quantity === 'presence') return `${o.component} on the board: ${o.value}.`;
    if (rd.quantity === 'continuity') return `${o.component} continuity: ${o.value} ${o.unit || ''}.`.replace(/\s+\./, '.');
    const drawnTxt = drawn && drawn.value != null ? ` · drawn ${fmtVal(drawn.kind, drawn.value)}` : '';
    const fits = rd.scored?.fits || []; const boardRight = fits.length === 1 && !fits[0].startsWith('changed:') ? ' · the board is right' : fits.length === 1 && fits[0].startsWith('changed:') ? ` · ${o.component} is not what the drawing says` : '';
    return `${o.component} read ${o.value} ${o.unit || ''}${drawnTxt}${boardRight}.`;
  }
  // after the replay: the same field, open to the visitor. A what-if on the frozen bands; no model, no hardware
  function tryAnyValue(rd) {
    const srcs = [...new Set(rd.bands.map(b => b.source))]; const unit = rd.bands[0]?.unit || '';
    const sel = el('select', { 'aria-label': 'Source of the reading' }, ...srcs.map(s => el('option', { value: s }, BM.sourceShort(s))));
    if (rd.observed?.source) sel.value = rd.observed.source;
    const inp = el('input', { type: 'number', step: 'any', inputmode: 'decimal', placeholder: String(rd.observed?.value ?? ''), 'aria-label': `${rd.component} value in ${unit}` });
    const out = el('p', { class: 'tryout small' }, 'Type any value to see what the frozen bands would have said.');
    const go = () => { const v = Number(inp.value); if (!inp.value || !Number.isFinite(v)) { out.textContent = 'Type a number.'; return; }
      const fits = BM.bandFits(rd.bands, sel.value, v);
      out.textContent = fits.length === 1 ? `${v} ${unit} by ${BM.sourceShort(sel.value)}: only ${expName(fits[0])} fits; the rest would be crossed out.` : fits.length === 0 ? `${v} ${unit} by ${BM.sourceShort(sel.value)}: no explanation fits this reading; all would be crossed out.` : `${v} ${unit} by ${BM.sourceShort(sel.value)}: ${fits.map(expName).join(' and ')} both fit; this reading would not separate them.`; };
    inp.addEventListener('input', go); sel.addEventListener('change', go);
    return el('details', { class: 'card tryit', style: 'margin-top:12px' }, el('summary', {}, 'Try any value'), el('p', { class: 'small muted' }, `The bands were frozen before the operator read ${rd.component}. Put in any number: the same rule applies.`),
      el('div', { class: 'tryrow' }, el('span', { class: 'mono' }, `${rd.component} =`), inp, el('span', {}, unit), el('span', { class: 'muted small' }, 'by'), sel), out,
      el('p', { class: 'small faint' }, 'A what-if on the frozen bands, computed in your browser. No model, no hardware, nothing recorded.'));
  }
  // the group version: two values, one per body; every assignment of bodies to parts against the frozen bands, in the browser
  function tryAnyPair(rd) {
    const g = rd.group; const bands = g.bands || []; const bodies = g.bodies || []; const comps = g.components || []; const unit = bands[0]?.unit || 'µF';
    const perms = (arr) => arr.length <= 1 ? [arr] : arr.flatMap((x, i) => perms([...arr.slice(0, i), ...arr.slice(i + 1)]).map(r => [x, ...r]));
    const inputs = bodies.map(b => el('input', { type: 'number', step: 'any', inputmode: 'decimal', placeholder: String((g.observed?.readings || []).find(r => r.body === b)?.value ?? ''), 'aria-label': `${b} value in ${unit}` }));
    const out = el('p', { class: 'tryout small' }, 'Type two values to see which assignments the frozen bands would have allowed.');
    const go = () => {
      const vals = inputs.map(i => Number(i.value)); if (inputs.some(i => !i.value) || vals.some(v => !Number.isFinite(v))) { out.textContent = 'Type both numbers.'; return; }
      const v = Object.fromEntries(bodies.map((b, i) => [b, vals[i]]));
      const exps = [...new Set(bands.map(b => b.explanation))]; const lines = [];
      for (const x of exps) { const ok = perms(bodies).filter(order => comps.every((c, i) => { const b = bands.find(q => q.explanation === x && q.component === c); const val = v[order[i]]; return b && (b.low == null || val >= b.low) && (b.high == null || val <= b.high); }));
        const role = bands.find(b => b.explanation === x)?.role === 'reference' ? ' (reference, already ruled out by the bench tests)' : '';
        lines.push(`${expName(x)}${role}: ${ok.length ? ok.map(order => comps.map((c, i) => `${c} = ${order[i]}`).join(', ')).join(' or ') + (ok.length > 1 ? ' — both assignments fit, so the bodies would not be told apart' : '') : 'no assignment fits'}.`); }
      out.textContent = lines.join(' ');
    };
    inputs.forEach(i => i.addEventListener('input', go));
    return el('details', { class: 'card tryit', style: 'margin-top:12px' }, el('summary', {}, 'Try any two values'), el('p', { class: 'small muted' }, `The bands for ${comps.join(' and ')} were frozen before the operator read ${bodies.join(' and ')}. Put in any two numbers: every assignment of bodies to parts is tested against the same bands.`),
      el('div', { class: 'tryrow' }, ...bodies.flatMap((b, i) => [el('span', { class: 'mono' }, `${b} =`), inputs[i], el('span', {}, unit)])), out,
      el('p', { class: 'small faint' }, 'A what-if on the frozen bands, computed in your browser. No model, no hardware, nothing recorded.'));
  }
  function photoCard(ph) {
    const box = el('div', { class: 'photo' }); const img = el('img', { src: ph.crop_r1 || ph.image.file, alt: ph.documentary ? `Mini board, ${run.pair?.state || run.classification?.cohort?.state || 'faulted'} state, documentary photo` : ph.labels ? 'Mini board after the diagnosis, SAM 3.1 mask outlines' : 'Mini board after the diagnosis, R1 outlined by SAM 3.1' }); box.append(img);
    for (const c of ph.sam || []) for (const m of c.masks || []) if (m.overlay_file) box.append(el('img', { class: 'mask', src: m.overlay_file, alt: `SAM 3.1 mask, ${c.concept} object ${m.object_id}` }));
    const bd = run.reading?.binding; const bb = bd?.bounds; const cb = ph.crop_box || [0, 0, ph.image?.width || 1200, ph.image?.height || 1600]; const iw = cb[2] - cb[0], ih = cb[3] - cb[1];
    if (bb && bd?.component) box.append(el('span', { class: 'masklabel', style: `left:${((bb[0] + bb[2]) / 2 - cb[0]) / iw * 100}%;top:${((bb[3] - cb[1]) / ih * 100 + 2).toFixed(1)}%` }, `${bd.component} — SAM 3.1 mask`));
    const greads = run.reading?.group?.observed?.readings || [];
    for (const l of ph.labels || []) { const r = greads.find(x => x.body === l.text); box.append(maskLabel(r ? `${l.text} read ${r.value} ${r.unit}` : l.text, l.bounds, cb, (ph.labels || []).map(x => x.bounds), !!l.side)); }
    const notes = [ph.provenance ? el('p', { class: 'small', style: 'margin:6px 0 0' }, ph.provenance) : null, ...[ph.note].filter(Boolean).map(t => el('p', { class: 'small faint', style: 'margin:4px 0 0' }, t))].filter(Boolean);
    const parts = (ph.vision?.components || []).map(c => `${c.name} ${c.kind}: ${c.reading_status === 'unreadable' ? 'unreadable' : c.marking || '—'}`).join(' · ');
    if (ph.documentary) return el('div', {}, box, ...notes);
    return el('div', {}, box, ...notes, el('p', { class: 'small muted' }, `SAM 3.1 segmented the board${ph.sam?.length ? ` (${ph.sam.map(c => `${c.concept}: ${c.match_count}`).join(', ')})` : ''}; ${parts ? 'Muse Spark vision read the parts: ' + parts + '. ' : 'no part values were read from the photo. '}${ph.pairing ? ph.pairing.charAt(0).toUpperCase() + ph.pairing.slice(1) : ''}.`));
  }

  // ---------- idle notebook: why this case is here (from cases.json), nothing else before play
  function intro() {
    if (book.querySelector('.intro')) return;
    book.append(el('div', { class: 'entry intro' }, el('div', { class: 't' }), el('div', {},
      el('p', { class: 'lead' }, kase.symptom || kase.problem),
      el('dl', { class: 'kv small' }, el('dt', {}, 'Source'), el('dd', {}, el('a', { href: kase.source.url, target: '_blank', rel: 'noopener' }, `${kase.source.site}: ${kase.source.title}`))),
      el('p', { class: 'small faint' }, 'What the thread found, and what we kept or changed, opens with the seal at the end.'))));
  }
  // ---------- start
  waitingMeters(); intro();
  setSeal('sealed', 'Hidden fault sealed'); benchState();
  const t0 = Number(q.get('t')); if (t0) { seek(t0); idle.classList.add('off'); }
  if (q.get('play') === '1' && !REDUCED) setTimeout(() => { if (!playing) setPlaying(true); }, 700); // arrived by a Watch/Replay button: start without asking
  book.addEventListener('keydown', e => { if (e.key === ' ' && e.target === book) { e.preventDefault(); setPlaying(!playing); } });
  clock();
})();
