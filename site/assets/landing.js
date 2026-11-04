// Landing: the claim, the scope, the numbers, then the five cases with their recorded runs. Everything shown is read from data/.
(async () => {
  const { $, el, expName, fmtUSD, fmtDate, schematic, boardSVG, Scope, stepTraces, stepTime, verdictWords, kindWord, REDUCED, ev } = BM;
  const [cases, index, results, policy, census] = await Promise.all([BM.loadCases(), BM.loadRuns(), BM.loadResults(), BM.json('data/official-run-policy.json').catch(() => null), BM.json('data/census.json').catch(() => null)]);
  const runs = index.runs || [];
  for (const r of runs.filter(x => x.counted && x.state === 'faulted')) { try { const rr = await BM.loadRun(r.id); for (const g of rr.reading?.groups || []) for (const m of g.members || []) BM.names[m.id] = m.label || m.words; } catch (e) { /* no run file */ } }
  // the representative run: the policy's structure_spotlight names the slots, in priority order, whose first official
  // attempt may be shown first when it contains a genuine structure proposal selected by Muse Spark (04-F01, then 05-F01).
  // The slot's run id comes from the same policy file; the proposal is checked in the run file, never assumed. If no
  // slot qualifies: the first official attempt for case 01 (counted, earliest start), else the earliest pilot. Never "the best run".
  const spotlight = async () => {
    const sp = policy?.selection?.structure_spotlight; if (!sp?.priority?.length) return null;
    for (const slotId of sp.priority) {
      const slot = (policy.ordered_slots || []).find(x => x.slot_id === slotId); const r = slot?.run_id && runs.find(x => x.id === slot.run_id && x.counted);
      if (!r) continue;
      try { const rr = await BM.loadRun(r.id); if ((rr.structure || []).some(x => x.selected_by === 'muse_spark' && x.ev)) return rr; } catch (e) { /* no run file */ }
    }
    return null;
  };
  const spotRun = await spotlight();
  const first = spotRun ? runs.find(r => r.id === spotRun.id) : BM.defaultRun(runs, '01');
  const anyCounted = runs.some(r => r.counted);
  const c01 = cases.cases.find(c => c.id === '01');
  $('#cases-h').textContent = `${['One', 'Two', 'Three', 'Four', 'Five', 'Six', 'Seven', 'Eight'][cases.cases.length - 1] || cases.cases.length} cases from real forum threads`;

  // ---- hero scope: the representative run's decisive experiment (the one after which Spark proposed a part; else the
  // first experiment), measurement sweeping over its forecast, on loop
  const scope = new Scope($('#hero-scope'), { fill: true });
  if (first) {
    const run = spotRun || await BM.loadRun(first.id);
    const prop = (run.structure || []).find(x => x.selected_by === 'muse_spark' && x.ev) || null;
    const st = run.steps[(prop?.after_step || 1) - 1] || run.steps[0];
    const si = st.n - 1; // each fit entry lists the residuals for every experiment so far; this experiment's is at its own index
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
    const miss = nom ? (nom.decided_mV?.[si] ?? nom.miss_mV?.[si]) : null;
    $('#hero-caption').append(el('p', {},
      el('span', { class: 'badge ' + (run.counted ? 'live' : 'pilot') }, cls),
      el('span', { class: 'it' }, `Case ${run.case}, ${run.label}`), ev(el('span', { class: 'it num' }, fmtDate(run.started_utc)), run.timeline?.[0]?.ev, { run: run.id, what: 'run start' }),
      miss != null ? el('span', { class: 'it' }, 'The fit engine checked the drawing’s model against this measurement: off by ', ev(el('span', { class: 'num' }, `${Number(miss).toFixed(2)} mV`), st.fit_ev, { run: run.id, what: `residual of As drawn on step ${st.n}, worst region (the fit engine’s check, not the dashed forecast’s miss)`, fields: { decided_by: nom.worst_region?.[si] ? `worst region ${nom.worst_region[si]}` : 'whole step', whole_step_RMS_mV: nom.miss_mV?.[si], regions: nom.regions?.[si], allowance_mV: run.allowance_mV } }), `; the allowance is ${run.allowance_mV} mV.`) : null));
    // the bench cards: one real line each from this same run (never the part that was read: the seal is closed on this page)
    try {
      const exCase = `Case ${run.case}`;
      $('#bench-ex-spark').append(el('b', {}, `${exCase}, experiment ${st.n}: `), `${st.label}.`, st.reason ? el('q', {}, st.reason) : null);
      const samples = st.settings?.samples, per = st.settings?.period_us;
      $('#bench-ex-ardu').append(el('b', {}, `${exCase}, experiment ${st.n}: `), samples ? `${samples} samples${per ? ` at ${per / 1000} ms` : ''}; ` : '', miss != null ? `the fit engine’s check of the drawing’s model against this measurement: off by ${Number(miss).toFixed(2)} mV in its worst region, allowance ${run.allowance_mV} mV.` : '');
      const loads = run.steps.map(x => x.load_ohm ? 'on' : 'off'); const moves = loads.slice(1).filter((v, i) => v !== loads[i]).length;
      const bands = run.reading?.bands?.length || 0;
      $('#bench-ex-oper').append(el('b', {}, `${exCase}: `), moves ? `moved the load jumper ${moves === 1 ? 'once' : moves === 2 ? 'twice' : moves + ' times'} between experiments` : 'no jumper move was asked for', bands ? `; after the experiments, read one part. Its allowed range under each explanation was frozen first.` : '.');
    } catch (e) { /* the bench cards stay general */ }
    // ---- the representative path: the proposal run's record in four lines (every number from the run file, each clickable)
    if (prop) try {
      const kase = cases.cases.find(c => c.id === run.case);
      const num = (t) => el('span', { class: 'num' }, t);
      const fails = (st.fit || []).filter(f => f.passed?.[si] === false && f.decided_mV?.[si] != null);
      const added = (prop.diff?.added || [])[0];
      const partWords = added ? `${kindWord(added.kind)} from ${added.a} to ${added.b}` : 'a part the drawing does not show';
      const cap = (t) => t[0].toUpperCase() + t.slice(1);
      const survId = run.verification?.survivors?.[0] || prop.id;
      const scored = (run.verification?.scored || []).map(s => ({ s, c: s.conditional?.[survId] })).filter(x => x.c);
      const allPassed = scored.length && scored.every(x => x.c.passed);
      const sealPart = added ? (run.seal?.truth || []).find(t => t.kind === added.kind && t.nodes) : null;
      const sealNodes = sealPart ? String(sealPart.nodes).replace(/\s/g, '').split(/→|->/) : null;
      const sameDir = !!(sealNodes && sealNodes.length === 2 && added && sealNodes[0] === added.a && sealNodes[1] === added.b);
      const items = [];
      if (fails.length) items.push(el('li', {}, el('b', {}, 'Every value explanation failed.'),
        el('span', {}, `After experiment ${st.n} the fit engine refitted every explanation still standing. The best each could do, in its worst region: `,
          ...fails.flatMap((f, i) => [i ? ', ' : '', `${expName(f.id)} `, ev(num(`${Number(f.decided_mV[si]).toFixed(2)} mV`), st.fit_ev, { run: run.id, what: `residual of ${expName(f.id)} on step ${st.n}, worst region (the fit engine’s check after refitting)`, fields: { decided_by: f.worst_region?.[si] ? `worst region ${f.worst_region[si]}` : 'whole step', whole_step_RMS_mV: f.miss_mV?.[si], allowance_mV: run.allowance_mV } })]),
          `, against an allowance of ${run.allowance_mV} mV. All ${fails.length === 2 ? 'two' : fails.length === 3 ? 'three' : fails.length} were crossed out.`)));
      items.push(el('li', {}, el('b', {}, 'Spark proposed a part the drawing does not show.'),
        el('span', {}, ev(el('span', {}, `${cap(partWords)}, as a netlist it wrote itself`), prop.ev, { run: run.id, what: 'structure proposed', fields: { selected_by: prop.selected_by, added: (prop.diff?.added || []).map(x => `${x.name} ${x.kind} ${x.a}–${x.b}`).join(', ') } }), '.',
          prop.rationale ? el('q', {}, prop.rationale) : null)));
      if (scored.length) {
        const v = run.verification;
        const misses = scored.flatMap((x, i) => [i ? ' and ' : '', ev(num(`${Number(x.c.decided_mV).toFixed(2)} mV`), x.s.ev, { run: run.id, what: `held-back input ${x.s.index} scored: the frozen model driven by the measured input, worst region`, fields: { decided_by: x.c.worst_region ? `worst region ${x.c.worst_region}` : 'whole step', whole_step_RMS_mV: x.c.RMS_mV, passed: x.c.passed, allowance_mV: run.allowance_mV, input: x.s.settings } })]);
        items.push(el('li', {}, el('b', {}, 'Fitted, frozen, pushed, then tested.'),
          el('span', {}, 'The proposal was fitted in ngspice; its forecast was frozen and ',
            v.published && v.url ? el('a', { href: v.url, target: '_blank', rel: 'noopener' }, 'pushed to GitHub') : 'frozen',
            ` before ${scored.length === 2 ? 'two' : scored.length} held-back input${scored.length === 1 ? '' : 's'} ${scored.length === 1 ? 'was' : 'were'} measured against the frozen model: worst region${scored.length === 1 ? '' : 's'} `, ...misses, `, ${allPassed ? 'under' : 'against'} the ${run.allowance_mV} mV allowance.`)));
      }
      if (run.seal?.opened_ev && sealPart && sealNodes?.length === 2) {
        items.push(el('li', {}, el('b', {}, 'The seal opened.'),
          el('span', {}, ev(el('span', {}, `${cap(kindWord(sealPart.kind))} from ${sealNodes[0]} to ${sealNodes[1]}`), run.seal.opened_ev, { run: run.id, what: 'seal opened', fields: { sealed_sha256: run.seal.sealed_sha256, matches_commitment: run.seal.matches_commitment, location: sealPart.location } }),
            sameDir ? ', in the direction Spark wrote.' : '.',
            run.seal.transmitted_to_model === false ? ' Spark never saw this line' : '', run.seal.matches_commitment ? '; code checked the seal’s digest against the one committed before the first measurement.' : '.')));
      }
      if (items.length >= 3) {
        $('#path-h').append(el('span', {}, `Case ${run.case} · ${kase.title}: the record in ${['one', 'two', 'three', 'four'][items.length - 1]} lines`), el('small', {}, 'Every number is read from the run file; click one for the event behind it.'));
        $('#path-steps').append(...items); $('#path').hidden = false;
        const tp = (run.timeline || []).find(t => t.kind === 'structure_proposed' && t.id === prop.id)?.t_play;
        if (tp) { const j = $('#cta-jump'); j.href = `run.html?run=${run.id}&t=${Math.max(0, Math.floor(tp - 2))}&play=1`; j.hidden = false; }
        $('#cta-replay').textContent = `Watch Case ${run.case} from the start`;
      }
    } catch (e) { console.warn('representative path not shown', e); }
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
    $('#score-note').append(el('span', {}, `${results.official_runs.length} official runs on the real bench: every forecast frozen before its measurement and checked by code; every fault sealed until the verdict.`), el('small', {}, `Updated ${fmtDate(results.updated_utc)}`));
    for (const m of results.metrics) { const usd = m.label.includes('(USD)'); $('#score-grid').append(el('div', { class: 'k' }, el('b', {}, m.value == null ? '—' : usd ? '$' + m.value : m.value), el('span', {}, usd ? m.label.replace(' (USD)', '') : m.label))); }
    try { const m = (id) => results.metrics.find(x => x.id === id)?.value; const pr = m('proposals'), rd = m('readings'); if (pr != null && rd != null) $('#frontier-counts').textContent = `On this bench: ${pr} parts proposed that the drawing does not show, ${rd} readings asked for, counted from the records. `; } catch (e) { /* the note stays general */ }
    $('#score-foot').textContent = (census?.sentence ? census.sentence + ' ' : 'Counts, not a rate: stopped, abstained and miswired attempts are in the public ledger and named on the reports. ') + 'Costs are estimates at the published rates.';
  }

  // ---- the cases: one row per case with its recorded runs (fault run, restored rerun), in case order
  const cl = $('#case-list');
  const counted = runs.filter(r => r.counted);
  { const withRuns = cases.cases.filter(c => counted.some(r => r.case === c.id)).length; $('#cases-count').textContent = `Each case is a problem from a real forum thread, rebuilt on the bench with one sealed fault: ${counted.length} official runs replayed here${census?.counts ? `, out of ${census.counts.diagnostic_starts} diagnostic runs started` : ''}.`; }
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
      box.append(el('div', { class: 'run-line dev' }, el('span', { class: 'small' }, el('b', {}, `Case ${r.case} · ${r.label}`), ` · ${fmtDate(r.started_utc)} · ${r.steps} experiments · ${fmtUSD(r.spark_cost)} est. · ${outcomeLine(r)}`), el('span', { class: 'badge pilot' }, r.class_label || 'Pilot run — not counted'), el('span', { class: 'acts' }, el('a', { class: 'btn ghost sm', href: `run.html?run=${r.id}` }, 'Replay'), el('a', { class: 'small rep', href: `case.html?id=${r.case}&run=${r.id}` }, 'Report')))); }
  }
  if (policy) {
    const shown = cases.cases.map(c => c.id); const order = (policy.case_order || []).filter(id => shown.includes(id));
    $('#policy').append(el('details', { class: 'small muted' }, el('summary', {}, 'How the runs are counted and shown'), el('p', { style: 'margin-top:6px' }, `The order of the cases and the demo selection rule were registered before any official result (${policy.cohort_plan_id}, ${policy.created_local_date}); the cases ran ${order.join(' → ')}, each a fault run then a restored rerun. ${policy.display_rule_2026_11_04 ? policy.display_rule_2026_11_04.text + ' ' : `each case page shows the first started official attempt for that state, whatever its outcome. ${policy.selection_rule ? policy.selection_rule + '. ' : ''}`}Where a restored attempt reached a verdict other than consistency, the counted later attempt is shown and the earlier one is named on the report. The cases were known to the developers; this is not a blind test. Runs made while the pipeline was still being built are development records and are never counted.`)));
  }

  // ---- verify box (short)
  $('#verify-short').append(el('h3', {}, el('span', { class: 'n' }, '✓'), 'Verify it yourself'),
    el('p', {}, 'Every run is an append-only log; each event carries its hash and the previous one. One command re-checks any run offline and prints PASS or FAIL:'),
    el('pre', { class: 'cmd' }, 'python -m benchmate verify <run folder>'),
    el('p', { class: 'fine' }, 'It checks the hash chain, the frozen-forecast hashes and the forecast → measurement order. It proves integrity and order, not when it was written; the forecast commits on GitHub carry the time. ', el('a', { href: 'https://github.com/bami-codes/BenchMate/blob/main/docs/2026-11-03-offline-verification.md' }, 'Details'), '.'));
})();
