"""Append-only local photo observations. No evidence is fed to an experiment runner."""
from copy import deepcopy
from datetime import datetime, timezone
import re
from threading import RLock

from ..photo_bench.evidence import PhotoCatalog, point_evidence
from .runner_contract import atomic_json, digest, read_json
from .service import Conflict

FIELDS = {'revision', 'photo_revision', 'review_id', 'photo_id', 'photo_sha256', 'target_id',
          'view', 'point', 'visibility', 'proposed_component_ref', 'note'}


class PhotoReviewStore:
    def __init__(self, root, cases):
        self.catalog, self.cases, self.lock = PhotoCatalog(root), cases, RLock()

    def _folder(self, case_id):
        self.cases.get(case_id)
        folder = self.cases.output / case_id / 'photo-reviews'
        if folder.is_symlink():
            raise ValueError('Invalid photo review folder')
        return folder

    def _load(self, case_id):
        records, previous = [], '0' * 64
        for i, path in enumerate(sorted(self._folder(case_id).glob('revision-*.json')), 1):
            record = read_json(path)
            if path.name != f'revision-{i:04d}.json' or set(record) != {'observation', 'previous_sha256', 'sha256'}:
                raise ValueError('Invalid photo review revision')
            envelope = {k: v for k, v in record.items() if k != 'sha256'}
            if digest(envelope) != record['sha256'] or record['previous_sha256'] != previous:
                raise ValueError('Photo review integrity check failed')
            if record['observation']['case_id'] != case_id or record['observation']['photo_revision'] != i:
                raise ValueError('Cross-case photo review rejected')
            records.append(record)
            previous = record['sha256']
        return records

    def list(self, case_id):
        with self.lock:
            records = self._load(case_id)
            latest = {}
            for r in records:
                o = r['observation']
                latest[(o['photo_id'], o['target_id'])] = r
            return {'case_id': case_id, 'photo_revision': len(records), 'records': records,
                    'latest_by_target': list(latest.values()), 'corrections': len(records) - len(latest),
                    'electrically_verified_connections': 0, 'photo_state_linking_enabled': False,
                    'model_authored_observations': 0, 'can_authorize_repair': False}

    def review(self, case_id, request):
        if not isinstance(request, dict) or set(request) != FIELDS:
            raise ValueError('Unexpected photo observation fields')
        if not isinstance(request['review_id'], str) or not re.fullmatch(r'[0-9a-f]{32}', request['review_id']):
            raise ValueError('Expected a unique 32-character lowercase hex review ID')
        if type(request['revision']) is not int or type(request['photo_revision']) is not int:
            raise Conflict('Current case and photo revisions required')
        with self.lock:
            case = self.cases.get(case_id)
            m = case['manifest']
            if m['revision'] != request['revision'] or not m['experiment_link'] or not case['replay_eligibility']['allowed']:
                raise Conflict('Confirm the supported design before recording a photo reference')
            records = self._load(case_id)
            for r in records:
                if r['observation']['review_id'] == request['review_id']:
                    if r['observation']['request_sha256'] != digest(request):
                        raise Conflict('Review ID belongs to different input')
                    return r  # A lost HTTP response cannot append the same review twice.
            if request['photo_revision'] != len(records):
                raise Conflict('Photo observations changed; reload before saving')
            if len(records) >= 200:
                raise Conflict('Local photo review limit reached')
            photo = self.catalog.internal(request['photo_id'])
            if request['photo_sha256'] != photo['master']['sha256']:
                raise Conflict('Observation refers to another photo')
            if not self.catalog.describe(photo['id'])['available']:
                raise Conflict('Verified photo pixels are unavailable')
            targets = [x for x in photo['targets'] if x['id'] == request['target_id']]
            if len(targets) != 1:
                raise ValueError('Choose a declared photo target')
            # This is a proposed visual correspondence, never an electrical identification.
            if request['proposed_component_ref'] not in (None, 'R1', 'C1'):
                raise ValueError('Only nominal design references can be proposed; no extra capacitor is established')
            if not isinstance(request['note'], str) or not 1 <= len(request['note'].strip()) <= 2000:
                raise ValueError('A bounded observation note is required')
            evidence = point_evidence(photo, self.catalog.grid(photo['id']), request['view'], request['point'],
                                      request['visibility'], targets[0])
            observation = {'schema': 'benchmate.local_photo_observation.v1', 'case_id': case_id,
                'case_revision': m['revision'], 'case_manifest_sha256': case['manifest_sha256'],
                'photo_revision': len(records) + 1, 'review_id': request['review_id'], 'request_sha256': digest(request),
                'timestamp': datetime.now(timezone.utc).isoformat(), 'photo_id': photo['id'],
                'target_id': targets[0]['id'], 'target_description': targets[0]['description'],
                'submitted_point': request['point'], 'submitted_view': request['view'],
                'proposed_component_ref': request['proposed_component_ref'],
                'component_match_verified': False, 'measurement_support': [], 'note': request['note'],
                'electrical_graph_changed': False, 'runner_confirmation_created': False, 'evidence': evidence}
            envelope = {'observation': observation, 'previous_sha256': records[-1]['sha256'] if records else '0'*64}
            envelope['sha256'] = digest(envelope)
            folder = self._folder(case_id)
            folder.mkdir(exist_ok=True)
            atomic_json(folder / f'revision-{len(records)+1:04d}.json', envelope)
            return deepcopy(envelope)
