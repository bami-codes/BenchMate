from copy import deepcopy
import json
from pathlib import Path

import pytest

from benchmate import reading_photo_request_v5 as v5


def test_native_geometry_is_not_shifted_by_full_photo_scaling():
    body = {'id': 'sam-a', 'localizer': 'SAM-derived body mask',
            'native_object': {'bounds_half_open': [339, 605, 531, 646]}}
    g = v5.geometry(body, (3024, 4032), (1200, 1600))
    assert g['box_in_board_input_pixels'] == [339, 605, 531, 646]
    assert g['geometry_origin'] == 'native_SAM_input_coordinates'


def test_cv_fallback_without_native_object_retains_its_provenance():
    body = {'id': 'cv-a', 'localizer': 'OpenCV fallback', 'source_box': [2896, 0, 3024, 28]}
    g = v5.geometry(body, (3024, 4032), (1200, 1600))
    assert g['box_in_board_input_pixels'] == [1149, 0, 1200, 12]
    assert g['geometry_origin'] == 'OpenCV_full_photo_box_scaled_to_input'
    assert g['localizer'] == 'OpenCV fallback'


def test_unknown_non_native_localizer_is_rejected():
    with pytest.raises(ValueError, match='provenance'):
        v5.geometry({'id': 'manual-a', 'localizer': 'operator truth', 'source_box': [1, 2, 3, 4]}, (30, 40), (15, 20))


@pytest.mark.parametrize('box', [[-1, 0, 3, 4], [1, 2, 1, 4], [1, 2, 31, 4]])
def test_invalid_geometry_is_rejected(box):
    with pytest.raises(ValueError, match='geometry'):
        v5.geometry({'id': 'sam-a', 'localizer': 'SAM-derived body mask',
                     'native_object': {'bounds_half_open': box}}, (30, 40), (30, 40))


def test_mixed_candidates_are_all_preserved_and_no_values_enter_request(tmp_path, monkeypatch):
    from PIL import Image
    monkeypatch.setattr(v5, 'ROOT', tmp_path)
    parent = tmp_path / 'record'; decoded = parent / 'photo-faulted/decoded'; decoded.mkdir(parents=True)
    prepared = parent / 'photo-faulted/prepared'; prepared.mkdir()
    intake = parent / 'intake'; intake.mkdir()
    for p, size in [(prepared/'input.png', (30, 40)), (prepared/'clean-full.png', (60, 80)), (intake/'input.png', (30, 40))]:
        Image.new('RGB', size, 'white').save(p)
    bodies = []
    for ident in ('sam-a', 'cv-a'):
        crop = decoded/(ident+'.png'); Image.new('RGB', (6, 6), 'blue').save(crop)
        body = {'id': ident, 'read_selected': True, 'source_box': [2, 4, 12, 16],
                'localizer': 'OpenCV fallback', 'views': [{'file': crop.name, 'sha256': v5.sha(crop)}]}
        if ident.startswith('sam'):
            body.update(localizer='SAM-derived body mask', native_object={'bounds_half_open': [1, 2, 6, 8]})
        bodies.append(body)
    (decoded/'body-manifest.json').write_text(json.dumps({'components': bodies}))
    (parent/'state.json').write_text(json.dumps({'schematic_intake': 'intake', 'requested_component': 'R1'}))
    (parent/'private-assembly-local-only.json').write_text('HIDDEN_EXPECTED_PART_VALUE')
    content, tool, ids, inventory = v5.request(parent)
    assert ids == ['sam-a', 'cv-a']
    assert 'HIDDEN_EXPECTED_PART_VALUE' not in json.dumps(content)
    assert tool['parameters']['properties']['sam_body']['enum'] == ['sam-a', 'cv-a', None]
    assert 'private-assembly-local-only.json' not in json.dumps(inventory)
    assert 'native_SAM_input_coordinates' in content[0]['text']
    assert 'OpenCV_full_photo_box_scaled_to_input' in content[0]['text']
    before = deepcopy(inventory)
    (decoded/'cv-a.png').write_bytes(b'changed crop')
    with pytest.raises(ValueError, match='crop changed'):
        v5.request(parent)
    assert before == inventory
