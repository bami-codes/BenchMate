// Landing: the claim, the scope, then the cases. Everything shown is read from data/.
(async () => {
  const { $, el, expName, fmtUSD, fmtDate, schematic, boardSVG, Scope, stepTraces, stepTime, verdictWords, REDUCED, ev } = BM;
  const [cases, index, results, policy] = await Promise.all([BM.loadCases(), BM.loadRuns(), BM.loadResults(), BM.json('data/official-run-policy.json').catch(() => null)]);
  const runs = index.runs || [];
  for (const r of runs.filter(x => x.counted && x.state === 'faulted')) { try { const rr = await BM.loadRun(r.id); for (const g of rr.reading?.groups || []) for (const m of g.members || []) BM.names[m.id] = m.label || m.words; } catch (e) { /* no run file */ } }
  // default source: the first official attempt for case 01 (counted, earliest start) per the preregistered
  // policy; until one exists, the earliest pilot of case 01. Never "the best run".
  const first = BM.defaultRun(runs, '01');
  const anyCounted = runs.some(r => r.counted);
  const c01 = cases.cases.find(c => c.id === '01');
  $('#cases-h').textContent = `${['One', 'Two', 'Three', 'Four', 'Five', 'Six', 'Seven', 'Eight'][cases.cases.length - 1] || cases.cases.length} cases from real forum threads`;

  // ---- hero scope: the first experiment of the first recorded run, measurement sweeping over its forecast, on loop
  const scope = new Scope($('#hero-scope'), { fill: true });
  if (first) {
    const run = await BM.loadRun(first.id);
    const st = run.steps[0];
    const traces = stepTraces(st, { measuredProgress: REDUCED ? 1 : 0 });
    scope.set(stepTime(st), traces, `Step 1 · ${st.label}`);
    $('#cta-replay').href = `run.html?run=${run.id}`;
    const nom = (st.fit || []).find(f => f.id === 'nominal');
    const cls = run.classification?.public_label || run.classification?.label || (run.pilot ? 'Pilot run — not counted' : 'Counted run');
    $('#hero-under').append(document.createTextNode(BM.heroLine(run) + ' '));
    // one line: state · case · when · the drawing's miss (numbers are evidence targets)
    const miss = nom ? (nom.decided_mV?.[0] ?? nom.miss_mV?.[0]) : null;
    $('#hero-caption').append(el('p', {},
      el('span', { class: 'badge ' + (run.counted ? 'live' : 'pilot') }, cls), ' · ',
      `Case ${run.case}, ${run.label} · `, ev(el('span', { class: 'num' }, fmtDate(run.started_utc)), run.timeline?.[0]?.ev, { run: run.id, what: 'run start' }),
      miss != null ? [' · as drawn misses by ', ev(el('span', { class: 'num' }, `${Number(miss).toFixed(2)} mV`), st.fit_ev, { run: run.id, what: 'miss of As drawn on step 1', fields: { decided_by: nom.worst_region?.[0] ? `worst region ${nom.worst_region[0]}` : 'whole step', whole_step_RMS_mV: nom.miss_mV?.[0], regions: nom.regions?.[0] } }), nom.worst_region?.[0] ? ` in its worst region (allowance ${run.allowance_mV} mV)` : ` (allowance ${run.allowance_mV} mV)`] : null));
    if (!REDUCED) {
      const meas = traces.filter(t => t.kind !== 'fc'); let t0 = performance.now();
      const loop = (now) => { const ph = ((now - t0) / 1000) % 6.5; const p = Math.min(1, ph / 3.2); for (const t of meas) t.progress = p; scope.draw(); requestAnimationFrame(loop); };
      requestAnimationFrame(loop);
    }
    $('#hero-schem').append(await schematic(cases.cases.find(c => c.id === run.case).design));
    const kase = cases.cases.find(c => c.id === run.case);
    if (run.photo?.image?.file) { const ph = run.photo; $('#hero-board').append(el('div', { class: 'photo' }, el('img', { src: ph.crop_full || ph.crop || ph.image.file, alt: 'Mini board photo after the diagnosis' }))); $('#hero-board-note').textContent = 'Photo of the mini board after the diagnosis, untouched.'; }
    else if (kase.board) { $('#hero-board').append(boardSVG(kase.board, { crop: true })); $('#hero-board-note').textContent = `Diagram from the wiring record (${kase.board.record}); photo pending.`; }
  } else {
    $('#hero-schem').append(await schematic('design-01'));
    if (c01?.board) { $('#hero-board').append(boardSVG(c01.board, { crop: true })); $('#hero-board-note').textContent = 'Diagram from the wiring record; photo pending.'; }
  }

  // ---- replays
  const rl = $('#replay-list');
  if (!runs.length) rl.append(el('p', { class: 'muted' }, 'No recorded runs yet.'));
  const ordered = anyCounted ? [...runs.filter(r => r.counted), ...runs.filter(r => !r.counted)] : runs;
  let devHead = false;
  for (const r of ordered) {
    if (anyCounted && !r.counted && !devHead) { devHead = true; rl.append(el('h3', { class: 'group-head' }, 'Development records'), el('p', { class: 'small muted' }, 'Pilots and QA runs that shaped the bench. Not counted, kept in full.')); }
    const c = cases.cases.find(x => x.id === r.case);
    const outcome = r.outcome === 'stopped' ? 'stopped by the reference guard' : r.display_caption ? r.display_caption : r.state === 'faulted' && r.survivors?.length === 1 ? (r.verdict === 'structure_supported' ? (r.reading === 'one' ? 'Spark proposed a part the drawing does not show; held-back checks passed; one reading, bands frozen first, placed it; seal opened' : 'Spark proposed a part the drawing does not show; held-back checks passed; seal opened') : r.reading === 'group' ? 'one explanation left after the tests; two readings, bands frozen first, fixed which body; seal opened' : 'one explanation left after one reading; seal opened') : r.verdict ? verdictWords({ verdict: r.verdict, survivors: r.survivors }, {}) : r.outcome;
    rl.append(el('div', { class: 'case-row', style: 'grid-template-columns:40px minmax(0,1fr) auto' },
      el('div', { class: 'n' }, r.case),
      el('div', {}, el('h3', {}, c.title, ' ', el('span', { class: 'small muted' }, `· ${r.label}, ${fmtDate(r.started_utc)}`)),
        el('p', { class: 'small muted' }, `${r.steps} experiments · ${r.spark_calls} Spark calls · ${fmtUSD(r.spark_cost)} est. · ${outcome}`)),
      el('div', { class: 'acts' }, el('span', { class: 'badge ' + (r.counted ? 'live' : r.pilot ? 'pilot' : 'pending') }, r.class_label || (r.pilot ? 'Pilot run — not counted' : 'Counted run')),
        el('a', { class: 'btn sm', href: `run.html?run=${r.id}` }, 'Replay'), el('a', { class: 'btn ghost sm', href: `case.html?id=${r.case}&run=${r.id}` }, 'Report'))));
  }

  // ---- cases: one verified forum line each, the preregistered order and selection rule
  const cl = $('#case-list');
  { const withRuns = cases.cases.filter(c => runs.some(r => r.case === c.id)).length; $('#cases-count').textContent = `${cases.cases.length} cases, ${withRuns} with recorded runs.`; }
  const slotsOf = id => (policy?.ordered_slots || []).filter(s => s.case_id === id);
  for (const c of cases.cases) {
    const rs = runs.filter(r => r.case === c.id);
    const thumb = el('div', { class: 'thumb' }); thumb.append(await schematic(c.design));
    const counted = rs.filter(r => r.counted);
    const status = counted.length ? el('span', { class: 'badge live' }, `${counted.length} counted run${counted.length > 1 ? 's' : ''}`) : rs.length ? el('span', { class: 'badge pilot' }, 'Pilot run — not counted') : el('span', { class: 'badge pending' }, 'Not run yet');
    const slots = slotsOf(c.id);
    cl.append(el('div', { class: 'case-row' },
      el('div', { class: 'n' }, c.id), thumb,
      el('div', {}, el('h3', {}, c.title), el('p', {}, c.symptom || c.problem), el('p', { class: 'src' }, 'Source: ', el('a', { href: c.source.url, target: '_blank', rel: 'noopener' }, `${c.source.site}: ${c.source.title}`), c.source.date ? `, ${c.source.date.slice(0, 7)}` : ''),
        slots.length ? el('p', { class: 'small faint' }, `Official slots: ${slots.map(s => { const done = rs.find(r => r.counted && r.state === s.state); return `${s.slot_id} (${s.state}, ${done ? 'completed' : s.status.replace(/_/g, ' ')})`; }).join(', ')}${c.id === policy?.selection?.structure_spotlight?.priority?.[0]?.slice(0, 2) ? ' · structure-proposal spotlight, first priority' : c.id === policy?.selection?.structure_spotlight?.priority?.[1]?.slice(0, 2) ? ' · structure-proposal spotlight, second priority' : ''}`) : null),
      el('div', { class: 'acts' }, status, rs.length ? el('a', { class: 'btn sm', href: `run.html?run=${BM.defaultRun(runs, c.id).id}` }, 'Replay') : null, el('a', { class: 'btn ghost sm', href: `case.html?id=${c.id}` }, 'Report'))));
  }
  if (policy) {
    const shown = cases.cases.map(c => c.id); const order = (policy.case_order || []).filter(id => shown.includes(id));
    $('#policy').append(el('p', {}, `The order of the cases and the demo selection rule were registered before any official result (${policy.cohort_plan_id}, ${policy.created_local_date}); the cases ran ${order.join(' → ')}, each a fault run then a restored rerun. ${policy.display_rule_2026_11_04 ? policy.display_rule_2026_11_04.text + ' ' : `each case page shows the first started official attempt for that state, whatever its outcome. ${policy.selection_rule ? policy.selection_rule + '. ' : ''}`}Where a restored attempt reached a verdict other than consistency, the counted later attempt is shown and the earlier one is named on the report. Case 01 was known to the developers and is not a blind test. Runs made while the pipeline was still being built are development records and are never counted.`));
  }

  // ---- verify box (short)
  $('#verify-short').append(el('h3', {}, 'Verify it yourself'), el('p', { class: 'small muted' }, 'Every run is an append-only event log; each event carries its sha256 and the previous one. On any replay, click a number to see its event. In the repository, ', el('code', {}, 'python -m benchmate verify <run folder>'), ' prints PASS or FAIL and the number of events checked: the full hash chain, the frozen-forecast hashes and the forecast → measurement order, including the physical CAPTURE order. It proves the record’s internal integrity and order, not when it was written. Details: docs/2026-11-03-offline-verification.md.'));

  // ---- scoreboard: hidden until official result files exist
  if (results && results.official_runs?.length) {
    $('#score').hidden = false;
    $('#score-note').textContent = `${results.official_runs.length} official runs, scored by code against the sealed faults. Updated ${fmtDate(results.updated_utc)}.`;
    for (const m of results.metrics) $('#score-grid').append(el('div', { class: 'k' }, el('b', {}, m.value ?? '—'), el('span', {}, m.label)));
  }
})();
