// Landing: the claim, the scope, the numbers, then the five cases with their recorded runs. Everything shown is read from data/.
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
    scope.set(stepTime(st), traces, st.label); // the settings only; 'Experiment 1' is said in the key strip
    $('#cta-replay').href = `run.html?run=${run.id}&play=1`;
    const nom = (st.fit || []).find(f => f.id === 'nominal');
    const cls = run.classification?.public_label || run.classification?.label || (run.pilot ? 'Pilot run — not counted' : 'Counted run');
    // the scope, in plain words: what each line is (the keys sit on the scope itself; the mV/div HUD moves to the bottom)
    $('#hero-scope').append(el('div', { class: 'plain', 'aria-label': 'What the lines are' },
      el('b', {}, `Experiment ${st.n}`), el('span', { class: 'k fc' }, '– – forecast from the drawing'), el('span', { class: 'k out' }, '— output, measured'), el('span', { class: 'k in' }, '— input, measured')));
    // one plain sentence: the symptom (never the cause: the seal is still closed here), then what Spark did, from the run
    const kase0 = cases.cases.find(c => c.id === run.case);
    const nSteps = run.steps.length, nScored = (run.verification?.scored || []).length, rd = run.reading;
    const settled = rd?.group?.scored ? 'settled it with two multimeter readings' : rd?.scored ? 'settled it with one multimeter reading' : (run.outcome?.verdict === 'structure_supported' ? 'proposed a part the drawing does not show' : '');
    $('#hero-under').append(el('span', { class: 'case' }, `Case ${run.case} · ${kase0.title}.`), ' ',
      `Spark chose ${nSteps} experiment${nSteps === 1 ? '' : 's'}${nScored ? `, passed ${nScored === 2 ? 'two' : nScored} checks on inputs it had never seen` : ''}${settled ? ', and ' + settled : ''}. `,
      el('a', { class: 'watch', href: `run.html?run=${run.id}&play=1` }, 'Watch how →'));
    // one line of provenance under it: badge · run · when · the miss the scope shows
    const miss = nom ? (nom.decided_mV?.[0] ?? nom.miss_mV?.[0]) : null;
    $('#hero-caption').append(el('p', {},
      el('span', { class: 'badge ' + (run.counted ? 'live' : 'pilot') }, cls),
      el('span', { class: 'it' }, `Case ${run.case}, ${run.label}`), ev(el('span', { class: 'it num' }, fmtDate(run.started_utc)), run.timeline?.[0]?.ev, { run: run.id, what: 'run start' }),
      miss != null ? el('span', { class: 'it' }, 'The drawing’s forecast missed the board by ', ev(el('span', { class: 'num' }, `${Number(miss).toFixed(2)} mV`), st.fit_ev, { run: run.id, what: 'miss of As drawn on step 1', fields: { decided_by: nom.worst_region?.[0] ? `worst region ${nom.worst_region[0]}` : 'whole step', whole_step_RMS_mV: nom.miss_mV?.[0], regions: nom.regions?.[0], allowance_mV: run.allowance_mV } }), `; the allowance is ${run.allowance_mV} mV.`) : null));
    // the bench cards: one real line each from this same run (never the part that was read: the seal is closed on this page)
    try {
      const exCase = `Case ${run.case}`;
      $('#bench-ex-spark').append(el('b', {}, `${exCase}, experiment ${st.n}: `), `${st.label}.`, st.reason ? el('q', {}, st.reason) : null);
      const samples = st.settings?.samples, per = st.settings?.period_us;
      $('#bench-ex-ardu').append(el('b', {}, `${exCase}, experiment ${st.n}: `), samples ? `${samples} samples${per ? ` at ${per / 1000} ms` : ''}; ` : '', miss != null ? `the drawing’s forecast missed by ${Number(miss).toFixed(2)} mV, allowance ${run.allowance_mV} mV.` : '');
      const loads = run.steps.map(x => x.load_ohm ? 'on' : 'off'); const moves = loads.slice(1).filter((v, i) => v !== loads[i]).length;
      const bands = run.reading?.bands?.length || 0;
      $('#bench-ex-oper').append(el('b', {}, `${exCase}: `), moves ? `moved the load jumper ${moves === 1 ? 'once' : moves === 2 ? 'twice' : moves + ' times'} between experiments` : 'no jumper move was asked for', bands ? `; after the experiments, read one part. Its allowed range under each explanation was frozen first.` : '.');
    } catch (e) { /* the bench cards stay general */ }
    if (!REDUCED) {
      const meas = traces.filter(t => t.kind !== 'fc'); let t0 = performance.now();
      const loop = (now) => { const ph = ((now - t0) / 1000) % 6.5; const p = Math.min(1, ph / 3.2); for (const t of meas) t.progress = p; scope.draw(); requestAnimationFrame(loop); };
      requestAnimationFrame(loop);
    }
    $('#hero-schem').append(await schematic(cases.cases.find(c => c.id === run.case).design));
    const kase = cases.cases.find(c => c.id === run.case);
    if (run.photo?.image?.file) { const ph = run.photo; $('#hero-board').append(el('div', { class: 'photo' }, el('img', { src: ph.crop_full || ph.crop || ph.image.file, alt: 'Mini board photo after the diagnosis' }))); $('#hero-board-note').textContent = 'the mini board, photographed after the diagnosis'; }
    else if (kase.board) { $('#hero-board').append(boardSVG(kase.board, { crop: true })); $('#hero-board-note').textContent = 'the mini board, from the wiring record'; }
  } else {
    $('#hero-schem').append(await schematic('design-01'));
    if (c01?.board) { $('#hero-board').append(boardSVG(c01.board, { crop: true })); $('#hero-board-note').textContent = 'the mini board, from the wiring record'; }
  }

  // ---- scoreboard: hidden until official result files exist
  if (results && results.official_runs?.length) {
    $('#score').hidden = false;
    $('#score-note').textContent = `${results.official_runs.length} official runs on the real bench, scored by code against the sealed faults. Updated ${fmtDate(results.updated_utc)}.`;
    for (const m of results.metrics) $('#score-grid').append(el('div', { class: 'k' }, el('b', {}, m.value ?? '—'), el('span', {}, m.label)));
    $('#score-foot').textContent = 'Counts, not a rate: stopped, abstained and miswired attempts are in the public ledger and named on the reports. Costs are estimates at the published rates.';
  }

  // ---- the cases: one row per case with its recorded runs (fault run, restored rerun), in case order
  const cl = $('#case-list');
  const counted = runs.filter(r => r.counted);
  { const withRuns = cases.cases.filter(c => counted.some(r => r.case === c.id)).length; $('#cases-count').textContent = `${counted.length} official runs: a diagnosis on each faulted board, then the same procedure again after the fault was repaired. Spark was never told which fault was planted; the seal was opened only after its verdict.`; }
  const cap1 = (t) => { if (!t) return t; t = t[0].toUpperCase() + t.slice(1); return /[.!?]$/.test(t) ? t : t + '.'; };
  const outcomeLine = (r) => cap1(r.outcome === 'stopped' ? 'stopped by the reference guard' : r.display_caption ? r.display_caption : r.state === 'faulted' && r.survivors?.length === 1 ? (r.verdict === 'structure_supported' ? (r.reading === 'one' ? 'Spark proposed a part the drawing does not show; held-back checks passed; one multimeter reading, bands frozen first, placed it; the seal matched.' : 'Spark proposed a part the drawing does not show; held-back checks passed; the seal matched.') : r.reading === 'group' ? 'one explanation left after the tests; two multimeter readings, bands frozen first, fixed which body; the seal matched.' : 'one explanation left after one multimeter reading; the seal matched.') : r.verdict ? verdictWords({ verdict: r.verdict, survivors: r.survivors }, {}) : r.outcome);
  const runLine = (r) => { const restored = r.state === 'restored'; return el('div', { class: 'run-line ' + (restored ? 'restored' : 'fault') },
    el('div', { class: 'res' }, el('b', {}, restored ? 'Fixed, then rerun.' : 'Found it.'), ' ', outcomeLine(r)),
    el('div', { class: 'act' },
      el('a', { class: 'btn sm' + (restored ? ' ghost' : ''), href: `run.html?run=${r.id}&play=1` }, restored ? 'Watch the rerun' : 'Watch the diagnosis'),
      el('a', { class: 'small rep', href: `case.html?id=${r.case}&run=${r.id}` }, 'Report'),
      el('span', { class: 'small meta' }, `${r.steps} experiments · ${fmtUSD(r.spark_cost)}`))); };
  const monthYear = (c) => { if (c.source.date) { const d = new Date(c.source.date + 'T00:00:00Z'); return d.toLocaleString('en-GB', { month: 'long', year: 'numeric', timeZone: 'UTC' }); } return (c.source.date_label || '').replace(/\s*\(.*\)\s*$/, ''); };
  for (const c of cases.cases) {
    const rs = counted.filter(r => r.case === c.id).sort((a, b) => a.started_utc < b.started_utc ? -1 : 1);
    const thumb = el('div', { class: 'thumb' }); thumb.append(await schematic(c.design));
    cl.append(el('div', { class: 'case-row case-block' },
      el('div', { class: 'n' }, c.id), thumb,
      el('div', {}, el('h3', {}, c.title), el('p', {}, c.symptom || c.problem), el('p', { class: 'src' }, 'Source: ', el('a', { href: c.source.url, target: '_blank', rel: 'noopener' }, `${c.source.site} · ${c.source.title}`), monthYear(c) ? ` · ${monthYear(c)}` : ''),
        el('div', { class: 'runs' }, ...rs.map(runLine)))));
  }
  // development records: pilots and QA runs, not counted, kept in full
  const dev = runs.filter(r => !r.counted);
  if (anyCounted && dev.length) {
    const box = $('#dev-records');
    box.append(el('h3', { class: 'group-head' }, 'Development records'), el('p', { class: 'small muted' }, 'Pilots that shaped the bench before the pipeline was frozen. Not counted, kept in full.'));
    for (const r of dev) { const c = cases.cases.find(x => x.id === r.case);
      box.append(el('div', { class: 'run-line dev' }, el('a', { class: 'btn ghost sm', href: `run.html?run=${r.id}` }, 'Replay'), el('span', { class: 'small' }, el('b', {}, `Case ${r.case} · ${r.label}`), ` · ${fmtDate(r.started_utc)} · ${r.steps} experiments · ${r.spark_calls} Spark calls · ${fmtUSD(r.spark_cost)} est.`, el('span', { class: 'muted' }, ` — ${outcomeLine(r)}`)), el('span', { class: 'badge pilot' }, r.class_label || 'Pilot run — not counted'), el('a', { class: 'small rep', href: `case.html?id=${r.case}&run=${r.id}` }, 'Report'))); }
  }
  if (policy) {
    const shown = cases.cases.map(c => c.id); const order = (policy.case_order || []).filter(id => shown.includes(id));
    $('#policy').append(el('details', { class: 'small muted' }, el('summary', {}, 'Registration and display rules'), el('p', { style: 'margin-top:6px' }, `The order of the cases and the demo selection rule were registered before any official result (${policy.cohort_plan_id}, ${policy.created_local_date}); the cases ran ${order.join(' → ')}, each a fault run then a restored rerun. ${policy.display_rule_2026_11_04 ? policy.display_rule_2026_11_04.text + ' ' : `each case page shows the first started official attempt for that state, whatever its outcome. ${policy.selection_rule ? policy.selection_rule + '. ' : ''}`}Where a restored attempt reached a verdict other than consistency, the counted later attempt is shown and the earlier one is named on the report. The cases were known to the developers; this is not a blind test. Runs made while the pipeline was still being built are development records and are never counted.`)));
  }

  // ---- verify box (short)
  $('#verify-short').append(el('h3', {}, 'Verify it yourself'), el('p', { class: 'small muted' }, 'Every run is an append-only event log; each event carries its sha256 and the previous one. On any replay, click a number to see its event. In the repository, ', el('code', {}, 'python -m benchmate verify <run folder>'), ' prints PASS or FAIL and the number of events checked: the full hash chain, the frozen-forecast hashes and the forecast → measurement order, including the physical CAPTURE order. It proves the record’s internal integrity and order, not when it was written; the forecast commits on GitHub carry the time. Details: docs/2026-11-03-offline-verification.md.'));
})();
