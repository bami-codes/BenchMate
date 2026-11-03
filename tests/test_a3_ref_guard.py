"""Primary REF failures remain visible; A4 is explicitly auxiliary, not erased."""
import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from benchmate.a3_ref_guard import assess

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = json.loads((ROOT / 'examples/official-prepared/2026-11-03/design-01/protocol.json').read_text())
CONFIG = SimpleNamespace(**PROTOCOL['configuration'])
LIMITS = PROTOCOL['guard_limits']


def run_blocks(blocks):
    history = []; results = []
    for counts, hold in blocks:
        v = counts * CONFIG.vref_v / 16383
        history.append({'hold': hold, 'means': v.mean(0).tolist()})
        results.append(assess(counts, history, CONFIG, LIMITS, hold=hold))
    return results


def baseline():
    return np.full((512, 4), 5500, dtype=int)


def test_primary_REF_mean_change_above_3mV_is_rejected():
    a = baseline(); b = a.copy(); b[:, 2] += 14
    result, aux = run_blocks([(a, True), (b, False)])[-1]
    assert not result['REF_A3_block_mean_span']


def test_one_volt_REF_sample_failure_is_rejected_even_with_stable_mean():
    a = baseline(); a[477, 2] = 2128
    result, aux = run_blocks([(a, True)])[-1]
    assert not result['REF_A3_envelope'] and not result['path_samples_A1_A2_A3']


@pytest.mark.parametrize('channel', [0, 1])
def test_IN_OUT_rail_and_HOLD_protection_remain(channel):
    a = baseline(); a[0, channel] = 0
    result, aux = run_blocks([(a, True)])[-1]
    assert not result['rails_A1_A2_A3']
    assert not result['path_samples_A1_A2_A3']


def test_A4_failure_is_retained_as_warning_without_becoming_primary_REF():
    a = baseline(); b = a.copy(); b[:, 3] += 14
    result, aux = run_blocks([(a, True), (b, False)])[-1]
    assert all(result.values())
    assert not aux['block_mean_span_3mV_ok'] and aux['block_mean_span_mV'] > 3
    assert aux['role'] == 'record_and_report_only'


@pytest.mark.parametrize('run,expected_rejections', [
    ('20261103T072121-1138ccf241', ['training_2_origin_2_raw_capture']),
    ('20261103T074537-7424df4144', []),
])
def test_retained_failure_replay_is_guard_only_and_never_refits(run, expected_rejections):
    path = ROOT / 'examples/official-runs/2026-11-03/records' / run / 'events.jsonl'
    events = [json.loads(l) for l in path.read_text().splitlines()]
    history = []; rejected = []; auxiliary_warnings = []
    for e in events:
        if e['kind'] == 'netlist_physical_acquisition_plan' and e['payload']['fresh_boot_required']:
            history = []
        if not e['kind'].endswith('_raw_capture'):
            continue
        p = e['payload']; counts = np.asarray(p['rows'])[:, 2:6]
        hold = p['kind'].lower() == 'hold'
        history.append({'hold': hold, 'means': (counts * CONFIG.vref_v / 16383).mean(0).tolist()})
        checks, auxiliary = assess(counts, history, CONFIG, LIMITS, hold=hold)
        if not all(checks.values()): rejected.append(e['kind'])
        if not auxiliary['block_mean_span_3mV_ok']: auxiliary_warnings.append(e['kind'])
    assert rejected == expected_rejections
    if not expected_rejections:
        assert auxiliary_warnings == ['training_3_raw_capture']


def test_real_capture_packet_logs_all_channels_then_stops_on_A3_fault():
    from benchmate.a3_ref_guard import A3GuardMixin
    from benchmate.instrument import InstrumentConfig
    events = [json.loads(l) for l in (ROOT / 'examples/official-runs/2026-11-03/records/'
              '20261103T072121-1138ccf241/events.jsonl').read_text().splitlines()]
    packet = next(e['payload'] for e in events if e['kind'] == 'training_2_origin_2_raw_capture')
    calls = []
    b = A3GuardMixin()
    b.config = InstrumentConfig(**PROTOCOL['configuration'])
    b.p = PROTOCOL; b.capture_attempts = b.frames = 0; b.reference_means = []
    b.log = SimpleNamespace(add=lambda kind, data: calls.append((kind, data)))
    b._request = lambda *args: packet
    b._ping = lambda *args: calls.append(('postcheck', None))
    with pytest.raises(ValueError, match='Primary A3'):
        b._capture(None, SimpleNamespace(boot_id=packet['boot_id']), 'injected_capture',
                   {'kind': 'hold', 'samples': 512, 'period_us': 2000, 'hold_v': b.config.ref_v})
    assert b.frames == 512 and b.capture_attempts == 1
    assert calls[-1][0] == 'physical_electrical_guard'
    assert calls[-1][1]['primary_REF_channel'] == 'A3'
    assert len(calls[-1][1]['means_v']) == 4
