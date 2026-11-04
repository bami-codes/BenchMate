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


def seal_from_pair(run, pev, rd_fits):
    """Copy the seal commitment and (if present) the seal opening into the run. The truth is copied only
    from specimen_seal_opened; before that event only the digest exists."""
    sealed = next((e for e in pev if e['kind'] == 'specimen_assembly_sealed' and e['payload'].get('state') == 'faulted'), None)
    if sealed:
        run['seal'] = {'sealed_sha256': sealed['payload']['sha256'], 'transmitted_to_model': sealed['payload'].get('transmitted_to_model'), 'sealed_ev': env(sealed)}
    opened = next((e for e in pev if e['kind'] == 'specimen_seal_opened'), None)
    if not opened:
        return None
    p = opened['payload']
    a = p.get('assembly') or {}
    truth = []
    for x in a.get('specimen_truth', []):
        loc = x.get('location')
        if not loc and (x.get('anode_hole') or x.get('cathode_hole') or x.get('striped_cathode_hole')):
            loc = f"anode at {x.get('anode_hole')}, cathode at {x.get('striped_cathode_hole') or x.get('cathode_hole')}"
        clar = next((c for c in pev if c['kind'] == 'operator_fixture_contact_clarified'), None)
        if clar and x.get('kind') == 'D':
            loc = (loc or '') + ' (sealed record; the operator later clarified the anode sat at E30, the same OUT strip)'
        truth.append({'component': x.get('component'), 'kind': x.get('kind'), 'type': x.get('type'),
                      'value_nominal_ohm': x.get('value_nominal_ohm'), 'value_nominal_F': x.get('value_nominal_F'),
                      'nodes': f"{x.get('anode')}→{x.get('cathode')}" if x.get('anode') else None, 'location': loc})
    run['seal'] = {**(run.get('seal') or {}), 'opened_ev': env(opened), 'sealed_sha256_at_open': p.get('sealed_sha256'),
                   'matches_commitment': p.get('sealed_sha256') == (run.get('seal') or {}).get('sealed_sha256'), 'truth': truth,
                   'after_reading_score': p.get('after_reading_score'), 'after_reading_cancellation': p.get('after_reading_cancellation')}
    found = rd_fits if rd_fits is not None else ((run.get('outcome') or {}).get('survivors') or [])
    run['outcome'] = {'kind': 'report', 'verdict': (run.get('outcome') or {}).get('verdict'), 'components': (run.get('outcome') or {}).get('components'),
                      'survivors': found, 'text': (run.get('outcome') or {}).get('text'), 'ev': (run.get('outcome') or {}).get('ev'),
                      'seal_opened': True, 'found': found}
    return opened, truth


def extract_terminal_pair(pair, case, label, rates, photos, amendment=None):
    """A completed reading-assisted pair whose numeric reading was withdrawn (Codex schema
    benchmate.terminal_pair_reading_withdrawn.v1, case 04): both diagnosis children live inside the pair.
    Returns (fault_run, restored_run). The fault story ends at the seal reveal; nothing about the withdrawn
    reading is rendered (the request/forecast stay in the repository record). Earlier failed attempts under
    history/ are not rendered."""
    pair = pathlib.Path(pair)
    res = json.load(open(pair / 'result.json'))
    reg = json.load(open(pair / 'registration.json'))
    pev = [json.loads(l) for l in open(pair / 'events.jsonl')]
    intake = intake_from_pair(pair, rates)
    label_full = 'Official run · reading-assisted cohort · known to developers, not blind'
    if reg.get('blind_test') is False and not reg.get('known_case_development'):
        label_full = 'Official run · reading-assisted cohort · not a blind test'
    public = 'Official run · Spark did not know the fault'

    def classify_pair(run, state):
        run['pilot'], run['counted'] = False, bool(reg.get('counted'))
        run['classification'] = {'pilot': False, 'counted': run['counted'], 'label': label_full, 'public_label': public,
                                 'basis': 'pair registration committed before the first request (registration.json)',
                                 'cohort': {'plan': reg.get('cohort'), 'slot': reg.get('run_id'), 'ordinal': reg.get('attempt'), 'state': state}}
        run['pair_dir'] = pair.name
        run['registration'] = {k: reg.get(k) for k in ('cohort', 'attempt', 'official', 'counted', 'selected_first_attempt', 'freeze_commit', 'blind_test', 'known_case_development')}
        if amendment:
            # the amendment text claims what the image Spark read in THIS run shows; check it against the intake transcription
            comp = amendment.get('component'); want = amendment.get('image_value')
            if comp and want:
                read = next((c.get('marking') for c in intake['components'] if c.get('name') == comp), None)
                if read is None or f"{comp} {read}" != want:
                    raise SystemExit(f"amendment says the image shows {want!r} but intake {intake['run']} transcribed {comp} as {read!r}")
            run['design_amendment'] = {**amendment, 'intake_run': intake['run']}

    fchild = pair / res['faulted_diagnosis']
    fault = extract(fchild, case, label, intake, rates)
    fault['id'] = pair.name; fault['child_id'] = fchild.name
    classify_pair(fault, 'faulted')
    t0 = ts(fault['started_utc'])
    totals = dict(fault['totals'])
    play, last_t = fault['play_length_s'], max((e['t'] for e in fault['events']), default=0.0)

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
        fault['events'].append(item)
        return item

    # the withdrawn reading: its one selection request is spent and counted, nothing else is rendered
    sel_ev = next((e for e in pev if e['kind'] == 'reading_requested'), None)
    sel_dir = next(iter(sorted((pair / 'reading-selection').iterdir())), None) if (pair / 'reading-selection').exists() else None
    if sel_ev and sel_dir and (sel_dir / 'result.json').exists():
        u = (json.load(open(sel_dir / 'result.json')).get('usage') or {})
        if u:
            totals['spark_calls'] += 1; totals['spark_cost'] = round(totals['spark_cost'] + cost(u, rates['rates']), 6)
    cancel = next((e for e in pev if e['kind'] == 'operator_reading_cancelled'), None)
    fault['reading_withdrawn'] = {
        'withdrawn': True, 'ev': env(cancel) if cancel else None,
        'reason': (cancel or {}).get('payload', {}).get('reason'),
        'timing': (cancel or {}).get('payload', {}).get('timing'),
        'line': 'No bench reading was needed: one bounded explanation remained and the repair was external.',
        'selection_request_spent': bool(sel_ev), 'forecast_exercised': False}
    got = seal_from_pair(fault, pev, None)
    if got:
        opened, truth = got
        add(opened, 'seal_opened', truth=truth, matches=fault['seal']['matches_commitment'])
    fault['totals'] = totals
    fault['play_length_s'] = round(play, 2)
    if photos.get('board'):
        fault['photo'] = {'board': photos.get('board'), 'crop': photos.get('crop'), 'crop_full': photos.get('crop_full'), 'crop_r1': None,
                          'crop_box': photos.get('crop_box'), 'crop_full_box': photos.get('crop_full_box'),
                          'image': {'file': photos.get('crop_full') or photos.get('board'), 'width': photos.get('width'), 'height': photos.get('height'),
                                    'sha256_render': photos.get('sha256')},
                          'sam': [], 'vision': None, 'pairing': None, 'documentary': True,
                          'note': 'Documentary photo of the faulted board, taken after the diagnosis and before the diode was removed. Not sent to any model; no SAM, no reading.'}
    restore_ev = next((e for e in pev if e['kind'] == 'operator_restoration_confirmed'), None)

    rchild = pair / res['restored_diagnosis']
    restored = extract(rchild, case, 'Restored rerun', intake, rates)
    classify_pair(restored, 'restored')
    restored['pair'] = {'of': fault['id'], 'operator_restored': True, 'state': 'restored',
                        'restore_ev': env(restore_ev) if restore_ev else None,
                        'restored_what': (restore_ev or {}).get('payload', {}).get('external_fault_removed')}
    restored['display_caption'] = res.get('restored_caption') or 'No mismatch in the tests Spark chose'
    vt = pair / 'verification.txt'
    if vt.exists():
        fault['verify_output'] = vt.read_text().strip()
        fault['verify_command'] = 'python -m benchmate.reading_terminal_pair verify <record folder>'
        restored['verify_command'] = 'python -m benchmate verify <child folder>'
    return fault, restored


def _F_to_uF(x):
    return None if x is None else float(f'{x * 1e6:.5g}')  # 5 significant figures, no coarser than the record


PAIR_PROVENANCE = "The two capacitor bodies were picked by visual review at the operator's request (body-group.json: Codex_visual_review_requested_by_operator); Spark said the photo cannot tell which is C1 — the readings decide."


def extract_group_pair(pair, group, restored, case, label, rates, photos, extra):
    """Case 02 layout (Codex, 11/4): a reading-assisted pair whose photo stage ended at Spark's binding call
    (no body named: the two capacitors are identical parallel shunts), an UNORDERED reading supplement
    (benchmate.unordered_reading_supplement.v1: both capacitor bodies read, every assignment of bodies to
    parts scored against the frozen bands), and a restored continuation
    (benchmate.unordered_restored_continuation.v2: seal opened, operator restored, fresh-context rerun,
    documentary SAM photo). Returns (fault_run, restored_run). Earlier miswired / failed attempts are
    repository records only. The site never pairs bodies with parts: the assignment shown is the engine's
    bijection test, copied from group-reading-score.json."""
    pair, group, restored = pathlib.Path(pair), pathlib.Path(group), pathlib.Path(restored)
    child = sorted((pair / 'diagnosis-faulted').iterdir())[0]
    intake = intake_from_pair(pair, rates)
    run = extract(child, case, label, intake, rates)
    run['pair_dir'] = pair.name; run['id'] = pair.name; run['child_id'] = child.name
    pev = [json.loads(l) for l in open(pair / 'events.jsonl')]
    gev = [json.loads(l) for l in open(group / 'events.jsonl')]
    rev = [json.loads(l) for l in open(restored / 'events.jsonl')]
    reg = json.load(open(pair / 'registration.json'))
    greg = json.load(open(group / 'registration.json'))
    rreg = json.load(open(restored / 'registration.json'))
    label_full = 'Official run · reading-assisted cohort · known to developers, not blind'
    public = 'Official run · Spark did not know the fault'
    run['registration'] = {k: reg.get(k) for k in ('cohort', 'attempt', 'official', 'counted', 'selected_first_attempt', 'freeze_commit', 'blind_test', 'known_case_development')}
    run['pilot'], run['counted'] = False, bool(reg.get('counted'))
    run['classification'] = {'pilot': False, 'counted': run['counted'], 'label': label_full, 'public_label': public,
                             'basis': 'pair registration committed before the first request (registration.json); the reading supplement and the restored continuation are registered separately and linked by head sha256',
                             'cohort': {'plan': reg.get('cohort'), 'slot': reg.get('run_id'), 'ordinal': reg.get('attempt'), 'state': 'faulted'},
                             'linked_records': {'reading_supplement': greg.get('run_id'), 'restored_continuation': rreg.get('run_id')}}
    t0 = ts(run['started_utc'])
    totals = dict(run['totals'])
    play, last_t = run['play_length_s'], max((e['t'] for e in run['events']), default=0.0)

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

    fc = json.load(open(pair / 'reading-forecast.json'))
    sel_dir = sorted((pair / 'reading-selection').iterdir())[0]
    sel = json.load(open(sel_dir / 'result.json'))
    manifest = json.load(open(pair / 'photo-faulted' / 'decoded' / 'body-manifest.json'))
    plan = json.load(open(pair / 'photo-faulted' / 'prepared' / 'plan.json'))
    binding = json.load(open(extra / 'binding-result.json')) if (extra / 'binding-result.json').exists() else {}
    sam_dec = json.load(open(extra / 'faulted-sam-decoded.json')) if (extra / 'faulted-sam-decoded.json').exists() else {}
    display = json.load(open(extra / 'sam-display-manifest.json')) if (extra / 'sam-display-manifest.json').exists() else {}
    body_group = json.load(open(group / 'body-group.json'))
    gfc = json.load(open(group / 'group-reading-forecast.json'))
    gobs = json.load(open(group / 'group-reading-observation.json'))
    gscore = json.load(open(group / 'group-reading-score.json'))
    bodies = {c['id']: c for c in manifest['components']}
    rd = run.setdefault('reading', {'bands': [], 'binding': None, 'observed': None, 'scored': None})
    sealed = next((e for e in pev if e['kind'] == 'specimen_assembly_sealed' and e['payload'].get('state') == 'faulted'), None)
    if sealed:
        run['seal'] = {'sealed_sha256': sealed['payload']['sha256'], 'transmitted_to_model': sealed['payload'].get('transmitted_to_model'), 'sealed_ev': env(sealed)}

    # ---- the pair's own events after the diagnosis: request, C1-only forecast, photo, SAM, Spark names no body
    for e in pev:
        k, p = e['kind'], e['payload']
        if k == 'reading_requested':
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
            for b in fc['forecasts']:
                rule = b.get('rule') or {}
                if b['source'] == 'operator_dmm':
                    rng = (rule.get('intervals_by_meter_range') or [{}])[0]
                    bands.append({'explanation': b['explanation'], 'source': b['source'], 'component': fc['request']['component'],
                                  'low': _F_to_uF(rng.get('low', b.get('low'))), 'high': _F_to_uF(rng.get('high', b.get('high'))), 'unit': 'µF', 'observable': b.get('observable'),
                                  'rule': "fitted value's training envelope (every grid point whose waveforms stay within 9 mV); the meter's own allowance was not yet qualified at this point",
                                  'note': None, 'rule_raw': {kk: vv for kk, vv in rule.items() if kk != 'electrical_interval_rule'}})
                else:
                    bands.append({'explanation': b['explanation'], 'source': b['source'], 'component': fc['request']['component'], 'low': None, 'high': None, 'unit': 'µF',
                                  'observable': b.get('observable'), 'rule': 'printed nominal value only; a part whose actual value changed can keep its old label, so this band is open',
                                  'note': 'A marking confirms the nominal value, not the capacitance today.', 'rule_raw': rule})
            rd['bands'] = bands
            rd['sha'] = (p.get('sha256') or '')[:10]; rd['sha_full'] = p.get('sha256'); rd['frozen_ev'] = env(e)
            totals['forecasts_frozen'] += 1
            add(e, 'reading_forecast_frozen', bands=bands, sha=rd['sha'], sha_full=rd['sha_full'])
        elif k == 'reading_forecast_publication':
            rd.update({'published': p.get('published'), 'commit': p.get('commit'), 'url': p.get('url'), 'publish_ev': env(e)})
            add(e, 'reading_forecast_published', commit=p.get('commit'), url=p.get('url'), sha=rd['sha'])
        elif k == 'board_photo_received':
            add(e, 'board_photo', sha256=p.get('sha256'), new_capture=p.get('new_capture_operator_confirmed'))
        elif k == 'sam_localization_finished':
            totals['sam_calls'] = totals.get('sam_calls', 0) + int(p.get('requests') or 0)
            totals['sam_cost'] = round(totals.get('sam_cost', 0.0) + 0.0025 * int(p.get('requests') or 0), 6)
            add(e, 'sam_done', requests=p.get('requests'), masks=sam_dec.get('match_count') or len(sam_dec.get('masks', [])), bodies=len(manifest['components']))
        elif k == 'run_failed' and p.get('stage') == 'bind':
            # Spark, asked which body is C1, named none; its reply did not match the validator's JSON shape and the call was not retried
            u = binding.get('usage') or {}
            c = round(cost(u, rates['rates']), 6) if u else None
            if u:
                totals['spark_calls'] += 1; totals['spark_cost'] = round(totals['spark_cost'] + c, 6)
            args = binding.get('arguments') or {}
            rd['binding'] = {'sam_body': None, 'component': rd.get('component'), 'chosen_by': 'none', 'reason': args.get('reason'),
                             'operator_confirmed': False, 'abstained': True, 'format_stop': p.get('error'),
                             'calls': [{'cost': c, 'role': 'asked which body is C1', 'out_tokens': u.get('output_tokens'), 'in_tokens': u.get('input_tokens'), 'ev': env(e)}] if u else [], 'ev': env(e)}
            add(e, 'binding_abstained', component=rd.get('component'), reason=args.get('reason'), returned=args.get('sam_body'), format_stop=p.get('error'),
                bodies=len(manifest['components']), calls=rd['binding']['calls'])
    # ---- the unordered reading supplement: both capacitor bodies, every assignment scored
    comps = gfc['components']; sam_bodies = gfc['bodies']
    gbands = []
    for x in gfc['explanations']:
        for comp, iv in x['intervals'].items():
            gbands.append({'explanation': x['id'], 'role': x['role'], 'component': comp, 'source': gfc['source'],
                           'low': _F_to_uF(iv[0]), 'high': _F_to_uF(iv[1]), 'unit': 'µF',
                           'rule': ('training envelope of the fitted value' if (comp == 'C1' and x['id'].startswith('changed')) else 'drawn value ± 5 % part tolerance') + f", plus the meter's allowance ({int(gfc['meter']['relative_allowance'] * 100)} % + {gfc['meter']['digits_allowance']} digits on the {_F_to_uF(gfc['meter']['range_F']):g} µF range)"})
    rd['group'] = {'bodies': sam_bodies, 'components': comps, 'source': gfc['source'], 'bands': gbands,
                   'meter': {'range_uF': _F_to_uF(gfc['meter']['range_F']), 'resolution_uF': _F_to_uF(gfc['meter']['resolution_F']), 'relative_allowance': gfc['meter']['relative_allowance'], 'digits_allowance': gfc['meter']['digits_allowance'], 'basis': gfc['meter'].get('basis'), 'calibrated': gfc['meter'].get('accuracy_calibrated')},
                   'chosen_by': body_group.get('candidate_group_chosen_by'), 'spark_chose_group': body_group.get('Spark_chose_group'), 'spark_abstention_reason': body_group.get('Spark_abstention_reason'),
                   'correspondence': body_group.get('correspondence'), 'matching': gfc.get('matching'), 'scope': gfc.get('scope'), 'new_blind_test': gfc.get('new_blind_test'),
                   'body_boxes': {b: (bodies.get(b) or {}).get('native_object', {}).get('bounds_half_open') for b in sam_bodies},
                   'registration': {'schema': greg.get('schema'), 'run_id': greg.get('run_id'), 'parent_head_sha256': greg.get('parent_head_sha256'), 'counted_new_physical_attempt': greg.get('counted_new_physical_attempt'), 'paid_calls': greg.get('paid_calls')}}
    for e in gev:
        k, p = e['kind'], e['payload']
        if k == 'body_binding_ambiguity':
            rd['group']['ambiguity_ev'] = env(e)
            add(e, 'body_group', bodies=sam_bodies, components=comps, chosen_by=body_group.get('candidate_group_chosen_by'), spark_chose_group=body_group.get('Spark_chose_group'),
                spark_abstention_reason=body_group.get('Spark_abstention_reason'), topology=body_group.get('topology_conditioned'), boxes=rd['group']['body_boxes'],
                photo=photos.get('faulted_pair') or photos.get('faulted_sam'), provenance=PAIR_PROVENANCE, already_received={'body': (body_group.get('already_received_report') or {}).get('body'), 'source': (body_group.get('already_received_report') or {}).get('source'), 'actual_capacitance_measured': (body_group.get('already_received_report') or {}).get('actual_capacitance_measured')})
        elif k == 'reading_forecast_frozen':
            rd['group']['sha_full'] = p.get('sha256'); rd['group']['sha'] = (p.get('sha256') or '')[:10]; rd['group']['frozen_ev'] = env(e)
            totals['forecasts_frozen'] += 1
            add(e, 'group_reading_forecast', bands=gbands, bodies=sam_bodies, components=comps, source=gfc['source'], meter=rd['group']['meter'], sha=rd['group']['sha'], sha_full=p.get('sha256'), matching=gfc.get('matching'))
        elif k == 'reading_forecast_publication':
            rd['group'].update({'commit': p.get('commit'), 'remote': p.get('remote'), 'publish_ev': env(e)})
            add(e, 'reading_forecast_published', commit=p.get('commit'), url=p.get('url'), sha=rd['group']['sha'], group=True)
        elif k == 'group_reading_observed':
            readings = [{'body': r['body'], 'value': r['value'], 'unit': {'uF': 'µF'}.get(r['unit'], r['unit']), 'range_uF': _F_to_uF(r.get('range_F')), 'isolated': r.get('isolated_confirmed')} for r in p['readings']]
            rd['group']['observed'] = {'source': p['source'], 'power_off': p.get('power_off_confirmed'), 'discharge_wait': p.get('discharge_wait_confirmed'), 'readings': readings, 'ev': env(e)}
            rd['observed'] = {'component': None, 'group': True, 'value': None, 'unit': 'µF', 'source': p['source'], 'readings': readings, 'ev': env(e)}
            add(e, 'group_reading_observed', source=p['source'], readings=readings, power_off=p.get('power_off_confirmed'), discharge_wait=p.get('discharge_wait_confirmed'))
        elif k == 'group_reading_scored':
            if not any(b['source'] == (rd['group'].get('observed') or {}).get('source') for b in gbands):
                sys.exit('group_reading_scored without a frozen band for the reported source')
            rd['group']['scored'] = {'fits': p['fits'], 'ruled_out': p.get('ruled_out_by_reading') or [], 'reference_fits': p.get('reference_fits'), 'matches': p.get('matches'),
                                     'binding': p.get('conditional_unique_binding'), 'outcome_raw': p.get('outcome'), 'body_identity_status': p.get('body_identity_status'),
                                     'nearest_value_assignment': p.get('nearest_value_assignment'), 'refitted': p.get('refitted'), 'forecast_sha256': p.get('forecast_sha256'), 'observation_sha256': p.get('observation_sha256'), 'ev': env(e)}
            rd['scored'] = {'fits': p['fits'], 'ruled_out': p.get('ruled_out_by_reading') or [], 'group': True, 'ev': env(e)}
            rd['outcome'] = {'one_explanation_remains': 'one', 'indistinguishable': 'several', 'all_explanations_rejected': 'none'}.get(p.get('outcome'), 'one' if len(p['fits']) == 1 else ('none' if not p['fits'] else 'several'))
            add(e, 'group_reading_scored', fits=p['fits'], ruled_out=rd['scored']['ruled_out'], matches=p.get('matches'), binding=p.get('conditional_unique_binding'), outcome=rd['outcome'],
                body_identity_status=p.get('body_identity_status'), nearest_value_assignment=p.get('nearest_value_assignment'), refitted=p.get('refitted'))
    # ---- the seal opens in the restored continuation's record (after the readings were scored)
    opened = next((e for e in rev if e['kind'] == 'specimen_seal_opened'), None)
    if opened:
        p = opened['payload']; a = p.get('assembly') or {}
        truth = [{'component': x.get('component'), 'kind': x.get('kind'), 'value_nominal_ohm': x.get('value_nominal_ohm'), 'value_nominal_F': x.get('value_nominal_F'),
                  'marking': x.get('marking'), 'location': x.get('location')} for x in a.get('specimen_truth', [])]
        run['seal'] = {**(run.get('seal') or {}), 'opened_ev': env(opened), 'sealed_sha256_at_open': p.get('sealed_sha256'),
                       'matches_commitment': p.get('sealed_sha256') == (run.get('seal') or {}).get('sealed_sha256'), 'truth': truth,
                       'after_group_reading_score': p.get('after_group_reading_score'), 'opened_in_record': rreg.get('run_id')}
        run['outcome'] = {'kind': 'report', 'verdict': (run.get('outcome') or {}).get('verdict'), 'components': (run.get('outcome') or {}).get('components'),
                          'survivors': rd['scored']['fits'], 'text': (run.get('outcome') or {}).get('text'), 'ev': (run.get('outcome') or {}).get('ev'), 'seal_opened': True, 'found': rd['scored']['fits']}
        add(opened, 'seal_opened', truth=truth, matches=run['seal']['matches_commitment'])
    run['totals'] = totals
    run['play_length_s'] = round(play, 2)
    disp = display.get('faulted') or {}
    # replay and end scene: the SAM input with only the two read bodies outlined (overlay-provenance.json recipe); the
    # 7-contour display-rule image is kept for the report page only, as documentary
    run['photo'] = {'board': photos.get('board'), 'image': {'file': photos.get('faulted_pair') or photos.get('faulted_sam'), 'width': plan['input']['width'], 'height': plan['input']['height'], 'sha256_sam_input': plan['input']['sha256']},
                    'sam': [{'concept': 'electronic component', 'match_count': sam_dec.get('match_count'), 'displayed': 2,
                             'masks': [{'object_id': m.get('object_id'), 'bounds_half_open': m.get('bounds_half_open'), 'confidence': m.get('confidence'), 'overlay_file': None, 'source_mask_file': None, 'resize_to_box': m.get('resize_to_box')} for m in sam_dec.get('masks', [])]}],
                    'vision': None, 'pairing': 'no model paired a body with a drawing part; which body is C1 followed from the readings (the engine’s assignment test)',
                    'labels': [{'text': b, 'bounds': rd['group']['body_boxes'].get(b), 'side': True} for b in sam_bodies],
                    'provenance': PAIR_PROVENANCE,
                    'note': 'Photo untouched apart from the two green outlines: the boundaries of the sam-2 and sam-3 body masks SAM 3.1 returned, drawn by the recipe in overlay-provenance.json (annotation only, no new capture, native masks unchanged).',
                    'display_rule_image': {'file': photos.get('faulted_sam'), 'displayed': disp.get('displayed_mask_records'), 'rule': display.get('rule'),
                                           'note': f"Documentary: the same photo with every native SAM 3.1 mask outlined under a display-only rule chosen after the results (a mask is left out when its box contains two others; {disp.get('displayed_mask_records')} of {sam_dec.get('match_count')} shown). Not an identification (docs/2026-11-04-case02-SAM-display-revision.md)."}}
    vt = child / 'verification.txt'
    if vt.exists():
        run['verify_outputs'] = [f"# diagnosis child, python -m benchmate verify\n{vt.read_text().strip()}"]
    gvt = group / 'verification.txt'
    if gvt.exists():
        run['verify_outputs'].append(f"# reading supplement\n{gvt.read_text().strip()}")
    run['verify_command'] = 'python -m benchmate verify <diagnosis child folder>'

    # ---- restored continuation: a fresh-context rerun on the same drawing after the operator's restoration
    rchild = sorted((restored / 'diagnosis-restored').iterdir())[0]
    rrun = extract(rchild, case, 'Restored rerun', intake, rates)
    rrun['id'] = restored.name; rrun['child_id'] = rchild.name; rrun['pair_dir'] = restored.name
    rrun['pilot'], rrun['counted'] = False, bool(rreg.get('counted'))
    rrun['classification'] = {'pilot': False, 'counted': rrun['counted'], 'label': label_full, 'public_label': public,
                              'basis': 'restored continuation registered before its first request (registration.json), linked to the pair and the reading supplement by head sha256',
                              'cohort': {'plan': rreg.get('cohort'), 'slot': rreg.get('run_id'), 'ordinal': rreg.get('attempt'), 'state': 'restored'}}
    rrun['registration'] = {k: rreg.get(k) for k in ('cohort', 'attempt', 'official', 'counted', 'state', 'followup_of', 'original_status', 'original_selection_unchanged')}
    restore_ev = next((e for e in rev if e['kind'] == 'operator_restoration_confirmed'), None)
    rres = json.load(open(restored / 'result.json')) if (restored / 'result.json').exists() else {}
    rrun['pair'] = {'of': run['id'], 'operator_restored': True, 'state': 'restored', 'restore_ev': env(restore_ev) if restore_ev else None,
                    'restored_what': (restore_ev or {}).get('payload', {}).get('instruction'), 'closeout': {k: rres.get(k) for k in ('restored_verdict', 'restored_photo_documentary_only', 'restored_binding_performed', 'prior_restored_binding_requirement_waived', 'SAM_used_as_identification_evidence', 'restored_mask_records', 'photo_SAM_requests', 'photo_Spark_requests')}}
    rrun['display_caption'] = rres.get('display_caption') or 'No mismatch in the tests Spark chose'
    rdisp = display.get('restored') or {}
    rsam = json.load(open(restored / 'photo-restored' / 'sam-decoded.json')) if (restored / 'photo-restored' / 'sam-decoded.json').exists() else {}
    if photos.get('restored_sam'):
        rrun['totals']['sam_calls'] = rrun['totals'].get('sam_calls', 0) + int(rres.get('photo_SAM_requests') or 0)
        rrun['totals']['sam_cost'] = round(rrun['totals'].get('sam_cost', 0.0) + 0.0025 * int(rres.get('photo_SAM_requests') or 0), 6)
        nm = rsam.get('match_count') or len(rsam.get('masks', []))
        rrun['photo'] = {'board': None, 'image': {'file': photos.get('restored_board') or photos.get('restored_sam'), 'width': 1200, 'height': 1600},
                         'sam': [{'concept': 'electronic component', 'match_count': nm, 'displayed': 0, 'masks': []}],
                         'vision': None, 'pairing': None, 'documentary': True,
                         'note': f"Documentary photo of the restored board, untouched. SAM 3.1 returned {nm} masks; nothing was identified or read from it and no body was paired with a part.",
                         'display_rule_image': {'file': photos.get('restored_sam'), 'displayed': rdisp.get('displayed_mask_records'),
                                                'note': f"Documentary: the same photo with the native SAM 3.1 masks outlined under the display-only rule chosen after the results ({rdisp.get('displayed_mask_records')} of {nm} shown). Not an identification (docs/2026-11-04-case02-SAM-display-revision.md)."}}
    for vt, head in ((rchild / 'verification.txt', '# diagnosis child, python -m benchmate verify'), (restored / 'verification.txt', '# whole restored continuation, python -m benchmate.reading_restored_sam_closeout verify')):
        if vt.exists():
            rrun.setdefault('verify_outputs', []).append(f"{head}\n{vt.read_text().strip()}")
    rrun['verify_command'] = 'python -m benchmate verify <diagnosis child folder>'
    return run, rrun


def _band_rows(fc, meter_range, quantity):
    """Bands from an operator-reading-v1 forecast file, per explanation and per source, for the meter range the
    operator actually used. Resistance bands are shown in kΩ when every band sits at or above 1 kΩ, else in Ω, so a
    near-short band (0–12.2 Ω) and a kilohm band keep their own resolution. Returns (bands, unit)."""
    rows = []
    for b in fc['forecasts']:
        rule = b.get('rule') or {}
        low, high, note = b.get('low'), b.get('high'), None
        rng = next((x for x in rule.get('intervals_by_meter_range', []) if x['meter_range'] == meter_range), None)
        if b['source'] == 'operator_dmm' and rng:
            low, high = rng['low'], rng['high']
            mr = f"{int(meter_range / 1000)} kΩ" if meter_range >= 1000 else f"{int(meter_range)} Ω"
            rtext = f"fitted value's training envelope (every grid point whose waveforms stay within 9 mV) plus the meter's allowance on the {mr} range"
            if rule.get('nominal_rule'):
                rtext = f"drawn value ± 5 % part tolerance plus the meter's allowance on the {mr} range"
            if b['explanation'].startswith('external_path'):
                rtext = f"near-short category declared before the reading (0–10 Ω) plus the meter's allowance on the {mr} range"
        else:
            rtext = ('printed nominal value only; a part whose actual value changed can keep its old label, so this band is open'
                     if rule.get('printed_value_unconstrained') else 'printed nominal value ± 5 % part tolerance')
            if rule.get('actual_value_not_measured'):
                note = 'A marking confirms the nominal value, not the resistance today.'
        rows.append({'explanation': b['explanation'], 'source': b['source'], 'low': low, 'high': high, 'unit': b.get('unit'), 'observable': b.get('observable'),
                     'rule': rtext, 'note': note, 'envelope': {'low': b.get('low'), 'high': b.get('high'), 'note': 'range-independent envelope'},
                     'meter_range': meter_range if b['source'] == 'operator_dmm' else None,
                     'rule_raw': {kk: vv for kk, vv in rule.items() if kk != 'electrical_interval_rule'}})
    unit = 'Ω'
    if quantity == 'resistance' and all(r['unit'] == 'ohm' for r in rows):
        dmm = [r for r in rows if r['source'] == 'operator_dmm' and r['low'] is not None]
        if dmm and all(r['low'] >= 1000 for r in dmm):
            unit = 'kΩ'
            for r in rows:
                for k in ('low', 'high'):
                    if r[k] is not None:
                        r[k] = round(r[k] / 1000.0, 2)
                for k in ('low', 'high'):
                    if r['envelope'][k] is not None:
                        r['envelope'][k] = round(r['envelope'][k] / 1000.0, 2)
        else:
            for r in rows:
                for k in ('low', 'high'):
                    if r[k] is not None:
                        r[k] = round(r[k], 1) if r[k] < 100 else int(round(r[k]))
        for r in rows:
            r['unit'] = unit
    return rows, unit


def _observed_value(p, unit):
    """The operator's typed value in the band unit (kohm → kΩ or Ω as the bands are shown). Raw value and unit are kept."""
    v, u = p.get('value'), p.get('unit')
    ohm = v * 1000.0 if u == 'kohm' else v
    if unit == 'kΩ':
        return round(ohm / 1000.0, 3), {'kohm': 'kΩ', 'ohm': 'Ω'}.get(u, u)
    return round(ohm, 1), {'kohm': 'kΩ', 'ohm': 'Ω'}.get(u, u)


def _usage_call(result_json, rates, role, e):
    u = (result_json or {}).get('usage') or {}
    if not u:
        return None, None
    c = round(cost(u, rates['rates']), 6)
    return c, {'seconds': None, 'cost': c, 'out_tokens': u.get('output_tokens'), 'in_tokens': u.get('input_tokens'),
               'reasoning_tokens': (u.get('output_tokens_details') or {}).get('reasoning_tokens'), 'role': role, 'ev': env(e)}


def _native_bounds(native_dir, object_id):
    m = json.load(open(pathlib.Path(native_dir) / 'crop-manifest.json'))
    o = next((x for x in m['objects'] if str(x['object_id']) == str(object_id)), None)
    return (o or {}).get('bounds_half_open'), (o or {}).get('confidence'), (o or {}).get('input_image_sha256'), len(m['objects'])


def _followup_classification(reg, state, basis):
    return {'pilot': False, 'counted': bool(reg.get('counted')), 'label': 'Official run · reading-assisted cohort · known to developers, not blind',
            'public_label': 'Official run · Spark did not know the fault', 'basis': basis,
            'cohort': {'plan': reg.get('cohort'), 'slot': reg.get('run_id'), 'ordinal': reg.get('attempt') or reg.get('attempt_ordinal'), 'state': state}}


def _photo_block(photos, state, binding=None, sam_count=None, pairing=None, note=None, documentary=False, display=None):
    """The photo block the pages render: a clean crop of the metadata-free SAM input and, where a record ties a native
    mask to a part or a candidate, a transparent outline layer drawn from that mask (tools/photo_derivatives.py)."""
    key = f'{state}_crop'
    if not photos.get(key):
        return None
    ph = {'board': photos.get(f'{state}_full'), 'crop': photos.get(key), 'crop_box': photos.get(f'{state}_crop_box'),
          'image': {'file': photos.get(key), 'width': photos.get('width', 1200), 'height': photos.get('height', 1600), 'sha256_sam_input': photos.get(f'{state}_sha256')},
          'sam': [{'concept': 'electronic component', 'match_count': sam_count, 'displayed': 1 if binding else 0,
                   'masks': ([{'object_id': binding.get('object_id'), 'bounds_half_open': binding.get('bounds'), 'confidence': binding.get('confidence'),
                               'overlay_file': photos.get(f'{state}_outline'), 'source_mask_file': binding.get('mask_file'), 'resize_to_box': False}] if binding else [])}],
          'vision': None, 'pairing': pairing, 'documentary': documentary, 'note': note, 'provenance': photos.get('provenance')}
    if display:
        ph['display_rule_image'] = display
    return ph


def extract_wire_pair(pair, case, label, rates, photos):
    """Case 05 layout (Codex, 11/4, benchmate.wire_path_pair_result.v1): a reading-assisted pair whose fault diagnosis ended
    in a structure proposal (a series resistor in place of the drawn wire W1), followed by the wire-path reading stage:
    the engine splits the one surviving proposal into two bounded placements of the same series resistance (an ENGINE
    RULE: the mini-board IN–OUT path carries it / the path is near-short and the resistance sits outside), Spark picks
    W1's resistance as the reading, bands are frozen per placement and per source and pushed, the board is photographed,
    SAM 3.1 segments it, Spark names the body that is W1 and the operator confirms, the operator reads the isolated path,
    the frozen bands score it, the seal opens. The pair's own restored child (attempt 1, abstained) is recorded on the
    run for the report; the restored rerun shown is the counted follow-up (see extract_timing_followup)."""
    pair = pathlib.Path(pair)
    res = json.load(open(pair / 'result.json'))
    reg = json.load(open(pair / 'registration.json'))
    pev = [json.loads(l) for l in open(pair / 'events.jsonl')]
    intake = intake_from_pair(pair, rates)
    child = pair / res['faulted_diagnosis']
    run = extract(child, case, label, intake, rates)
    run['pair_dir'] = pair.name; run['id'] = pair.name; run['child_id'] = child.name
    run['registration'] = {k: reg.get(k) for k in ('cohort', 'attempt', 'official', 'counted', 'selected_first_attempt', 'freeze_commit', 'blind_test', 'known_case_development')}
    run['pilot'], run['counted'] = False, bool(reg.get('counted'))
    run['classification'] = _followup_classification(reg, 'faulted', 'pair registration committed before the first request (registration.json)')
    t0 = ts(run['started_utc'])
    totals = dict(run['totals'])
    play, last_t = run['play_length_s'], max((e['t'] for e in run['events']), default=0.0)

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

    catalog = json.load(open(pair / 'wire-reading-catalog.json'))
    fc = json.load(open(pair / 'wire-reading-forecast.json'))
    obs = json.load(open(pair / 'wire-reading-observation.json'))
    sel = json.load(open(sorted((pair / 'wire-reading-selection').iterdir())[0] / 'result.json'))
    cand = json.load(open(sorted((pair / 'photo-faulted' / 'candidates-v3').iterdir())[0] / 'result.json'))
    proposal = json.load(open(pair / 'photo-faulted' / 'candidate-proposal.json'))
    confirm = json.load(open(pair / 'wire-path-confirmation.json'))
    native = pair / 'photo-faulted' / 'decoded' / 'native-SAM'
    rd = run.setdefault('reading', {'bands': [], 'binding': None, 'observed': None, 'scored': None})
    sealed = next((e for e in pev if e['kind'] == 'specimen_assembly_sealed' and e['payload'].get('state') == 'faulted'), None)
    if sealed:
        run['seal'] = {'sealed_sha256': sealed['payload']['sha256'], 'transmitted_to_model': sealed['payload'].get('transmitted_to_model'), 'sealed_ev': env(sealed)}
    fitted = next((x for x in run['structure'] if x['id'] == 'proposal:1'), None)
    r_fit = ((fitted or {}).get('fit') or {}).get('fitted_parameters') or {}
    unit = 'Ω'
    confirm_ev = next((e for e in pev if e['kind'] == 'wire_path_confirmed'), None)
    isol_ev = next((e for e in pev if e['kind'] == 'wire_path_isolation_confirmed'), None)
    for e in pev:
        k, p = e['kind'], e['payload']
        if k == 'reading_catalog_generated':
            # two bounded placements of the same validated series path: an engine rule, never a Spark proposal
            words = {'on_board_path:proposal:1': ('in the W1 path, on the board', 'the resistance sits in the mini-board W1 path and its contacts'),
                     'external_path:proposal:1': ('off the board, W1 path near-short', 'the mini-board W1 path is near-short and the resistance sits outside the mini board')}
            members = [{'id': x['id'], 'label': words.get(x['id'], (x['id'], x['id']))[0], 'words': words.get(x['id'], (x['id'], x['id']))[1], 'kind': 'R', 'a': 'IN', 'b': 'OUT', 'description': x.get('description')} for x in catalog['explanations']]
            g = {'base_explanation': 'proposal:1', 'members': members, 'source': 'engine_rule', 'split_base': True,
                 'reason': f"Generated by the engine from the verified terminal model (series path fitted at {fmt_ohm(r_fit.get('R2'))}): the terminal waveforms are the same wherever that resistance sits, so the measurement cannot place it. Both placements use the same model; nothing extra is fitted.",
                 'ev': env(e), 'catalog_sha256': p.get('sha256')}
            rd.setdefault('groups', []).append(g)
            add(e, 'equivalence_group', **{a: b for a, b in g.items() if a != 'ev'})
        elif k == 'reading_requested':
            c, call = _usage_call(sel, rates, 'chose the reading', e)
            if call:
                totals['spark_calls'] += 1; totals['spark_cost'] = round(totals['spark_cost'] + c, 6)
            rd.update({'component': p['component'], 'quantity': p['quantity'], 'reason': p['reason'], 'chosen_by': p['chosen_by'], 'request_ev': env(e),
                       'observable': 'the isolated mini-board IN–OUT path, W1 and its socket contacts left in place, all three leads lifted from the fixture'})
            add(e, 'reading_requested', component=p['component'], quantity=p['quantity'], reason=p['reason'], chosen_by=p['chosen_by'], calls=[call] if call else [])
        elif k == 'wire_reading_forecast_frozen':
            bands, unit = _band_rows(fc, obs.get('meter_range'), fc['request'].get('quantity'))
            rd['bands'] = bands
            rd['sha_full'] = p.get('forecast_sha256'); rd['sha'] = (rd['sha_full'] or '')[:10]; rd['frozen_ev'] = env(e)
            totals['forecasts_frozen'] += 1
            add(e, 'reading_forecast_frozen', bands=bands, sha=rd['sha'], sha_full=rd['sha_full'])
        elif k == 'wire_reading_forecast_publication':
            rd.update({'published': p.get('published'), 'commit': p.get('commit'), 'url': p.get('url'), 'publish_ev': env(e)})
            add(e, 'reading_forecast_published', commit=p.get('commit'), url=p.get('url'), sha=rd['sha'])
        elif k == 'board_photo_received':
            add(e, 'board_photo', sha256=p.get('sha256'), new_capture=p.get('new_capture_operator_confirmed'))
        elif k == 'sam_localization_finished':
            n = _native_bounds(native, proposal['sam_body'].split('-')[-1])[3]
            totals['sam_calls'] = totals.get('sam_calls', 0) + int(p.get('requests') or 0)
            totals['sam_cost'] = round(totals.get('sam_cost', 0.0) + 0.0025 * int(p.get('requests') or 0), 6)
            add(e, 'sam_done', requests=p.get('requests'), masks=n, bodies=n)
        elif k == 'body_candidates_proposed':
            c, call = _usage_call(cand, rates, 'pointed at the body', e)
            if call:
                totals['spark_calls'] += 1; totals['spark_cost'] = round(totals['spark_cost'] + c, 6)
            bounds, conf, in_sha, n = _native_bounds(native, p['sam_body'].split('-')[-1])
            rd['binding'] = {'sam_body': p['sam_body'], 'component': p['component'], 'chosen_by': p['chosen_by'], 'reason': p['reason'],
                             'candidates': p.get('candidate_bodies'), 'mapping_status': p.get('mapping_status'),
                             'operator_confirmed': bool(confirm.get('candidate_operator_confirmed')), 'operator_verbatim': confirm.get('operator_verbatim'),
                             'confirm_ev': env(confirm_ev) if confirm_ev else None, 'localizer': 'native SAM 3.1 mask',
                             'photo': photos.get('faulted_crop'), 'overlay_file': photos.get('faulted_outline'), 'crop_box': photos.get('faulted_crop_box'),
                             'bounds': bounds, 'confidence': conf, 'input_image_sha256': in_sha, 'bodies': n, 'object_id': p['sam_body'].split('-')[-1],
                             'calls': [call] if call else [], 'ev': env(e)}
            add(e, 'body_binding', **{a: b for a, b in rd['binding'].items() if a != 'ev'})
        elif k == 'reading_observed':
            v, raw_unit = _observed_value(p, unit)
            setup = (isol_ev or {}).get('payload', {}).get('setup') or {}
            rd['observed'] = {'component': p['component'], 'value': v, 'unit': unit, 'source': p['source'], 'raw_value': p.get('value'), 'raw_unit': raw_unit,
                              'note': 'USB off, all three leads lifted from the fixture, W1 and its contacts left in place' if setup.get('all_three_fixture_leads_disconnected') else None,
                              'power_off': p.get('power_off_confirmed'), 'isolated': p.get('component_isolated_confirmed'), 'meter_range': p.get('meter_range'),
                              'operator_verbatim': (isol_ev or {}).get('payload', {}).get('operator_verbatim'), 'photo': None,
                              'evidence_link': None, 'evidence_sha256': (p.get('photo') or {}).get('sha256'), 'ev': env(e)}
            add(e, 'reading_observed', **{a: b for a, b in rd['observed'].items() if a != 'ev'})
        elif k == 'wire_reading_scored':
            if not any(b['source'] == rd['observed']['source'] for b in rd['bands']):
                sys.exit('wire_reading_scored without a frozen band for the reported source')
            rd['scored'] = {'fits': p['fits'], 'ruled_out': p.get('ruled_out_by_reading') or [], 'outcome_raw': p.get('outcome'),
                            'forecast_sha256': p.get('forecast_sha256'), 'observation_sha256': p.get('observation_sha256'), 'refitted': p.get('refitted'), 'ev': env(e)}
            rd['outcome'] = {'one_explanation_remains': 'one', 'indistinguishable': 'several', 'all_explanations_rejected': 'none'}.get(p.get('outcome'), 'one' if len(p['fits']) == 1 else ('none' if not p['fits'] else 'several'))
            add(e, 'reading_scored', fits=p['fits'], ruled_out=rd['scored']['ruled_out'], outcome=rd['outcome'])
        elif k == 'specimen_seal_opened':
            got = seal_from_pair(run, pev, rd['scored']['fits'])
            if got:
                opened, truth = got
                add(opened, 'seal_opened', truth=truth, matches=run['seal']['matches_commitment'])
            break
    # the pair's own restored attempt: reached a verdict (abstained), counted, not rendered as a replay; the counted follow-up is
    rfin = next((e for e in pev if e['kind'] == 'diagnosis_finished' and e['payload'].get('state') == 'restored'), None)
    if rfin:
        ar = rfin['payload'].get('agent_report') or {}
        run['restored_attempts'] = [{'attempt': 1, 'record': res.get('restored_diagnosis'), 'verdict': ar.get('verdict'), 'text': ar.get('explanation'), 'ev': env(rfin), 'counted': True, 'caption': res.get('restored_caption')}]
    run['totals'] = totals
    run['play_length_s'] = round(play, 2)
    run['photo'] = _photo_block(photos, 'faulted', binding=rd.get('binding'), sam_count=(rd.get('binding') or {}).get('bodies'),
                                pairing='Spark pointed at sam-1 as W1; confirmed by the operator',
                                note='Photo untouched apart from the outline: the boundary of the native SAM 3.1 mask Spark named as W1.')
    run['verify_command'] = 'python -m benchmate.reading_wire_stage verify <pair folder>'
    return run


def fmt_ohm(v):
    if v is None:
        return 'the fitted value'
    return f'{v / 1000:.2f} kΩ' if v >= 1000 else f'{v:.0f} Ω'


def extract_timing_followup(rec, pair, case, rates, photos, verify_outputs=None):
    """Case 05 restored rerun (Codex, 11/4, benchmate.frame_timing_restored_followup.v4): a counted restored attempt 2 in its
    own record, a normal v2 run registered against the original pair, whose own restored attempt had abstained. The
    frame-anchored timing model it runs on was published before this run (registration.qualification_file)."""
    rec, pair = pathlib.Path(rec), pathlib.Path(pair)
    reg = json.load(open(rec / 'registration.json'))
    res = json.load(open(rec / 'result.json'))
    pev = [json.loads(l) for l in open(pair / 'events.jsonl')]
    intake = intake_from_pair(pair, rates)
    run = extract(rec, case, 'Restored rerun', intake, rates)
    run['pilot'], run['counted'] = False, bool(reg.get('counted'))
    run['classification'] = _followup_classification(reg, 'restored', 'follow-up registration committed before the first request (registration.json), linked to the pair by head sha256; attempt 2 after the pair’s own restored attempt abstained')
    run['registration'] = {k: reg.get(k) for k in ('cohort', 'attempt_ordinal', 'official', 'counted', 'selected_first_attempt', 'blind_test', 'original_pair', 'original_restored_verdict', 'qualification_file')}
    restore_ev = next((e for e in pev if e['kind'] == 'operator_restoration_confirmed'), None)
    nr = next((e for e in pev if e['kind'] == 'restored_photo_not_repeated'), None)
    rfin = next((e for e in pev if e['kind'] == 'diagnosis_finished' and e['payload'].get('state') == 'restored'), None)
    ar = ((rfin or {}).get('payload') or {}).get('agent_report') or {}
    run['pair'] = {'of': pair.name, 'operator_restored': True, 'state': 'restored', 'attempt': reg.get('attempt_ordinal'),
                   'restore_ev': env(restore_ev) if restore_ev else None,
                   'restored_what': ((nr or {}).get('payload') or {}).get('operator_report', {}).get('operator_statement'),
                   'external_only': bool(((nr or {}).get('payload') or {}).get('operator_report', {}).get('only_external_fault_removed')),
                   'previous_attempt': {'attempt': 1, 'record': pair.name, 'verdict': ar.get('verdict'), 'text': ar.get('explanation'), 'ev': env(rfin) if rfin else None, 'counted': True,
                                        'note': 'The pair’s own restored rerun ended abstained: the drawing’s model missed the 0–5 ms region of both steps by 9.3 and 10.2 mV. The channel-timing model used from here on was qualified and published before this attempt.'},
                   'timing_model': res.get('timing_model_version')}
    run['display_caption'] = res.get('display_caption') or 'No mismatch in the tests Spark chose'
    if photos.get('faulted_crop'):
        run['photo'] = _photo_block(photos, 'faulted', documentary=True, sam_count=_native_bounds(pair / 'photo-faulted' / 'decoded' / 'native-SAM', '1')[3],
                                    note='The mini board was not changed by the restoration: only the 20 kΩ resistor outside it was removed, so no new photo was taken. This is the original fault-state capture, shown as recorded; nothing was identified or read from it.')
    if verify_outputs:
        run['verify_outputs'] = verify_outputs
    run['verify_command'] = 'python -m benchmate verify <record folder>'
    return run


def extract_chain(root, case, label, rates, photos, verify_outputs=None):
    """Case 03 layout (Codex, 11/4): one restored-only root record (benchmate.restored_after_photo_observation.v5) that
    carries the whole chain under history/reading/: the original pair (fault diagnosis, Spark's reading request, bands frozen
    and pushed, the photo and SAM; it then stopped on a local input error before Spark's body call), the photo-binding
    follow-up (Spark named the body), the reading continuation (operator confirmation, the isolated reading, the score,
    the seal), and at the root the restored diagnosis plus a documentary restored photo. Returns (fault_run, restored_run)."""
    root = pathlib.Path(root)
    rd_rec = root / 'history' / 'reading'
    orig = rd_rec / 'history' / 'original'
    bf = rd_rec / 'history' / 'body-followup'
    rreg = json.load(open(root / 'registration.json'))
    oreg = json.load(open(orig / 'registration.json'))
    rdreg = json.load(open(rd_rec / 'registration.json'))
    oev = [json.loads(l) for l in open(orig / 'events.jsonl')]
    bev = [json.loads(l) for l in open(bf / 'events.jsonl')]
    cev = [json.loads(l) for l in open(rd_rec / 'events.jsonl')]
    rev = [json.loads(l) for l in open(root / 'events.jsonl')]
    intake = intake_from_pair(orig, rates)
    child = sorted((orig / 'diagnosis-faulted').iterdir())[0]
    run = extract(child, case, label, intake, rates)
    run['pair_dir'] = oreg.get('run_id') or orig.name; run['id'] = run['pair_dir']; run['child_id'] = child.name  # the copy under history/ keeps the pair's registered id
    run['registration'] = {k: oreg.get(k) for k in ('cohort', 'attempt', 'official', 'counted', 'selected_first_attempt', 'freeze_commit', 'blind_test', 'known_case_development')}
    run['pilot'], run['counted'] = False, bool(oreg.get('counted'))
    run['classification'] = _followup_classification(oreg, 'faulted', 'pair registration committed before the first request (registration.json); the photo-binding follow-up and the reading continuation are registered separately and linked by head sha256')
    run['classification']['linked_records'] = {'photo_binding_followup_head_sha256': rdreg.get('body_followup_head_sha256'),
                                               'reading_continuation': rdreg.get('run_id'), 'restored_continuation': rreg.get('run_id')}
    t0 = ts(run['started_utc'])
    totals = dict(run['totals'])
    play, last_t = run['play_length_s'], max((e['t'] for e in run['events']), default=0.0)

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

    fc = json.load(open(rd_rec / 'reading-forecast.json'))
    obs = json.load(open(rd_rec / 'reading-observation.json'))
    sel = json.load(open(sorted((orig / 'reading-selection').iterdir())[0] / 'result.json'))
    bres = json.load(open(sorted((bf / 'spark').iterdir())[0] / 'result.json'))
    binding = json.load(open(rd_rec / 'body-binding.json'))
    native = orig / 'photo-faulted' / 'decoded' / 'native-SAM'
    rd = run.setdefault('reading', {'bands': [], 'binding': None, 'observed': None, 'scored': None})
    sealed = next((e for e in oev if e['kind'] == 'specimen_assembly_sealed' and e['payload'].get('state') == 'faulted'), None)
    if sealed:
        run['seal'] = {'sealed_sha256': sealed['payload']['sha256'], 'transmitted_to_model': sealed['payload'].get('transmitted_to_model'), 'sealed_ev': env(sealed)}
    unit = 'Ω'
    # ---- the original pair after its diagnosis
    for e in oev:
        k, p = e['kind'], e['payload']
        if k == 'reading_requested':
            c, call = _usage_call(sel, rates, 'chose the reading', e)
            if call:
                totals['spark_calls'] += 1; totals['spark_cost'] = round(totals['spark_cost'] + c, 6)
            rd.update({'component': p['component'], 'quantity': p['quantity'], 'reason': p['reason'], 'chosen_by': p['chosen_by'], 'request_ev': env(e)})
            add(e, 'reading_requested', component=p['component'], quantity=p['quantity'], reason=p['reason'], chosen_by=p['chosen_by'], calls=[call] if call else [])
        elif k == 'reading_forecast_frozen':
            bands, unit = _band_rows(fc, obs.get('meter_range'), fc['request'].get('quantity'))
            rd['bands'] = bands
            rd['sha_full'] = p.get('sha256'); rd['sha'] = (rd['sha_full'] or '')[:10]; rd['frozen_ev'] = env(e)
            totals['forecasts_frozen'] += 1
            add(e, 'reading_forecast_frozen', bands=bands, sha=rd['sha'], sha_full=rd['sha_full'])
        elif k == 'reading_forecast_publication':
            rd.update({'published': p.get('published'), 'commit': p.get('commit'), 'url': p.get('url'), 'publish_ev': env(e)})
            rd['sha_full'] = rd.get('sha_full') or p.get('sha256'); rd['sha'] = (rd['sha_full'] or '')[:10]
            add(e, 'reading_forecast_published', commit=p.get('commit'), url=p.get('url'), sha=rd['sha'])
        elif k == 'board_photo_received':
            add(e, 'board_photo', sha256=p.get('sha256'), new_capture=p.get('new_capture_operator_confirmed'))
        elif k == 'sam_localization_finished':
            n = _native_bounds(native, '1')[3]
            totals['sam_calls'] = totals.get('sam_calls', 0) + int(p.get('requests') or 0)
            totals['sam_cost'] = round(totals.get('sam_cost', 0.0) + 0.0025 * int(p.get('requests') or 0), 6)
            add(e, 'sam_done', requests=p.get('requests'), masks=n, bodies=n)
        elif k == 'run_failed':
            run['continuation'] = {'stopped_at': p.get('stage'), 'error': p.get('error'), 'ev': env(e), 'counted_failure': True,
                                   'line': 'The pair record stopped here on a local input error (KeyError) while preparing Spark’s body call; no model was called. The failure is counted. The chain continues in two linked records, registered first and tied to this one by head sha256.'}
            add(e, 'binding_stopped', stage=p.get('stage'), error=p.get('error'), line=run['continuation']['line'])
    # ---- the photo-binding follow-up: Spark names the body
    for e in bev:
        k, p = e['kind'], e['payload']
        if k == 'body_candidates_proposed':
            c, call = _usage_call(bres, rates, 'pointed at the body', e)
            if call:
                totals['spark_calls'] += 1; totals['spark_cost'] = round(totals['spark_cost'] + c, 6)
            bounds, conf, in_sha, n = _native_bounds(native, p['sam_body'].split('-')[-1])
            conf_ev = next((x for x in cev if x['kind'] == 'body_binding'), None)
            rd['binding'] = {'sam_body': p['sam_body'], 'component': p['component'], 'chosen_by': p['chosen_by'], 'reason': p['reason'],
                             'candidates': p.get('candidate_bodies'), 'mapping_status': p.get('mapping_status'),
                             'operator_confirmed': bool(binding.get('operator_confirmed')), 'operator_verbatim': binding.get('operator_verbatim'),
                             'confirm_ev': env(conf_ev) if conf_ev else None, 'localizer': 'native SAM 3.1 mask',
                             'photo': photos.get('faulted_crop'), 'overlay_file': photos.get('faulted_outline'), 'crop_box': photos.get('faulted_crop_box'),
                             'bounds': bounds, 'confidence': conf, 'input_image_sha256': in_sha, 'bodies': n, 'object_id': p['sam_body'].split('-')[-1],
                             'calls': [call] if call else [], 'ev': env(e)}
            add(e, 'body_binding', **{a: b for a, b in rd['binding'].items() if a != 'ev'})
    # ---- the reading continuation: the operator reads, the bands score, the seal opens
    for e in cev:
        k, p = e['kind'], e['payload']
        if k == 'reading_observed':
            v, raw_unit = _observed_value(p, unit)
            rep = next((x for x in cev if x['kind'] == 'operator_reading_reported'), None)
            rd['observed'] = {'component': p['component'], 'value': v, 'unit': unit, 'source': p['source'], 'raw_value': p.get('value'), 'raw_unit': raw_unit,
                              'note': 'power off, both leads lifted' if p.get('component_isolated_confirmed') else None,
                              'power_off': p.get('power_off_confirmed'), 'isolated': p.get('component_isolated_confirmed'), 'meter_range': p.get('meter_range'),
                              'operator_verbatim': ((rep or {}).get('payload') or {}).get('operator_verbatim'), 'photo': None,
                              'evidence_link': None, 'evidence_sha256': (p.get('photo') or {}).get('sha256'), 'ev': env(e)}
            add(e, 'reading_observed', **{a: b for a, b in rd['observed'].items() if a != 'ev'})
        elif k == 'reading_scored':
            if not any(b['source'] == rd['observed']['source'] for b in rd['bands']):
                sys.exit('reading_scored without a frozen band for the reported source')
            rd['scored'] = {'fits': p['fits'], 'ruled_out': p.get('ruled_out_by_reading') or [], 'outcome_raw': p.get('outcome'),
                            'forecast_sha256': p.get('forecast_sha256'), 'observation_sha256': p.get('observation_sha256'), 'refitted': p.get('refitted'), 'ev': env(e)}
            rd['outcome'] = {'one_explanation_remains': 'one', 'indistinguishable': 'several', 'all_explanations_rejected': 'none'}.get(p.get('outcome'), 'one' if len(p['fits']) == 1 else ('none' if not p['fits'] else 'several'))
            add(e, 'reading_scored', fits=p['fits'], ruled_out=rd['scored']['ruled_out'], outcome=rd['outcome'])
        elif k == 'specimen_seal_opened':
            got = seal_from_pair(run, cev, rd['scored']['fits'])
            if got:
                opened, truth = got
                add(opened, 'seal_opened', truth=truth, matches=run['seal']['matches_commitment'])
            break
    run['totals'] = totals
    run['play_length_s'] = round(play, 2)
    run['photo'] = _photo_block(photos, 'faulted', binding=rd.get('binding'), sam_count=(rd.get('binding') or {}).get('bodies'),
                                pairing='Spark pointed at sam-1 as R1; confirmed by the operator',
                                note='Photo untouched apart from the outline: the boundary of the native SAM 3.1 mask Spark named as R1.')
    run['verify_command'] = 'PYTHONPATH=src python -S -m benchmate.reading_restored_after_photo_v5 verify <record folder>'
    if verify_outputs and verify_outputs.get('fault'):
        run['verify_outputs'] = verify_outputs['fault']

    # ---- the restored rerun at the root: fresh context, then a documentary restored photo
    rchild = sorted((root / 'diagnosis-restored').iterdir())[0]
    rrun = extract(rchild, case, 'Restored rerun', intake, rates)
    rrun['id'] = root.name; rrun['child_id'] = rchild.name; rrun['pair_dir'] = root.name
    rrun['pilot'], rrun['counted'] = False, bool(rreg.get('counted'))
    rrun['classification'] = _followup_classification(rreg, 'restored', 'restored continuation registered before its first request (registration.json), linked to the reading record by head sha256')
    rrun['registration'] = {k: rreg.get(k) for k in ('cohort', 'attempt', 'official', 'counted', 'state', 'followup_of', 'original_primary_status', 'original_selection_unchanged')}
    restore_ev = next((e for e in rev if e['kind'] == 'operator_restoration_confirmed'), None)
    rrep = json.load(open(root / 'operator-restoration-report.json')) if (root / 'operator-restoration-report.json').exists() else {}
    rres = json.load(open(root / 'result.json')) if (root / 'result.json').exists() else {}
    scope = json.load(open(root / 'restored-photo-scope.json')) if (root / 'restored-photo-scope.json').exists() else {}
    rrun['pair'] = {'of': run['id'], 'operator_restored': True, 'state': 'restored', 'restore_ev': env(restore_ev) if restore_ev else None,
                    'restored_what': rrep.get('operator_verbatim'),
                    'closeout': {'restored_verdict': rres.get('restored_verdict'), 'restored_photo_documentary_only': scope.get('SAM_role') == 'documentary_display_only',
                                 'restored_binding_performed': bool(scope.get('Spark_binding_requests')), 'SAM_used_as_identification_evidence': bool(scope.get('component_identity_claimed')),
                                 'photo_SAM_requests': 1, 'photo_Spark_requests': scope.get('Spark_binding_requests', 0)}}
    rrun['display_caption'] = rres.get('restored_caption') or 'No mismatch in the tests Spark chose'
    sam_ev = next((e for e in rev if e['kind'] == 'sam_localization_finished'), None)
    rnative = root / 'photo-restored' / 'decoded' / 'native-SAM'
    nm = len(json.load(open(rnative / 'crop-manifest.json'))['objects']) if (rnative / 'crop-manifest.json').exists() else None
    if sam_ev:
        rrun['totals']['sam_calls'] = rrun['totals'].get('sam_calls', 0) + int(sam_ev['payload'].get('requests') or 0)
        rrun['totals']['sam_cost'] = round(rrun['totals'].get('sam_cost', 0.0) + 0.0025 * int(sam_ev['payload'].get('requests') or 0), 6)
    if photos.get('restored_crop'):
        rrun['photo'] = _photo_block(photos, 'restored', documentary=True, sam_count=nm,
                                     note=f"Documentary photo of the restored board, untouched. SAM 3.1 returned {nm} masks; nothing was identified or read from it and no body was paired with a part.",
                                     display={'file': photos.get('restored_documentary'), 'displayed': nm,
                                              'note': f"Documentary: the same photo with every native SAM 3.1 mask outlined ({nm} of {nm}). Not an identification; declared display-only before the photo was taken (restored-photo-scope.json)."})
    if verify_outputs and verify_outputs.get('restored'):
        rrun['verify_outputs'] = verify_outputs['restored']
    rrun['verify_command'] = 'PYTHONPATH=src python -S -m benchmate.reading_restored_after_photo_v5 verify <record folder>'
    return run, rrun


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
        if e['kind'] in ('reading_forecast_published', 'board_photo', 'sam_done', 'seal_opened', 'binding_abstained', 'binding_stopped', 'body_group',
                         'group_reading_forecast', 'group_reading_observed', 'group_reading_scored') and (e['ev']['seq'], e['ev']['kind']) not in {(x['ev']['seq'], x['ev']['kind']) for x in out if x.get('ev')}:
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
                        'state': (run.get('pair') or {}).get('state') or ('faulted' if (run.get('reading') or run.get('seal')) else None),
                        'display_caption': run.get('display_caption'),
                        'reading': ('group' if (run.get('reading') or {}).get('group') else 'one' if (run.get('reading') or {}).get('observed') else None),
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
    if len(sys.argv) > 1 and sys.argv[1] in ('--pair', '--followup', '--pair-terminal', '--pair-group', '--pair-wire', '--pair-chain'):
        ap = argparse.ArgumentParser()
        ap.add_argument(sys.argv[1], dest='rec', required=True, help='pair folder (reading-assisted cohort) or follow-up record folder')
        ap.add_argument('--case', required=True)
        ap.add_argument('--label', required=True)
        ap.add_argument('--rates', required=True, help='any JSON with rates_usd_per_million')
        ap.add_argument('--photos', default=None, help='JSON {board, overlay, outline, crop, evidence}: site-relative paths of sanitized derivatives')
        ap.add_argument('--pair-of', default=None)
        ap.add_argument('--amendment', default=None, help='JSON file describing a public design amendment made before any measurement')
        ap.add_argument('--group', default=None, help='unordered reading supplement record (benchmate.unordered_reading_supplement.v1)')
        ap.add_argument('--restored', default=None, help='restored continuation record (unordered_restored_continuation.v2, or the frame-timing follow-up record for --pair-wire)')
        ap.add_argument('--extra', default=None, help='folder with the pair files that sit too deep to stage: binding-result.json, faulted-sam-decoded.json, sam-display-manifest.json')
        ap.add_argument('--verify', default=None, help='JSON {fault: [lines], restored: [lines]}: outputs of the keyless verifiers, run on the public copies, copied as written')
        a = ap.parse_args()
        cj = json.load(open(a.rates))
        rates = {'rates': cj['rates_usd_per_million'], 'source': 'https://dev.meta.ai/docs/pricing-rate-limits'}
        photos = json.load(open(a.photos)) if a.photos else {}
        verify = json.load(open(a.verify)) if a.verify else {}
        if sys.argv[1] == '--pair-wire':
            fault = extract_wire_pair(a.rec, a.case, a.label, rates, photos)
            if verify.get('fault'):
                fault['verify_outputs'] = verify['fault']
            fault['timeline'] = timeline_pair(fault)
            write_run(fault, a.case, a.label)
            if a.restored:
                restored = extract_timing_followup(a.restored, a.rec, a.case, rates, photos, verify.get('restored'))
                restored['timeline'] = timeline(restored)
                write_run(restored, a.case, restored['label'], fault['id'])
            return
        if sys.argv[1] == '--pair-chain':
            fault, restored = extract_chain(a.rec, a.case, a.label, rates, photos, verify)
            fault['timeline'] = timeline_pair(fault)
            restored['timeline'] = timeline(restored)
            write_run(fault, a.case, a.label)
            write_run(restored, a.case, restored['label'], fault['id'])
            return
        if sys.argv[1] == '--pair-group':
            fault, restored = extract_group_pair(a.rec, a.group, a.restored, a.case, a.label, rates, photos, pathlib.Path(a.extra or a.rec))
            fault['timeline'] = timeline_pair(fault)
            restored['timeline'] = timeline(restored)
            write_run(fault, a.case, a.label)
            write_run(restored, a.case, restored['label'], fault['id'])
            return
        if sys.argv[1] == '--pair-terminal':
            amend = json.load(open(a.amendment)) if a.amendment else None
            fault, restored = extract_terminal_pair(a.rec, a.case, a.label, rates, photos, amend)
            fault['timeline'] = timeline_pair(fault)
            restored['timeline'] = timeline(restored)
            write_run(fault, a.case, a.label)
            write_run(restored, a.case, restored['label'], fault['id'])
            return
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
