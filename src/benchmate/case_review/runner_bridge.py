"""Supervise bounded D01 scripted mocks; no API-provider or hardware launch path."""
from datetime import datetime, timezone
import os
from pathlib import Path
import re
import subprocess
import sys
from threading import RLock
import uuid

from ..d01_repair import reviewed_design
from .service import Conflict
from .runner_contract import (CAPABILITIES, CHECKS, FAULTS, MODE, PROTOCOL_SHA, atomic_json,
                              digest, read_events, read_json, record_folder, validate_response,
                              verified_protocol)


def identity(value):
    if not isinstance(value, str) or not re.fullmatch(r'[0-9a-f]{32}', value):
        raise ValueError('Expected a 32-character lowercase hex identity')
    return value


def exact(value, keys):
    if not isinstance(value, dict) or set(value) != set(keys):
        raise ValueError('Unexpected request fields')


class RunnerBridge:
    def __init__(self, root, store, *, confirmation_timeout_s=300):
        if not 0 < confirmation_timeout_s <= 300:
            raise ValueError('Invalid timeout')
        self.root, self.store = Path(root).resolve(), store
        self.output = store.output / 'runner-runs'
        if self.output.is_symlink():
            raise ValueError('Invalid runner directory')
        self.output.mkdir(exist_ok=True)
        self.timeout = confirmation_timeout_s
        self.lock, self.children, self.closed = RLock(), {}, False

    def _folder(self, run_id):
        folder = self.output / identity(run_id)
        if folder.is_symlink() or not folder.is_dir():
            raise KeyError('Unknown run')
        return folder

    def _audit(self, folder, kind, details):
        target = folder / 'bridge-actions'
        target.mkdir(exist_ok=True)
        if target.is_symlink():
            raise ValueError('Invalid audit directory')
        if len(list(target.iterdir())) >= 1000:
            raise Conflict('Run action limit reached')
        atomic_json(target / (uuid.uuid4().hex + '.json'), {
            'timestamp': datetime.now(timezone.utc).isoformat(), 'kind': kind, **details})

    def launch(self, case_id, request):
        exact(request, ('revision', 'mode', 'fault', 'launch_id'))
        run_id = identity(request['launch_id'])
        if request['mode'] != MODE or request['fault'] not in FAULTS:
            raise ValueError('Only a registered scripted mock is available')
        if type(request['revision']) is not int:
            raise Conflict('Current integer case revision required')
        with self.lock:
            if self.closed:
                raise Conflict('Runner bridge is closed')
            case = self.store.get(case_id)
            m = case['manifest']
            if m['revision'] != request['revision'] or not m['experiment_link'] or not case['replay_eligibility']['allowed']:
                raise Conflict('Confirm and seal the matching nominal design before a mock run')
            design = m['intended_design']['reviewed']
            _, design_sha = reviewed_design(design)
            launch = {'schema': 'benchmate.interactive_mock_launch.v1', 'run_id': run_id,
                      'mode': MODE, 'fault': request['fault'], 'case_id': case_id,
                      'case_revision': m['revision'], 'case_manifest_sha256': case['manifest_sha256'],
                      'reviewed_design_sha256': design_sha, 'protocol_sha256': PROTOCOL_SHA,
                      'confirmation_timeout_s': self.timeout, 'question_sent_to_model': False}
            folder = self.output / run_id
            if folder.exists():
                if read_json(self._folder(run_id) / 'launch.json') != launch:
                    raise Conflict('Launch identity belongs to a different request')
                return self.snapshot(run_id)  # Lost HTTP response must not launch another worker.
            if any(child.poll() is None for child in self.children.values()):
                raise Conflict('Another mock run is active')
            if len(list(self.output.iterdir())) >= 100:
                raise Conflict('Local run limit reached')
            verified_protocol(self.root)  # Fail before spawning if the frozen closure changed.
            folder.mkdir()
            atomic_json(folder / 'launch.json', launch)
            atomic_json(folder / 'reviewed-design.json', design)
            self._audit(folder, 'launch', {'launch_sha256': digest(launch), 'mode': MODE})
            # No API keys, device paths, arbitrary executable or provider is inherited.
            env = {key: os.environ[key] for key in ('PATH', 'LANG', 'LC_ALL', 'SYSTEMROOT') if key in os.environ}
            env.update({'PYTHONPATH': str(self.root / 'src'), 'PYTHONDONTWRITEBYTECODE': '1',
                        'OPENBLAS_NUM_THREADS': '1', 'OMP_NUM_THREADS': '1', 'MKL_NUM_THREADS': '1'})
            try:
                with (folder / 'worker.log').open('xb') as stream:
                    self.children[run_id] = subprocess.Popen(
                        [sys.executable, '-m', 'benchmate.case_review.runner_worker', '--run-dir', str(folder)],
                        cwd=self.root, env=env, stdin=subprocess.DEVNULL, stdout=stream, stderr=stream,
                        start_new_session=True)
            except OSError as error:
                self._audit(folder, 'launch_failed', {'error': type(error).__name__})
                raise Conflict('Worker did not start; failed launch preserved') from None
            return self.snapshot(run_id)

    def _events(self, folder):
        record = record_folder(folder)
        return read_events(record / 'events.jsonl') if record else []

    def _pending(self, folder, events):
        requests = [e for e in events if e['kind'] == 'operator_action_requested' and e['payload'].get('request_id')]
        if not requests:
            return None
        event = requests[-1]
        request = event['payload']
        request_id = identity(request['request_id'])
        contexts = [e for e in events[:event['sequence']] if e['kind'] == 'bridge_operator_context']
        if not contexts:
            raise ValueError('Operator request lacks bridge context')
        context = contexts[-1]['payload']
        if context['action'] != request['action'] or context['prediction_sha256'] != request['prediction_sha256']:
            raise ValueError('Operator request context mismatch')
        if any(e['kind'] == 'bridge_operator_response_consumed' and e['payload']['request_id'] == request_id for e in events):
            return None
        record = record_folder(folder)
        if (record / ('operator-response-' + request_id + '.json')).exists():
            return None
        if request['action'] not in CHECKS:
            raise ValueError('Unknown operator action')
        return {'request_id': request_id, 'action': request['action'], 'fixture': 'output_load',
                'prediction_sha256': request['prediction_sha256'], 'expected_boot_id': context['boot_id'],
                'wiring_revision': context['wiring_revision'], 'request_sha256': digest({'run_id': folder.name, 'request': request, 'context': context}),
                'event_sequence': event['sequence'], 'required_checks': list(CHECKS[request['action']]),
                'simulated': True, 'physical_action_requested': False,
                'instruction': 'SIMULATION ONLY: confirm the simulated load connection.' if request['action'] == 'attach_output_load' else
                               'SIMULATION ONLY: confirm simulated capacitor removal after the local mock forecast freeze.'}

    def snapshot(self, run_id):
        with self.lock:
            folder = self._folder(run_id)
            launch = read_json(folder / 'launch.json')
            events = self._events(folder)
            terminal = events[-1] if events and events[-1]['kind'] in ('run_completed', 'run_failed') else None
            child = self.children.get(run_id)
            running = child is not None and child.poll() is None
            cancelled = (folder / 'cancel-request.json').exists()
            pending = self._pending(folder, events) if running and not terminal and not cancelled else None
            if terminal:
                status = terminal['payload']['termination']
            elif cancelled:
                status = 'cancelling' if running else 'cancelled'
            elif not running:
                status = 'interrupted'
            else:
                status = 'awaiting_operator' if pending else 'running'
            publication = next((e['payload'] for e in reversed(events) if e['kind'] == 'repair_prediction_publication'), None)
            return {'schema': 'benchmate.interactive_mock_snapshot.v1', 'run_id': run_id,
                    'case_id': launch['case_id'], 'case_revision': launch['case_revision'], 'mode': MODE,
                    'data_origin': 'Simulated', 'decision_actor': 'scripted_controller', 'status': status,
                    'paid_api_calls': 0, 'physical_measurements': 0, 'hardware_IO': False,
                    'question_sent_to_model': False, 'automatic_retry': False,
                    'event_count': len(events), 'last_event_sha256': events[-1]['sha256'] if events else None,
                    'mock_waveforms': sum(e['kind'] == 'mock_rc_observation' for e in events),
                    'pending_request': pending, 'publication': publication,
                    'publication_label': 'Local mock freeze; not published remotely' if publication else None,
                    'result': terminal['payload'] if terminal else None}

    def list_runs(self, case_id):
        with self.lock:
            self.store.get(case_id)
            return [self.snapshot(p.name) for p in sorted(self.output.iterdir())
                    if re.fullmatch(r'[0-9a-f]{32}', p.name) and not p.is_symlink()
                    and read_json(p / 'launch.json')['case_id'] == case_id]

    def events(self, run_id, after=-1):
        if type(after) is not int or not -1 <= after <= 10000:
            raise ValueError('Invalid event cursor')
        with self.lock:
            events = self._events(self._folder(run_id))
            page = [e for e in events if e['sequence'] > after][:50]
            return {'run_id': run_id, 'data_origin': 'Simulated', 'events': page,
                    'next_after': page[-1]['sequence'] if page else after, 'total': len(events)}

    def predictions(self, run_id):
        with self.lock:
            folder = self._folder(run_id)
            events = self._events(folder)
            frozen = next((e for e in events if e['kind'] == 'repair_prediction_frozen'), None)
            published = next((e for e in events if e['kind'] == 'repair_prediction_publication'), None)
            if not frozen or not published:
                raise Conflict('Local mock prediction freeze is not available')
            value = read_json(record_folder(folder) / 'predictions-frozen.json')
            if (digest(value) != published['payload']['sha256'] or digest(value) != frozen['payload']['sha256']
                or {k: v for k, v in frozen['payload'].items() if k != 'sha256'} != value
                or published['payload'].get('remote') is not False):
                raise ValueError('Mock prediction integrity check failed')
            return {'data_origin': 'Simulated', 'label': 'Before-acquisition commanded-input forecast',
                    'publication_label': 'Local mock freeze; not published remotely',
                    'sha256': digest(value), 'event_sequence': frozen['sequence'], 'predictions': value}

    def respond(self, run_id, response):
        with self.lock:
            folder = self._folder(run_id)
            try:
                pending = self.snapshot(run_id)['pending_request']
                if not pending:
                    raise Conflict('No current operator request; do not retry a confirmation')
                keys = ('request_id', 'action', 'fixture', 'prediction_sha256', 'expected_boot_id',
                        'wiring_revision', 'request_sha256', 'simulated', 'verbatim', *pending['required_checks'])
                if not isinstance(response, dict):
                    raise ValueError('Object confirmation required')
                if any(response.get(k) != pending[k] for k in ('request_id', 'action', 'fixture', 'prediction_sha256',
                       'expected_boot_id', 'wiring_revision', 'request_sha256')) or type(response.get('wiring_revision')) is not int:
                    raise Conflict('Stale or mismatched operator request')
                exact(response, keys)
                if not isinstance(response['verbatim'], str) or len(response['verbatim']) > 2000:
                    raise ValueError('Bounded confirmation text required')
                validate_response(response, pending)
                path = record_folder(folder) / ('operator-response-' + pending['request_id'] + '.json')
                atomic_json(path, response)
                self._audit(folder, 'operator_response_accepted', {'request_id': pending['request_id'], 'response_sha256': digest(response)})
            except (ValueError, Conflict) as error:
                self._audit(folder, 'operator_response_rejected', {'error': str(error)})
                raise
            return self.snapshot(run_id)

    def cancel(self, run_id, reason):
        if not isinstance(reason, str) or not reason.strip() or len(reason) > 500:
            raise ValueError('A bounded cancellation reason is required')
        with self.lock:
            folder = self._folder(run_id)
            state = self.snapshot(run_id)
            if state['status'] not in ('running', 'awaiting_operator', 'cancelling'):
                return state
            marker = folder / 'cancel-request.json'
            if not marker.exists():
                atomic_json(marker, {'reason': reason, 'source': 'local_software_operator', 'simulated': True})
                self._audit(folder, 'cancel_requested', {'reason': reason})
            child = self.children.get(run_id)
            if child and child.poll() is None and state['status'] != 'cancelling':
                child.terminate()  # Only a child created by this manager, never a persisted PID.
            return self.snapshot(run_id)

    def close(self):
        with self.lock:
            self.closed = True
            for run_id, child in self.children.items():
                if child.poll() is None:
                    try:
                        self.cancel(run_id, 'Local server closed')
                    except (ValueError, KeyError, OSError, Conflict):
                        # Corrupt records must not prevent cleanup of our own child.
                        if child.poll() is None:
                            child.terminate()
                    try:
                        child.wait(timeout=3)
                    except subprocess.TimeoutExpired:
                        child.kill()
                        child.wait(timeout=3)
