#!/usr/bin/env python3
"""SAM-first passive photo parts: full-resolution crops, independent Spark reads.

No intended design, diagnosis, assembly truth or case mapping is accepted.
Prepare/decode are offline; segment/read require explicit execution.
"""
import argparse
from dataclasses import asdict
import hashlib
import importlib.util
import io
import json
import math
from pathlib import Path
import sys

from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from benchmate.records import canonical, read_events

CONCEPTS = ('resistor', 'capacitor')
SOURCES = ('scripts/photo_parts.py', 'scripts/photo_model_probe.py',
           'src/benchmate/known_design.py', 'src/benchmate/image_archive.py',
           'src/benchmate/records.py', 'src/benchmate/providers.py', 'src/benchmate/config.py')


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def save(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n')


def png(image):
    clean = Image.frombytes('RGB', image.size, image.convert('RGB').tobytes())
    out = io.BytesIO(); clean.save(out, format='PNG')
    return out.getvalue()


def prepare(source, output):
    from benchmate.known_design import sanitize_image
    from benchmate.image_archive import verify_clean_png
    raw = Path(source).read_bytes()
    small, info = sanitize_image(raw)
    verify_clean_png(small)
    with Image.open(io.BytesIO(raw)) as original:
        oriented = ImageOps.exif_transpose(original).convert('RGBA')
        background = Image.new('RGBA', oriented.size, 'white')
        background.alpha_composite(oriented)
        full = background.convert('RGB')
    full_raw = png(full)
    out = Path(output); out.mkdir(parents=True, exist_ok=False)
    (out / 'input.png').write_bytes(small)
    (out / 'clean-full.png').write_bytes(full_raw)
    plan = {'schema': 'benchmate.photo_parts.v1', 'hardware_IO': False,
            'order': 'SAM concepts, then all retained masks/crops, then independent per-crop Spark',
            'concepts': list(CONCEPTS), 'SAM_requests_max': 2, 'Spark_reads_max': 8,
            'read_selection': 'First eight returned crop records in concept/record order; no quality/ranking filter',
            'automatic_retry': False, 'input': info,
            'full': {'sha256': sha(full_raw), 'width': full.width, 'height': full.height},
            'crop_padding_fraction': .15, 'crop_edge_max': 1600,
            'sources': {n: sha((ROOT / n).read_bytes()) for n in SOURCES},
            'excluded_from_model': ['file paths/names', 'intended design', 'ADC data', 'diagnosis',
                                    'operator assembly truth', 'case mapping', 'original metadata'],
            'scope': 'R/C/D visual readings; no Q/LED schema yet; no electrical-connectivity claim'}
    save(out / 'plan.json', plan)
    print(json.dumps({'prepared': str(out), 'SAM_requests_max': 2, 'Spark_reads_max': 8,
                      'API_calls': 0, 'hardware_IO': False})); return plan


def checked(directory):
    directory = Path(directory)
    plan = json.loads((directory / 'plan.json').read_text())
    for name, digest in plan['sources'].items():
        if sha((ROOT / name).read_bytes()) != digest:
            raise ValueError('Photo source changed: ' + name)
    for name, key in (('input.png', 'input'), ('clean-full.png', 'full')):
        if sha((directory / name).read_bytes()) != plan[key]['sha256']:
            raise ValueError('Photo input changed.')
    return directory, plan


def segment(prepared, execute):
    if not execute:
        raise ValueError('Explicit --execute after planned-call disclosure required.')
    directory, plan = checked(prepared)
    if (directory / 'sam-outcomes.json').exists():
        raise ValueError('Segmentation already attempted; no automatic retry.')
    spec = importlib.util.spec_from_file_location('preserved_photo_probe', ROOT / 'scripts/photo_model_probe.py')
    probe = importlib.util.module_from_spec(spec); spec.loader.exec_module(probe)
    outcomes = []
    # This helper reserves against the preserved original ledger. It never
    # resets that counter or bypasses its hard cap.
    for concept in plan['concepts']:
        run, result = probe.sam_attempt((directory / 'input.png').read_bytes(), concept,
                                        output=directory / 'sam' / concept)
        outcomes.append({'concept': concept, 'run': str(run.relative_to(directory)), **result})
        save(directory / 'sam-outcomes.json', outcomes)
        print(json.dumps({'stage': 'SAM', 'concept': concept, **result}), flush=True)


def crop_box(bounds, input_size, full_size, padding):
    l, t, r, b = bounds
    iw, ih = input_size; fw, fh = full_size
    if not (0 <= l < r <= iw and 0 <= t < b <= ih):
        raise ValueError('SAM box outside exact input image.')
    dx, dy = (r-l)*padding, (b-t)*padding
    return [max(0, math.floor((l-dx)*fw/iw)), max(0, math.floor((t-dy)*fh/ih)),
            min(fw, math.ceil((r+dx)*fw/iw)), min(fh, math.ceil((b+dy)*fh/ih))]


def decode(prepared, output):
    from importlib.metadata import version
    from meta_sam_parser import image_segmentation_format, CompletedOutcome, decode_mask_to_raster
    if version('meta-sam-parser') != '0.1.0':
        raise ValueError('Pinned meta-sam-parser 0.1.0 required.')
    directory, plan = checked(prepared)
    out = Path(output); out.mkdir(parents=True, exist_ok=False)
    small = Image.open(directory / 'input.png').convert('RGB')
    full = Image.open(directory / 'clean-full.png').convert('RGB')
    outcomes = json.loads((directory / 'sam-outcomes.json').read_text())
    objects = []; summaries = []
    for attempt in outcomes:
        run = (directory / attempt['run']).resolve()
        if not run.is_relative_to(directory.resolve()):
            raise ValueError('Unexpected SAM record location.')
        events = read_events(run)
        request = next(e['payload'] for e in events if e['kind'] == 'sam_request_frozen')
        if request['image_sha256'] != plan['input']['sha256']:
            raise ValueError('SAM ran on a different photo.')
        concept = attempt['concept']
        if attempt['status'] != 'completed':
            summaries.append({'concept': concept, 'status': 'failed', 'run': attempt['run']}); continue
        text = (run / 'output-text.txt').read_text()
        parser = image_segmentation_format().create_parser(); parser.push(text)
        parsed = parser.finish(CompletedOutcome()).result
        masks = [r for r in parsed.records if r.kind == 'mask']
        if len(masks) > 64:
            raise ValueError('Over 64 masks; raw response retained, no silent filter.')
        report = {'concept': concept, 'parser_version': version('meta-sam-parser'),
                  'diagnostics': [asdict(x) for x in parsed.diagnostics], 'masks': []}
        for index, record in enumerate(masks):
            bounds = [record.bounds.left, record.bounds.top, record.bounds.right, record.bounds.bottom]
            if any(x != int(x) for x in bounds):
                raise ValueError('Non-integer mask bounds.')
            bounds = [int(x) for x in bounds]
            box = crop_box(bounds, small.size, full.size, plan['crop_padding_fraction'])
            raster = decode_mask_to_raster(record.mask)
            if record.mask.width * record.mask.height > small.width * small.height:
                raise ValueError('Raster exceeds photo area.')
            local = Image.frombytes('L', (record.mask.width, record.mask.height), bytes(x*255 for x in raster))
            name = f'{concept}-object-{int(record.object_id)}-record-{index}'
            local.save(out / (name + '-raster.png'))
            source_mask = None
            if local.size == (bounds[2]-bounds[0], bounds[3]-bounds[1]):
                source_mask = Image.new('L', small.size, 0)
                source_mask.paste(local, bounds[:2]); source_mask.save(out / (name + '-mask.png'))
                layer = Image.new('RGBA', small.size, (30, 190, 120, 0))
                layer.putalpha(source_mask.point(lambda v: round(v*.4)))
                Image.alpha_composite(small.convert('RGBA'), layer).convert('RGB').save(out / (name + '-overlay.png'))
            crop = full.crop(box); crop.thumbnail((1600, 1600), Image.Resampling.LANCZOS)
            raw_crop = png(crop); (out / (name + '-crop.png')).write_bytes(raw_crop)
            item = {'photo_component_id': plan['input']['sha256'][:12] + ':' + name,
                    'concept': concept, 'object_id': record.object_id, 'record_index': index,
                    'input_image_sha256': plan['input']['sha256'], 'bounds_half_open': bounds,
                    'confidence': record.confidence, 'raster_size': list(local.size),
                    'source_mask_file': name + '-mask.png' if source_mask is not None else None,
                    'mask_mapping_status': 'exact_no_resize' if source_mask is not None else 'raster_bounds_mismatch',
                    'full_pixel_crop_box': box, 'crop_file': name + '-crop.png',
                    'crop_sha256': sha(raw_crop), 'crop_size': list(crop.size),
                    'schematic_ref': None, 'association_status': 'unassigned'}
            report['masks'].append(item); objects.append(item)
        report['match_count'] = len(masks)
        save(out / (concept + '-decoded.json'), report)
        summaries.append({'concept': concept, 'status': 'decoded', 'match_count': len(masks),
                          'diagnostic_count': len(parsed.diagnostics)})
    result = {'schema': 'benchmate.photo_parts_decoded.v1', 'prepared': str(directory.resolve()),
              'plan_sha256': sha((directory / 'plan.json').read_bytes()), 'objects': objects,
              'summaries': summaries, 'all_masks_retained': True, 'manual_mask_edits': False,
              'new_API_calls': 0, 'Pillow_version': Image.__version__}
    save(out / 'crop-manifest.json', result)
    print(json.dumps({'decoded': str(out), 'objects': len(objects), 'new_API_calls': 0})); return result


def read_parts(decoded, execute):
    if not execute:
        raise ValueError('Disclose actual crop-read count before explicit --execute.')
    from benchmate.known_design import extract
    from benchmate.image_archive import verify_clean_png
    out = Path(decoded)
    manifest = json.loads((out / 'crop-manifest.json').read_text())
    directory, plan = checked(manifest['prepared'])
    if sha((directory / 'plan.json').read_bytes()) != manifest['plan_sha256']:
        raise ValueError('Photo plan changed.')
    if (out / 'components.json').exists():
        raise ValueError('Parts already read; no automatic retry.')
    budget = ROOT / '.private/photo-parts-budget.json'
    if not budget.exists():
        raise ValueError('Authorized photo allowance ledger required.')
    results = []
    for index, item in enumerate(manifest['objects']):
        entry = {**item, 'vision_run': None, 'vision_components': [], 'vision_status': 'not_read_budget'}
        if index < plan['Spark_reads_max']:
            raw = (out / item['crop_file']).read_bytes()
            if sha(raw) != item['crop_sha256']:
                raise ValueError('Frozen crop changed.')
            run, result = extract(raw, verify_clean_png(raw), 'assembly_photo', output=out / 'vision',
                                  env_path=ROOT / '.env', budget_path=budget)
            entry.update(vision_run=str(run.relative_to(out)), vision_status=result['status'])
            for c in result.get('candidate', {}).get('components', []):
                status = ('unreadable' if c['value_si'] is None else 'readable') if c['kind'] in ('R', 'C') else 'observed_without_numeric_value'
                entry['vision_components'].append({**c, 'reading_status': status})
            print(json.dumps({'part': item['photo_component_id'], 'status': result['status']}), flush=True)
        results.append(entry)
        save(out / 'components.json', {'schema': 'benchmate.photo_parts_readings.v1',
             'input_image_sha256': plan['input']['sha256'], 'components': results,
             'expected_mask_records': len(manifest['objects']), 'records_processed': len(results),
             'completed': len(results) == len(manifest['objects']),
             'intended_design_received': False, 'diagnosis_received': False, 'hardware_IO': False})
    if not results:
        save(out / 'components.json', {'schema': 'benchmate.photo_parts_readings.v1',
            'input_image_sha256': plan['input']['sha256'], 'components': [], 'reason': 'No returned masks',
            'intended_design_received': False, 'diagnosis_received': False, 'hardware_IO': False})


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__); sub = p.add_subparsers(dest='command', required=True)
    a = sub.add_parser('prepare'); a.add_argument('--image', required=True); a.add_argument('--output', required=True)
    a = sub.add_parser('segment'); a.add_argument('--prepared', required=True); a.add_argument('--execute', action='store_true')
    a = sub.add_parser('decode'); a.add_argument('--prepared', required=True); a.add_argument('--output', required=True)
    a = sub.add_parser('read'); a.add_argument('--decoded', required=True); a.add_argument('--execute', action='store_true')
    args = p.parse_args()
    if args.command == 'prepare': prepare(args.image, args.output)
    elif args.command == 'segment': segment(args.prepared, args.execute)
    elif args.command == 'decode': decode(args.prepared, args.output)
    else: read_parts(args.decoded, args.execute)
