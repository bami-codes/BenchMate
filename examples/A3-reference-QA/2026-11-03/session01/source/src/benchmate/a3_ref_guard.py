"""Prospective A3 primary REF guard; retain every A4 observation as auxiliary.

No regression, offset fit, sample removal or threshold relaxation. The original
PhysicalBench and firmware stay unchanged. This mixin replaces only the guard
implementation in a new explicitly versioned adapter.
"""
import numpy as np

from .instrument import capture_command, validate_block

VERSION = 'primary-REF-A3-v1'


def assess(counts, history, config, limits, *, hold):
    counts = np.asarray(counts)
    if counts.ndim != 2 or counts.shape[1] != 4 or not len(counts):
        raise ValueError('Four raw ADC channels required for A3 guard.')
    nominal = counts * config.vref_v / 16383
    means = nominal.mean(axis=0)
    reference = np.asarray([r['means'] for r in history])
    envelope = limits.get('REF_envelope_v', limits['A4_envelope_v'])
    checks = {
        'rails_A1_A2_A3': bool(((counts[:, :3] > 16) & (counts[:, :3] < 16367)).all()),
        'REF_A3_envelope': bool((abs(nominal[:, 2] - config.ref_v) <= envelope).all()),
        'REF_A3_block_mean_span': bool(float(np.ptp(reference[:, 2])) <= .003),
    }
    if hold:
        stationary = np.asarray([r['means'] for r in history if r['hold']])
        checks.update(
            stationary_path_mean_span_A1_A2_A3=bool((np.ptp(stationary[:, :3], axis=0) <= .003).all()),
            path_means_A1_A2_A3=bool((abs(means[:3] - config.ref_v) <= limits['REF_mean_delta_v_max']).all()),
            path_samples_A1_A2_A3=bool((abs(nominal[:, :3] - config.ref_v) <= limits['REF_any_sample_delta_v_max']).all()),
            path_spread_A1_A2_A3=bool(float(np.ptp(means[:3])) <= limits['REF_channel_mean_spread_v_max']))
    else:
        checks['signal_envelope_A1_A2_A3'] = bool((abs(nominal[:, :3] - config.ref_v) <= limits['signal_envelope_v']).all())
    auxiliary = {
        'channel': 'A4', 'role': 'record_and_report_only',
        'rails_ok': bool(((counts[:, 3] > 16) & (counts[:, 3] < 16367)).all()),
        'REF_envelope_ok': bool((abs(nominal[:, 3] - config.ref_v) <= limits['A4_envelope_v']).all()),
        'block_mean_span_mV': float(np.ptp(reference[:, 3])) * 1000,
        'block_mean_span_3mV_ok': bool(float(np.ptp(reference[:, 3])) <= .003),
        'A4_minus_A3_block_mean_mV': float(means[3] - means[2]) * 1000,
    }
    return checks, auxiliary


class A3GuardMixin:
    def _capture(self, board, continuity, label, settings):
        # Preserve the original byte protocol, park check, sample validation,
        # channel readbacks and post-capture PING before evaluating new guards.
        command = capture_command(self.config, boot_id=continuity.boot_id, **settings)
        self.capture_attempts += 1
        block = self._request(board, continuity, command, label + '_raw_capture', 30)
        validate_block(block, expected_command=command)
        if block.get('parked_ref_code') != self.config.ref_code:
            raise ValueError('REF park not reported.')
        self.frames += len(block['rows'])
        self._ping(board, continuity, label + '_postcheck', True)
        rows = np.asarray(block['rows'])
        nominal = rows[:, 2:6] * self.config.vref_v / 16383
        hold = settings['kind'] == 'hold'
        self.reference_means.append({'label': label, 'hold': hold, 'means': nominal.mean(axis=0).tolist()})
        checks, auxiliary = assess(rows[:, 2:6], self.reference_means, self.config,
                                    self.p['guard_limits'], hold=hold)
        self.log.add('physical_electrical_guard', {'guard_version': VERSION,
            'primary_REF_channel': 'A3', 'trusted_channels': ['A1', 'A2', 'A3'],
            'label': label, 'checks': checks, 'means_v': nominal.mean(axis=0).tolist(),
            'A4_auxiliary': auxiliary})
        if not all(checks.values()):
            raise ValueError('Primary A3 electrical/reference guard failed; no next stimulus.')
        return rows
