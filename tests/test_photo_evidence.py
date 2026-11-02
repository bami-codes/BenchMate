"""Photo/mask identity, guarded coordinates and independent observation history."""
from copy import deepcopy
import json
from pathlib import Path
import re
import threading
import uuid

import httpx
import pytest

from benchmate.photo_bench.evidence import PhotoCatalog, point_evidence
from benchmate.case_review.photo_service import PhotoReviewStore
from benchmate.case_review.service import CaseStore, Conflict
from benchmate.case_review.web import make_server

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def catalog(): return PhotoCatalog(ROOT)


def fixture_point(catalog):
    photo = catalog.internal('img_8887')
    grid = catalog.grid('img_8887')
    # A known grid point exercises geometry, not an independently labelled wire endpoint.
    point = grid['strips']['lower']['fit'][0]['image_xy']
    return photo, grid, point, photo['targets'][0]


def test_all_archived_sam_outcomes_are_retained_and_bound(catalog):
    p = catalog.describe('img_8885')
    assert p['available'] and [t['match_count'] for t in p['sam_trials']] == [0, 1, 0, 1, 0]
    assert all(t['input_sha256'] == p['photo_sha256'] for t in p['sam_trials'])
    assert all(t['no_match_means_absent'] is False and t['circuit_identity_verified'] is False for t in p['sam_trials'])
    assert catalog.mask('img_8885', 'sam-2', '0').startswith(b'\x89PNG')
    assert catalog.mask('img_8885', 'sam-4', '0', overlay=True).startswith(b'\x89PNG')
    for photo, trial, mask in [('img_8887', 'sam-2', '0'), ('img_8885', 'sam-1', '0'), ('img_8885', 'sam-2', '../x')]:
        with pytest.raises(KeyError): catalog.mask(photo, trial, mask)
    assert p['same_state_verified'] is False and p['can_authorize_repair'] is False


def test_mask_input_mismatch_rejected_before_display(catalog):
    catalog.photos = deepcopy(catalog.photos)
    catalog.photos['img_8885']['sam_trials'][1]['input']['sha256'] = '0'*64
    with pytest.raises(ValueError, match='different image'): catalog.trials('img_8885')


def test_private_photos_optional_and_never_grouped(catalog):
    catalog.photos = deepcopy(catalog.photos)
    catalog.photos['img_8887']['master']['path'] = '.private/does-not-exist.png'
    p = catalog.describe('img_8887')
    assert p['available'] is False and p['image_url'] is None and p['issue'] == 'private_photo_not_present'
    assert p['capture_state_id'] is None
    assert len(p['targets']) == 10
    assert catalog.list()['same_state_groups'] == []


def test_corrupted_asset_hash_and_non_whitelisted_path_rejected(catalog):
    catalog.photos = deepcopy(catalog.photos)
    catalog.photos['img_8885']['overview']['sha256'] = 'a'*64
    with pytest.raises(ValueError, match='hash mismatch'): catalog.image('img_8885')
    catalog.photos['img_8885']['master']['path'] = '../outside.png'
    with pytest.raises(ValueError, match='checkout'): catalog.image('img_8885', 'master')


def test_overview_and_master_coordinates_match_without_electrical_claim(catalog):
    photo, grid, point, target = fixture_point(catalog)
    expected = point_evidence(photo, grid, 'master', point, 'visible', target)
    w, h = photo['master']['width'], photo['master']['height']
    view_point = [point[0] * photo['overview']['width']/w, point[1] * photo['overview']['height']/h]
    result = point_evidence(photo, grid, 'overview', view_point, 'visible', target)
    assert result['point_master'] == pytest.approx(point)
    assert result['grid_candidate']['column_from_right'] == expected['grid_candidate']['column_from_right']
    assert result['status'] == 'photo_local_candidate_only'
    assert result['electrical_address'] is None and not result['electrical_connection_verified']
    assert result['grid_candidate']['occupancy'] == 'unknown' and not result['can_authorize_repair']


@pytest.mark.parametrize('visibility', ['occluded', 'out_of_frame'])
def test_hidden_point_never_snaps_or_counts_as_removal(catalog, visibility):
    photo, grid, point, target = fixture_point(catalog)
    result = point_evidence(photo, grid, 'master', point, visibility, target)
    assert result['status'] == 'needs_view' and result['grid_candidate'] is None
    assert result['additional_view_request']['actor'] == 'BenchMate'
    assert not result['additional_view_request']['model_authored']
    assert 'absence is not removal' in result['additional_view_request']['reason']


def test_projection_does_not_extrapolate_into_unverified_region(catalog):
    photo, grid, _, target = fixture_point(catalog)
    hole = next(h for h in grid['strips']['lower']['holes'] if h['in_image'] and not h['within_anchor_domain'])
    result = point_evidence(photo, grid, 'master', hole['image_xy'], 'visible', target)
    assert result['grid_candidate'] is None and result['status'] == 'outside_calibrated_contacts'


def test_grid_mismatch_failure_and_ambiguity_do_not_confirm(catalog):
    photo, grid, point, target = fixture_point(catalog)
    wrong = deepcopy(grid); wrong['master_sha256'] = 'f'*64
    with pytest.raises(ValueError): point_evidence(photo, wrong, 'master', point, 'visible', target)
    failed = deepcopy(grid); failed['geometry_gate_passed'] = False
    assert point_evidence(photo, failed, 'master', point, 'visible', target)['status'] == 'grid_failed'
    duplicate = deepcopy(grid); duplicate['strips']['copy'] = duplicate['strips']['lower']
    assert point_evidence(photo, duplicate, 'master', point, 'visible', target)['status'] == 'ambiguous_projection'


@pytest.mark.parametrize('point', [None, [float('nan'), 1], [True, 1], [-1, 2], [3024, 2], [1, float('inf')]])
def test_invalid_or_invisible_coordinates_rejected(catalog, point):
    photo, grid, _, target = fixture_point(catalog)
    with pytest.raises(ValueError): point_evidence(photo, grid, 'master', point, 'visible', target)


@pytest.fixture
def reviews(tmp_path):
    cases = CaseStore(ROOT, tmp_path / 'cases')
    store = PhotoReviewStore(ROOT, cases)
    m = cases.create('Software QA photo reference', 'recorded_walkthrough')['manifest']
    m = cases.confirm_for_replay(m['case_id'], m['revision'], m['intended_design']['draft_candidate'])['manifest']
    return store, m


def request(store, m):
    return {'revision': m['revision'], 'photo_revision': 0, 'review_id': uuid.uuid4().hex,
            'photo_id': 'img_8885', 'photo_sha256': store.catalog.internal('img_8885')['master']['sha256'],
            'target_id': 'blue-body', 'view': 'master', 'point': [600, 600], 'visibility': 'visible',
            'proposed_component_ref': 'C1', 'note': 'SOFTWARE QA: body point; no specimen or wiring identity confirmed.'}


def test_observations_append_correct_without_changing_case_or_electrical_graph(reviews):
    store, m = reviews
    req = request(store, m); first = store.review(m['case_id'], req)
    assert first['observation']['evidence']['status'] == 'body_point_only'
    assert not first['observation']['component_match_verified']
    assert first['observation']['measurement_support'] == []
    assert store.review(m['case_id'], req) == first
    corrected = {**req, 'photo_revision': 1, 'review_id': uuid.uuid4().hex, 'visibility': 'occluded', 'point': None}
    store.review(m['case_id'], corrected)
    history = store.list(m['case_id'])
    assert history['photo_revision'] == 2 and history['corrections'] == 1
    assert history['records'][0] == first
    assert history['latest_by_target'][0]['observation']['evidence']['status'] == 'needs_view'
    assert store.cases.get(m['case_id'])['manifest'] == m
    assert not any(r['observation']['runner_confirmation_created'] or r['observation']['electrical_graph_changed'] for r in history['records'])


def test_stale_foreign_or_assertive_observations_rejected(reviews):
    store, m = reviews; req = request(store, m)
    for change in ({'revision': 1}, {'photo_revision': True}, {'photo_revision': 1}, {'photo_sha256': 'f'*64},
                   {'proposed_component_ref': 'C2'}, {'target_id': 'unknown'}, {'removed': True},
                   {'visibility': 'confirmed_removed'}, {'same_state_verified': True}, {'note': ''}):
        with pytest.raises((ValueError, Conflict)): store.review(m['case_id'], {**req, **change})
    assert store.list(m['case_id'])['photo_revision'] == 0
    store.review(m['case_id'], req)
    with pytest.raises(Conflict): store.review(m['case_id'], {**req, 'point': [601, 600]})
    with pytest.raises(Conflict): store.review(m['case_id'], {**req, 'review_id': uuid.uuid4().hex})


def test_history_corruption_blocks_further_use(reviews):
    store, m = reviews; store.review(m['case_id'], request(store, m))
    path = store._folder(m['case_id']) / 'revision-0001.json'
    raw = json.loads(path.read_text()); raw['observation']['component_match_verified'] = True
    path.write_text(json.dumps(raw))
    with pytest.raises(ValueError): store.list(m['case_id'])


def test_http_photo_assets_and_mutations_keep_origin_guard(tmp_path):
    server = make_server(root=ROOT, output=tmp_path/'http', port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
    try:
        with httpx.Client(base_url=f'http://127.0.0.1:{server.server_port}', trust_env=False) as client:
            token = re.search(r'name="benchmate-session" content="([^"]+)"', client.get('/').text).group(1)
            headers = {'X-BenchMate-Session': token}
            assert client.get('/api/photo-evidence', headers={'Origin': 'https://evil.example'}).status_code == 403
            catalog = client.get('/api/photo-evidence').json()
            assert len(catalog['photos']) == 4 and catalog['same_state_groups'] == []
            assert client.get('/api/photo-evidence/img_8885/image').headers['Content-Type'] == 'image/png'
            assert client.get('/api/photo-evidence/img_8885/masks/sam-2/0').status_code == 200
            assert client.get('/api/photo-evidence/img_8887/masks/sam-2/0').status_code == 404
            assert client.get('/api/photo-evidence/img_8887/grid').json()['electrical_address_mapping'] == 'unconfirmed'
            m = client.post('/api/cases', headers=headers, json={'question':'HTTP photo QA', 'scope':'recorded_walkthrough'}).json()['manifest']
            m = client.post(f"/api/cases/{m['case_id']}/confirm", headers=headers,
                json={'revision':m['revision'], 'candidate':m['intended_design']['draft_candidate']}).json()['manifest']
            req = request(server.photo_store, m); url = f"/api/cases/{m['case_id']}/photo-reviews"
            assert client.post(url, json=req).status_code == 403
            assert client.post(url, headers=headers, json=req).status_code == 200
            assert client.get(url).json()['photo_revision'] == 1
            assert client.get('/api/runner-capabilities').json()['live_enabled'] is False
    finally:
        server.shutdown(); server.server_close(); thread.join(timeout=3)
