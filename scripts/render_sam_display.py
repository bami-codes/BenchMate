"""Offline, post-result SAM display revision; never edits experiment records.

Requires Pillow, NumPy and OpenCV. No model/provider/serial imports or calls.
"""
import argparse
import hashlib
import json
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, __version__ as pillow_version


ROOT = Path(__file__).resolve().parents[1]
COLOR = (30, 190, 120)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def repo_path(path):
    return path.resolve().relative_to(ROOT).as_posix()


def inventory(directory):
    return {repo_path(p): sha(p) for p in sorted(directory.rglob('*')) if p.is_file()}


def contains(outer, inner):
    return (outer[0] <= inner[0] and outer[1] <= inner[1]
            and outer[2] >= inner[2] and outer[3] >= inner[3])


def overlay(photo_directory):
    candidates = [photo_directory / 'native-SAM',
                  photo_directory / 'decoded/native-SAM']
    native, = [p for p in candidates if (p / 'crop-manifest.json').is_file()]
    manifest_path = native / 'crop-manifest.json'
    objects = json.loads(manifest_path.read_text())['objects']
    image_path = photo_directory / 'prepared/input.png'
    with Image.open(image_path) as image:
        canvas = np.array(image.convert('RGB'))
    image_hash = sha(image_path)
    records = []
    for i, obj in enumerate(objects):
        if obj['schematic_ref'] is not None or obj['association_status'] != 'unassigned':
            raise ValueError('Display-only inputs must have no component assignments.')
        if obj['input_image_sha256'] != image_hash:
            raise ValueError('Native mask and photograph hashes disagree.')
        bounds = obj['bounds_half_open']
        contained = [q['photo_component_id'] for j, q in enumerate(objects)
                     if i != j and contains(bounds, q['bounds_half_open'])]
        excluded = len(contained) >= 2
        record = {
            'photo_component_id': obj['photo_component_id'],
            'object_id': obj['object_id'],
            'bounds_half_open': bounds,
            'contained_mask_ids': contained,
            'excluded_by_containment': excluded,
            'displayed': False,
        }
        mask_name = obj['source_mask_file']
        if mask_name is None:
            record['reason'] = 'no_native_mask'
        else:
            mask_path = native / mask_name
            if obj['mask_mapping_status'] != 'exact_no_resize':
                raise ValueError('Only exact native mask mappings are supported.')
            with Image.open(mask_path) as mask:
                if mask.size != (canvas.shape[1], canvas.shape[0]):
                    raise ValueError('Do not resize or stretch native masks.')
                binary = np.where(np.array(mask.convert('L')) > 0, 255, 0).astype(np.uint8)
            record.update(mask_file=repo_path(mask_path), mask_sha256=sha(mask_path))
            if excluded:
                record['reason'] = 'background_for_display_contains_at_least_two_other_bboxes'
            else:
                contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL,
                                               cv2.CHAIN_APPROX_SIMPLE)
                record['external_contours'] = len(contours)
                if contours:
                    cv2.drawContours(canvas, contours, -1, COLOR, 3, lineType=cv2.LINE_8)
                    record.update(displayed=True, reason='individual_native_external_contours')
                else:
                    record['reason'] = 'empty_native_mask'
        records.append(record)
    return Image.fromarray(canvas), {
        'input_file': repo_path(image_path), 'input_sha256': image_hash,
        'native_manifest': repo_path(manifest_path), 'native_manifest_sha256': sha(manifest_path),
        'native_mask_records': len(objects),
        'displayed_mask_records': sum(r['displayed'] for r in records),
        'records': records,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--faulted', type=Path, required=True, help='Existing faulted photo directory')
    parser.add_argument('--restored', type=Path, required=True, help='Existing restored photo directory')
    parser.add_argument('--output', type=Path, required=True, help='New directory outside both records')
    args = parser.parse_args()
    sources = [args.faulted.resolve(), args.restored.resolve()]
    output = args.output.resolve()
    repo_path(output)
    for directory in sources:
        if output == directory or output.is_relative_to(directory):
            raise ValueError('Output must be outside the original photo records.')
    if output.exists():
        raise ValueError('Refuse to overwrite an existing display revision.')
    before = [inventory(p) for p in sources]
    faulted, faulted_record = overlay(sources[0])
    restored, restored_record = overlay(sources[1])
    canvas = Image.new('RGB', (faulted.width + restored.width + 24,
                              max(faulted.height, restored.height) + 110), 'white')
    canvas.paste(faulted, (0, 110))
    canvas.paste(restored, (faulted.width + 24, 110))
    draw = ImageDraw.Draw(canvas)
    for x, label, record in [(12, 'Faulted', faulted_record),
                             (faulted.width + 36, 'Restored', restored_record)]:
        draw.text((x, 8), f"{label} photograph - {record['displayed_mask_records']} / "
                  f"{record['native_mask_records']} SAM regions displayed", fill='black', font_size=24)
    draw.text((12, 45), 'Post-result display revision, 2026-11-04. Original masks retained.',
              fill='black', font_size=22)
    draw.text((12, 76), 'Visualization only; no component identity, value or absence inferred. Images are not spatially registered.',
              fill='black', font_size=20)
    if before != [inventory(p) for p in sources]:
        raise ValueError('Original photo records changed during rendering.')
    output.mkdir(parents=True)
    for name, image in [('faulted-SAM-overview.png', faulted),
                        ('restored-SAM-overview.png', restored),
                        ('before-after-SAM.png', canvas)]:
        image.save(output / name, format='PNG')
    manifest = {
        'schema': 'benchmate.sam_display_revision.v1',
        'purpose': 'visualization_only', 'rule_selected_on': '2026-11-04',
        'rule_selected_after_results_and_images_seen': True,
        'rule': 'Exclude a mask from display if its half-open bounding box fully contains at least two other SAM record bounding boxes; self excluded; equal edges count as contained.',
        'area_threshold_used': False,
        'outline': 'Each displayed native mask separately: RETR_EXTERNAL, CHAIN_APPROX_SIMPLE, green RGB(30,190,120), 3px LINE_8; no union; internal hole contours not drawn.',
        'same_rule_for_both_photos': True, 'native_masks_modified': False,
        'original_photo_records_unchanged': True,
        'original_photo_inventory': dict(sorted({**before[0], **before[1]}.items())),
        'identification_evidence': False, 'component_assignments': [], 'values_read': [],
        'Spark_requests': 0, 'SAM_requests': 0, 'hardware_operations': 0, 'added_cost_USD': 0,
        'OpenCV_segmentation_fallbacks': 0,
        'faulted': faulted_record, 'restored': restored_record,
        'renderer': {'repo_file': repo_path(Path(__file__)), 'sha256': sha(Path(__file__)),
                     'Pillow': pillow_version, 'NumPy': np.__version__, 'OpenCV': cv2.__version__},
        'artifacts': {p.name: sha(p) for p in sorted(output.glob('*.png'))},
    }
    (output / 'manifest.json').write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + '\n')
    print(json.dumps({'output': repo_path(output), 'faulted_displayed': faulted_record['displayed_mask_records'],
                      'restored_displayed': restored_record['displayed_mask_records'],
                      'original_records_unchanged': True, 'new_API_calls': 0, 'added_cost_USD': 0}))


if __name__ == '__main__':
    main()
