"""Local-only transport contract for an interactive, scripted D01 mock."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import uuid

from ..records import canonical, decode_events

PROTOCOL = 'examples/d01-repair-protocol/2026-11-01-repair-first/protocol.json'
PROTOCOL_SHA = '7eaecf38afb676465bad0619da2a49c4a773f313f797e108fcd7e93298b83824'
FAULTS = ('none', 'publication_failure', 'stale_boot', 'reset_during_reserved', 'repair_failed', 'reserved_failure')
MODE = 'scripted_mock'
CHECKS = {
    'attach_output_load': ('USB_connected', 'USB_off_wiring_confirmed', 'remaining_wiring_unchanged'),
    'restore_nominal_capacitance': ('USB_connected', 'USB_off_wiring_confirmed', 'additional_capacitor_removed',
                                  'original_capacitor_and_load_retained', 'remaining_wiring_unchanged'),
}
CAPABILITIES = {'modes': [MODE], 'data_origin': 'Simulated', 'decision_actor': 'scripted_controller',
                'paid_api': False, 'hardware_execution': False, 'live_enabled': False,
                'automatic_retry': False, 'faults': list(FAULTS), 'confirmation_timeout_s': 300}


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def read_json(path, maximum=2_000_000):
    path = Path(path)
    if path.is_symlink() or not path.is_file() or path.stat().st_size > maximum:
        raise ValueError('Invalid local runner file')
    def invalid(_):
        raise ValueError('Non-finite JSON is invalid')
    return json.loads(path.read_bytes(), parse_constant=invalid)


def atomic_json(path, value):
    """Expose a complete response atomically, without replacing an existing response."""
    path = Path(path)
    temp = path.with_name('.' + path.name + '.' + uuid.uuid4().hex)
    try:
        with temp.open('xb') as out:
            out.write(canonical(value) + b'\n')
            out.flush()
            os.fsync(out.fileno())
        os.link(temp, path)
    finally:
        temp.unlink(missing_ok=True)


def verified_protocol(root):
    root = Path(root).resolve()
    path = root / PROTOCOL
    if path.is_symlink() or hashlib.sha256(path.read_bytes()).hexdigest() != PROTOCOL_SHA:
        raise ValueError('Frozen D01 protocol mismatch')
    value = read_json(path)
    for relative, expected in value['source_sha256'].items():
        source = root / relative
        if source.is_symlink() or not source.resolve().is_relative_to(root) or hashlib.sha256(source.read_bytes()).hexdigest() != expected:
            raise ValueError('Frozen D01 source mismatch: ' + relative)
    return value


def frozen_runner(root):
    protocol = verified_protocol(root)
    path = Path(root) / 'scripts/physical_d01_repair.py'
    spec = importlib.util.spec_from_file_location('benchmate_frozen_repair_runner', path)
    runner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runner)
    if runner.source_hashes() != protocol['source_sha256'] or runner.POLICY != protocol['repair_policy']:
        raise ValueError('Frozen experiment closure mismatch')
    return runner, protocol


def read_events(path):
    path = Path(path)
    if not path.exists():
        return []
    if path.is_symlink() or path.stat().st_size > 32_000_000:
        raise ValueError('Invalid or oversized event record')
    raw = path.read_bytes()
    # A worker append may be in progress; only newline-terminated records are public.
    if raw and not raw.endswith(b'\n'):
        raw = raw[:raw.rfind(b'\n') + 1]
    return decode_events(raw, require_terminal=False, include_hash=True)


def record_folder(run):
    run = Path(run)
    marker = run / 'record-location.json'
    if not marker.exists():
        return None
    relative = read_json(marker)['path']
    path = run / relative
    if Path(relative).is_absolute() or len(Path(relative).parts) != 2 or Path(relative).parts[0] != 'records':
        raise ValueError('Invalid record location')
    if path.is_symlink() or not path.resolve().is_relative_to((run / 'records').resolve()):
        raise ValueError('Invalid record location')
    return path


def validate_response(report, request):
    """Same minimum physical report fields, explicitly marked as simulated transport."""
    if (not isinstance(report, dict) or report.get('simulated') is not True
        or report.get('request_id') != request['request_id'] or report.get('action') != request['action']
        or report.get('prediction_sha256') != request['prediction_sha256']
        or report.get('fixture') != 'output_load' or report.get('cancelled') is True
        or any(report.get(k) is not True for k in CHECKS[request['action']])
        or not isinstance(report.get('verbatim'), str) or not report['verbatim'].strip()):
        raise ValueError('Matching simulated operator confirmation required')
