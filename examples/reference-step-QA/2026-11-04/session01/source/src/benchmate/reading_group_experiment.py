"""Additive case02 unordered capacitance reading; no API or serial commands.

Usage: python -m benchmate.reading_group_experiment {register,publish,observe,verify}
The original terminal pair is a dependency, never reopened or relabelled.
"""
import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess

from .records import Recorder, canonical, decode_events
from .reading_binding_v2 import parse_binding
from .reading_rules import normalize
from .reading_unordered import compare_unordered
from .reading_verify import check_file, verify_run as verify_parent

ROOT = Path(__file__).resolve().parents[2]
PUBLIC = Path('examples/reading-groups/2026-11-04/records')
PARENT = Path('examples/reading-cohort/2026-11-03/records/20261103T165506-b6ad3e8cf7')
NOTE = 'docs/2026-11-04-parallel-reading-amendment.md'
EXTRA = ('src/benchmate/reading_group_experiment.py', 'src/benchmate/reading_binding_v2.py',
         'src/benchmate/reading_unordered.py', 'tests/test_reading_binding_v2.py',
         'tests/test_reading_group_experiment.py', NOTE)
METER = {'available': True, 'range_F': 2e-6, 'resolution_F': 1e-9,
         'relative_allowance': .05, 'digits_allowance': 2,
         'basis': 'Operator reports capacitance mode: dial 2u, open display 0.000uF.',
         'accuracy_calibrated': False, 'allowance_is_engineering_acceptance_not_manufacturer_accuracy': True}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x') as f:
        f.write(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False)+'\n')


def artifact(root, path):
    return {'file': str(Path(path).relative_to(root)), 'sha256': sha(path)}


def electrical_rows(catalog):
    """Inherited training envelope, with a new prospectively fixed meter allowance."""
    survivor = next(e for e in catalog['explanations'] if e['id'] == 'changed:C1')
    if len(catalog['explanations']) != 1:
        raise ValueError('This amendment requires the existing sole changed:C1 survivor.')
    rows = []
    for role, identity in [('active', 'changed:C1'), ('reference', 'nominal')]:
        base = {c: survivor['components'][c]['electrical_interval'] for c in ('C1', 'C2')}
        if role == 'reference':
            base = {c: [catalog['components'][c]['value']*.95, catalog['components'][c]['value']*1.05]
                    for c in ('C1', 'C2')}
        intervals = {c: [max(0., lo*(1-METER['relative_allowance'])-METER['digits_allowance']*METER['resolution_F']),
                         None if hi is None else hi*(1+METER['relative_allowance'])+METER['digits_allowance']*METER['resolution_F']]
                     for c, (lo, hi) in base.items()}
        rows.append({'id': identity, 'role': role, 'intervals': intervals})
    return rows


def score(forecast, observation):
    if (set(observation) != {'source', 'power_off_confirmed', 'discharge_wait_confirmed', 'readings'}
            or observation['source'] != 'operator_dmm' or observation['power_off_confirmed'] is not True
            or observation['discharge_wait_confirmed'] is not True):
        raise ValueError('Power-off, discharge wait and actual DMM source required.')
    readings = observation['readings']
    if not isinstance(readings, list) or len(readings) != len(forecast['bodies']):
        raise ValueError('Exactly one reading per group body required.')
    values = {}
    meter = forecast['meter']
    if meter['available'] is not True:
        raise ValueError('Capacitance mode is unavailable.')
    for r in readings:
        if (not isinstance(r, dict) or set(r) != {'body', 'value', 'unit', 'range_F', 'resolution_F', 'isolated_confirmed'}
                or not isinstance(r['body'], str) or r['body'] not in forecast['bodies'] or r['body'] in values
                or r['isolated_confirmed'] is not True
                or type(r['range_F']) not in (int, float) or r['range_F'] != meter['range_F']
                or type(r['resolution_F']) not in (int, float) or r['resolution_F'] != meter['resolution_F']):
            raise ValueError('Unique existing body, isolated component and the frozen range/resolution required.')
        value, unit = normalize(r['value'], r['unit'])
        if (unit != 'F' or value >= meter['range_F']
                or abs(value/meter['resolution_F']-round(value/meter['resolution_F'])) > 1e-7):
            raise ValueError('Finite in-range capacitance at the actual display resolution required; no OL guessing.')
        values[r['body']] = value
    return {**compare_unordered(values, forecast['explanations']),
            'values_F': values, 'source': 'operator_dmm',
            'forecast_sha256': hashlib.sha256(canonical(forecast)).hexdigest(),
            'observation_sha256': hashlib.sha256(canonical(observation)).hexdigest(),
            'scope': forecast['scope'], 'new_blind_test': False}


def make_overlay(parent, output):
    from PIL import Image, ImageChops, ImageDraw, ImageFilter
    photo = parent/'photo-faulted/prepared/input.png'
    image = Image.open(photo).convert('RGB')
    color = Image.new('RGB', image.size, (30, 190, 110))
    mask_files = []
    union = Image.new('L', image.size)
    for body in ('sam-2', 'sam-3'):
        file = parent/f'photo-faulted/decoded/{body}-body-mask.png'
        mask = Image.open(file).convert('L').resize(image.size, Image.Resampling.NEAREST)
        outline = ImageChops.subtract(mask.filter(ImageFilter.MaxFilter(7)), mask.filter(ImageFilter.MinFilter(5)))
        union = ImageChops.lighter(union, outline)
        mask_files.append({'file': str(file.relative_to(ROOT)), 'sha256': sha(file)})
    result = Image.composite(color, image, union)
    draw = ImageDraw.Draw(result)
    for text, xy in [('sam-2: C1 or C2', (755, 575)), ('sam-3: C1 or C2', (755, 745))]:
        draw.rectangle((xy[0]-4, xy[1]-4, xy[0]+180, xy[1]+26), fill='white')
        draw.text(xy, text, fill=(0, 100, 50), font_size=20)
    result.save(output, format='PNG')
    return {'source': {'file': str(photo.relative_to(ROOT)), 'sha256': sha(photo)}, 'masks': mask_files,
            'recipe': 'Nearest-neighbor existing full-size derived SAM masks to 1200x1600; Max7-Min5 outline; same green on both; labels outside body.',
            'annotation_only': True, 'new_capture': False, 'native_masks_changed': False}


def register():
    parent = ROOT/PARENT
    verified = verify_parent(parent)
    if not verified['passed'] or verified['run_status'] != 'run_failed':
        raise ValueError('Verified failed parent required.')
    native = json.loads(next((parent/'photo-faulted/binding').glob('*/result.json')).read_text())['arguments']
    manifest = json.loads((parent/'photo-faulted/decoded/body-manifest.json').read_text())
    parsed = parse_binding(native, [b['id'] for b in manifest['components']])
    if parsed['sam_body'] is not None or native['sam_body'] != 'null':
        raise ValueError('This supplement is only for the retained literal-null abstention.')
    frozen = json.loads((ROOT/'examples/reading-cohort/2026-11-03/freeze/manifest.json').read_text())
    for name, h in frozen['source_sha256'].items():
        if sha(ROOT/name) != h:
            raise ValueError('Original frozen source changed: '+name)
    log = Recorder(ROOT/'runs/reading-groups', mode='unordered_reading_supplement_not_replacement')
    sources = {n: sha(ROOT/n) for n in EXTRA}
    for n in EXTRA:
        destination = log.path/'source'/n
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT/n, destination)
    reg = {'schema': 'benchmate.unordered_reading_supplement.v1', 'case_id': '02', 'run_id': log.path.name,
           'parent_record': str(PARENT), 'parent_head_sha256': verified['head_sha256'],
           'parent_status_unchanged': 'run_failed', 'counted_new_physical_attempt': False,
           'selected_first_attempt_changed': False, 'blind_test': False,
           'extra_reading_requested_by': 'operator_requested_amendment', 'source_sha256': sources,
           'paid_calls': 0, 'hardware_commands': 0,
           'public_record': str(PUBLIC/log.path.name)}
    group = {'components': ['C1', 'C2'], 'sam_bodies': ['sam-2', 'sam-3'],
             'correspondence': 'unresolved', 'individual_bindings': None,
             'candidate_group_chosen_by': 'Codex_visual_review_requested_by_operator',
             'Spark_chose_group': False, 'Spark_abstention_reason': native['reason'],
             'topology_conditioned': 'Two capacitors on the intended OUT-REF parallel branch.',
             'earlier_single_body_confirmation_question_withdrawn': True,
             'already_received_report': {'body': 'sam-2', 'raw_text': '그게 474야.',
                 'source': 'operator_marking', 'actual_capacitance_measured': False,
                 'C1_identity_confirmed': False, 'received_before_this_forecast': True}}
    catalog = json.loads((parent/'reading-catalog.json').read_text())
    forecast = {'schema': 'benchmate.unordered_capacitance_forecast.v1', 'bodies': ['sam-2', 'sam-3'],
                'components': ['C1', 'C2'], 'source': 'operator_dmm', 'unit': 'F', 'meter': deepcopy(METER),
                'explanations': electrical_rows(catalog), 'observation_received': False,
                'printed_474_report_already_received': True, 'new_blind_test': False,
                'matching': 'All interval-compatible bijections; never nearest-value assignment.',
                'catalog_sha256': sha(parent/'reading-catalog.json'),
                'scope': 'Non-blind isolated-reading supplement to existing bounded changed:C1 diagnosis; nominal is a rejected reference, not a survivor. Does not complete the repair pair.'}
    provenance = make_overlay(parent, log.path/'capacitor-candidates.png')
    for name, data in [('registration.json', reg), ('body-group.json', group),
                       ('binding-parser-review.json', {'post_hoc_review': True, 'original_failure_unchanged': True, **parsed}),
                       ('group-reading-forecast.json', forecast), ('overlay-provenance.json', provenance)]:
        save(log.path/name, data)
    log.add('group_reading_registered', reg)
    log.add('body_binding_ambiguity', group)
    log.add('reading_forecast_frozen', {'file': 'group-reading-forecast.json', 'sha256': sha(log.path/'group-reading-forecast.json')})
    log.add('review_artifacts_bound', {'artifacts': [artifact(log.path, p) for p in sorted(log.path.rglob('*')) if p.is_file() and p.name != 'events.jsonl']})
    log.add('group_state', {'phase': 'awaiting_publication'})
    export(log.path)
    print(json.dumps({'record': str(log.path), 'public_record': reg['public_record'], 'API_calls': 0, 'hardware_commands': 0}))


def export(path):
    reg = json.loads((path/'registration.json').read_text())
    shutil.copytree(path, ROOT/reg['public_record'], dirs_exist_ok=True)


def open_record(path):
    path = Path(path).resolve()
    if not path.is_relative_to((ROOT/'runs/reading-groups').resolve()):
        raise ValueError('Use a local group supplement record.')
    events = decode_events((path/'events.jsonl').read_bytes(), require_terminal=False, include_hash=True)
    if events[-1]['kind'] in ('run_completed', 'run_failed'):
        raise ValueError('Terminal supplement; no retry.')
    reg = json.loads((path/'registration.json').read_text())
    for name, h in reg['source_sha256'].items():
        if sha(ROOT/name) != h:
            raise ValueError('Frozen supplement source changed: '+name)
    if not verify(path)['passed']:
        raise ValueError('Supplement audit failed.')
    log = Recorder.__new__(Recorder)
    log.path = path
    log.file = path/'events.jsonl'
    log.sequence = len(events)
    log.previous = events[-1]['sha256']
    return log, events, reg


def publish(path):
    log, events, reg = open_record(path)
    if events[-1]['kind'] != 'group_state' or events[-1]['payload']['phase'] != 'awaiting_publication':
        raise ValueError('Publication is not the next stage.')
    commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    remote = subprocess.check_output(['git', 'ls-remote', 'origin', 'refs/heads/main'], cwd=ROOT, text=True).split()[0]
    if commit != remote:
        raise ValueError('Remote publication receipt missing.')
    for relative in ('group-reading-forecast.json', 'registration.json'):
        committed = subprocess.check_output(['git', 'show', commit+':'+reg['public_record']+'/'+relative], cwd=ROOT)
        if committed != (log.path/relative).read_bytes():
            raise ValueError('Forecast/registration not remotely committed.')
    log.add('reading_forecast_publication', {'commit': commit, 'remote': True,
            'file': 'group-reading-forecast.json', 'sha256': sha(log.path/'group-reading-forecast.json'),
            'before_new_electrical_values': True, 'before_printed_474_report': False})
    log.add('group_state', {'phase': 'awaiting_isolated_values'})
    export(log.path)
    print(json.dumps({'record': str(log.path), 'phase': 'awaiting_isolated_values', 'commit': commit}))


def observe(path, observation_file):
    log, events, _ = open_record(path)
    if events[-1]['kind'] != 'group_state' or events[-1]['payload']['phase'] != 'awaiting_isolated_values':
        raise ValueError('Publish the group forecast before intake.')
    observation = json.loads(Path(observation_file).read_text())
    forecast = json.loads((log.path/'group-reading-forecast.json').read_text())
    result = score(forecast, observation)
    save(log.path/'group-reading-observation.json', observation)
    save(log.path/'group-reading-score.json', result)
    log.add('group_reading_observed', observation)
    log.add('group_reading_scored', result)
    log.add('run_completed', {'outcome': result['outcome'], 'repair_pair_completed': False,
                             'original_terminal_status_unchanged': True, 'API_calls': 0, 'hardware_commands': 0})
    export(log.path)
    print(json.dumps(result))


def verify(path):
    result = {'passed': False, 'events': 0, 'error': None}
    try:
        path = Path(path)
        events = decode_events((path/'events.jsonl').read_bytes(), require_terminal=False, include_hash=True)
        expected = ['run_started', 'group_reading_registered', 'body_binding_ambiguity',
                    'reading_forecast_frozen', 'review_artifacts_bound', 'group_state',
                    'reading_forecast_publication', 'group_state', 'group_reading_observed',
                    'group_reading_scored', 'run_completed']
        if len(events) not in (6, 8, 11) or [e['kind'] for e in events] != expected[:len(events)]:
            raise ValueError('Invalid supplement stage order.')
        if events[5]['payload'] != {'phase': 'awaiting_publication'} or (
                len(events) >= 8 and events[7]['payload'] != {'phase': 'awaiting_isolated_values'}):
            raise ValueError('Invalid supplement state.')
        result['events'] = len(events)
        reg = json.loads((path/'registration.json').read_text())
        if Path(reg['parent_record']) != PARENT:
            raise ValueError('Unexpected parent.')
        parent = verify_parent(ROOT/PARENT)
        if not parent['passed'] or parent['head_sha256'] != reg['parent_head_sha256'] or parent['run_status'] != 'run_failed':
            raise ValueError('Original terminal failure changed.')
        for name, h in reg['source_sha256'].items():
            file = (path/'source'/name).resolve()
            if not file.is_relative_to((path/'source').resolve()) or sha(file) != h:
                raise ValueError('Frozen source snapshot mismatch.')
        forecast = json.loads((path/'group-reading-forecast.json').read_text())
        catalog = json.loads((ROOT/PARENT/'reading-catalog.json').read_text())
        if (forecast['schema'] != 'benchmate.unordered_capacitance_forecast.v1'
                or forecast['source'] != 'operator_dmm' or forecast['unit'] != 'F'
                or forecast['bodies'] != ['sam-2', 'sam-3'] or forecast['components'] != ['C1', 'C2']
                or forecast['meter'] != METER or forecast['explanations'] != electrical_rows(catalog)
                or forecast['observation_received'] is not False or forecast['new_blind_test'] is not False
                or forecast['printed_474_report_already_received'] is not True
                or forecast['catalog_sha256'] != sha(ROOT/PARENT/'reading-catalog.json')):
            raise ValueError('Inherited intervals, source or range changed.')
        frozen = publication = observation = scored = None
        terminal = False
        for e in events:
            if terminal:
                raise ValueError('Event after terminal.')
            kind, p = e['kind'], e['payload']
            if kind == 'group_reading_registered' and p != reg:
                raise ValueError('Registration mismatch.')
            if kind == 'review_artifacts_bound':
                for item in p['artifacts']:
                    check_file(path, item)
            if kind == 'reading_forecast_frozen':
                if frozen or observation is not None:
                    raise ValueError('Forecast duplicated or late.')
                check_file(path, p)
                frozen = p
            if kind == 'reading_forecast_publication':
                if (not frozen or publication or observation is not None or p['sha256'] != frozen['sha256']
                        or p['remote'] is not True or not re.fullmatch('[0-9a-f]{40}', p['commit'])
                        or p['before_new_electrical_values'] is not True or p['before_printed_474_report'] is not False):
                    raise ValueError('Invalid forecast publication order.')
                publication = p
            if kind == 'group_reading_observed':
                if not publication or observation is not None:
                    raise ValueError('Reading before publication or duplicated.')
                observation = p
                if json.loads((path/'group-reading-observation.json').read_text()) != p:
                    raise ValueError('Observation file mismatch.')
            if kind == 'group_reading_scored':
                if observation is None or scored is not None or score(forecast, observation) != p:
                    raise ValueError('Reading score mismatch.')
                if json.loads((path/'group-reading-score.json').read_text()) != p:
                    raise ValueError('Score file mismatch.')
                scored = p
            if kind in ('run_completed', 'run_failed'):
                terminal = True
                if kind != 'run_completed' or scored is None or p['outcome'] != scored['outcome'] or p['repair_pair_completed'] is not False:
                    raise ValueError('Invalid terminal supplement.')
        if not frozen:
            raise ValueError('No frozen forecast.')
        result.update(passed=True, run_status=events[-1]['kind'], head_sha256=events[-1]['sha256'],
                      parent_head_sha256=parent['head_sha256'], scope='internal_integrity+recorded_order', creation_time='unproven')
    except (ValueError, KeyError, TypeError, OSError, StopIteration) as exc:
        result['error'] = str(exc)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('register')
    for name in ('publish', 'observe', 'verify'):
        p = sub.add_parser(name)
        p.add_argument('record')
        if name == 'observe':
            p.add_argument('observation_file')
    args = parser.parse_args()
    if args.command == 'register':
        register()
    elif args.command == 'publish':
        publish(args.record)
    elif args.command == 'observe':
        observe(args.record, args.observation_file)
    else:
        r = verify(args.record)
        print(('PASS' if r['passed'] else 'FAIL')+' '+json.dumps(r, separators=(',', ':')))
        raise SystemExit(0 if r['passed'] else 1)


if __name__ == '__main__':
    main()
