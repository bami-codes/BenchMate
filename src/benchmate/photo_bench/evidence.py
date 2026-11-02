"""Photo-local evidence and archived SAM masks, never electrical connectivity."""
from copy import deepcopy
import hashlib
import io
import json
from pathlib import Path

from PIL import Image

from ..records import decode_events
from .media import CropTransform
from .geometry import nearest_grid_point

CATALOG = 'examples/photo-targets/2026-11-02/catalog.json'


def point_evidence(photo, grid, view, point, visibility, target):
    if view not in ('master', 'overview') or visibility not in ('visible', 'occluded', 'out_of_frame'):
        raise ValueError('Unknown photo view or visibility')
    master_point = None
    if point is not None:
        if (not isinstance(point, list) or len(point) != 2 or
            any(type(x) not in (int, float) for x in point) or
            not all(0 <= x < photo[view][dimension] for x, dimension in zip(point, ('width', 'height')))):
            raise ValueError('Finite point inside the specified image required')
        master_point = list(CropTransform(**photo['overview']['transform']).to_master(*point)) if view == 'overview' else point
    if visibility == 'visible' and master_point is None:
        raise ValueError('Visible evidence requires a point')
    base = {'photo_sha256': photo['master']['sha256'], 'point_master': master_point,
            'visibility': visibility, 'electrical_address': None, 'electrical_connection_verified': False,
            'same_state_verified': False, 'can_authorize_repair': False, 'grid_candidate': None,
            'source_actor': 'local_operator', 'model_authored': False, 'additional_view_request': None}
    if visibility != 'visible':
        base.update(status='needs_view', additional_view_request={
            'actor': 'BenchMate', 'model_authored': False,
            'reason': 'This endpoint is occluded or outside this view; absence is not removal.',
            'instruction': 'Take a closer oblique view of ' + target['description'] +
                ', including adjacent holes. Keep wiring unchanged and retain the capture-state record.'})
        return base
    if target['kind'] == 'body_check':
        return {**base, 'status': 'body_point_only'}
    if not grid:
        return {**base, 'status': 'grid_unavailable'}
    if grid['master_sha256'] != photo['master']['sha256']:
        raise ValueError('Grid belongs to another photo')
    if grid.get('geometry_gate_passed') is not True:
        return {**base, 'status': 'grid_failed'}
    candidates = []
    for name, strip in grid['strips'].items():
        if strip.get('geometry_gate_passed') is not True:
            continue
        holes = strip['holes']
        columns = max(p['grid'][0] for p in holes) + 1
        rows = max(p['grid'][1] for p in holes) + 1
        candidate = nearest_grid_point(strip['homography'], master_point, columns, rows)
        if candidate:
            index = [candidate['column_from_right'], candidate['row_from_image_top']]
            matched = [p for p in holes if p['grid'] == index and p['in_image'] and p['within_anchor_domain']]
            if len(matched) == 1:
                candidates.append({'strip': name, **candidate})
    if len(candidates) == 1:
        return {**base, 'status': 'photo_local_candidate_only', 'grid_candidate': candidates[0]}
    return {**base, 'status': 'ambiguous_projection' if candidates else 'outside_calibrated_contacts'}


class PhotoCatalog:
    def __init__(self, root):
        self.root = Path(root).resolve()
        self.manifest = json.loads((self.root / CATALOG).read_bytes())
        if self.manifest['schema'] != 'benchmate.photo_evidence_catalog.v1':
            raise ValueError('Unknown photo catalog')
        self.photos = {p['id']: p for p in self.manifest['photos']}
        if len(self.photos) != len(self.manifest['photos']):
            raise ValueError('Duplicate photo identity')
        self.cache = {}

    def _bytes(self, ref):
        path = self.root / ref['path']
        if path.is_symlink() or not path.resolve().is_relative_to(self.root):
            raise ValueError('Photo asset must stay within this checkout')
        key = (ref['path'], ref['sha256'])
        if key not in self.cache:
            if not 0 < path.stat().st_size <= 80_000_000:
                raise ValueError('Photo evidence size limit')
            data = path.read_bytes()
            if hashlib.sha256(data).hexdigest() != ref['sha256']:
                raise ValueError('Photo evidence hash mismatch')
            self.cache[key] = data
        return self.cache[key]

    def _image(self, ref, *, mask=False):
        raw = self._bytes(ref)
        if not raw.startswith(b'\x89PNG\r\n\x1a\n'):
            raise ValueError('PNG evidence required')
        with Image.open(io.BytesIO(raw)) as image:
            image.load()
            if image.info or image.getexif() or getattr(image, 'n_frames', 1) != 1:
                raise ValueError('Metadata-free single image required')
            if image.mode != ('L' if mask else 'RGB'):
                raise ValueError('Unexpected image mode')
            if mask:
                colors = image.getcolors(maxcolors=3)
                if colors is None or any(value not in (0, 255) for _, value in colors):
                    raise ValueError('Binary mask required')
            if not mask and image.size != (ref['width'], ref['height']):
                raise ValueError('Image dimensions mismatch')
            return raw, image.size

    def internal(self, photo_id):
        if photo_id not in self.photos:
            raise KeyError('Unknown photo')
        return self.photos[photo_id]

    def image(self, photo_id, view='overview'):
        if view not in ('master', 'overview'):
            raise ValueError('Unknown image view')
        return self._image(self.internal(photo_id)[view])[0]

    def grid(self, photo_id):
        photo = self.internal(photo_id)
        if 'grid' not in photo:
            return None
        grid = json.loads(self._bytes(photo['grid']))
        if grid['master_sha256'] != photo['master']['sha256']:
            raise ValueError('Grid/photo mismatch')
        return grid

    def trials(self, photo_id):
        photo = self.internal(photo_id)
        trials = []
        for trial in photo['sam_trials']:
            if trial['input']['sha256'] != photo['master']['sha256']:
                raise ValueError('SAM mask belongs to a different image')
            self._bytes(trial['input'])
            decode_events(self._bytes(trial['events']))
            decoded = json.loads(self._bytes(trial['decoded']))
            if decoded['match_count'] != trial['match_count'] or trial['match_count'] != len(trial['masks']):
                raise ValueError('Mask count mismatch')
            masks = []
            for m, recorded in zip(trial['masks'], decoded['masks']):
                if m['bounds_half_open'] != recorded['bounds_half_open']:
                    raise ValueError('Recorded mask bounds mismatch')
                _, size = self._image(m['mask'], mask=True)
                if size != (photo['master']['width'], photo['master']['height']):
                    raise ValueError('Mask must use this exact full image plane')
                masks.append({'id': m['id'], 'bounds_half_open': m['bounds_half_open'],
                              'confidence': m['confidence'], 'confidence_is_accuracy': False,
                              'mask_url': f"/api/photo-evidence/{photo_id}/masks/{trial['id']}/{m['id']}",
                              'overlay_url': f"/api/photo-evidence/{photo_id}/overlays/{trial['id']}/{m['id']}"})
            trials.append({'id': trial['id'], 'concept': trial['concept'], 'match_count': trial['match_count'],
                           'source_actor': trial['source_actor'], 'source_events_sha256': trial['events']['sha256'],
                           'decoded_sha256': trial['decoded']['sha256'], 'input_sha256': trial['input']['sha256'],
                           'outcome': 'masks_returned' if masks else 'no_match', 'masks': masks,
                           'no_match_means_absent': False, 'circuit_identity_verified': False})
        return trials

    def mask(self, photo_id, trial_id, mask_id, *, overlay=False):
        # Validate attribution and the unedited source record before exposing a mask.
        self.trials(photo_id)
        photo = self.internal(photo_id)
        for trial in photo['sam_trials']:
            if trial['id'] == trial_id:
                for m in trial['masks']:
                    if m['id'] == mask_id:
                        ref = m['overlay' if overlay else 'mask']
                        if overlay:
                            ref = {**ref, 'width': photo['master']['width'], 'height': photo['master']['height']}
                        return self._image(ref, mask=not overlay)[0]
        raise KeyError('No such mask on this photo')

    def describe(self, photo_id):
        photo = self.internal(photo_id)
        available, issue = True, None
        try:
            self.image(photo_id, 'master')
            self.image(photo_id, 'overview')
        except FileNotFoundError:
            available, issue = False, 'private_photo_not_present'
        except ValueError:
            available, issue = False, 'photo_integrity_check_failed'
        return {'id': photo_id, 'label': photo['label'], 'available': available, 'issue': issue,
                'private_local_asset': photo['private'], 'photo_sha256': photo['master']['sha256'],
                'width': photo['master']['width'], 'height': photo['master']['height'],
                'overview_width': photo['overview']['width'], 'overview_height': photo['overview']['height'],
                'image_url': f'/api/photo-evidence/{photo_id}/image?view=overview' if available else None,
                'master_url': f'/api/photo-evidence/{photo_id}/image?view=master' if available else None,
                'overview_to_master': deepcopy(photo['overview']['transform']),
                'same_state_verified': False, 'capture_state_id': None, 'electrical_address_mapping': 'unconfirmed',
                'role': 'historical_development_reference', 'can_authorize_repair': False,
                'targets': deepcopy(photo['targets']), 'sam_trials': self.trials(photo_id),
                'grid_available': 'grid' in photo and available,
                'notice': 'Historical photo; not established as the Oct 30 specimen or the current live board.'}

    def list(self):
        return {'schema': self.manifest['schema'], 'photos': [self.describe(k) for k in self.photos],
                'same_state_groups': [], 'new_API_calls': 0, 'hardware_IO': False,
                'selection_note': self.manifest['selection_note']}
