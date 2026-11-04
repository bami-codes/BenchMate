"""Apply an actual, separately recorded Spark photo reprocessing to site data.

No API calls; no historical experiment mutation; no frontend source modification.
Run after site/tools/extract_runs.py when regenerating the historical bench data.
"""
import argparse
from copy import deepcopy
from datetime import datetime
import hashlib
import json
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

from benchmate.reading_candidates_v3 import parse
from benchmate.records import decode_events

ROOT = Path(__file__).resolve().parents[1]
RUN_ID = '20261103T165506-b6ad3e8cf7'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, value, compact=False):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=None if compact else 1,
                               separators=(',', ':') if compact else None) + '\n')


def envelope(e):
    return {'seq': e['sequence'], 'ts': e['timestamp'], 'kind': e['kind'],
            'sha256': e['sha256'], 'prev': e['previous_sha256']}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('record', type=Path)
    args = p.parse_args()
    rec = args.record.resolve()
    record_name = str(rec.relative_to(ROOT))
    events = decode_events((rec / 'events.jsonl').read_bytes(), include_hash=True)
    declaration = next(e['payload'] for e in events if e['kind'] == 'photo_reprocessing_declared')
    plan_file = ROOT / declaration['plan_file']
    assert sha(plan_file) == declaration['sha256']
    plan = json.loads(plan_file.read_text())
    link = next(e['payload'] for e in events if e['kind'] == 'model_subrecord_linked')
    child_events = rec / link['file']
    assert sha(child_events) == link['sha256']
    child = decode_events(child_events.read_bytes(), include_hash=True)
    assert child[-1]['kind'] == 'run_completed' and child[-1]['payload']['requests'] == 1
    receipt = parse(child[-1]['payload']['arguments'], plan['candidate_ids_supplied'])
    proposal = json.loads((rec / 'candidate-proposal.json').read_text())
    for k, v in receipt.items():
        assert proposal[k] == v
    event = next(e for e in events if e['kind'] == 'body_candidates_proposed')
    assert event['payload']['sha256'] == sha(rec / 'candidate-proposal.json')
    summary = json.loads((rec / 'result.json').read_text())
    assert events[-1]['kind'] == 'run_completed' and events[-1]['payload'] == summary
    # This site branch is the unordered C1/C2 demo. A different response must not
    # silently be reshaped to fit it; it needs its own presentation path.
    ids = [c['sam_body'] for c in proposal['candidate_bodies']]
    assert proposal['mapping_status'] == 'ambiguous' and proposal['sam_body'] is None
    assert len(ids) == 2 and all(c['kind'] == 'C' for c in proposal['candidate_bodies'])
    parent = ROOT / plan['parent']
    manifest = json.loads((parent / 'photo-faulted/decoded/body-manifest.json').read_text())
    bodies = {b['id']: b for b in manifest['components']}
    image_file = parent / 'photo-faulted/prepared/input.png'
    image = np.array(Image.open(image_file).convert('RGB'))
    masks = []
    boxes = {}
    for body in ids:
        native = bodies[body]['native_object']
        file = parent / 'photo-faulted/decoded/native-SAM' / native['source_mask_file']
        mask = np.array(Image.open(file).convert('L'))
        assert mask.shape == image.shape[:2]
        contours, _ = cv2.findContours(np.where(mask > 0, 255, 0).astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cv2.drawContours(image, contours, -1, (30, 190, 120), 3, lineType=cv2.LINE_8)
        masks.append({'id': body, 'file': str(file.relative_to(ROOT)), 'sha256': sha(file)})
        boxes[body] = native['bounds_half_open']
    rendered = rec.parent.parent / 'rendered'
    rendered.mkdir(exist_ok=True)
    overlay = rendered / 'spark-candidate-overview.png'
    Image.fromarray(image).save(overlay)
    asset = ROOT / 'site/assets/photos/case02-spark-candidates.png'
    asset.write_bytes(overlay.read_bytes())
    render_manifest = {'schema': 'benchmate.Spark_candidate_overlay.v1', 'model_record': record_name,
        'candidate_event_sha256': event['sha256'], 'chosen_by': 'muse_spark', 'candidates': proposal['candidate_bodies'],
        'individual_mapping': 'ambiguous', 'sam_body': None, 'native_masks_modified': False,
        'photo_input': str(image_file.relative_to(ROOT)), 'input_sha256': sha(image_file), 'masks': masks,
        'recipe': 'Only model-selected native masks, external contours separately, 3px RGB(30,190,120); no component names before readings.',
        'overlay_sha256': sha(overlay), 'new_API_calls': 0}
    write(rendered / 'manifest.json', render_manifest)
    verify = f"PASS reprocessing_events={len(events)} Spark_events={len(child)} candidate_ids={','.join(ids)} original_experiment_modified=false scope=record_integrity+model_output_binding creation_time=unproven\n"
    (rec / 'verification.txt').write_text(verify)

    site = ROOT / 'site'
    file = site / 'data/runs' / (RUN_ID + '.json')
    run = json.loads(file.read_text())
    if run.get('demo_photo_reprocessing', {}).get('record') == record_name:
        print(verify.strip() + ' site_already_applied=true')
        return
    before = deepcopy(run)
    ev = envelope(event)
    cost = summary['estimated_cost_USD']
    timestamp = event['timestamp']
    note = ('Muse Spark selected ' + ' and '.join(ids) + ' as capacitor candidates; C1/C2 identity remains ambiguous. '
            'Photo stage reprocessed on 4 Nov for this demo, using the earlier photograph and SAM masks; '
            'the bench readings below replay the earlier experiment. Spark 1 call, estimated $' + f'{cost:.5f}' + '.')
    run['demo_photo_reprocessing'] = {'record': record_name, 'event': ev, 'candidate_bodies': proposal['candidate_bodies'],
        'mapping_status': proposal['mapping_status'], 'sam_body': proposal['sam_body'], 'source_commit': declaration['publication_commit'],
        'after_original_experiment': True, 'original_readings_sent_to_model': False, 'note': note, **summary}
    run.setdefault('verify_outputs', []).append('# demo photo-stage reprocessing, separate record\n' + verify.strip())
    run['historical_photo_stage'] = {'binding': run['reading'].get('binding'),
        'group_selection': {k: run['reading']['group'].get(k) for k in ('chosen_by', 'spark_chose_group', 'ambiguity_ev')},
        'events': [e for e in run['events'] if e['kind'] in ('binding_abstained', 'body_group')]}
    run['reading']['binding'] = None
    group = run['reading']['group']
    # The old DMM observations were taken using the original candidate group.
    # Its authorship remains historical; the replay body_group event below is
    # explicitly replaced by the new model-selected demo photo stage.
    group.update(body_boxes=boxes, photo_stage_reprocessing=run['demo_photo_reprocessing'])
    group['scope'] = (group.get('scope', '') + ' These are the original bench-reading group records; '
                      'a later Spark photo-stage reprocessing is displayed with the board photo.').strip()
    ph = run['photo']
    ph['image']['file'] = 'assets/photos/case02-spark-candidates.png'
    ph.update(provenance=note, note='Only the two model-selected capacitor masks are outlined. All original SAM masks are retained.',
              pairing='Spark selected the candidate set; C1/C2 correspondence follows only from the earlier isolated readings and frozen bands',
              labels=[{'text': body, 'bounds': boxes[body], 'side': True} for body in ids])
    for key in ('events', 'timeline'):
        run[key] = [e for e in run[key] if e['kind'] != 'binding_abstained']
        active = False
        for e in run[key]:
            if e['kind'] == 'body_group':
                active = True
                e.update(ev=ev, chosen_by='muse_spark', spark_chose_group=True, photo=ph['image']['file'],
                         boxes=boxes, provenance=note, topology=proposal['reason'],
                         candidate_bodies=proposal['candidate_bodies'], photo_stage_reprocessing=True)
                actual = (datetime.fromisoformat(timestamp) - datetime.fromisoformat(run['started_utc'])).total_seconds()
                e['t' if key == 'events' else 't_log'] = actual
            if active and e.get('totals'):
                e['totals']['spark_calls'] += 1
                e['totals']['spark_cost'] = round(e['totals']['spark_cost'] + cost, 8)
    run['totals']['spark_calls'] += 1
    run['totals']['spark_cost'] = round(run['totals']['spark_cost'] + cost, 8)
    # Keep every measured/scored value and its actual observation envelope intact.
    for field in ('steps', 'verification', 'outcome', 'seal'):
        assert run[field] == before[field], field
    for field in ('bands', 'observed', 'scored'):
        assert run['reading']['group'][field] == before['reading']['group'][field], field
    write(file, run, compact=True)
    index_file = site / 'data/runs/index.json'
    index = json.loads(index_file.read_text())
    for entry in index['runs']:
        if entry['id'] == RUN_ID:
            entry.update(spark_calls=run['totals']['spark_calls'], spark_cost=run['totals']['spark_cost'],
                         photo_stage_reprocessed=True)
    write(index_file, index)
    results_file = site / 'data/results.json'
    results = json.loads(results_file.read_text())
    results['photo_reprocessing'] = {'record': record_name, 'Spark_requests': 1, 'SAM_requests': 0, 'estimated_cost_USD': cost}
    for metric in results['metrics']:
        if metric['id'] == 'spark_calls': metric['value'] = 65
        if metric['id'] == 'cost': metric['value'] = round(.63350110 + cost, 2)
    results['sources'].append(f'{record_name}: demo photo reprocessing adds 1 Spark, 0 SAM, estimated ${cost:.8f}; cumulative 65 Spark + 3 SAM, ${.63350110 + cost:.8f}')
    write(results_file, results)
    photos_file = site / 'tools/photos-case02.json'
    photos = json.loads(photos_file.read_text())
    photos.update(spark_candidates=ph['image']['file'], spark_candidate_record=record_name)
    write(photos_file, photos)
    hashes_file = site / 'tools/photos-case02-hashes.json'
    hashes = json.loads(hashes_file.read_text())
    hashes[ph['image']['file']] = {'sha256': sha(asset), 'bytes': asset.stat().st_size,
        'source_record': record_name, 'candidate_event_sha256': event['sha256'], 'selected_by': 'muse_spark'}
    write(hashes_file, hashes)
    print(verify.strip() + ' site_applied=true')


if __name__ == '__main__':
    main()
