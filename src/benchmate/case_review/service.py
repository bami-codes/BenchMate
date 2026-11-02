"""Immutable local case revisions; archived experiments remain independent."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
from threading import RLock
import uuid

from ..design_replay import D01, VISION, IMAGE_SHA, RESULT_SHA, load_demo, matches_d01
from ..known_design import confirm_design, validate_candidate, candidate_netlist
from ..records import canonical
from .evidence import RecordedConversation

SCHEMA = 'benchmate.case_session.v1'
SCOPES = ('recorded_walkthrough', 'different_specimen')
CAPABILITIES = {'paid_api': False, 'hardware_execution': False, 'photo_state_linking': False}
SCENES = [
    {'event_sequence': 50, 'label': 'Unexpected response'},
    {'event_sequence': 54, 'label': 'Spark requests a load'},
    {'event_sequence': 94, 'label': 'Compare the explanations'},
    {'event_sequence': 139, 'label': 'Verification and conclusion'},
]


class Conflict(ValueError):
    """A stale revision, invalid local record, or unsupported handoff."""


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def text_field(value, name, maximum=2000):
    if not isinstance(value, str) or not value.strip() or len(value) > maximum or '\x00' in value:
        raise ValueError(f'{name} must contain 1–{maximum} characters')
    return value.strip()


def eligibility(case):
    if case['scope'] != 'recorded_walkthrough':
        return {'allowed': False, 'code': 'different_specimen',
                'message': 'This is a different circuit. The archived D01 run cannot diagnose it.'}
    design = case['intended_design']
    if not design['reviewed']:
        code = design.get('review_state', 'review_required')
        return {'allowed': False, 'code': code,
                'message': {'needs_information': 'Resolve the unreadable value or connection before linking evidence.',
                            'unsupported_design': 'This design is outside the supported one-R / one-C low-pass.'}.get(
                                code, 'Check the schematic values and connections, then save your review.')}
    if not matches_d01(design['reviewed']):
        return {'allowed': False, 'code': 'nominal_design_mismatch',
                'message': 'The archived example requires 10 kΩ and 1 µF. This reviewed design differs.'}
    return {'allowed': True, 'code': 'matching_historical_example',
            'message': 'Matching nominal design. The schematic reading and physical experiment are separate records.'}


class CaseStore:
    def __init__(self, root, output):
        self.demo = load_demo(Path(root))  # Verify pinned archive bytes and event chains once, then serve that snapshot.
        self.conversation = RecordedConversation(root)
        self.output = Path(output).resolve()
        self.output.mkdir(parents=True, exist_ok=True)
        self.lock = RLock()

    def _folder(self, case_id):
        if not isinstance(case_id, str) or not re.fullmatch(r'[0-9a-f]{32}', case_id):
            raise KeyError('Unknown case')
        folder = self.output / case_id
        if folder.is_symlink():
            raise Conflict('Local case integrity check failed')
        return folder

    def _load(self, case_id):
        folder = self._folder(case_id)
        if not folder.is_dir():
            raise KeyError('Unknown case')
        paths = sorted(folder.glob('revision-*.json'))
        if not paths:
            raise Conflict('Local case has no complete revision')
        previous = '0' * 64
        try:
            for revision, path in enumerate(paths, 1):
                if path.is_symlink() or path.name != f'revision-{revision:04d}.json' or path.stat().st_size > 200_000:
                    raise ValueError('Invalid revision')
                envelope = json.loads(path.read_bytes())
                if set(envelope) != {'manifest', 'previous_sha256', 'sha256'}:
                    raise ValueError('Invalid envelope')
                claimed = envelope.pop('sha256')
                if digest(envelope) != claimed or envelope['previous_sha256'] != previous:
                    raise ValueError('Invalid revision chain')
                case = envelope['manifest']
                if case['schema'] != SCHEMA or case['case_id'] != case_id or case['revision'] != revision:
                    raise ValueError('Invalid manifest')
                if case['capabilities'] != CAPABILITIES:
                    raise ValueError('Invalid capability')
                previous = claimed
            return case, previous
        except (ValueError, KeyError, TypeError, OSError):
            raise Conflict('Local case integrity check failed') from None

    def _save(self, case, previous):
        folder = self._folder(case['case_id'])
        folder.mkdir(exist_ok=True)
        envelope = {'manifest': case, 'previous_sha256': previous}
        envelope['sha256'] = digest(envelope)
        # A revision is never replaced. Truncated writes fail closed on the next read.
        with (folder / f"revision-{case['revision']:04d}.json").open('x') as file:
            file.write(json.dumps(envelope, ensure_ascii=False, indent=2, allow_nan=False) + '\n')
        return self.get(case['case_id'])

    def get(self, case_id):
        with self.lock:
            case, record_sha = self._load(case_id)
            return {'manifest': deepcopy(case), 'manifest_sha256': digest(case),
                    'revision_record_sha256': record_sha, 'replay_eligibility': eligibility(case)}

    def summaries(self):
        result = []
        with self.lock:
            for folder in sorted(self.output.iterdir()):
                if not re.fullmatch(r'[0-9a-f]{32}', folder.name):
                    continue
                try:
                    case, _ = self._load(folder.name)
                    result.append({'case_id': case['case_id'], 'question': case['question']['text'],
                                   'revision': case['revision'], 'status': case['status']})
                except (Conflict, KeyError):
                    result.append({'case_id': folder.name, 'question': 'Unreadable local case',
                                   'revision': None, 'status': 'integrity_error'})
        return result

    def create(self, question, scope):
        question = text_field(question, 'Question')
        if scope not in SCOPES:
            raise ValueError('Choose the recorded example or a different circuit')
        with self.lock:
            if len(self.summaries()) >= 100:
                raise Conflict('This local library is limited to 100 cases')
            case = {'schema': SCHEMA, 'case_id': uuid.uuid4().hex, 'revision': 1,
                    'created_at': datetime.now(timezone.utc).isoformat(), 'scope': scope,
                    'status': 'review_required', 'capabilities': deepcopy(CAPABILITIES),
                    'question': {'text': question, 'source': 'current_user',
                                 'task': 'd01_response_mismatch', 'sent_to_model': False,
                                 'included_in_historical_experiment': False},
                    'intended_design': {'source_kind': 'recorded_intended_schematic',
                        'source_record': VISION, 'source_date_kst': '2026-10-31',
                        'vision_record_sha256': self.demo['provenance']['vision_record_sha256'],
                        'image_sha256': IMAGE_SHA, 'original_result_sha256': RESULT_SHA,
                        'original_candidate': deepcopy(self.demo['result']['candidate']),
                        'draft_candidate': deepcopy(self.demo['result']['candidate']),
                        'reviewed': None, 'review_note': None, 'review_state': 'review_required'},
                    'observed_assembly': None, 'component_mapping': [], 'capture_state': None,
                    'measurement_registry': [], 'hypotheses': [], 'answer': None,
                    'operator_request': None, 'experiment_link': None,
                    'history_note': 'New local question and review; no historical experiment is changed.'}
            return self._save(case, '0' * 64)

    def _current(self, case_id, expected_revision):
        case, record_sha = self._load(case_id)
        if type(expected_revision) is not int or expected_revision != case['revision']:
            raise Conflict('This case changed. Reload it before saving another action.')
        return deepcopy(case), record_sha

    def review(self, case_id, expected_revision, candidate, note):
        note = text_field(note, 'Review note')
        if len(canonical(candidate)) > 24_000:
            raise ValueError('Design candidate is too large')
        checked = validate_candidate(candidate)
        with self.lock:
            case, previous = self._current(case_id, expected_revision)
            if case['experiment_link']:
                raise Conflict('This evidence link is sealed. Start a new case to change its design.')
            design = case['intended_design']
            design.update(draft_candidate=deepcopy(checked), review_note=note,
                          review_saved_at=datetime.now(timezone.utc).isoformat())
            try:
                design['reviewed'] = confirm_design(self.demo['result'], checked, reviewer_note=note)
                design['review_state'] = 'reviewed'
            except ValueError:
                design['reviewed'] = None
                unknown = (checked['status'] == 'incomplete' or bool(checked['ambiguities'])
                           or any(p['value_si'] is None or 'UNKNOWN' in (p['a'], p['b']) for p in checked['components']))
                design['review_state'] = 'needs_information' if unknown else 'unsupported_design'
            design['candidate_netlist'] = candidate_netlist(checked)
            gate = eligibility(case)
            case['status'] = 'ready_for_replay' if gate['allowed'] else gate['code']
            case['revision'] += 1
            return self._save(case, previous)

    def link_replay(self, case_id, expected_revision):
        with self.lock:
            case, previous = self._current(case_id, expected_revision)
            if case['experiment_link']:
                raise Conflict('This recorded experiment is already linked')
            gate = eligibility(case)
            if not gate['allowed']:
                raise Conflict(gate['message'])
            case['experiment_link'] = {'source_record': D01,
                'record_sha256': self.demo['provenance']['physical_record_sha256'],
                'source_date_kst': '2026-10-30', 'data_origin': 'Physical', 'view_mode': 'Replay',
                'relationship': 'same_nominal_design_only', 'same_specimen_established': False,
                'new_measurement': False, 'question_was_input_to_run': False,
                'scenes': deepcopy(SCENES)}
            case['status'] = 'replay_linked'
            case['revision'] += 1
            return self._save(case, previous)

    def replay(self, case_id):
        with self.lock:
            case, _ = self._load(case_id)
            if not case['experiment_link'] or not eligibility(case)['allowed']:
                raise Conflict('Review and link this case before opening its recorded experiment')
            return self.demo['viewer']

    def conversation_snapshot(self, case_id, cursor):
        with self.lock:
            self.replay(case_id)  # Same case-specific design/link gate as the evidence viewer.
            return self.conversation.snapshot(cursor)

    def conversation_event(self, case_id, sequence, cursor):
        with self.lock:
            self.replay(case_id)
            return self.conversation.event(sequence, cursor)

    def confirm_for_replay(self, case_id, expected_revision, candidate):
        with self.lock:
            # Explicit button confirmation; this generated note is not user prose.
            result = self.review(case_id, expected_revision, candidate,
                'Design confirmed via the review button; generated action note, no free-text note supplied.')
            if result['replay_eligibility']['allowed']:
                return self.link_replay(case_id, result['manifest']['revision'])
            return result
