"""DEV ONLY. Builds tools/DEV-structure-run.json to exercise the structure-proposal scene, the held-back
check stage and the counted-run end scene in the replay. It uses Pilot A's timeline for pacing and the
retained MOCK events from Codex's contract example (scripted_controller, not Spark) for the case-04
hypotheses, the proposal and its fit. The explanations come from the example's own
component_hypotheses_fitted (R1, R2 against the divider design), never from Pilot A's RC case.
The two held-back "scored" entries are placeholders copied from the proposal's training checks, flagged
dev_placeholder, so the page's check stage renders; they are not measurements. The file carries dev:true,
the page watermarks it, and it is never listed in data/runs/index.json. Not a real run.
"""
import json, pathlib, copy, sys
SITE = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SITE / 'tools'))
from extract_runs import env, elements_of, hyp, netlist_diff, decided, regions_of, check_against_design

run = json.loads((SITE / 'data/runs/20261102T160841-eff2b65334.json').read_text())
ex = json.loads((SITE / 'tools/fixtures/structure-events.example.json').read_text())
ev = {e['kind']: e for e in ex['events']}
fitted = ev['component_hypotheses_fitted']
rows = [hyp(h) for h in fitted['payload']['hypotheses']]

run = copy.deepcopy(run)
run['id'] = 'DEV-structure-fixture'; run['label'] = 'DEV fixture'; run['dev'] = True
run['pilot'] = False; run['counted'] = False
run['classification'] = {'pilot': False, 'counted': False, 'label': 'DEV fixture — not a run', 'basis': 'tools/make_dev_fixture.py', 'cohort': None}
run['case'] = '04'
run['design'] = elements_of(fitted['payload']['hypotheses'][0]['model'])  # the divider: R1, R2
check_against_design(run['design'], rows, 'DEV fixture')
run['note_after'] = None

# keep Pilot A's pacing up to its last fit; replace every explanation with the example's own
keep = ('spark_choice', 'forecast_frozen', 'bench_request', 'operator_confirm', 'capture', 'fit_result', 'ruled_out')
tl = [e for e in run['timeline'] if e['kind'] in keep and not e.get('verification') and not e.get('final')]
ids = [r['id'] for r in rows]
for st in run['steps']:
    st['forecasts'] = [{'id': i, 'v': st['forecasts'][0]['v']} for i in ids[:len(st['forecasts']) or 1]]  # pacing only; DEV
    st['fit'] = rows
nsteps = len([e for e in tl if e['kind'] == 'fit_result'])
fits = [e for e in tl if e['kind'] == 'fit_result']
tl = [e for e in tl if e['kind'] != 'ruled_out']
for k, f in enumerate(fits):
    f['results'] = [{'id': r['id'], 'miss_mV': r['miss_mV'][min(k, len(r['miss_mV']) - 1)],
                     'decided_mV': r['decided_mV'][min(k, len(r['decided_mV']) - 1)], 'worst_region': r['worst_region'][min(k, len(r['worst_region']) - 1)],
                     'regions': r['regions'][min(k, len(r['regions']) - 1)],
                     'passed_this_step': r['passed'][min(k, len(r['passed']) - 1)],
                     'adequate': (k < nsteps - 1) and r['id'] == 'nominal', 'status': 'adequate' if ((k < nsteps - 1) and r['id'] == 'nominal') else 'inadequate',
                     'value': r['value'], 'kind': r['kind'], 'changed': r['changed']} for r in rows]
    f['all_inadequate'] = (k == nsteps - 1)
for e in tl:
    if e['kind'] == 'forecast_frozen':
        e['ids'] = ids if e['step'] == 1 else ['nominal']
dead = {}
extra = []
for f in fits:
    for r in f['results']:
        if not r['adequate'] and r['id'] not in dead:
            dead[r['id']] = f['step']
            extra.append({'t_log': f['t_log'] + 0.3, 't_play': f['t_play'] + 0.3, 'kind': 'ruled_out', 'totals': f['totals'], 'ev': f.get('ev'), 'step': f['step'], 'id': r['id'], 'miss_mV': r['miss_mV']})
tl += extra
tl.sort(key=lambda e: e['t_play'])
last = max(e['t_play'] for e in tl)
t = last + 2
p = ev['structure_proposed']; f = ev['structure_fit']
prop_el = elements_of(p['payload'])
tl.append({'t_log': t, 't_play': t, 'kind': 'structure_proposed', 'totals': fits[-1]['totals'], 'ev': env(p), 'id': p['payload']['id'],
           'elements': prop_el, 'diff': netlist_diff(run['design'], prop_el), 'rationale': p['payload']['rationale'], 'selected_by': p['payload']['selected_by']})
row = hyp(f['payload'])
tl.append({'t_log': t + 3, 't_play': t + 3, 'kind': 'structure_fit', 'totals': fits[-1]['totals'], 'ev': env(f), 'id': row['id'], 'status': row['status'], 'error': row.get('error'),
           'miss_mV': row['decided_mV'][-1] if row['decided_mV'] else None, 'misses': row['decided_mV'], 'passed': row['passed'], 'fitted_parameters': row['fitted_parameters'],
           'simulator_calls': f['payload'].get('simulator_calls'), 'elements': row['elements']})
tl.append({'t_log': t + 5, 't_play': t + 5, 'kind': 'verification_requested', 'totals': fits[-1]['totals'], 'ev': None, 'calls': []})
# DEV placeholders for the check stage: numbers copied from the proposal's training checks, flagged
run['reserved'] = run['reserved'] or [{'kind': 'step', 'amplitude_v': 0.35}, {'kind': 'sine', 'amplitude_v': 0.65, 'frequency_hz': 5}]
checks = f['payload'].get('training_checks') or []
run['verification'] = {'sha': 'DEVFIXTURE', 'reserved': run['reserved'], 'forecasts': [], 'observations': [], 'scored': []}
for i in (1, 2):
    c = checks[min(i, len(checks) - 1)]
    dm, wr = decided(c)
    cond = {row['id']: {'RMS_mV': round(c['RMS_mV'], 2), 'passed': c['passed'], 'regions': regions_of(c), 'decided_mV': dm, 'worst_region': wr, 'dev_placeholder': True}}
    run['verification']['scored'].append({'index': i, 'conditional': cond, 'dev_placeholder': True})
    tl.append({'t_log': t + 5 + 2 * i, 't_play': t + 5 + 2 * i, 'kind': 'verification_observed', 'totals': fits[-1]['totals'], 'ev': None, 'index': i})
    tl.append({'t_log': t + 6 + 2 * i, 't_play': t + 6 + 2 * i, 'kind': 'verification_scored', 'totals': fits[-1]['totals'], 'ev': env(f), 'index': i, 'conditional': cond, 'dev_placeholder': True})
tl.append({'t_log': t + 11, 't_play': t + 11, 'kind': 'report', 'totals': fits[-1]['totals'], 'ev': env(f), 'verdict': 'structure_supported', 'survivors': [row['id']], 'components': None,
           'text': 'DEV FIXTURE: verdict text invented only to exercise the page.'})
run['structure'] = [{'id': row['id'], 'elements': prop_el, 'diff': netlist_diff(run['design'], prop_el), 'rationale': p['payload']['rationale'], 'selected_by': p['payload']['selected_by'], 'fit': row}]
run['outcome'] = {'kind': 'report', 'verdict': 'structure_supported', 'survivors': [row['id']], 'text': 'DEV FIXTURE'}
run['timeline'] = tl; run['play_length_s'] = t + 12
(SITE / 'tools/DEV-structure-run.json').write_text(json.dumps(run, separators=(',', ':')))
print('wrote tools/DEV-structure-run.json', len(tl), 'events; explanations', ids)
