"""Fixed input-linked REF reproducibility model, not physical REF calibration.

Only A1, A3 and A4 enter the coefficient fit. Origins come from three raw HOLDs.
One shared, immutable k is used for both REF channels and every waveform.
"""
from copy import deepcopy
import hashlib
import json

import numpy as np

POLICY = {
    'version': 'fixed-k-ref-repro-v1',
    'name': 'Reproducibility check allowing fixed input-linked variation',
    'shared_k_for_A3_A4': True, 'fit_intercept': False,
    'hard_abs_k_max': .03, 'limit_v': .003,
    'origin': 'first three raw HOLD blocks, frozen per boot/fixture',
    'IN_alignment': 'same frame A1; completion offsets retained; no time/phase fit',
    'wave_checks': ['RMS', 'every_fixed_region_mean', 'all_block_mean_span'],
    'step_region_edges_ms': [0, 5, 20, 80],
    'sine_regions': 'four contiguous quarters',
    'raw_HOLD_and_electrical_guards_unchanged': True,
    'raw_A3_REF_envelope_added': True,
    'diagnostic_IN_OUT_corrected': False,
    'physical_REF_stability_established': False,
    'retrospective_reclassification': False,
}


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def origin(blocks):
    if len(blocks) != 3 or any(b['settings']['kind'] != 'hold' for b in blocks):
        raise ValueError('Exactly three raw origin HOLDs required')
    means = np.asarray([np.asarray(b['rows'])[:, 2:6].mean(axis=0) for b in blocks])
    return {'counts': means.mean(axis=0).tolist(), 'HOLD_frames': sum(len(b['rows']) for b in blocks),
            'OUT_used_for_fit': False, 'intercept_fitted': False}


def trace(block, origins, vref_v):
    a = np.asarray(block['rows'], dtype=float)
    if a.ndim != 2 or a.shape[1] != 10 or len(a) < 16:
        raise ValueError('Expected complete raw ten-column frames')
    scale = vref_v / 16383
    # No OUT values are used here, including its origin.
    x = (a[:, 2] - origins['counts'][0]) * scale
    y = (a[:, [4, 5]] - np.asarray(origins['counts'])[[2, 3]]) * scale
    return x, y


def regions(block):
    n = len(block['rows']); s = block['settings']
    if s['kind'] == 'hold': return [('whole', np.arange(n))]
    if s['kind'] == 'sine':
        return [(f'quarter{i+1}', x) for i, x in enumerate(np.array_split(np.arange(n), 4))]
    t = np.asarray(block['rows'])[:, 0] * .001
    edge = t[n // 10]; elapsed = t - edge
    spans = [('before_step', elapsed < 0), ('0_to_5ms', (elapsed >= 0) & (elapsed < 5)),
             ('5_to_20ms', (elapsed >= 5) & (elapsed < 20)),
             ('20_to_80ms', (elapsed >= 20) & (elapsed < 80)), ('after_80ms', elapsed >= 80)]
    return [(name, np.flatnonzero(mask)) for name, mask in spans if mask.any()]


def evaluate(blocks, origins, vref_v, k):
    if not np.isfinite(k) or abs(k) > POLICY['hard_abs_k_max']:
        raise ValueError('Fixed k exceeds the prospectively declared bound')
    rows = []; means = []
    for b in blocks:
        x, y = trace(b, origins, vref_v); residual = y - k * x[:, None]
        mean = residual.mean(axis=0); means.append(mean)
        rms = np.sqrt((residual**2).mean(axis=0))
        reg = [{'name': name, 'means_mV': (residual[ix].mean(axis=0)*1000).tolist()}
               for name, ix in regions(b)]
        passed = bool((rms <= POLICY['limit_v'] + 1e-12).all()
                      and all(max(abs(v) for v in r['means_mV']) <= 3. + 1e-9 for r in reg))
        rows.append({'label': b['label'], 'RMS_mV': (rms*1000).tolist(), 'regions': reg,
                     'mean_mV': (mean*1000).tolist(), 'passed': passed})
    spans = np.ptp(np.asarray(means), axis=0) * 1000 if means else np.zeros(2)
    return {'passed': bool(rows and all(r['passed'] for r in rows) and (spans <= 3. + 1e-9).all()),
            'blocks': rows, 'residual_block_mean_span_mV': spans.tolist(),
            'k_was_refitted': False, 'physical_REF_stability_established': False}


def _linear_interval(a, b, limit):
    # |a - k*b| <= limit
    if abs(b) < 1e-15:
        return (-np.inf, np.inf) if abs(a) <= limit + 1e-12 else (1., -1.)
    return tuple(sorted(((a-limit)/b, (a+limit)/b)))


def fit(blocks, origins, vref_v):
    """Intersect every training constraint; never fit validation data or OUT."""
    lo, hi = -POLICY['hard_abs_k_max'], POLICY['hard_abs_k_max']
    constraints = []; descriptive = []; xy = xx = 0.; means = []
    def intersect(bounds, label):
        nonlocal lo, hi
        lo, hi = max(lo, float(bounds[0])), min(hi, float(bounds[1]))
        constraints.append({'label': label, 'interval': [lo, hi], 'compatible': lo <= hi})
    for b in blocks:
        x, y = trace(b, origins, vref_v); a = float(np.mean(x*x))
        means.append((x.mean(), y.mean(axis=0)))
        if b['settings']['kind'] != 'hold':
            xy += float(np.mean(x[:, None]*y)); xx += a
            slopes = (np.mean(x[:, None]*y, axis=0)/a).tolist() if a > 1e-12 else [None, None]
            descriptive.append({'label': b['label'], 'kind': b['settings']['kind'],
                                'frequency_hz': b['settings'].get('frequency_hz'),
                                'fixed_origin_descriptive_k_A3_A4': slopes,
                                'used_as_per_capture_correction': False})
        for ch in range(2):
            c = float(np.mean(y[:, ch]**2)) - POLICY['limit_v']**2
            bb = float(np.mean(x*y[:, ch]))
            if a < 1e-15:
                interval = (-np.inf, np.inf) if c <= 0 else (1., -1.)
            else:
                d = bb*bb - a*c
                interval = ((bb-np.sqrt(max(0., d)))/a, (bb+np.sqrt(max(0., d)))/a) if d >= -1e-18 else (1., -1.)
            intersect(interval, b['label']+f':A{ch+3}:RMS')
            for name, ix in regions(b):
                intersect(_linear_interval(float(y[ix, ch].mean()), float(x[ix].mean()), POLICY['limit_v']),
                          b['label']+f':A{ch+3}:'+name)
    for i, (xm, ym) in enumerate(means):
        for j, (xn, yn) in enumerate(means[:i]):
            for ch in range(2):
                intersect(_linear_interval(float(ym[ch]-yn[ch]), float(xm-xn), POLICY['limit_v']),
                          f'block_mean_span:{i}:{j}:A{ch+3}')
    if lo > hi or xx <= 1e-12:
        return {'passed': False, 'reason': 'No common fixed k satisfies every training constraint',
                'intersection': [lo, hi], 'constraints': constraints, 'descriptive_k': descriptive,
                'fit_OUT_used': False, 'automatic_retry': False}
    ols = xy/xx
    k = ols if lo < ols < hi else (lo+hi)/2
    check = evaluate(blocks, origins, vref_v, k)
    if not check['passed']: raise ValueError('Numerically inconsistent fixed-k training fit')
    candidate = {'schema': 'benchmate.fixed-k-ref-model.v1', 'policy': deepcopy(POLICY), 'fixed_k': k,
                 'feasible_training_interval': [lo, hi], 'selection': 'equal-waveform shared no-intercept LS, otherwise interval midpoint',
                 'training_sha256': digest(blocks), 'training_origin': deepcopy(origins),
                 'descriptive_k': descriptive, 'training_check': check,
                 'fit_OUT_used': False, 'physical_REF_stability_established': False,
                 'qualified_fixtures': [], 'runtime_use_allowed': False}
    return {'passed': True, 'candidate': candidate}


def raw_checks(rows, settings, config, limits, hold_means):
    a = np.asarray(rows); v = a[:, 2:6] * config.vref_v / 16383; means = v.mean(axis=0)
    checks = {'rails': bool(((a[:, 2:6] > 16) & (a[:, 2:6] < 16367)).all()),
              'A4_envelope': bool((abs(v[:, 3]-config.ref_v) <= limits['A4_envelope_v']).all()),
              'A3_REF_envelope': bool((abs(v[:, 2]-config.ref_v) <= limits['A4_envelope_v']).all())}
    if settings['kind'] == 'hold':
        stationary = np.asarray(hold_means + [means.tolist()])
        checks.update(stationary_path_mean_span=bool((np.ptp(stationary, axis=0) <= .003).all()),
            path_means=bool((abs(means-config.ref_v) <= limits['REF_mean_delta_v_max']).all()),
            path_samples=bool((abs(v-config.ref_v) <= limits['REF_any_sample_delta_v_max']).all()),
            path_spread=float(np.ptp(means)) <= limits['REF_channel_mean_spread_v_max'])
    else:
        checks['signal_envelope'] = bool((abs(v[:, :3]-config.ref_v) <= limits['signal_envelope_v']).all())
    return checks, means.tolist()


def fault_checks(blocks, origins, config, limits, k):
    """Software-only injections into copies, never physical fault insertion."""
    source = next(b for b in blocks if b['settings']['kind'] == 'step' and b['settings']['amplitude_v'] == .5)
    real = deepcopy(source); a = np.asarray(real['rows'], dtype=float)
    x, _ = trace(real, origins, config.vref_v)
    a[:, 4:6] += (.008*x[:, None]) * 16383/config.vref_v
    real['rows'] = a.tolist(); real['label'] = 'injected_real_input_linked_REF_8mV_pp'
    # Compare original and injected blocks in one fixed-origin context.
    linked = not evaluate([source, real], origins, config.vref_v, k)['passed']
    hold = deepcopy(next(b for b in blocks if b['settings']['kind'] == 'hold'))
    low = np.asarray(hold['rows'], dtype=float); low[:, 5] = .87*16383/config.vref_v
    raw, _ = raw_checks(low, hold['settings'], config, limits, [])
    dropout = not all(raw.values())
    drift = np.asarray(hold['rows'], dtype=float); drift[:, 4:6] += .004*16383/config.vref_v
    old_holds = [np.asarray(b['rows'])[:, 2:6].mean(axis=0).tolist() for b in blocks[:3]]
    old_holds = (np.asarray(old_holds)*config.vref_v/16383).tolist()
    raw, _ = raw_checks(drift, hold['settings'], config, limits, old_holds)
    drift_caught = not raw['stationary_path_mean_span']
    return {'software_only': True, 'physical_faults_inserted': False,
            'REF_0_87V_caught': dropout, 'raw_HOLD_4mV_drift_caught': drift_caught,
            'additional_real_input_linked_8mV_pp_caught_without_refit': linked,
            'passed': bool(dropout and drift_caught and linked)}
