"""Turn one BenchMate run folder into the replay file the site plays.

Usage
  python3 tools/extract_runs.py --run <run folder> --case 01 --label "Pilot A" \
      --intake <schematic-intake summary.json> --rates <schematic-intake cost.json> --image 1 \
      [--photo <photo-run root>] [--render <render dir with *-decoded.json>] \
      [--pair-restore <operator restoration record.json>] [--note "..."]

Writes data/runs/<run id>.json and updates data/runs/index.json.

What this script does and does not do
- Copies numbers from the logs. Nothing is scored or recomputed here, except the token-based
  cost estimate at the published per-token rates (--rates).
- Classification (pilot / counted / unclassified) comes from the run's own metadata
  (see classify()), never from a CLI flag. Unknown runs are "Not counted (unclassified)".
- Keeps, for every rendered event, its envelope: sequence, timestamp, kind, sha256,
  previous_sha256. The site shows these as evidence. Operator-only payload fields are not
  copied wholesale; only the fields the pages render are kept.
- Structure proposals (structure_proposed / structure_fit) are joined by id and diffed
  against the reviewed design. The verification chain is linked by model id. The site never
  picks a verdict: agent_report.verdict and the survivors list are copied as written.
- Photo results (optional) are read from the photo run root result.json -> vision result
  and the render dir's <concept>-decoded.json. R/C with value_si null are marked
  reading_status "unreadable"; D is not. SAM objects are never auto-paired with parts.
- The reading stage (equivalence_group, reading_requested, reading_forecast_frozen, body_binding,
  reading_observed, reading_scored) is copied into run.reading and the timeline. An equivalence
  group is an ENGINE RULE (electrically equivalent members of one surviving explanation), never a
  Spark proposal; structure proposals exist only on the all-ruled-out path. A reading_scored without a frozen
  band for the reported source is an error (no score without its forecast). Runs without the
  stage render nothing for it. The site never decides which explanation a reading fits: it
  shows reading_scored.fits as written; the visitor's "try any value" compares against the same
  frozen bands in the browser and is labelled a what-if.

Replay pacing: event times are the real log times. Gaps longer than GAP_S (the operator
rewiring the bench) are shortened to GAP_PLAY_S in playback and carry the real duration.
"""
import argparse, json, pathlib, re, sys
from datetime import datetime

SITE = pathlib.Path(__file__).resolve().parents[1]
GAP_S, GAP_PLAY_S = 30.0, 2.5

ACTION = {
    'unloaded_step_small': ('step', 0.2, None, 'Step, ±0.2 V, no load'),
    'loaded_step_small': ('step', 0.2, 9990, 'Step, ±0.2 V, 9.99 kΩ load'),
    'unloaded_step_large': ('step', 0.5, None, 'Step, ±0.5 V, no load'),
    'loaded_step_large': ('step', 0.5, 9990, 'Step, ±0.5 V, 9.99 kΩ load'),
    'unloaded_sine_1hz_small': ('sine1', 0.2, None, 'Sine, 1 Hz, 0.2 V, no load'),
    'unloaded_sine_1hz_large': ('sine1', 0.8, None, 'Sine, 1 Hz, 0.8 V, no load'),
    'unloaded_sine_5hz_small': ('sine5', 0.15, None, 'Sine, 5 Hz, 0.15 V, no load'),
    'loaded_sine_5hz_small': ('sine5', 0.15, 9990, 'Sine, 5 Hz, 0.15 V, 9.99 kΩ load'),
}
BENCH_CHOICE = {
    'connect_output_load': 'connect the 9.99 kΩ output load',
    'disconnect_output_load': 'remove the 9.99 kΩ output load',
    'remove_output_load': 'remove the 9.99 kΩ output load',
}


def ts(s):
    return datetime.fromisoformat(s).timestamp()


def dec(a, k=2, nd=5):
    return [round(x, nd) for x in a[::k]]


def cost(u, r):
    cached = u.get('input_tokens_details', {}).get('cached_tokens', 0)
    return ((u['input_tokens'] - cached) * r['input'] + cached * r['cached_input']
            + u['output_tokens'] * r['output']) / 1e6


def env(e):
    """The evidence envelope kept for every rendered event."""
    return {'seq': e['sequence'], 'ts': e['timestamp'], 'kind': e['kind'],
            'sha256': e.get('sha256'), 'prev': e.get('previous_sha256')}


def elements_of(m):
    return [{'name': x['name'], 'kind': x['kind'], 'a': x['a'], 'b': x['b'], 'value': x.get('value'),
             'model': x.get('model')} for x in (m or {}).get('elements', [])]


def hyp(h):
    """One explanation row from component_hypotheses_fitted / structure_fit / verification models.
    Missing model (fit_error) is tolerated: no KeyError, no invented values."""
    changed = h.get('changed_component')
    els = elements_of(h.get('model'))
    val = kind = None
    if changed:
        for x in els:
            if x['name'] == changed:
                val, kind = x['value'], x['kind']
    checks = h.get('training_checks') or []
    return {
        'id': h['id'], 'changed': changed, 'value': val, 'kind': kind, 'status': h.get('status'),
        'error': h.get('error'),
        'miss_mV': [round(c['RMS_mV'], 2) for c in checks],
        'passed': [c['passed'] for c in checks],
        'regions': [regions_of(c) for c in checks],
        'decided_mV': [decided(c)[0] for c in checks],
        'worst_region': [decided(c)[1] for c in checks],
        'fitted_parameters': h.get('fitted_parameters'),
        'at_bound': h.get('parameter_at_bound'),
        'simulator_calls': h.get('simulator_calls'),
        'optimizer_converged': h.get('optimizer_converged'),
        'parameters_identifiable': h.get('parameters_identifiable'),
        'elements': els if h.get('id', '').startswith('proposal') else None,
        'diode': (h.get('model') or {}).get('diode') if h.get('id', '').startswith('proposal') else None,
    }


def regions_of(c):
    return [{'name': r['name'], 'samples': r.get('samples'), 'RMS_mV': round(r['RMS_mV'], 2), 'passed': r.get('passed')}
            for r in (c.get('regions') or [])]


def decided(c):
    """The number that decided pass/fail for one check: the worst of the whole-step RMS and every
    region RMS (the allowance applies to all of them). Returns (mV, region name or None)."""
    if c.get('RMS_mV') is None:
        return None, None
    best, name = round(c['RMS_mV'], 2), None
    for r in c.get('regions') or []:
        if r.get('RMS_mV') is not None and round(r['RMS_mV'], 2) > best:
            best, name = round(r['RMS_mV'], 2), r['name']
    return best, name


def check_against_design(design, rows, where):
    """Every explanation must name a part of this case's reviewed design. Anything else is an
    extractor error, never rendered silently."""
    names = {x['name'] for x in design or []}
    for r in rows:
        if r.get('changed') and r['changed'] not in names:
            sys.exit(f"{where}: explanation {r['id']} names {r['changed']!r}, which is not in the reviewed design {sorted(names)}")


def netlist_diff(before, after):
    """added / removed / reconnected between two element lists (by name)."""
    b = {x['name']: x for x in before or []}
    a = {x['name']: x for x in after or []}
    added = [a[n] for n in a if n not in b]
    removed = [b[n] for n in b if n not in a]
    recon = [a[n] for n in a if n in b and {a[n]['a'], a[n]['b']} != {b[n]['a'], b[n]['b']}]
    return {'added': added, 'removed': removed, 'reconnected': recon}


def classify(ev, result):
    """pilot / counted / unclassified, from run metadata only."""
    kinds = {e['kind'] for e in ev}
    started = next((e['payload'] for e in ev if e['kind'] == 'run_started'), {}) or {}
    cohort = None
    for e in ev:
        p = e.get('payload') or {}
        if e['kind'] in ('official_cohort_bound', 'official_cohort_binding', 'cohort_binding', 'reading_cohort_diagnosis_bound',
                         'restored_followup_registered', 'reading_pair_registered') or (isinstance(p, dict) and p.get('cohort_plan_id') and p.get('slot_id')):
            if isinstance(p, dict) and p.get('counted') is False:
                continue
            cohort = {'plan': p.get('cohort_plan_id') or p.get('cohort'), 'slot': p.get('slot_id') or p.get('run_id'),
                      'ordinal': p.get('ordinal') or p.get('attempt_ordinal') or p.get('attempt'),
                      'state': p.get('state'), 'seq': e['sequence'], 'official': p.get('official'), 'blind_test': p.get('blind_test')}
            break
    pilot_flags = []
    if 'pilot_protocol_frozen' in kinds:
        pilot_flags.append('event pilot_protocol_frozen')
    for e in ev:
        if e['kind'] == 'tool_result':
            r = (e.get('payload') or {}).get('result') or {}
            if isinstance(r, dict) and (r.get('pilot') or r.get('excluded_from_evaluation')):
                pilot_flags.append('tool_result pilot/excluded_from_evaluation')
                break
    if isinstance(result, dict) and (result.get('pilot') or result.get('excluded_from_evaluation')):
        pilot_flags.append('result.json pilot/excluded_from_evaluation')
    if cohort and not pilot_flags:
        label, public = 'Counted run', 'Official run'
        if cohort.get('plan') == 'reading-assisted-v1':
            label, public = 'Official run · reading-assisted cohort · known to developers, not blind', 'Official run · Spark did not know the fault'
        return {'pilot': False, 'counted': True, 'label': label, 'public_label': public, 'basis': 'official cohort binding before the first request', 'cohort': cohort}
    if pilot_flags:
        return {'pilot': True, 'counted': False, 'label': 'Pilot run — not counted', 'basis': '; '.join(sorted(set(pilot_flags))), 'cohort': cohort}
    return {'pilot': False, 'counted': False, 'label': 'Not counted (unclassified)', 'basis': 'no cohort binding and no pilot flag in the run metadata', 'cohort': None}


def equivalence_of(g):
    """An engine rule that splits one surviving explanation into electrically equivalent members.
    Members keep their id; words come from data, with a fallback from kind + nodes."""
    members = []
    for m in g.get('members') or []:
        words = m.get('words') or m.get('label')
        if not words and m.get('kind'):
            kw = {'R': 'an extra resistor', 'C': 'an extra capacitor', 'D': 'a diode', 'W': 'a wire'}.get(m['kind'], m['kind'])
            words = f"{kw} between {m.get('a')} and {m.get('b')}"
        members.append({'id': m.get('id'), 'label': m.get('label') or words, 'words': words, 'kind': m.get('kind'), 'a': m.get('a'), 'b': m.get('b')})
    return {'base_explanation': g.get('base_explanation') or g.get('base'), 'members': members,
            'source': g.get('source') or 'engine_rule', 'reason': g.get('reason')}


def extract(run_dir, case, label, intake, rates):
    ev = [json.loads(l) for l in open(run_dir / 'events.jsonl')]
    result = json.load(open(run_dir / 'result.json')) if (run_dir / 'result.json').exists() else {}
    t0 = ts(ev[0]['timestamp'])
    cls = classify(ev, result)
    run = {
        'id': run_dir.name, 'case': case, 'label': label,
        'pilot': cls['pilot'], 'counted': cls['counted'], 'classification': cls,
        'started_utc': ev[0]['timestamp'], 'ended_utc': ev[-1]['timestamp'],
        'model': result.get('model'), 'reasoning_effort': result.get('reasoning_effort'),
        'rates_usd_per_million': rates['rates'], 'rates_source': rates['source'],
        'design': None, 'reviewed_design_sha256': None, 'menu': None, 'allowance_mV': None, 'reserved': None,
        'instrument': None, 'schematic_read': intake, 'steps': [], 'verification': None,
        'structure': [], 'events': [], 'outcome': None, 'event_log': 'events.jsonl', 'event_count': len(ev),
        'first_sha256': ev[0].get('sha256'), 'last_sha256': ev[-1].get('sha256'),
    }
    steps, step = run['steps'], None
    play, last_t = 0.0, 0.0
    totals = {'spark_calls': 0, 'spark_cost': 0.0, 'captures': 0, 'guards_passed': 0,
              'guards_failed': 0, 'bench_changes': 0, 'sim_calls': 0, 'forecasts_frozen': 0}
    pending_calls = []  # api_response envelopes since the last tool call, folded into it

    def add(e, kind, **kw):
        nonlocal play, last_t
        t = ts(e['timestamp']) - t0
        dt = max(0.0, t - last_t)
        gap = None
        if dt > GAP_S:
            gap = round(dt, 1)
            dt = GAP_PLAY_S
        play += dt
        last_t = t
        item = {'t': round(t, 3), 'play': round(play, 3), 'kind': kind, 'ev': env(e), **kw}
        if gap:
            item['gap_real_s'] = gap
        item['totals'] = dict(totals)
        run['events'].append(item)
        return item

    def take_calls():
        c = list(pending_calls)
        pending_calls.clear()
        return c

    for e in ev:
        k, p = e['kind'], e['payload']
        if k == 'run_started':
            add(e, 'start')
        elif k == 'pilot_protocol_frozen':
            run['instrument'] = p.get('instrument')
            add(e, 'protocol', sha=p['protocol_sha256'][:10])
        elif k == 'netlist_v2_protocol':
            pol = p['policy']
            run['allowance_mV'] = pol.get('allowance_mV')
            run['whole_and_every_region'] = pol.get('whole_and_every_region')
            run['menu'] = list(pol['training_menu'])
            run['reserved'] = pol.get('reserved')
            run['max_proposals'] = pol.get('max_proposals')
            rd = p.get('reviewed_design')
            if isinstance(rd, dict) and 'elements' in rd:
                run['design'] = elements_of(rd)
            run['reviewed_design_sha256'] = p.get('reviewed_design_sha256')
            add(e, 'policy')
        elif k == 'api_response':
            totals['spark_calls'] += 1
            c = cost(p['usage'], rates['rates'])
            totals['spark_cost'] = round(totals['spark_cost'] + c, 6)
            pending_calls.append({'seconds': round(p.get('elapsed_s', 0), 1), 'cost': round(c, 6),
                                  'out_tokens': p['usage']['output_tokens'], 'in_tokens': p['usage']['input_tokens'],
                                  'reasoning_tokens': p['usage'].get('output_tokens_details', {}).get('reasoning_tokens'),
                                  'ev': env(e)})
            add(e, 'spark_call', n=totals['spark_calls'])
        elif k == 'tool_call' and p['name'] == 'inspect_experiment':
            add(e, 'inspect')  # its api_response folds into the next choice
        elif k == 'tool_call' and p['name'] == 'measure':
            a = json.loads(p['arguments'])
            kind, amp, load, text = ACTION.get(a['action'], ('other', None, None, a['action']))
            step = {'n': len(steps) + 1, 'action': a['action'], 'label': text, 'reason': a.get('reason'),
                    'chosen_utc': e['timestamp'], 'kind': kind, 'amplitude_v': amp, 'load_ohm': load,
                    'forecast_sha': None, 'forecasts': [], 'observation': None, 'fit': None,
                    'guard_failed': None, 'ev': env(e)}
            steps.append(step)
            add(e, 'choose', step=step['n'], action=a['action'], label=text, reason=a.get('reason'), calls=take_calls())
        elif k == 'training_forecasts_frozen' and step:
            step['forecast_sha'] = p['sha256'][:10]
            step['forecast_sha_full'] = p['sha256']
            step['settings'] = p.get('settings')
            step['forecasts'] = [{'id': m['id'], 'v': dec(m['command_forecast_v'])} for m in p['models']]
            totals['forecasts_frozen'] += 1
            add(e, 'forecast', step=step['n'], sha=p['sha256'][:10], sha_full=p['sha256'], models=[m['id'] for m in p['models']])
        elif k == 'operator_action_requested':
            totals['bench_changes'] += 1
            add(e, 'bench_request', step=step and step['n'],
                text=BENCH_CHOICE.get(p['choice'], p['choice'].replace('_', ' ')),
                detail=p.get('instruction'), fixture=p.get('fixture'))
        elif k == 'operator_wiring_confirmation':
            add(e, 'bench_done', text=p.get('verbatim'), fixture=p.get('fixture'), choice=p.get('choice'))
        elif k.endswith('_raw_capture'):
            totals['captures'] += 1
            add(e, 'capture', label=k.replace('_raw_capture', ''))
        elif k == 'physical_electrical_guard':
            ok = all(p['checks'].values())
            totals['guards_passed' if ok else 'guards_failed'] += 1
            failed = [c for c, v in p['checks'].items() if not v]
            add(e, 'guard', label=p['label'], ok=ok, failed=failed)
            if not ok and step:
                step['guard_failed'] = {'label': p['label'], 'failed': failed}
        elif k == 'netlist_observation' and step is None and run.get('verification') is not None:
            d = p['input_template']['data']
            v = run['verification']; v.setdefault('observations', [])
            v['observations'].append({'index': len(v['observations']) + 1, 't_s': dec(d['frame_time_s'], nd=6),
                                      'in_v': dec(d['input_minus_ref_v']), 'out_v': dec(p['output_minus_ref_v']),
                                      'all_guards_passed': p.get('all_guards_passed'), 'ev': env(e)})
            add(e, 'verification_observed', index=len(v['observations']))
        elif k == 'netlist_observation' and step:
            d = p['input_template']['data']
            step['observation'] = {'t_s': dec(d['frame_time_s'], nd=6), 'in_v': dec(d['input_minus_ref_v']),
                                   'out_v': dec(p['output_minus_ref_v']),
                                   'all_guards_passed': p['all_guards_passed'], 'ev': env(e)}
            add(e, 'observe', step=step['n'])
        elif k == 'component_hypotheses_fitted' and step:
            totals['sim_calls'] += int(p.get('simulator_calls') or 0)
            step['fit'] = [hyp(h) for h in p['hypotheses']]
            check_against_design(run['design'], step['fit'], f"step {step['n']} component_hypotheses_fitted")
            step['sim_calls'] = p.get('simulator_calls')
            step['all_inadequate'] = p.get('all_inadequate')
            step['fit_ev'] = env(e)
            add(e, 'fit', step=step['n'], all_inadequate=p.get('all_inadequate'))
        # ---- structure proposals (contract §2)
        elif k == 'structure_proposed':
            prop = {'id': p['id'], 'elements': elements_of(p), 'rationale': p.get('rationale'),
                    'topology_sha256': p.get('topology_sha256'), 'selected_by': p.get('selected_by'),
                    'after_step': step and step['n'], 'ev': env(e), 'fit': None}
            prop['diff'] = netlist_diff(run['design'], prop['elements'])
            run['structure'].append(prop)
            add(e, 'structure_proposed', id=p['id'], diff=prop['diff'], elements=prop['elements'],
                rationale=p.get('rationale'), selected_by=p.get('selected_by'))
        elif k == 'structure_fit':
            row = hyp(p)
            totals['sim_calls'] += int(p.get('simulator_calls') or 0)
            prop = next((x for x in run['structure'] if x['id'] == p.get('id')), None)
            if prop:
                prop['fit'] = row
            add(e, 'structure_fit', id=p.get('id'), status=row['status'], error=row.get('error'),
                miss_mV=row['miss_mV'][-1] if row['miss_mV'] else None, misses=row['miss_mV'],
                passed=row['passed'], fitted_parameters=row['fitted_parameters'],
                simulator_calls=p.get('simulator_calls'), elements=row['elements'])
        # ---- verification chain
        elif k == 'tool_call' and p['name'] == 'verify_prediction':
            run['verification'] = {'ev': env(e)}
            step = None
            add(e, 'verify_request', calls=take_calls())
        elif k == 'verification_forecast_frozen':
            run['verification'] = run.get('verification') or {}
            run['verification'].update({
                'sha': p['sha256'][:10], 'sha_full': p['sha256'],
                'models': [hyp(m) for m in p['models']],
                'reserved': p['policy']['reserved'],
                'forecasts': [{mid: dec(vals) for mid, vals in cf.items()} for cf in p['command_forecasts']],
                'frozen_ev': env(e),
            })
            totals['forecasts_frozen'] += 1
            add(e, 'final_forecast', sha=p['sha256'][:10], sha_full=p['sha256'], ids=[m['id'] for m in p['models']])
        elif k == 'verification_publication':
            run['verification'].update({'published': p['published'], 'commit': p['commit'], 'url': p['url'],
                                        'published_utc': e['timestamp'], 'publish_ev': env(e)})
            add(e, 'publish', commit=p['commit'][:7], commit_full=p['commit'], url=p['url'])
        elif k == 'reserved_prediction_scored':
            # contract: {prediction_sha256, settings, conditional{id: check}, command_forecast, OUT_refitted};
            # the reserved input's index is its order in the run (the engine scores them in RESERVED order)
            cond = p.get('conditional') or {}
            scored = {}
            for mid, v in cond.items():
                if not isinstance(v, dict):
                    scored[mid] = {'RMS_mV': None, 'passed': None, 'regions': [], 'decided_mV': None, 'worst_region': None}
                    continue
                dm, wr = decided(v)
                scored[mid] = {'RMS_mV': round(v['RMS_mV'], 2) if v.get('RMS_mV') is not None else None,
                               'passed': v.get('passed'), 'regions': regions_of(v), 'decided_mV': dm, 'worst_region': wr}
            sc = run['verification'].setdefault('scored', [])
            idx = p.get('index') or p.get('reserved_index') or len(sc) + 1
            sc.append({'index': idx, 'settings': p.get('settings'), 'conditional': scored,
                       'OUT_refitted': p.get('OUT_refitted'), 'prediction_sha256': p.get('prediction_sha256'), 'ev': env(e)})
            add(e, 'verification_scored', index=idx, settings=p.get('settings'), conditional=scored, OUT_refitted=p.get('OUT_refitted'))
        elif k == 'netlist_verification_completed':
            run['verification']['survivors'] = p.get('survivors')
            run['verification']['completed_ev'] = env(e)
            add(e, 'verification_completed', survivors=p.get('survivors'))
        elif k == 'agent_report':
            run['outcome'] = {'kind': 'report', 'verdict': p.get('verdict'), 'components': p.get('components'),
                              'survivors': p.get('survivors') or (run.get('verification') or {}).get('survivors'),
                              'text': p.get('summary') or p.get('text'), 'ev': env(e)}
            add(e, 'report', verdict=p.get('verdict'), components=p.get('components'), survivors=run['outcome']['survivors'], text=run['outcome']['text'])
        # ---- the reading stage (one operator reading, forecast per explanation and per source, frozen first)
        elif k == 'reading_requested':
            rd = run.setdefault('reading', {})
            rd.update({'component': p.get('component'), 'quantity': p.get('quantity'), 'reason': p.get('reason'),
                       'chosen_by': p.get('chosen_by'), 'request_ev': env(e), 'bands': [], 'binding': None, 'observed': None, 'scored': None})
            add(e, 'reading_requested', component=p.get('component'), quantity=p.get('quantity'), reason=p.get('reason'),
                chosen_by=p.get('chosen_by'), calls=take_calls())
        elif k == 'equivalence_group':
            rd = run.setdefault('reading', {'bands': []})
            g = equivalence_of(p)
            rd.setdefault('groups', []).append({**g, 'ev': env(e)})
            add(e, 'equivalence_group', **g)
        elif k == 'reading_forecast_frozen':
            rd = run.setdefault('reading', {'bands': []})
            for g in (p.get('equivalence_groups') or ([p['equivalence_group']] if p.get('equivalence_group') else [])):
                g = equivalence_of(g)
                rd.setdefault('groups', []).append({**g, 'ev': env(e)})
                add(e, 'equivalence_group', **g)
            bands = p.get('bands') or p.get('forecasts') or p.get('models') or []
            rd['bands'] = [{'explanation': b.get('explanation') or b.get('id'), 'source': b.get('source'), 'low': b.get('low'), 'high': b.get('high'),
                            'unit': b.get('unit'), 'rule': b.get('rule'), 'note': b.get('note')} for b in bands]
            rd['sha'] = (p.get('sha256') or '')[:10]; rd['sha_full'] = p.get('sha256'); rd['frozen_ev'] = env(e)
            rd['published'] = p.get('published'); rd['commit'] = p.get('commit'); rd['url'] = p.get('url')
            totals['forecasts_frozen'] += 1
            add(e, 'reading_forecast_frozen', bands=rd['bands'], sha=rd['sha'], sha_full=rd['sha_full'], commit=p.get('commit'), url=p.get('url'))
        elif k == 'body_binding':
            rd = run.setdefault('reading', {'bands': []})
            rd['binding'] = {'sam_body': p.get('sam_body'), 'component': p.get('component'), 'chosen_by': p.get('chosen_by'),
                             'reason': p.get('reason'), 'operator_confirmed': p.get('operator_confirmed'), 'overlay_file': p.get('overlay_file'),
                             'photo': p.get('photo'), 'ev': env(e)}
            add(e, 'body_binding', **{a: b for a, b in rd['binding'].items() if a != 'ev'})
        elif k == 'reading_observed':
            rd = run.setdefault('reading', {'bands': []})
            rd['observed'] = {'component': p.get('component'), 'value': p.get('value'), 'unit': p.get('unit'), 'source': p.get('source'),
                              'photo': p.get('photo'), 'ev': env(e)}
            add(e, 'reading_observed', **{a: b for a, b in rd['observed'].items() if a != 'ev'})
        elif k == 'reading_scored':
            rd = run.setdefault('reading', {'bands': []})
            src = (rd.get('observed') or {}).get('source')
            if not any(b.get('source') == src for b in rd['bands']):
                sys.exit(f"reading_scored for source {src!r} but no frozen band for that source: refusing to render a score without its forecast")
            fits = p.get('fits') or []
            rd['scored'] = {'fits': fits, 'ev': env(e)}
            rd['outcome'] = 'one' if len(fits) == 1 else ('none' if not fits else 'several')
            add(e, 'reading_scored', fits=fits, outcome=rd['outcome'])
        elif k == 'probe_path_declared':
            run['probe_path'] = p.get('text') or p
            add(e, 'probe_path', text=p.get('text'))
        elif k == 'run_failed':
            run['outcome'] = {'kind': 'stopped', 'reason': p.get('error'), 'ev': env(e)}
            add(e, 'stop', reason=p.get('error'))
        elif k in ('run_completed',):
            run['outcome'] = run['outcome'] or {'kind': 'completed', 'ev': env(e)}
            add(e, 'end')
    run['totals'] = totals
    run['play_length_s'] = round(play, 2)
    return run


def timeline(run):
    """Ordered events {t_log, t_play, kind, ev, ...} the replay plays. Nothing is recomputed."""
    out = []
    steps = {s['n']: s for s in run['steps']}
    dead = {}

    def put(e, kind, **kw):
        out.append({'t_log': e['t'], 't_play': e['play'], 'kind': kind, 'totals': e.get('totals'), 'ev': e.get('ev'), **kw})

    for e in run['events']:
        k = e['kind']
        if k == 'choose':
            put(e, 'spark_choice', step=e['step'], action=e['action'], label=e['label'], reason=e.get('reason'), calls=e.get('calls') or [])
        elif k == 'forecast':
            st = steps[e['step']]
            put(e, 'forecast_frozen', step=e['step'], sha=e['sha'], sha_full=e.get('sha_full'), ids=[f['id'] for f in st['forecasts']])
        elif k == 'bench_request':
            put(e, 'bench_request', step=e.get('step'), text=e.get('text'), detail=e.get('detail'), fixture=e.get('fixture'))
        elif k == 'bench_done':
            put(e, 'operator_confirm', text=e.get('text'), fixture=e.get('fixture'), gap_real_s=e.get('gap_real_s'))
        elif k == 'capture' and re.fullmatch(r'(training|verification)_\d+', e['label']):
            n = int(e['label'].split('_')[1])
            put(e, 'capture', step=n, label=e['label'], verification=e['label'].startswith('verification'))
        elif k == 'guard' and not e['ok']:
            put(e, 'guard_stop', label=e['label'], failed=e['failed'])
        elif k == 'fit':
            st = steps[e['step']]
            res = [{'id': f['id'], 'miss_mV': f['miss_mV'][-1] if f['miss_mV'] else None,
                    'decided_mV': f['decided_mV'][-1] if f.get('decided_mV') else (f['miss_mV'][-1] if f['miss_mV'] else None),
                    'worst_region': f['worst_region'][-1] if f.get('worst_region') else None,
                    'regions': f['regions'][-1] if f['regions'] else [],
                    'passed_this_step': f['passed'][-1] if f['passed'] else None,
                    'adequate': f['status'] == 'adequate', 'status': f['status'], 'error': f.get('error'),
                    'value': f['value'], 'kind': f['kind'], 'changed': f['changed'], 'at_bound': f.get('at_bound')} for f in st['fit']]
            put(e, 'fit_result', step=e['step'], results=res, all_inadequate=e.get('all_inadequate'), sim_calls=st.get('sim_calls'))
            for r in res:
                if not r['adequate'] and r['id'] not in dead:
                    dead[r['id']] = e['step']
                    put(e, 'ruled_out', step=e['step'], id=r['id'], miss_mV=r['miss_mV'])
        elif k == 'structure_proposed':
            put(e, 'structure_proposed', id=e['id'], diff=e['diff'], elements=e['elements'], rationale=e.get('rationale'), selected_by=e.get('selected_by'))
        elif k == 'structure_fit':
            put(e, 'structure_fit', **{a: b for a, b in e.items() if a not in ('t', 'play', 'kind', 'totals', 'ev')})
        elif k == 'verify_request':
            put(e, 'verification_requested', calls=e.get('calls') or [])
        elif k == 'final_forecast':
            put(e, 'forecast_frozen', step='verification', sha=e['sha'], sha_full=e.get('sha_full'), ids=e.get('ids') or [], final=True)
        elif k == 'publish':
            put(e, 'verification_published', commit=e['commit'], commit_full=e.get('commit_full'), url=e['url'])
        elif k == 'verification_observed':
            put(e, 'verification_observed', index=e.get('index'))
        elif k == 'verification_scored':
            put(e, 'verification_scored', index=e.get('index'), settings=e.get('settings'), conditional=e.get('conditional'), OUT_refitted=e.get('OUT_refitted'))
        elif k == 'verification_completed':
            put(e, 'verification_completed', survivors=e.get('survivors'))
        elif k == 'report':
            put(e, 'report', verdict=e.get('verdict'), components=e.get('components'), survivors=e.get('survivors'), text=e.get('text'))
        elif k == 'probe_path':
            put(e, 'probe_path', text=e.get('text'))
        elif k in ('equivalence_group', 'reading_requested', 'reading_forecast_frozen', 'body_binding', 'reading_observed', 'reading_scored'):
            put(e, k, **{a: b for a, b in e.items() if a not in ('t', 'play', 'kind', 'totals', 'ev')})
            if k == 'reading_scored':  # explanations the reading ruled out, in the same order as the fit stage
                rd = run.get('reading') or {}
                src = (rd.get('observed') or {}).get('source')
                live = [b['explanation'] for b in rd.get('bands', []) if b.get('source') == src]
                for x in live:
                    if x not in (e.get('fits') or []) and x not in dead:
                        dead[x] = 'reading'
                        put(e, 'ruled_out_by_reading', id=x)
        elif k == 'stop':
            put(e, 'stopped', reason=e.get('reason'))
        elif k == 'end':
            put(e, 'ended')
    return out


def load_photo(root, render):
    """Contract §3: root result.json -> vision/<run>/result.json; render dir -> <concept>-decoded.json."""
    root = pathlib.Path(root)
    out = {'root': str(root), 'vision': None, 'sam': [], 'image': None, 'pairing': 'not paired'}
    res = json.load(open(root / 'result.json'))
    plan = json.load(open(root / 'plan.json')) if (root / 'plan.json').exists() else {}
    img = plan.get('image') or {}
    out['image'] = {'file': str(root / 'input.png'), 'width': img.get('width'), 'height': img.get('height'), 'sha256': img.get('sha256')}
    for o in res.get('outcomes', []):
        if o.get('task', '').startswith('vision') or 'vision' in o.get('run', ''):
            vr = json.load(open(root / o['run'] / 'result.json'))
            cand = vr.get('candidate') or {}
            comps = []
            for c in cand.get('components', []):
                unreadable = c.get('kind') in ('R', 'C') and c.get('value_si') is None
                comps.append({**{k: c.get(k) for k in ('name', 'kind', 'a', 'b', 'value_si', 'marking', 'evidence', 'bbox')},
                              'reading_status': 'unreadable' if unreadable else ('read' if c.get('value_si') is not None else 'not applicable')})
            out['vision'] = {'run': o['run'], 'status': vr.get('status'), 'candidate_status': cand.get('status'),
                             'summary': cand.get('summary'), 'ambiguities': cand.get('ambiguities'), 'components': comps,
                             'requests': vr.get('requests')}
    if render:
        for f in sorted(pathlib.Path(render).glob('*-decoded.json')):
            d = json.load(open(f))
            out['sam'].append({'concept': f.name.replace('-decoded.json', ''), 'match_count': d.get('match_count', len(d.get('masks', []))),
                               'masks': [{k: m.get(k) for k in ('object_id', 'bounds_half_open', 'confidence', 'overlay_file', 'source_mask_file', 'resize_to_box')} for m in d.get('masks', [])]})
    return out


def intake_from_pair(pair, rates):
    """The fresh schematic read of a reading-assisted pair: schematic-intake/<run>/result.json + plan.json."""
    d = sorted((pair / 'schematic-intake').iterdir())[0]
    r = json.load(open(d / 'result.json'))
    m = re.match(r'(\d{8})T(\d{6})', d.name)
    return {'run': d.name, 'utc': datetime.strptime(m.group(1) + m.group(2), '%Y%m%d%H%M%S').isoformat() + '+00:00',
            'requests': r.get('requests'), 'cost': round(cost(r['usage'], rates['rates']), 6), 'out_tokens': r['usage']['output_tokens'],
            'summary': r['candidate'].get('summary'),
            'components': [{'name': c['name'], 'kind': c['kind'], 'nodes': c['nodes'], 'marking': c.get('marking'), 'bbox': c.get('bbox'),
                            'evidence': c.get('evidence')} for c in r['candidate']['components']]}


def extract_pair(pair, case, label, rates, photos):
    """Reading-assisted cohort layout (Codex, 11/3): a pair folder with a parent events.jsonl and children.
    The faulted diagnosis child is a normal v2 run; the reading stage lives in the parent events and JSON files.
    Output: one run JSON for the fault + reading story, through the seal reveal. The parent's failed restored
    child is not rendered (repository record only); the restored rerun comes from the follow-up record."""
    pair = pathlib.Path(pair)
    child = sorted((pair / 'diagnosis-faulted').iterdir())[0]
    intake = intake_from_pair(pair, rates)
    run = extract(child, case, label, intake, rates)
    run['pair_dir'] = pair.name
    run['id'] = pair.name  # the pair id is the public record id; the child id stays in child_id
    run['child_id'] = child.name
    pev = [json.loads(l) for l in open(pair / 'events.jsonl')]
    reg = json.load(open(pair / 'registration.json'))
    run['registration'] = {k: reg.get(k) for k in ('cohort', 'attempt', 'official', 'counted', 'selected_first_attempt', 'freeze_commit', 'blind_test', 'known_case_development')}
    run['pilot'], run['counted'] = False, bool(reg.get('counted'))
    run['classification'] = {'pilot': False, 'counted': run['counted'], 'label': 'Official run · reading-assisted cohort · known to developers, not blind',
                             'public_label': 'Official run · Spark did not know the fault',
                             'basis': 'pair registration committed before the first request (registration.json)', 'cohort': {'plan': reg.get('cohort'), 'slot': reg.get('run_id'), 'ordinal': reg.get('attempt'), 'state': 'faulted'}}
    t0 = ts(run['started_utc'])
    totals = dict(run['totals'])
    play, last_t = run['play_length_s'], max((e['t'] for e in run['events']), default=0.0)
    # seal: the hidden fault was committed before the diagnosis; copy only the fact and the digest, never the truth before the reveal
    sealed = next((e for e in pev if e['kind'] == 'specimen_assembly_sealed' and e['payload'].get('state') == 'faulted'), None)
    if sealed:
        run['seal'] = {'sealed_sha256': sealed['payload']['sha256'], 'transmitted_to_model': sealed['payload'].get('transmitted_to_model'), 'sealed_ev': env(sealed)}

    def add(e, kind, **kw):
        nonlocal play, last_t
        t = ts(e['timestamp']) - t0
        dt = max(0.0, t - last_t)
        gap = None
        if dt > GAP_S:
            gap = round(dt, 1); dt = GAP_PLAY_S
        play += dt; last_t = t
        item = {'t': round(t, 3), 'play': round(play, 3), 'kind': kind, 'ev': env(e), **kw}
        if gap:
            item['gap_real_s'] = gap
        item['totals'] = dict(totals)
        run['events'].append(item)
        return item

    catalog = json.load(open(pair / 'reading-catalog.json'))
    fc = json.load(open(pair / 'reading-forecast.json'))
    obs = json.load(open(pair / 'reading-observation.json'))
    score = json.load(open(pair / 'reading-score.json'))
    sel_dir = sorted((pair / 'reading-selection').iterdir())[0]
    sel = json.load(open(sel_dir / 'result.json'))
    photo_stage = json.load(open(pair / 'photo-faulted' / 'stage-summary.json'))
    manifest = json.load(open(pair / 'photo-faulted' / 'decoded' / 'body-manifest.json'))
    rd = run.setdefault('reading', {'bands': [], 'binding': None, 'observed': None, 'scored': None})
    for e in pev:
        k, p = e['kind'], e['payload']
        if k == 'reading_catalog_generated':
            base = next((x for x in catalog['explanations'] if not x['id'].startswith('external_equivalent')), None)
            members = []
            for x in catalog['explanations']:
                if x['id'].startswith('external_equivalent:'):
                    comp = x['id'].split(':')[-1]
                    members.append({'id': x['id'], 'label': f'an extra resistor between IN and {comp}', 'words': f'an extra resistor between IN and {comp}',
                                    'kind': 'R', 'a': 'IN', 'b': comp, 'description': x.get('description')})
            g = {'base_explanation': base['id'] if base else None, 'members': members, 'source': 'engine_rule',
                 'reason': 'Generated by the engine from the verified terminal model: the same waveforms at the terminals, so the measurement cannot separate them.',
                 'ev': env(e), 'catalog_sha256': p.get('sha256')}
            rd.setdefault('groups', []).append(g)
            add(e, 'equivalence_group', **{a: b for a, b in g.items() if a != 'ev'})
        elif k == 'reading_requested':
            u = sel.get('usage') or {}
            c = round(cost(u, rates['rates']), 6) if u else None
            if u:
                totals['spark_calls'] += 1; totals['spark_cost'] = round(totals['spark_cost'] + c, 6)
            rd.update({'component': p['component'], 'quantity': p['quantity'], 'reason': p['reason'], 'chosen_by': p['chosen_by'], 'request_ev': env(e)})
            add(e, 'reading_requested', component=p['component'], quantity=p['quantity'], reason=p['reason'], chosen_by=p['chosen_by'],
                calls=[{'seconds': None, 'cost': c, 'out_tokens': u.get('output_tokens'), 'in_tokens': u.get('input_tokens'),
                        'reasoning_tokens': (u.get('output_tokens_details') or {}).get('reasoning_tokens'), 'role': 'chose the reading', 'ev': env(e)}] if u else [])
        elif k == 'reading_forecast_frozen':
            bands = []
            mr = obs.get('meter_range')
            for b in fc['forecasts']:
                rule = b.get('rule') or {}
                low, high, note = b.get('low'), b.get('high'), None
                rng = next((x for x in rule.get('intervals_by_meter_range', []) if x['meter_range'] == mr), None)
                if b['source'] == 'operator_dmm' and rng:
                    low, high = rng['low'], rng['high']
                    rtext = f"fitted value's training envelope (every grid point whose waveforms stay within 9 mV) plus the meter's allowance on the {int(mr/1000)} kΩ range"
                    if rule.get('nominal_rule') or (b['explanation'].startswith('external')):
                        rtext = f"drawn value ± 5 % part tolerance plus the meter's allowance on the {int(mr/1000)} kΩ range"
                else:
                    rtext = ('printed nominal value only; a part whose actual value changed can keep its old label, so this band is open'
                             if rule.get('printed_value_unconstrained') else 'printed nominal value ± 5 % part tolerance')
                    if rule.get('actual_value_not_measured'):
                        note = 'A marking confirms the nominal value, not the resistance today.'
                unit = b.get('unit')
                if unit == 'ohm' and (fc['request'].get('quantity') == 'resistance'):
                    low = None if low is None else round(low / 1000.0, 2); high = None if high is None else round(high / 1000.0, 2); unit = 'kΩ'
                    env_lo = None if b.get('low') is None else round(b['low'] / 1000.0, 2); env_hi = None if b.get('high') is None else round(b['high'] / 1000.0, 2)
                else:
                    env_lo, env_hi = b.get('low'), b.get('high')
                bands.append({'explanation': b['explanation'], 'source': b['source'], 'low': low, 'high': high, 'unit': unit,
                              'observable': b.get('observable'), 'rule': rtext, 'note': note,
                              'envelope': {'low': env_lo, 'high': env_hi, 'note': 'range-independent envelope'}, 'meter_range': mr if b['source'] == 'operator_dmm' else None,
                              'rule_raw': {kk: vv for kk, vv in rule.items() if kk != 'electrical_interval_rule'}})
            rd['bands'] = bands
            rd['sha'] = p['sha256'][:10] if p.get('sha256') else fc.get('sha256', '')[:10]
            rd['sha_full'] = p.get('sha256'); rd['frozen_ev'] = env(e)
            totals['forecasts_frozen'] += 1
            add(e, 'reading_forecast_frozen', bands=bands, sha=rd['sha'], sha_full=rd['sha_full'])
        elif k == 'reading_forecast_publication':
            rd.update({'published': p.get('published'), 'commit': p.get('commit'), 'url': p.get('url'), 'publish_ev': env(e)})
            rd['sha_full'] = rd.get('sha_full') or p.get('sha256'); rd['sha'] = (rd['sha_full'] or '')[:10]
            add(e, 'reading_forecast_published', commit=p.get('commit'), url=p.get('url'), sha=rd['sha'])
        elif k == 'board_photo_received':
            add(e, 'board_photo', sha256=p.get('sha256'), new_capture=p.get('new_capture_operator_confirmed'))
        elif k == 'sam_localization_finished':
            totals['sam_calls'] = totals.get('sam_calls', 0) + int(p.get('requests') or 0)
            totals['sam_cost'] = round(totals.get('sam_cost', 0.0) + float(photo_stage.get('SAM_estimated_usd') or 0.0), 6)
            add(e, 'sam_done', requests=p.get('requests'), masks=photo_stage.get('SAM_native_mask_count'), bodies=photo_stage.get('retained_body_count'))
        elif k == 'body_binding':
            c = float(photo_stage.get('binding_estimated_usd') or 0.0)
            totals['spark_calls'] += int(photo_stage.get('Spark_binding_requests') or 0); totals['spark_cost'] = round(totals['spark_cost'] + c, 6)
            comp = next((x for x in manifest['components'] if x['id'] == p['sam_body']), {})
            nat = comp.get('native_object') or {}
            rd['binding'] = {'sam_body': p['sam_body'], 'component': p['component'], 'chosen_by': p['chosen_by'], 'reason': p['reason'],
                             'operator_confirmed': p['operator_confirmed'], 'localizer': p.get('localizer'),
                             'photo': photos.get('crop_r1') or photos.get('board'), 'overlay_file': None,
                             'crop_box': photos.get('crop_box'), 'bounds': nat.get('bounds_half_open'), 'confidence': nat.get('confidence'),
                             'input_image_sha256': nat.get('input_image_sha256'), 'bodies': photo_stage.get('retained_body_count'),
                             'calls': [{'cost': round(c, 6), 'role': 'pointed at the body', 'ev': env(e)}], 'ev': env(e)}
            add(e, 'body_binding', **{a: b for a, b in rd['binding'].items() if a != 'ev'})
        elif k == 'reading_observed':
            unit = {'kohm': 'kΩ', 'ohm': 'Ω', 'uF': 'µF', 'nF': 'nF'}.get(p['unit'], p['unit'])
            rd['observed'] = {'component': p['component'], 'value': p['value'], 'unit': unit, 'source': p['source'],
                              'note': 'power off, both leads lifted' if p.get('component_isolated_confirmed') else None,
                              'power_off': p.get('power_off_confirmed'), 'isolated': p.get('component_isolated_confirmed'),
                              'meter_range': p.get('meter_range'), 'photo': None, 'evidence_link': photos.get('evidence'),
                              'evidence_sha256': (p.get('photo') or {}).get('sha256'), 'ev': env(e)}
            add(e, 'reading_observed', **{a: b for a, b in rd['observed'].items() if a != 'ev'})
        elif k == 'reading_scored':
            src = rd['observed']['source']
            if not any(b['source'] == src for b in rd['bands']):
                sys.exit('reading_scored without a frozen band for the reported source')
            rd['scored'] = {'fits': p['fits'], 'ruled_out': p.get('ruled_out_by_reading') or [], 'outcome_raw': p.get('outcome'),
                            'forecast_sha256': p.get('forecast_sha256'), 'observation_sha256': p.get('observation_sha256'), 'refitted': p.get('refitted'), 'ev': env(e)}
            rd['outcome'] = {'one_explanation_remains': 'one', 'indistinguishable': 'several', 'all_explanations_rejected': 'none'}.get(p.get('outcome'), 'one' if len(p['fits']) == 1 else ('none' if not p['fits'] else 'several'))
            add(e, 'reading_scored', fits=p['fits'], ruled_out=rd['scored']['ruled_out'], outcome=rd['outcome'])
        elif k == 'specimen_seal_opened':
            a = p.get('assembly') or {}
            truth = [{'component': x.get('component'), 'kind': x.get('kind'), 'value_nominal_ohm': x.get('value_nominal_ohm'),
                      'value_nominal_F': x.get('value_nominal_F'), 'location': x.get('location')} for x in a.get('specimen_truth', [])]
            run['seal'] = {**(run.get('seal') or {}), 'opened_ev': env(e), 'sealed_sha256_at_open': p.get('sealed_sha256'),
                           'matches_commitment': p.get('sealed_sha256') == (run.get('seal') or {}).get('sealed_sha256'), 'truth': truth}
            run['outcome'] = {'kind': 'report', 'verdict': (run.get('outcome') or {}).get('verdict'), 'components': (run.get('outcome') or {}).get('components'),
                              'survivors': p and rd['scored']['fits'], 'text': (run.get('outcome') or {}).get('text'), 'ev': (run.get('outcome') or {}).get('ev'),
                              'seal_opened': True, 'found': rd['scored']['fits']}
            add(e, 'seal_opened', truth=truth, matches=run['seal']['matches_commitment'])
            break  # the public story ends at the reveal; the restored stage is a separate record
    run['totals'] = totals
    run['play_length_s'] = round(play, 2)
    run['photo'] = {'board': photos.get('board'), 'crop': photos.get('crop'), 'crop_full': photos.get('crop_full'), 'crop_r1': photos.get('crop_r1'),
                    'crop_box': photos.get('crop_box'), 'crop_full_box': photos.get('crop_full_box'),
                    'image': {'file': photos.get('crop_r1') or photos.get('board'), 'width': 1200, 'height': 1600, 'sha256_sam_input': (rd.get('binding') or {}).get('input_image_sha256')},
                    'sam': [{'concept': 'electronic component', 'match_count': photo_stage.get('SAM_native_mask_count'),
                             'masks': [{'object_id': '1', 'bounds_half_open': (rd.get('binding') or {}).get('bounds'), 'confidence': (rd.get('binding') or {}).get('confidence'),
                                        'overlay_file': None, 'source_mask_file': 'electronic component-object-1-record-1-mask.png', 'resize_to_box': False}]}],
                    'vision': None, 'pairing': 'Spark pointed at sam-1 as R1; confirmed by the operator',
                    'note': 'Photo untouched; the outline is the boundary of the native SAM 3.1 mask.'}
    return run


def extract_followup(rec, case, label, rates, pair_of):
    """Restored rerun from a follow-up record (Codex layout): a normal v2 run with a registration."""
    rec = pathlib.Path(rec)
    reg = json.load(open(rec / 'registration.json'))
    orig = rec / 'history' / 'original'
    intake = intake_from_pair(orig, rates) if (orig / 'schematic-intake').exists() else None
    run = extract(rec, case, label, intake, rates)
    run['pilot'], run['counted'] = False, bool(reg.get('counted'))
    run['classification'] = {'pilot': False, 'counted': run['counted'], 'label': 'Official run · reading-assisted cohort · known to developers, not blind',
                             'public_label': 'Official run · Spark did not know the fault',
                             'basis': 'follow-up registration committed before the first request (registration.json)',
                             'cohort': {'plan': reg.get('cohort'), 'slot': reg.get('run_id'), 'ordinal': reg.get('attempt_ordinal'), 'state': reg.get('state')}}
    run['pair'] = {'of': pair_of, 'operator_restored': True, 'state': 'restored'}
    res = json.load(open(rec / 'result.json')) if (rec / 'result.json').exists() else {}
    run['display_caption'] = res.get('display_caption') or 'No mismatch in the tests Spark chose'
    vt = rec / 'verification.txt'
    if vt.exists():
        run['verify_output'] = vt.read_text().strip()
    return run


def timeline_pair(run):
    """Timeline for a pair run: the v2 timeline plus the reading-stage events the pair extractor adds.
    The diagnosis child's report comes BEFORE the reading, so it is shown as Spark's report after the
    measurements (not the end); the end scene is the seal opening, after the reading is scored."""
    out = timeline(run)
    has_seal = any(e['kind'] == 'seal_opened' for e in run['events'])
    if has_seal:
        out = [x for x in out if x['kind'] != 'ended']
        for x in out:
            if x['kind'] == 'report':
                x['kind'] = 'spark_report'
    seen = {(x['ev'] or {}).get('seq') for x in out if x.get('ev')}
    extra = []
    for e in run['events']:
        if e['kind'] in ('reading_forecast_published', 'board_photo', 'sam_done', 'seal_opened') and e['ev']['seq'] not in seen:
            item = {'t_log': e['t'], 't_play': e['play'], 'kind': e['kind'], 'totals': e.get('totals'), 'ev': e.get('ev'),
                    **{a: b for a, b in e.items() if a not in ('t', 'play', 'kind', 'totals', 'ev')}}
            if e['kind'] == 'seal_opened':
                o = run.get('outcome') or {}
                item.update({'verdict': o.get('verdict'), 'components': o.get('components'), 'survivors': o.get('survivors'), 'text': None})
            extra.append(item)
    out = sorted(out + extra, key=lambda x: (x['t_play'], x['ev']['seq'] if x.get('ev') else 0))
    return out


def convert(path):
    path = pathlib.Path(path)
    run = json.loads(path.read_text())
    run['timeline'] = timeline(run)
    path.write_text(json.dumps(run, ensure_ascii=False, separators=(',', ':')))
    print(path.name, len(run['timeline']), 'timeline events')


def write_run(run, case, label, pair_of=None):
    out = SITE / 'data' / 'runs'
    out.mkdir(parents=True, exist_ok=True)
    (out / f"{run['id']}.json").write_text(json.dumps(run, ensure_ascii=False, separators=(',', ':')))
    idx_p = out / 'index.json'
    idx = json.loads(idx_p.read_text()) if idx_p.exists() else {'runs': []}
    idx['runs'] = [r for r in idx['runs'] if r['id'] != run['id']]
    idx['runs'].append({'id': run['id'], 'case': case, 'label': label, 'pilot': run['pilot'],
                        'counted': run['counted'], 'class_label': run['classification'].get('public_label') or run['classification']['label'],
                        'class_label_full': run['classification']['label'],
                        'started_utc': run['started_utc'], 'model': run['model'], 'steps': len(run['steps']),
                        'spark_calls': run['totals']['spark_calls'], 'spark_cost': run['totals']['spark_cost'],
                        'sam_calls': run['totals'].get('sam_calls', 0),
                        'outcome': run['outcome'] and run['outcome']['kind'], 'verdict': (run['outcome'] or {}).get('verdict'),
                        'survivors': (run['outcome'] or {}).get('survivors'),
                        'state': (run.get('pair') or {}).get('state') or ('faulted' if run.get('reading') else None),
                        'display_caption': run.get('display_caption'),
                        'pair_of': pair_of})
    idx['runs'].sort(key=lambda r: r['started_utc'])
    idx_p.write_text(json.dumps(idx, ensure_ascii=False, indent=1))
    t = run['totals']
    print(run['id'], label, run['classification']['label'], 'steps', len(run['steps']), 'events', len(run['events']),
          'play', run['play_length_s'], 's', t)


def main():
    if len(sys.argv) > 2 and sys.argv[1] == '--convert':
        for p in sys.argv[2:]:
            convert(p)
        return
    if len(sys.argv) > 1 and sys.argv[1] in ('--pair', '--followup'):
        ap = argparse.ArgumentParser()
        ap.add_argument(sys.argv[1], dest='rec', required=True, help='pair folder (reading-assisted cohort) or follow-up record folder')
        ap.add_argument('--case', required=True)
        ap.add_argument('--label', required=True)
        ap.add_argument('--rates', required=True, help='any JSON with rates_usd_per_million')
        ap.add_argument('--photos', default=None, help='JSON {board, overlay, outline, crop, evidence}: site-relative paths of sanitized derivatives')
        ap.add_argument('--pair-of', default=None)
        a = ap.parse_args()
        cj = json.load(open(a.rates))
        rates = {'rates': cj['rates_usd_per_million'], 'source': 'https://dev.meta.ai/docs/pricing-rate-limits'}
        photos = json.load(open(a.photos)) if a.photos else {}
        if sys.argv[1] == '--pair':
            run = extract_pair(a.rec, a.case, a.label, rates, photos)
            run['timeline'] = timeline_pair(run)
        else:
            run = extract_followup(a.rec, a.case, a.label, rates, a.pair_of)
            run['timeline'] = timeline(run)
        write_run(run, a.case, a.label, a.pair_of)
        return
    ap = argparse.ArgumentParser()
    ap.add_argument('--run', required=True)
    ap.add_argument('--case', required=True)
    ap.add_argument('--label', required=True)
    ap.add_argument('--intake', required=True, help='schematic-intake summary.json')
    ap.add_argument('--rates', required=True, help='schematic-intake cost.json')
    ap.add_argument('--image', type=int, required=True, help='image number in the intake summary')
    ap.add_argument('--photo', default=None, help='photo run root (result.json, plan.json, vision/)')
    ap.add_argument('--render', default=None, help='render dir with <concept>-decoded.json and overlay PNGs')
    ap.add_argument('--pair-restore', default=None, help='operator restoration record JSON for a restored rerun')
    ap.add_argument('--pair-of', default=None, help='run id of the fault run this restored rerun pairs with')
    ap.add_argument('--note', default=None, help='short plain-text note shown after the run')
    ap.add_argument('--pilot', action='store_true', help='ignored: classification comes from run metadata')
    a = ap.parse_args()
    cj = json.load(open(a.rates))
    rates = {'rates': cj['rates_usd_per_million'], 'source': 'https://dev.meta.ai/docs/pricing-rate-limits'}
    s = json.load(open(a.intake))
    o = next(x for x in s['outcomes'] if x['image_number'] == a.image)
    m = re.match(r'(\d{8})T(\d{6})', o['run'])
    read_utc = datetime.strptime(m.group(1) + m.group(2), '%Y%m%d%H%M%S').isoformat() + '+00:00'
    intake = {'run': o['run'], 'utc': read_utc, 'requests': o['requests'],
              'cost': round(cost(o['usage'], rates['rates']), 6),
              'out_tokens': o['usage']['output_tokens'],
              'summary': o['candidate'].get('summary'),
              'components': [{'name': c['name'], 'kind': c['kind'], 'nodes': c['nodes'],
                              'marking': c.get('marking'), 'bbox': c.get('bbox'),
                              'evidence': c.get('evidence')} for c in o['candidate']['components']]}
    run = extract(pathlib.Path(a.run), a.case, a.label, intake, rates)
    if a.pilot and not run['pilot']:
        print('note: --pilot ignored; classification is', run['classification']['label'], file=sys.stderr)
    if a.note:
        run['note_after'] = a.note
    if a.photo:
        run['photo'] = load_photo(a.photo, a.render)
    if a.pair_restore:
        run['pair'] = {'of': a.pair_of, 'restore_record': a.pair_restore, 'operator_restored': True}
    run['timeline'] = timeline(run)
    out = SITE / 'data' / 'runs'
    out.mkdir(parents=True, exist_ok=True)
    (out / f"{run['id']}.json").write_text(json.dumps(run, ensure_ascii=False, separators=(',', ':')))
    idx_p = out / 'index.json'
    idx = json.loads(idx_p.read_text()) if idx_p.exists() else {'runs': []}
    idx['runs'] = [r for r in idx['runs'] if r['id'] != run['id']]
    idx['runs'].append({'id': run['id'], 'case': a.case, 'label': a.label, 'pilot': run['pilot'],
                        'counted': run['counted'], 'class_label': run['classification']['label'],
                        'started_utc': run['started_utc'], 'model': run['model'], 'steps': len(run['steps']),
                        'spark_calls': run['totals']['spark_calls'], 'spark_cost': run['totals']['spark_cost'],
                        'outcome': run['outcome'] and run['outcome']['kind'], 'verdict': (run['outcome'] or {}).get('verdict'),
                        'survivors': (run['outcome'] or {}).get('survivors'),
                        'pair_of': a.pair_of})
    idx['runs'].sort(key=lambda r: r['started_utc'])
    idx_p.write_text(json.dumps(idx, ensure_ascii=False, indent=1))
    t = run['totals']
    print(run['id'], a.label, run['classification']['label'], 'steps', len(run['steps']), 'events', len(run['events']),
          'play', run['play_length_s'], 's', t)


if __name__ == '__main__':
    main()
