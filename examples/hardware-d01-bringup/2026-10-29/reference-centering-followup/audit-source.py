"""Offline continuation audit. Reads captured evidence; never opens a device."""
import hashlib
import json
import shutil
import sys
from pathlib import Path

ROOT = Path('/Users/bami/Documents/metaai')
STAGE = Path('/private/tmp/benchmate-continuation-audit')
sys.path.insert(0, str(ROOT / 'src'))
from benchmate.records import read_events
from benchmate.instrument import validate_block

sources = {
    'alignment-after-dmm': 'runs/hardware-d01-reference-alignment/20261029T141757-e5abc8312a',
    'centering-plan': 'runs/hardware-local-ref-centering-plan/20261029T142321-622c7d06f9',
    'centering-trial': 'runs/hardware-local-ref-centering-trial/20261029T142505-120bb8e3b0',
    'centering-after-dmm': 'runs/hardware-d01-reference-alignment/20261029T142841-35469e8228',
    'centering-assessment': 'runs/hardware-local-ref-centering-assessment/20261029T143635-7472a4b244',
    'fixed-output-observation': 'runs/hardware-simultaneous-ref-difference/20261029T143944-c8d95652c0',
}
if STAGE.exists():
    raise RuntimeError('Staging destination already exists')
STAGE.mkdir()
manifest = []
for label, relative in sources.items():
    src = ROOT / relative
    events = read_events(src)
    assert events[-1]['kind'] == 'run_completed', relative
    shutil.copytree(src, STAGE / label)
    for path in sorted(src.rglob('*')):
        if path.is_file():
            suffix = path.relative_to(src)
            copied = STAGE / label / suffix
            assert path.read_bytes() == copied.read_bytes()
            manifest.append({'source': str(path.relative_to(ROOT)), 'copy': str(copied.relative_to(STAGE)),
                             'sha256': hashlib.sha256(path.read_bytes()).hexdigest()})

source = ROOT / sources['fixed-output-observation']
events = read_events(source)
s = json.loads((source / 'summary.json').read_text())
p = json.loads((ROOT / sources['centering-plan'] / 'plan.json').read_text())
capture_command = f"CAPTURE {s['boot_id']} HOLD 512 2000 {s['held_code']} 0"
raw_blocks = [e['payload'] for e in events if e['kind'] == 'hold_raw_capture']
assert len(raw_blocks) == len(s['blocks']) == 10
for b in raw_blocks:
    validate_block(b, expected_command=(capture_command + '\n').encode())
    assert b['boot_id'] == s['boot_id'] and b['overruns'] == 0
    assert len(b['rows']) == 512
    assert all(row[1] == s['held_code'] for row in b['rows'])
commands = [e['payload']['request'] for e in events if e['kind'] == 'serial_command']
assert set(commands) == {'PING', capture_command}
for e in events:
    b = e['payload']
    if b.get('type') == 'pong':
        assert b['boot_id'] == s['boot_id']
        assert b['current_code'] == b['ref_code'] == s['held_code']
        assert b['armed'] is True

gain = p['supply_estimate_v'] / 16383
anchored = []
for block, raw in zip(s['blocks'], raw_blocks):
    counts = block['mean_counts']
    for i, channel in enumerate(['A1', 'A2', 'A3', 'A4']):
        assert abs(counts[channel] - sum(row[i + 2] for row in raw['rows']) / 512) < 1e-9
    estimate = {}
    for channel in ['A3', 'A4']:
        a = p['control_anchor'][channel]
        estimate[channel] = a['anchor_v'] + a['gain_v_per_count_assumed'] * (counts[channel] - p['anchor_mean_counts'][channel])
    anchored.append((estimate['A3'] - estimate['A4']) * 1000)
raw_differences = [b['raw_nominal_A3_minus_A4_mV'] for b in s['blocks']]
spans = {ch: (max(b['mean_counts'][ch] for b in s['blocks']) - min(b['mean_counts'][ch] for b in s['blocks'])) * gain * 1000 for ch in ['A1', 'A2', 'A3', 'A4']}
report = {
    'mode': 'offline_continuation_audit_no_hardware_IO',
    'capture_start_utc': s['UTC_start'], 'capture_end_utc': s['UTC_end'],
    'boot_id': s['boot_id'], 'held_code': s['held_code'],
    'blocks': len(raw_blocks), 'frames': sum(len(b['rows']) for b in raw_blocks),
    'all_hash_chains_valid': True, 'all_blocks_valid': True,
    'only_same_code_hold_and_ping': True, 'overruns': 0,
    'raw_nominal_difference_mV_range': [min(raw_differences), max(raw_differences)],
    'existing_local_anchor_difference_mV_range': [min(anchored), max(anchored)],
    'existing_local_anchor_difference_mV_mean': sum(anchored) / len(anchored),
    'block_mean_span_mV': spans,
    'operator_report': {
        'verbatim': '해봤자 +- 0.002?',
        'source_session_id': '01a187d7-c426-7340-8518-ad7cde31c32c',
        'source_message_timestamp_utc': '2026-10-29T14:42:26.955Z',
        'interpretation': 'Approximate millivolt-scale variation; not an exact signed minimum/maximum or calibrated bound.',
        'exact_observation_interval_unknown': True,
        'contact_continuity_not_explicitly_confirmed': True,
    },
    'timing_limit': 'ADC window was 23:39:46.829–23:40:16.964 KST. Start notice was recorded at 23:40:06.052 KST; delivery/read time and operator interval are unknown. Exact overlap is not established.',
    'assessment': 'Existing local-anchor estimate is roughly compatible with the approximate report, but neither simultaneous accuracy nor automatic tracking is validated.',
    'no_new_fit_or_offset_adjustment': True,
    'automatic_tracking_enabled': False, 'full_D2_accepted': False,
    'physical_repair_performed': False,
    'hardware_status_report_in_continuation': '이전 세션 중단, USB·배선 그대로',
    'hardware_status_independently_rechecked': False,
    'next_order': [
        'Verify same boot and held state before any device operation.',
        'Resolve the remaining A4 tracking check with a clearly synchronized differential meter interval, or retain manual reference checks for a separately logged engineering repair.',
        'Freeze the repair prediction before requesting extra-capacitor removal; obtain fresh boot and reference checks after USB reconnection.',
        'Verify physical repair without refitting; restore B1 and complete the B1/B6 before/after-shunt gate.',
    ],
}
(STAGE / 'assessment.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
(STAGE / 'provenance.json').write_text(json.dumps(manifest, indent=2) + '\n')
shutil.copyfile(__file__, STAGE / 'audit-source.py')
(STAGE / 'README.md').write_text('''# Reference centering follow-up and session continuation

This archive preserves the fixed-output DMM bracket, one local centering move,
its independent DMM check, the later ADC mismatch, and the ten-block observation.
The original event chains and summaries are copied unchanged; their historical
`DMM_interval_report_pending` fields remain as originally recorded. The later
operator reply is added separately in [assessment.json](assessment.json).

The one move from code 1369 to 1374 passed the independent DMM point check
(REF / DRIVE / REF = 1.635 / 1.635 / 1.635 V). A later A4 mean changed by
5.53 mV, so this did not establish automatic reference tracking.

The subsequent capture ran from **23:39:46.829 to 23:40:16.964 KST on October
29, 2026**. All ten 512-frame blocks passed their original transport/timing
validation: 5,120 frames, zero overruns, the same boot and code 1374, and only
PING and fixed-code HOLD commands. The event hash chains verify locally;
they do not provide external attestation.

Across these ten blocks, channel-mean spans were **0.395 / 0.148 / 0.350 /
0.346 mV for A1 / A2 / A3 / A4** under the retained nominal conversion.
These are spans of block means, not per-sample noise or absolute accuracy.
Raw nominal A3-minus-A4 was -4.558 to -3.961 mV. Applying the already saved
local anchors, without any new fitting, gives **-2.012 to -1.415 mV**, mean
**-1.705 mV**.

The operator's later verbatim reply was **“해봤자 +- 0.002?”**. This is an
approximate report of millivolt-scale variation; it does not supply exact
signed extrema, a central value, contact continuity or observation timestamps.
The start notice was recorded at 23:40:06.052 KST, around 19 seconds into
the capture; message delivery/read time is unknown. Exact overlap between
the ADC and the operator's observation is therefore not established.

The existing anchor result is roughly compatible with that approximate
report. This is **not** a new calibration, a scored pass, proof of simultaneous
accuracy, or validation of automatic tracking. Original failed D01 predictions
remain failed. Full D2 acceptance and physical repair remain pending.

The continuation-session user confirmed that the previous session was stopped
and USB/wiring were unchanged. This is an operator status report, not a new
device PING. No hardware command or API call was made by this offline audit.

Resume order: confirm boot/held state; finish the remaining tracking check or
retain explicit manual REF checks for a separately logged repair; freeze the
repair prediction before removing the added capacitor; verify repair without
refitting; restore B1 and perform the B1/B6 shunt comparison. The extra capacitor
and output load are still installed according to the last confirmed setup.
''')
print(json.dumps({'staged': str(STAGE), 'archived_files': len(manifest), 'frames_validated': report['frames'], 'anchored_difference_mV_range': report['existing_local_anchor_difference_mV_range'], 'hardware_IO': False}, ensure_ascii=False))
