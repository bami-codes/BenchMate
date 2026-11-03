"""DEV ONLY. Builds tools/DEV-reading-run.json to exercise the reading stage in the replay and report.

It takes Pilot A (case 01, real timeline up to its last fit) and appends an invented reading stage:
Spark asks for R1's resistance; bands are frozen per explanation and per source (dmm 23.9–26.4 kΩ for
"R1 changed", 4.47–4.93 kΩ for "a resistor outside the board"; marking bands that cannot separate);
a body binding; an observed 4.71 kΩ operator_dmm reading; a score with one fit. The guard stop and the
pilot ending are dropped so the counted-run end scene renders. The file carries dev:true, the page
watermarks it, and it is never listed in data/runs/index.json. Not a real run.
"""
import json, pathlib, copy
SITE = pathlib.Path(__file__).resolve().parents[1]

run = json.loads((SITE / 'data/runs/20261102T160841-eff2b65334.json').read_text())
run = copy.deepcopy(run)
run['id'] = 'DEV-reading-fixture'; run['label'] = 'DEV reading fixture'; run['dev'] = True
run['pilot'] = False; run['counted'] = False
run['classification'] = {'pilot': False, 'counted': False, 'label': 'DEV fixture — not a run', 'basis': 'tools/make_dev_reading_fixture.py', 'cohort': None}
run['note_after'] = None

keep = ('spark_choice', 'forecast_frozen', 'bench_request', 'operator_confirm', 'capture', 'fit_result', 'ruled_out')
tl = [e for e in run['timeline'] if e['kind'] in keep and not e.get('verification') and not e.get('final')]
fits = [e for e in tl if e['kind'] == 'fit_result']
last_fit = fits[-1]
# after the last real fit, the ENGINE RULE splits the surviving "R1 changed" into electrically equivalent
# members: R1 itself changed, or an extra resistor between IN and R1 (same waveforms at the terminals).
t = max(e['t_play'] for e in tl) + 2
tot = last_fit['totals']
ev0 = {'seq': 9001, 'ts': '2026-11-02T16:30:00+00:00', 'kind': 'DEV', 'sha256': 'DEV' * 21 + 'D', 'prev': 'DEV' * 21 + 'D'}
def E(seq, kind): return {**ev0, 'seq': seq, 'kind': kind}
EQ = 'equiv:R1:series'
group = {'base_explanation': 'changed:R1', 'members': [{'id': EQ, 'label': 'an extra resistor between IN and R1', 'words': 'an extra resistor between IN and R1', 'kind': 'R', 'a': 'IN', 'b': 'R1'}],
         'source': 'engine_rule', 'reason': 'DEV FIXTURE: a resistor in series before R1 adds to the same path; terminal measurements see only the sum.'}
tl.append({'t_log': t, 't_play': t, 'kind': 'equivalence_group', 'totals': tot, 'ev': E(9001, 'equivalence_group'), **group})
run['structure'] = []

bands = [
    {'explanation': 'changed:R1', 'source': 'operator_dmm', 'low': 23.9, 'high': 26.4, 'unit': 'kΩ', 'rule': 'fitted R1-path value ± fit uncertainty, measured out of circuit'},
    {'explanation': EQ, 'source': 'operator_dmm', 'low': 4.47, 'high': 4.93, 'unit': 'kΩ', 'rule': 'drawn 4.7 kΩ ± 5 % part tolerance; the extra resistance sits outside the board'},
    {'explanation': 'changed:R1', 'source': 'operator_marking', 'low': 4.47, 'high': 4.93, 'unit': 'kΩ', 'rule': 'a marking states the nominal value; a damaged 4.7 kΩ part still reads 4.7 kΩ', 'note': 'cannot separate'},
    {'explanation': EQ, 'source': 'operator_marking', 'low': 4.47, 'high': 4.93, 'unit': 'kΩ', 'rule': 'drawn 4.7 kΩ ± 5 % part tolerance', 'note': 'cannot separate'},
]
run['reading'] = {'component': 'R1', 'quantity': 'resistance', 'reason': 'DEV FIXTURE: at the terminals a larger R1 and a resistor in series before R1 look the same. R1 alone, measured out of circuit, separates them.',
                  'chosen_by': 'muse_spark', 'bands': bands, 'sha': 'DEVREADING', 'sha_full': 'DEV' * 21 + 'D', 'commit': 'deadbeef0', 'url': '#',
                  'binding': {'sam_body': 'resistor/object 0', 'component': 'R1', 'chosen_by': 'muse_spark', 'reason': 'DEV FIXTURE: the only resistor body, between the IN lead and the capacitor.', 'operator_confirmed': True, 'photo': None, 'overlay_file': None},
                  'observed': {'component': 'R1', 'value': 4.71, 'unit': 'kΩ', 'source': 'operator_dmm', 'photo': None},
                  'scored': {'fits': [EQ]}, 'outcome': 'one', 'groups': [group]}
tl.append({'t_log': t + 5, 't_play': t + 5, 'kind': 'reading_requested', 'totals': tot, 'ev': E(9003, 'reading_requested'), 'component': 'R1', 'quantity': 'resistance',
           'reason': run['reading']['reason'], 'chosen_by': 'muse_spark', 'calls': []})
tl.append({'t_log': t + 7, 't_play': t + 7, 'kind': 'reading_forecast_frozen', 'totals': tot, 'ev': E(9004, 'reading_forecast_frozen'), 'bands': bands, 'sha': 'DEVREADING', 'sha_full': 'DEV' * 21 + 'D', 'commit': 'deadbeef0', 'url': '#'})
tl.append({'t_log': t + 9, 't_play': t + 9, 'kind': 'body_binding', 'totals': tot, 'ev': E(9005, 'body_binding'), **{k: v for k, v in run['reading']['binding'].items()}})
tl.append({'t_log': t + 12, 't_play': t + 12, 'kind': 'reading_observed', 'totals': tot, 'ev': E(9006, 'reading_observed'), **run['reading']['observed'], 'gap_real_s': 142})
tl.append({'t_log': t + 14, 't_play': t + 14, 'kind': 'reading_scored', 'totals': tot, 'ev': E(9007, 'reading_scored'), 'fits': [EQ], 'outcome': 'one'})
tl.append({'t_log': t + 14.3, 't_play': t + 14.3, 'kind': 'ruled_out_by_reading', 'totals': tot, 'ev': E(9007, 'reading_scored'), 'id': 'changed:R1'})
tl.append({'t_log': t + 16, 't_play': t + 16, 'kind': 'report', 'totals': tot, 'ev': E(9008, 'agent_report'), 'verdict': 'equivalent_member_supported', 'survivors': [EQ], 'components': None,
           'text': 'DEV FIXTURE: verdict text invented only to exercise the page.'})
run['verification'] = None
run['outcome'] = {'kind': 'report', 'verdict': 'equivalent_member_supported', 'survivors': [EQ], 'text': 'DEV FIXTURE'}
run['timeline'] = tl; run['play_length_s'] = t + 17
(SITE / 'tools/DEV-reading-run.json').write_text(json.dumps(run, separators=(',', ':')))
print('wrote tools/DEV-reading-run.json', len(tl), 'events')
