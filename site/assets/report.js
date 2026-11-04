// Case report: the forum context, the drawing the model read, every experiment with its forecasts and
// misses, the check, the outcome, the pair status with the restored rerun, and how to verify it.
// Cases without a run show the context and the drawing only. Nothing here is a placeholder box.
(async () => {
  const { $, el, expName, fmtVal, fmtUSD, fmtDate, schematic, overlaySVG, fitOverlay, netlistSVG, boardSVG, Scope, stepTraces, stepTime, verdictWords, fmtMiss, ev } = BM;
  const q = new URLSearchParams(location.search);
  const [cases, index, notes] = await Promise.all([BM.loadCases(), BM.loadRuns(), BM.loadNotes()]);
  const id = q.get('id') || '01';
  const c = cases.cases.find(x => x.id === id);
  const runsOf = index.runs.filter(r => r.case === id);
  const runId = q.get('run') || (runsOf.find(r => r.counted) || runsOf[runsOf.length - 1])?.id;
  const run = q.get('devsrc') ? await BM.json(q.get('devsrc')) : runId ? await BM.loadRun(runId) : null; // devsrc: tools/ fixtures only, never linked
  if (run?.dev) document.body.classList.add('dev');
  const EV = (node, evd, what, fields) => run ? ev(node, evd, { run: run.id, what, fields }) : node;
  const R = $('#report'); R.innerHTML = '';
  for (const pr of run?.structure || []) BM.names[pr.id] = BM.proposalName(pr);
  for (const g of run?.reading?.groups || []) for (const m of g.members || []) BM.names[m.id] = m.label || m.words;
  document.title = `Case ${c.id} ${c.title} · BenchMate`;
  const h2 = (t) => el('h2', { style: 'margin-top:22px' }, t);

  R.append(el('div', { style: 'display:flex;flex-wrap:wrap;gap:8px 14px;align-items:center' },
    el('span', { class: 'small muted' }, `Case ${c.id}`), run ? el('span', { class: 'badge ' + (run.counted ? 'live' : run.pilot ? 'pilot' : 'pending'), title: run.classification?.basis || '' }, run.classification?.public_label || run.classification?.label || (run.pilot ? 'Pilot run — not counted' : 'Counted run')) : el('span', { class: 'badge pending' }, 'Not run yet'),
    el('span', { class: 'noprint', style: 'margin-left:auto;display:flex;gap:6px;flex-wrap:wrap' }, el('button', { class: 'btn ghost sm', onclick: () => print() }, 'Print'),
      run ? el('a', { class: 'btn ghost sm', href: `data/runs/${run.id}.json`, download: '' }, 'Download run JSON') : null,
      run ? el('a', { class: 'btn sm', href: `run.html?run=${run.id}` }, 'Replay') : null)));
  R.append(el('h1', { style: 'margin-top:6px' }, c.title), c.title_after_reveal ? el('p', { class: 'small muted', style: 'margin-top:2px' }, `Case ${c.id} — ${c.title_after_reveal.toLowerCase()}`) : null, el('p', { style: 'margin-top:6px;font-size:17px' }, c.forum_line || c.problem));

  if (run) {
    const t = run.totals;
    R.append(el('div', { class: 'stats' },
      el('div', {}, el('b', {}, run.steps.length), el('span', {}, 'experiments Spark chose')), el('div', {}, el('b', {}, t.spark_calls), el('span', {}, 'Muse Spark calls')),
      el('div', {}, el('b', {}, fmtUSD(t.spark_cost)), el('span', {}, 'estimated cost')), el('div', {}, el('b', {}, t.forecasts_frozen), el('span', {}, 'forecasts frozen before measuring')),
      el('div', {}, el('b', {}, t.bench_changes), el('span', {}, 'bench changes requested')), el('div', {}, el('b', {}, t.sim_calls), el('span', {}, 'ngspice simulations'))));
    R.append(el('p', { class: 'small muted' }, `${run.label}, recorded ${fmtDate(run.started_utc)}, ${run.model}, reasoning effort ${run.reasoning_effort}. Cost from token counts at the published rates. Classification: ${run.classification?.label || ''} (${run.classification?.basis || 'n/a'}).`));
  }

  // the drawing the model read, in its context frame
  R.append(h2('What the model received'));
  const model = el('div', { class: 'model' }, el('span', { class: 'lab' }, 'Model input')); model.append(await schematic(c.design));
  R.append(el('div', { class: 'frame' }, el('div', { class: 'grey' }, c.context.in, el('small', {}, 'original setup')), model, el('div', { class: 'grey' }, c.context.out, el('small', {}, 'original setup'))));
  R.append(el('p', { class: 'small muted' }, 'Muse Spark received the drawing in the middle and the shared bench description (test menu and fixture), the same for every case. The grey boxes, the case name and the hidden fault were never sent to the model.'));
  if (c.probe) R.append(el('div', { class: 'card', style: 'margin-top:8px' }, el('h4', {}, c.probe.title), ...c.probe.lines.map(l => el('p', { class: 'small' }, l))));
  if (run?.schematic_read) {
    const sr = run.schematic_read;
    R.append(el('p', { style: 'margin-top:8px' }, el('b', {}, 'Muse Spark vision read the drawing: '), sr.summary, ` (${sr.requests} call, ${fmtUSD(sr.cost)}, ${fmtDate(sr.utc)}, intake run ${sr.run}).`),
      el('ul', { class: 'small muted', style: 'margin:4px 0 0 18px' }, ...sr.components.map(k => el('li', {}, `${k.name} ${k.kind} ${k.marking} between ${k.nodes.join(' and ')}: ${k.evidence}`))));
  }
  if (run?.design_amendment) R.append(el('p', { class: 'small muted', style: 'margin-top:6px' }, el('b', {}, 'Public design amendment: '), run.design_amendment.detail || run.design_amendment.text, run.design_amendment.doc ? ` Record: ${run.design_amendment.doc}.` : ''));
  if (c.board && !run?.photo) R.append(el('div', { style: 'margin-top:10px;max-width:460px' }, boardSVG(c.board), el('p', { class: 'small muted' }, `Built: diagram from the wiring record (${c.board.record}); photo pending.`)));

  R.append(h2('What we kept from the forum case'));
  R.append(el('dl', { class: 'kv' }, el('dt', {}, 'Cause'), el('dd', {}, c.cause), el('dt', {}, 'Kept'), el('dd', {}, c.kept), el('dt', {}, 'Changed'), el('dd', {}, c.changed),
    el('dt', {}, 'Source'), el('dd', {}, el('a', { href: c.source.url, target: '_blank', rel: 'noopener' }, `${c.source.site}: ${c.source.title}`), c.source.date ? `, ${c.source.date}` : '')));
  R.append(el('p', { class: 'small muted' }, 'Same principle, reproduced on our bench. We did not repair the original poster’s board.'));

  if (!run) {
    R.append(el('p', { class: 'muted', style: 'margin-top:18px' }, c.pending_note || 'This case has not been run on the bench yet. Its replay and report appear here from the run files.'));
    return;
  }

  // experiments
  R.append(h2('Experiments chosen by Muse Spark'));
  R.append(el('p', { class: 'small muted' }, `Fixed menu: ${run.menu.map(m => BM.menuLabel(m).join(' ')).join('; ')}. Allowance ${run.allowance_mV} mV RMS, whole step and every region. Reserved for the check: ${(run.reserved || []).map(r => `${r.kind} ${r.amplitude_v} V${r.frequency_hz ? ' ' + r.frequency_hz + ' Hz' : ''}`).join(', ')}.`));
  const dead = {};
  for (const st of run.steps) {
    const box = el('div', { class: 'exp' });
    box.append(el('h3', {}, el('span', { class: 'n', style: 'display:inline-grid;place-items:center;width:24px;height:24px;border-radius:50%;background:var(--ink);color:#fff;font-size:12px;margin-right:8px;vertical-align:2px' }, st.n), st.label),
      el('p', { class: 'quote', style: 'font-family:var(--narrow);font-size:16px;margin:4px 0' }, `“${st.reason || ''}”`),
      el('p', { class: 'small muted' }, `Chosen ${fmtDate(st.chosen_utc)}. Forecast frozen before measuring, `, EV(el('span', {}, `sha256 ${st.forecast_sha}`), st.ev, 'experiment choice', { forecast_sha256: st.forecast_sha_full }), st.forecasts.length ? ' for ' + st.forecasts.map(f => expName(f.id)).join(', ') : '', '.'));
    const grid = el('div', { class: 'grid' });
    const ms = el('div', { class: 'scope mini-scope' }); const sc = new Scope(ms, { ratio: 0.52 }); grid.append(ms);
    const rows = el('tbody');
    for (const f of st.fit || []) { if (f.status !== 'adequate' && dead[f.id] == null) dead[f.id] = st.n; }
    for (const f of st.fit || []) {
      const k = f.miss_mV.length - 1; const whole = f.miss_mV[k]; const miss = f.decided_mV?.[k] ?? whole; const worst = f.worst_region?.[k]; const bad = f.passed[k] === false; const out = f.status !== 'adequate';
      rows.append(el('tr', { class: out ? 'out' : '' }, el('td', {}, expName(f.id)), el('td', { class: 'muted small' }, f.value != null ? ['fitted so far ', EV(el('span', {}, BM.fmtFit(f.kind, f.value, f.at_bound)), st.fit_ev, `fitted value of ${expName(f.id)} on step ${st.n}`, { explanation: f.id, raw_value: f.value, kind: f.kind, parameter_at_bound: f.at_bound, fit_range: BM.FIT_BOUNDS[f.kind] })] : 'drawn values'), el('td', {}, EV(el('span', { class: `miss ${bad ? 'bad' : 'good'}` }, fmtMiss(miss)), st.fit_ev, `miss on step ${st.n}`, { explanation: f.id, decided_by: worst ? `worst region ${worst}` : 'whole step', decided_mV: miss, whole_step_RMS_mV: whole, regions: f.regions?.[k], status: f.status }), worst ? el('small', { class: 'muted' }, ` worst region: ${worst.replace(/_/g, ' ')}`) : null), el('td', {}, out ? el('span', { class: 'tape red' }, `Ruled out after step ${dead[f.id]}`) : el('span', { class: 'small muted' }, 'still fits'))));
    }
    grid.append(el('div', {}, el('div', { class: 'tscroll' }, el('table', { class: 'fit-table' }, el('thead', {}, el('tr', {}, el('th', {}, 'Explanation'), el('th', {}, 'Value'), el('th', {}, 'Miss'), el('th', {}, ''))), rows)),
      st.guard_failed ? el('p', { class: 'small', style: 'color:var(--fault);margin-top:6px' }, `Reference guard failed on ${st.guard_failed.label}; no result scored.`) : null));
    box.append(grid); R.append(box);
    requestAnimationFrame(() => sc.set(stepTime(st), stepTraces(st), `Step ${st.n}`));
  }

  // structure proposals
  if (run.structure?.length) {
    R.append(h2('Parts the drawing does not show'));
    for (const pr of run.structure) {
      const added = (pr.diff?.added || []).map(x => x.name), recon = (pr.diff?.reconnected || []).map(x => x.name);
      R.append(el('div', { class: 'card violet', style: 'margin-top:8px' }, el('div', { class: 'schem-wrap' }, netlistSVG(pr.elements, { highlight: added.concat(recon) })),
        el('p', { style: 'margin-top:6px' }, el('b', {}, BM.words.structure({ diff: pr.diff })), ' ', pr.rationale ? el('span', { class: 'quote' }, pr.rationale) : null),
        el('p', { class: 'small muted' }, BM.diffWords(pr.diff)),
        el('p', { class: 'small muted' }, `${BM.proposerWords(pr.selected_by)}. ${pr.fit ? `Fit: ${pr.fit.status}${pr.fit.miss_mV?.length ? `, misses ${pr.fit.miss_mV.map(fmtMiss).join(', ')}` : ''}${pr.fit.simulator_calls ? `, ${pr.fit.simulator_calls} ngspice runs` : ''}${pr.fit.error ? `, error: ${pr.fit.error}` : ''}.` : 'Not fitted.'} A fit to the training measurements is not a verdict.`)));
    }
  }

  // a reading that was asked for and then withdrawn: one line, nothing else (the request and forecast stay in the repository record)
  if (run.reading_withdrawn?.withdrawn && !run.reading?.observed) R.append(el('p', { class: 'small muted', style: 'margin-top:8px' }, EV(el('span', {}, run.reading_withdrawn.line), run.reading_withdrawn.ev, 'reading withdrawn', { reason: run.reading_withdrawn.reason, timing: run.reading_withdrawn.timing, forecast_exercised: run.reading_withdrawn.forecast_exercised })));
  // the one reading (only when the run has the stage)
  if (run.reading?.component) {
    const rd = run.reading; const bands = rd.bands || []; const srcs = [...new Set(bands.map(b => b.source))]; const exps = [...new Set(bands.map(b => b.explanation))];
    R.append(h2(rd.group ? 'The reading at the bench: two bodies, bands frozen first' : 'One reading at the bench'));
    for (const g of rd.groups || []) R.append(el('p', { class: 'small' }, el('span', { class: 'chip' }, el('i'), 'engine rule — electrically equivalent'), ` ${BM.words.equivalence(g)} ${expName(g.base_explanation)} and ${(g.members || []).map(m => m.words || m.label).join(', ')} give the same waveforms at the terminals.`, g.reason ? ` ${g.reason}` : ''));
    R.append(el('p', {}, el('b', {}, `Spark asked for ${BM.quantityWord(rd.quantity, rd.component)}`), ` (${BM.chosenWord(rd.chosen_by)}). `, rd.reason ? el('span', { class: 'quote' }, rd.reason) : null));
    R.append(el('p', { class: 'small muted' }, 'Bands frozen before anyone read the part, per explanation and per source', rd.sha_full ? [': ', EV(el('span', { class: 'mono' }, `sha256 ${rd.sha}`), rd.frozen_ev, 'frozen reading forecast', { sha256_full: rd.sha_full, bands })] : null, rd.commit ? [', pushed as ', el('a', { class: 'linkish', href: rd.url || '#', target: '_blank', rel: 'noopener' }, String(rd.commit).slice(0, 7))] : null, '.'));
    R.append(el('div', { class: 'tscroll' }, el('table', { class: 'fit-table' }, el('thead', {}, el('tr', {}, el('th', {}, 'Explanation'), ...srcs.map(s => el('th', {}, `If read by ${BM.sourceShort(s)}`)))),
      el('tbody', {}, ...exps.map(x => el('tr', {}, el('td', {}, expName(x)), ...srcs.map(s => { const b = bands.find(q => q.explanation === x && q.source === s); return el('td', {}, b ? [EV(el('span', { class: 'miss' }, BM.bandText(b)), rd.frozen_ev, `frozen band for ${expName(x)}, ${BM.sourceShort(s)}`, { explanation: x, source: s, low: b.low, high: b.high, unit: b.unit, rule: b.rule, note: b.note }), el('small', { class: 'muted', style: 'display:block' }, `${b.rule || ''}${b.note ? ' — ' + b.note : ''}`)] : el('span', { class: 'muted' }, '—')); })))))));
    if (run.continuation) R.append(el('p', { class: 'small', style: 'margin-top:8px' }, el('b', {}, 'Record stopped: '), EV(el('span', {}, run.continuation.line), run.continuation.ev, 'run_failed', { stage: run.continuation.stopped_at, error: run.continuation.error, counted_failure: run.continuation.counted_failure, linked_records: run.classification?.linked_records })));
    if (rd.binding?.abstained) R.append(el('p', { class: 'small', style: 'margin-top:8px' }, el('b', {}, 'Which body: '), EV(el('span', {}, `asked which body is ${rd.binding.component}, Spark named none. `), rd.binding.ev, 'binding call stopped', { returned: 'null (string)', stop: rd.binding.format_stop, calls: rd.binding.calls }), rd.binding.reason ? el('span', { class: 'quote' }, rd.binding.reason) : null, ` Spark’s body-pointing call stopped on a response-format error (the string "null" where the validator expected JSON null) and was not retried; the pair record ends there and the reading continues in a linked record.`));
    else if (rd.binding) R.append(el('p', { class: 'small', style: 'margin-top:8px' }, el('b', {}, 'Which body: '), EV(el('span', {}, `${rd.binding.sam_body || 'SAM body'} → ${rd.binding.component}, ${BM.chosenWord(rd.binding.chosen_by)}${rd.binding.operator_confirmed ? ', confirmed by the operator' : ''}${rd.binding.bodies ? `, from the ${rd.binding.bodies} bodies SAM 3.1 returned` : ''}${(rd.binding.candidates || []).length > 1 ? ` (Spark kept ${rd.binding.candidates.map(c => c.sam_body).join(' and ')} as candidates and named one)` : ''}. `), rd.binding.ev, 'body binding', { sam_body: rd.binding.sam_body, component: rd.binding.component, candidates: rd.binding.candidates, mapping_status: rd.binding.mapping_status, operator_confirmed: rd.binding.operator_confirmed, operator_verbatim: rd.binding.operator_verbatim, mask_bounds_in_sam_input: rd.binding.bounds, sam_confidence: rd.binding.confidence }), rd.binding.reason ? el('span', { class: 'quote' }, rd.binding.reason) : null));
    if (rd.binding?.photo) { const box = el('div', { class: 'photo', style: 'max-width:420px;margin-top:6px' }, el('img', { src: rd.binding.photo, alt: 'Board photo with the SAM outline' })); if (rd.binding.overlay_file) box.append(el('img', { class: 'mask', src: rd.binding.overlay_file, alt: 'SAM 3.1 outline' })); R.append(box); }
    if (rd.observed && !rd.group) R.append(el('p', { style: 'margin-top:8px' }, el('b', {}, 'Read: '), EV(el('span', { class: 'miss' }, `${rd.observed.component} = ${rd.observed.value} ${rd.observed.unit || ''}`), rd.observed.ev, 'operator reading', { component: rd.observed.component, value: rd.observed.value, unit: rd.observed.unit, source: rd.observed.source, photo: rd.observed.photo }), `, ${BM.sourceWord(rd.observed.source)}.`));
    if (rd.observed?.photo) R.append(el('img', { src: rd.observed.photo, alt: 'Evidence photo of the reading', style: 'max-width:220px;height:auto;border-radius:3px;border:1px solid var(--rule);margin-top:4px' }));
    if (rd.scored && !rd.group) R.append(el('p', { style: 'margin-top:6px' }, el('b', {}, 'Scored: '), EV(el('span', {}, BM.words.readingScored({ outcome: rd.outcome, fits: rd.scored.fits }, bands)), rd.scored.ev, 'reading scored', { fits: rd.scored.fits, outcome: rd.outcome })), el('p', { class: 'small muted' }, 'Scored by code against the frozen bands. Explanations outside their band are marked “ruled out by one reading”, apart from those the bench measurements ruled out.'));
    if (rd.group) {
      const g = rd.group; const gb = g.bands || []; const comps = g.components || []; const bodies = g.bodies || []; const gexps = [...new Set(gb.map(b => b.explanation))];
      R.append(el('h3', { style: 'margin-top:14px' }, 'Two bodies, read out of circuit'));
      R.append(el('p', { class: 'small' }, `${bodies.join(' and ')} are the two capacitor bodies in the photo, picked by a visual review at the operator’s request (recorded as “${g.chosen_by}”), not by a model. ${g.scope || ''}`));
      R.append(el('p', { class: 'small muted' }, 'Bands for both parts under each explanation, frozen before the readings', g.sha_full ? [': ', EV(el('span', { class: 'mono' }, `sha256 ${g.sha}`), g.frozen_ev, 'frozen group reading forecast', { sha256_full: g.sha_full, bands: gb, meter: g.meter, matching: g.matching })] : null, g.commit ? [', pushed as commit ', el('span', { class: 'mono' }, String(g.commit).slice(0, 7))] : null, `. Multimeter, ${g.meter?.range_uF} µF range, ${g.meter?.resolution_uF} µF resolution, allowance ${Math.round((g.meter?.relative_allowance || 0) * 100)} % + ${g.meter?.digits_allowance} digits (an engineering acceptance, not a manufacturer accuracy). Rule: ${g.matching || ''}`));
      R.append(el('div', { class: 'tscroll' }, el('table', { class: 'fit-table' }, el('thead', {}, el('tr', {}, el('th', {}, 'Explanation'), ...comps.map(c => el('th', {}, `${c} band`)))),
        el('tbody', {}, ...gexps.map(x => { const role = gb.find(b => b.explanation === x)?.role; return el('tr', { class: role === 'reference' ? 'out' : '' }, el('td', {}, expName(x), el('small', { class: 'muted', style: 'display:block' }, role === 'reference' ? 'reference, already ruled out by the bench tests' : 'surviving explanation')), ...comps.map(c => { const b = gb.find(q => q.explanation === x && q.component === c); return el('td', {}, b ? [EV(el('span', { class: 'miss' }, BM.bandText(b)), g.frozen_ev, `frozen band for ${c} under ${expName(x)}`, { explanation: x, component: c, low: b.low, high: b.high, unit: b.unit, rule: b.rule }), el('small', { class: 'muted', style: 'display:block' }, b.rule || '')] : el('span', { class: 'muted' }, '—')); })); })))));
      if (g.observed) R.append(el('p', { style: 'margin-top:8px' }, el('b', {}, 'Read: '), EV(el('span', { class: 'miss' }, (g.observed.readings || []).map(r => `${r.body} = ${r.value} ${r.unit}`).join(' · ')), g.observed.ev, 'operator readings', { readings: g.observed.readings, source: g.observed.source, power_off: g.observed.power_off, discharge_wait: g.observed.discharge_wait }), `, ${BM.sourceWord(g.observed.source)}, each capacitor removed from the board${g.observed.power_off ? ', USB off' : ''}.`));
      if (g.scored) {
        const sc = g.scored; const bind = sc.binding || {}; const vals = Object.fromEntries((g.observed?.readings || []).map(r => [r.body, r.value]));
        const perms = (arr) => arr.length <= 1 ? [arr] : arr.flatMap((x, i) => perms([...arr.slice(0, i), ...arr.slice(i + 1)]).map(r => [x, ...r]));
        const assigns = perms(bodies).map(order => Object.fromEntries(comps.map((c, i) => [c, order[i]])));
        const engineFits = (x, a) => ((sc.matches || []).find(mm => mm.explanation === x)?.assignments || []).some(as => comps.every(c => as[c] === a[c]));
        R.append(el('p', { style: 'margin-top:8px' }, el('b', {}, 'Scored: '), EV(el('span', {}, `Which body is ${comps[0]} follows from the readings themselves: of the ${assigns.length === 2 ? 'two' : assigns.length} possible assignments, only one fits the frozen bands. ${Object.keys(bind).length ? comps.map(c => `${c} = ${bind[c]}`).join(', ') + '.' : 'No assignment fits.'}`), sc.ev, 'group reading score', { fits: sc.fits, matches: sc.matches, binding: sc.binding, outcome: sc.outcome_raw, body_identity_status: sc.body_identity_status, nearest_value_assignment: sc.nearest_value_assignment, refitted: sc.refitted, forecast_sha256: sc.forecast_sha256, observation_sha256: sc.observation_sha256 })));
        R.append(el('ul', { class: 'small', style: 'margin:6px 0 0 18px' }, ...gexps.flatMap(x => assigns.map(a => { const ok = engineFits(x, a); return el('li', {}, `${expName(x)}, ${comps.map(c => `${c} = ${a[c]} (${vals[a[c]]} µF)`).join(', ')}: `, el('span', { class: `miss ${ok ? 'good' : 'bad'}` }, ok ? 'fits' : 'misses')); }))));
        R.append(el('p', { class: 'small muted' }, `Engine result as written: fits ${(sc.fits || []).map(expName).join(', ') || 'none'}; body identity ${String(sc.body_identity_status || '').replace(/_/g, ' ')}; nearest-value assignment ${sc.nearest_value_assignment ? 'used' : 'not used'}; ${sc.refitted ? 're-fitted' : 'nothing re-fitted'}. The site never pairs a body with a part itself.`));
      }
    }
  }

  // check
  R.append(h2('The check on held-back inputs'));
  if (run.verification?.sha) {
    const v = run.verification;
    R.append(el('div', { class: 'card' }, el('p', {}, `Muse Spark asked for the check. The engine froze one forecast per reserved input, `, EV(el('span', {}, `sha256 ${v.sha}`), v.frozen_ev, 'final forecast', { sha256_full: v.sha_full }), v.commit ? ', pushed as commit ' : '', v.commit ? EV(el('a', { class: 'linkish', href: v.url, target: '_blank', rel: 'noopener' }, v.commit.slice(0, 7)), v.publish_ev, 'publication', { commit: v.commit, url: v.url }) : null, `, then measured. Carried forward: ${v.models.map(m => `${expName(m.id)}${m.value != null ? ' at ' + fmtVal(m.kind, m.value) : ''}`).join(', ')}.`),
      v.scored?.length ? el('ul', { class: 'small', style: 'margin:6px 0 0 18px' }, ...v.scored.map(s => el('li', {}, `Held-back input ${s.index ?? ''}: `, ...Object.entries(s.conditional).flatMap(([id, x], i) => [i ? '; ' : '', `${expName(id)} `, EV(el('span', { class: `miss ${x.passed ? 'good' : 'bad'}` }, fmtMiss(x.decided_mV ?? x.RMS_mV)), s.ev, `held-back input ${s.index}`, { explanation: id, decided_by: x.worst_region ? `worst region ${x.worst_region}` : 'whole input', decided_mV: x.decided_mV, whole_RMS_mV: x.RMS_mV, regions: x.regions, passed: x.passed }), ` ${x.passed ? 'within' : 'outside'} allowance`])))) : el('p', { class: 'small', style: 'color:var(--fault);margin-top:6px' }, 'Not scored: the reference guard stopped the run after the first held-back input.'),
      v.survivors ? el('p', { class: 'small muted', style: 'margin-top:6px' }, `Survivors after the check: ${v.survivors.map(expName).join(', ') || 'none'}.`) : null));
  } else R.append(el('p', { class: 'muted' }, 'The run stopped before Spark asked for the check.'));

  // outcome and the seal
  R.append(h2(run.outcome?.kind === 'stopped' ? 'Outcome: stopped' : 'Outcome'));
  const nt = notes.runs?.[run.id];
  if (run.outcome?.kind === 'report') R.append(el('div', { class: 'verdict-card' }, el('div', { class: 'big' }, verdictWords(run.outcome, run)), run.outcome.text ? el('p', {}, run.outcome.text) : null, el('p', { class: 'small muted', style: 'margin-top:6px' }, `Engine verdict: ${run.outcome.verdict}. Copied from the report event; the site does not pick verdicts.`)));
  else R.append(el('div', { class: run.outcome?.kind === 'stopped' ? 'card red' : 'card' }, el('p', {}, run.outcome?.reason || run.outcome?.text || ''), nt?.guard_detail ? el('p', { class: 'small', style: 'margin-top:4px' }, nt.guard_detail, ' ', el('span', { class: 'faint' }, `Source: ${nt.source}`)) : null));
  if (run.note_after) R.append(el('p', { style: 'margin-top:8px' }, run.note_after));

  R.append(h2(run.pilot ? 'Hidden fault, opened for comparison' : run.pair?.state === 'restored' ? 'The fault, restored before this rerun' : 'Hidden fault, opened after the run'));
  const sw = el('div', { class: 'schem-wrap' }); const ssvg = await schematic(c.design); sw.append(ssvg); const ovs = overlaySVG(c.overlay, ssvg.getAttribute('viewBox')); const ov = el('div', { class: 'ov' }); ov.append(ovs); sw.append(ov); requestAnimationFrame(() => fitOverlay(ssvg, ovs));
  R.append(sw, el('p', { style: 'margin-top:8px' }, el('b', {}, 'Hidden: '), c.hidden), run.seal?.truth ? el('p', { class: 'small muted' }, EV(el('span', {}, `Sealed before the diagnosis: ${run.seal.truth.map(t => `${t.component.replace('external_', 'hidden ')} ${t.value_nominal_ohm != null ? BM.fmtR(t.value_nominal_ohm) : t.value_nominal_F != null ? BM.fmtC(t.value_nominal_F) : ''}${t.marking ? ' (marked ' + t.marking + ')' : ''} at ${t.location}`).join('; ')}. ${run.seal.matches_commitment ? 'The opened record matches the digest committed before the first measurement.' : 'The opened record does not match the committed digest.'}`), run.seal.opened_ev, 'seal opened', { sealed_sha256: run.seal.sealed_sha256, matches_commitment: run.seal.matches_commitment, truth: run.seal.truth })) : null, c.truth ? el('p', { class: 'small muted' }, `Measured on the bench: ${Object.entries(c.truth.measured_ohm || {}).map(([k, v]) => `${k.replace('hidden_', 'hidden ')} ${BM.fmtR(v)}`).join(', ')}${c.truth.series_total_ohm ? `; series total ${BM.fmtR(c.truth.series_total_ohm)}` : ''}. ${c.truth.source}`) : null, el('p', { class: 'small muted' }, c.limits));
  if (run.pilot) R.append(el('p', { class: 'small', style: 'margin-top:8px' }, el('span', { class: 'badge pilot' }, 'Pilot run — not counted'), ' Both pilots narrowed to a larger series resistance but stopped at the reference guard; neither is a verified diagnosis.'));

  // photo, only when it exists
  if (run.photo?.image?.file) {
    R.append(h2(run.photo.documentary ? 'The board photo (documentary)' : 'The board photo, read after the diagnosis'));
    const box = el('div', { class: 'photo', style: 'max-width:520px' }, el('img', { src: run.photo.image.file, alt: 'Mini board' }));
    for (const cc of run.photo.sam || []) for (const m of cc.masks || []) if (m.overlay_file) box.append(el('img', { class: 'mask', src: m.overlay_file, alt: `SAM mask ${cc.concept} ${m.object_id}` }));
    { const cb = run.photo.crop_box || [0, 0, run.photo.image.width || 1200, run.photo.image.height || 1600]; const iw = cb[2] - cb[0], ih = cb[3] - cb[1]; const greads = run.reading?.group?.observed?.readings || [];
      const all = (run.photo.labels || []).map(x => x.bounds);
      for (const l of run.photo.labels || []) { const r = greads.find(x => x.body === l.text); const bb = l.bounds; const up = all.some(o => o !== bb && o[1] >= bb[3] - 4 && o[1] < bb[3] + 0.09 * ih && o[0] < bb[2] && o[2] > bb[0]);
        if (l.side) { box.append(el('span', { class: 'masklabel side', style: `left:${((bb[2] - cb[0]) / iw * 100 + 1.5).toFixed(1)}%;top:${((bb[1] + bb[3]) / 2 - cb[1]) / ih * 100}%` }, r ? `${l.text} read ${r.value} ${r.unit}` : l.text)); continue; }
        box.append(el('span', { class: 'masklabel' + (up ? ' up' : ''), style: up ? `left:${((bb[0] + bb[2]) / 2 - cb[0]) / iw * 100}%;bottom:${(100 - (bb[1] - cb[1]) / ih * 100 + 1.5).toFixed(1)}%` : `left:${((bb[0] + bb[2]) / 2 - cb[0]) / iw * 100}%;top:${((bb[3] - cb[1]) / ih * 100 + 2).toFixed(1)}%` }, r ? `${l.text} read ${r.value} ${r.unit}` : l.text)); } }
    R.append(box, run.photo.provenance ? el('p', { class: 'small', style: 'margin:6px 0 0' }, run.photo.provenance) : null, run.photo.contours_note ? el('p', { class: 'small faint', style: 'margin:4px 0 0' }, run.photo.contours_note) : null, el('ul', { class: 'small', style: 'margin:6px 0 0 18px' }, ...(run.photo.vision?.components || []).map(k => el('li', {}, `${k.name} ${k.kind}: ${k.reading_status === 'unreadable' ? 'unreadable' : (k.marking || '—')}${k.value_si != null ? ` (${fmtVal(k.kind, k.value_si)})` : ''} — ${k.evidence || ''}`))),
      run.photo.documentary ? el('p', { class: 'small muted' }, run.photo.note) : el('p', { class: 'small muted' }, `SAM 3.1: ${(run.photo.sam || []).map(cc => `${cc.concept} ${cc.match_count} match${cc.match_count === 1 ? '' : 'es'}`).join(', ') || 'not run'}. Pairing of SAM objects with drawing parts: ${run.photo.pairing}. ${(run.photo.vision?.ambiguities || []).length} ambiguities noted by the model.`));
    if (run.photo.display_rule_image?.file) R.append(el('details', { class: 'small', style: 'margin-top:8px' }, el('summary', {}, 'Documentary: all native SAM 3.1 masks under the display rule'), el('div', { class: 'photo', style: 'max-width:420px;margin-top:6px' }, el('img', { src: run.photo.display_rule_image.file, alt: 'The same photo with every native SAM 3.1 mask outlined under the display rule' })), el('p', { class: 'small faint', style: 'margin:4px 0 0' }, run.photo.display_rule_image.note)));
  }

  // pair status with the restored rerun
  const pair = index.runs.find(r => r.pair_of === run.id) || (run.pair?.of ? index.runs.find(r => r.id === run.pair.of) : null);
  if (pair || run.pair) {
    R.append(h2('Restored board and rerun'));
    const other = pair ? pair : null;
    const prevA = run.pair?.previous_attempt || (run.restored_attempts || [])[0];
    R.append(el('div', { class: 'card' }, el('p', {}, `Operator restored the board: ${run.pair?.operator_restored || other ? 'recorded' : 'pending'}. `, other ? el('a', { href: `run.html?run=${other.id}` }, `Paired run ${other.label}`) : null, other ? `: ${other.display_caption || (other.verdict ? verdictWords({ verdict: other.verdict, survivors: null }, run) : other.outcome)}.` : ''),
      run.pair?.restored_what ? el('p', { class: 'small' }, el('b', {}, 'Restoration, in the operator’s words: '), EV(el('span', { class: 'quote' }, run.pair.restored_what), run.pair.restore_ev, 'operator restoration confirmed', { closeout: run.pair.closeout, external_only: run.pair.external_only })) : null,
      prevA ? el('p', { class: 'small' }, el('b', {}, `Restored attempt ${prevA.attempt}: `), EV(el('span', {}, `ended ${prevA.verdict}, counted, in the pair record (${prevA.record}). `), prevA.ev, 'restored attempt 1, engine report', { verdict: prevA.verdict, record: prevA.record, engine_report: prevA.text }), el('span', { class: 'muted' }, prevA.note || 'The drawing’s model missed the 0–5 ms region of both steps by 9.3 and 10.2 mV against the 9 mV allowance; Spark proposed nothing and abstained. The counted attempt 2 shown as the paired run was made on the frame-anchored timing model, qualified and published before it.')) : null,
      run.pair?.closeout ? el('p', { class: 'small muted' }, `Closeout: restored verdict ${run.pair.closeout.restored_verdict}; restored photo documentary only${run.pair.closeout.restored_binding_performed === false ? ', no body paired with a part' : ''}; SAM used as identification evidence: ${run.pair.closeout.SAM_used_as_identification_evidence ? 'yes' : 'no'}.`) : null,
      el('p', { class: 'small muted' }, 'A restored rerun is a fresh Muse Spark context on the same drawing. The expected result is “No mismatch in the tests Spark chose”; it is shown as pair-level consistency, not as a repair claim.')));
  }

  // verify it yourself
  R.append(h2('Verify it yourself'));
  R.append(el('div', { class: 'card verify' },
    el('dl', { class: 'kv' }, el('dt', {}, 'Run'), el('dd', { class: 'mono' }, run.id), el('dt', {}, 'Events'), el('dd', {}, `${run.event_count} in events.jsonl, each with its sha256 and the previous one; first ${(run.first_sha256 || '').slice(0, 12)}…, last ${(run.last_sha256 || '').slice(0, 12)}…`),
      run.verification?.sha_full ? el('dt', {}, 'Frozen forecast') : null, run.verification?.sha_full ? el('dd', { class: 'mono' }, run.verification.sha_full) : null,
      run.verification?.commit ? el('dt', {}, 'Commit') : null, run.verification?.commit ? el('dd', {}, el('a', { href: run.verification.url, target: '_blank', rel: 'noopener' }, run.verification.commit)) : null,
      run.reading?.sha_full ? el('dt', {}, 'Frozen reading bands') : null, run.reading?.sha_full ? el('dd', {}, el('span', { class: 'mono' }, run.reading.sha_full), run.reading.commit ? [' · ', el('a', { href: run.reading.url, target: '_blank', rel: 'noopener' }, String(run.reading.commit).slice(0, 7))] : null) : null,
      run.reading?.group?.sha_full ? el('dt', {}, 'Frozen bands, both bodies') : null, run.reading?.group?.sha_full ? el('dd', {}, el('span', { class: 'mono' }, run.reading.group.sha_full), run.reading.group.commit ? el('span', { class: 'small muted' }, ` · commit ${String(run.reading.group.commit).slice(0, 7)}`) : null) : null,
      run.seal?.sealed_sha256 ? el('dt', {}, 'Sealed fault') : null, run.seal?.sealed_sha256 ? el('dd', {}, el('span', { class: 'mono' }, run.seal.sealed_sha256), el('span', { class: 'small muted' }, ` — digest committed before the first measurement; ${run.seal.matches_commitment ? 'matched when opened' : 'not matched when opened'}.`)) : null,
      el('dt', {}, 'Check'), el('dd', {}, el('code', {}, run.verify_command || `python -m benchmate verify <run folder>`), el('span', { class: 'small muted' }, ` — prints PASS or FAIL and the number of events checked: the full hash chain, the frozen-forecast hashes and the forecast → measurement order, including the physical CAPTURE order. It proves the record’s internal integrity and order, not when it was written. Details: docs/2026-11-03-offline-verification.md.`),
        run.verify_output || run.verify_outputs ? el('pre', { class: 'small', style: 'white-space:pre-wrap;margin-top:6px' }, (run.verify_outputs || [run.verify_output]).join('\n')) : null)),
    el('p', { class: 'small muted' }, 'On the replay, click any number to see the event it came from. ', el('a', { href: `data/runs/${run.id}.json`, download: '' }, 'Download this run’s JSON'), '.')));
})();
