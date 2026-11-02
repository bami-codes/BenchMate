"""Register a pixel-only local reference. No experiment-state assertion or upload."""
import argparse
import json
import os
from pathlib import Path
import uuid

from .media import import_photo, sha256


def register_board(root, source, label, capture_note=''):
    root, source = Path(root).resolve(), Path(source).resolve()
    if not isinstance(label, str) or not 1 <= len(label.strip()) <= 160 or len(capture_note) > 1000:
        raise ValueError('Bounded reference label and capture note required')
    photo_id = 'capture-' + sha256(source)[:16]
    folder = root / '.private/photo-bench/board-captures' / photo_id
    if folder.exists():
        raise FileExistsError('This image already has a preserved local registration')
    record = import_photo(source, folder)
    def ref(item):
        return {'path': str((folder / item['file']).relative_to(root)),
                'sha256': item['sha256'], 'width': item['width'], 'height': item['height']}
    entry = {'id': photo_id, 'label': label.strip(), 'capture_note': capture_note,
             'private': True, 'role': 'operator_supplied_reference', 'coordinate_system': record['coordinate_system'],
             'master': ref(record['master']), 'overview': {**ref(record['overview']), 'transform': record['overview']['transform']},
             'state_id': None, 'same_state_verified': False, 'sam_trials': [], 'targets': []}
    (folder / 'catalog-entry.json').write_text(json.dumps(entry, indent=2, ensure_ascii=False) + '\n')
    # Only the convenience pointer changes. Original pixels and older registrations remain.
    pointer = root / '.private/photo-bench/board-reference.json'
    temporary = pointer.with_name('.board-reference-' + uuid.uuid4().hex + '.json')
    temporary.write_text(json.dumps({'photo_id': photo_id}) + '\n')
    os.replace(temporary, pointer)
    return {'photo_id': photo_id, 'photo_sha256': entry['master']['sha256'],
            'metadata_present': False, 'same_state_verified': False, 'network_requests': 0,
            'hardware_commands': 0, 'image_url': '/board.jpg?photo=' + photo_id}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True)
    parser.add_argument('--label', required=True)
    parser.add_argument('--capture-note', default='')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[3]
    print(json.dumps(register_board(root, args.source, args.label, args.capture_note), ensure_ascii=False))


if __name__ == '__main__':
    main()
