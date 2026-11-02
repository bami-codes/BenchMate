#!/usr/bin/env python3
"""Read retained logs only. Never imports serial, providers or a live runner.

Descriptive post-hoc instrument analysis; it cannot accept a rejected capture,
refit a DUT model or change any runtime guard. No network/hardware capability.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys

import numpy as np
from scipy.signal import savgol_filter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from benchmate.records import read_events

RUNS = [
    ('pilot_1_A3_DRIVE', 'examples/passive-pilot/2026-11-03/design-01-fault/20261102T160841-eff2b65334', False),
    ('pilot_2_A3_REF', 'examples/passive-pilot/2026-11-03/design-01-fault/20261102T164944-16f6a79a31', True),
]
CONTEXT = [
    'examples/passive-pilot/2026-11-03/design-01-fault/20261102T154657-b43e7683e7',
    'examples/passive-reference-QA/2026-11-03/20261102T163017-f02faa7857',
    'examples/passive-reference-QA/2026-11-03/20261102T164218-ee4dbda508',
]


def wrap(degrees):
    return float((degrees+180) % 360-180)


def fit_columns(y, columns):
    x = np.column_stack([np.ones(len(y)), *columns])
    b, _, rank, _ = np.linalg.lstsq(x, y, rcond=None)
    prediction = x@b
    ss = float(np.sum((y-y.mean())**2))
    return {'coefficients': b.tolist(), 'rank': int(rank),
            'R2_descriptive': None if ss < 1e-20 else 1-float(np.sum((y-prediction)**2))/ss,
            'RMSE_mV': float(np.sqrt(np.mean((y-prediction)**2)))}, prediction


def harmonic(t, y, frequency):
    w = 2*np.pi*frequency
    fit, prediction = fit_columns(y, [t-t.mean(), np.sin(w*t), np.cos(w*t)])
    b = fit['coefficients']
    return {**fit, 'amplitude_mV': float(np.hypot(b[2], b[3])),
            'phase_deg': float(np.degrees(np.arctan2(b[3], b[2]))),
            'linear_trend_mV_per_s': b[1]}, prediction


def self_checks():
    t = np.linspace(0, 2.048, 512)
    known = 7.2*np.sin(2*np.pi*t+.3)+.4*(t-t.mean())+5
    result, prediction = harmonic(t, known, 1.)
    assert abs(result['amplitude_mV']-7.2) < 1e-9
    assert abs(result['phase_deg']-np.degrees(.3)) < 1e-9
    assert np.max(abs(prediction-known)) < 1e-9
    assert wrap(359.) == -1.
    return {'known_sine_amplitude_phase_and_trend_recovered': True,
            'wrapped_phase_convention_checked': True}


def analyze_run(label, relative, a3_ref):
    p = ROOT/relative
    events = read_events(p)
    protocol = json.loads((p/'protocol.json').read_text())
    scale = protocol['configuration']['vref_v']/16383
    origins = []; plan = None; waves = []; holds = []; traces = {}
    for e in events:
        q, kind = e['payload'], e['kind']
        if kind == 'netlist_physical_acquisition_plan':
            origins = []; plan = q
        if not isinstance(q, dict) or q.get('type') != 'capture':
            continue
        rows = np.asarray(q['rows'], float)
        if rows.shape != (512, 10) or not np.isfinite(rows).all():
            raise ValueError('Unexpected raw frame layout')
        volts = rows[:, 2:6]*scale
        t = rows[:, 0]*1e-6
        sample_t = t[:, None]+rows[:, 6:10]*1e-6
        base = {'run': label, 'raw_label': kind, 'kind': q['kind'], 'boot_id': q['boot_id'],
                'nominal_conversion_vref_v': protocol['configuration']['vref_v'],
                'channel_roles': {'A1': 'IN', 'A2': 'OUT', 'A3': 'REF' if a3_ref else 'pre-shunt DRIVE', 'A4': 'REF'},
                'sample_delay_median_us': np.median(rows[:, 6:10], axis=0).tolist(),
                'sample_state_before': q['adc_sample_states_readback_before'],
                'sample_state_after': q['adc_sample_states_readback_after'],
                'timing_valid': q['timing_valid'], 'overruns': q['overruns']}
        if q['kind'] == 'HOLD':
            holds.append({**base, 'means_nominal_v': volts.mean(axis=0).tolist()})
            if '_origin_' in kind: origins.append(volts.mean(axis=0))
            continue
        if len(origins) != 3:
            raise ValueError('Three independent center HOLD blocks required')
        center = np.mean(origins, axis=0)
        trace = {'volts': volts, 'rows': rows, 't': t, 'sample_t': sample_t,
                 'center': center, 'a3_ref': a3_ref, 'packet': q}
        traces[kind] = trace
        base.update(load_ohm=plan['settings']['load_ohm'],
                    command_peak_amplitude_v=q['amplitude_or_hold_code']*protocol['configuration']['vref_v']/4095,
                    center_HOLD_means_nominal_v=center.tolist())
        refs = [2, 3] if a3_ref else [3]
        if q['kind'] == 'STEP':
            n = q['step_index']; edge = t[n]
            pre = volts[5:n-5].mean(axis=0); post = volts[-100:].mean(axis=0)
            base.update(step_index=n, pre_window_indices=[5, n-5], post_window_indices=[len(t)-100, len(t)],
                        step_delta_nominal_v=(post-pre).tolist(), reference={})
            for c in refs:
                tr = sample_t[:, c]; mask = abs(tr-edge) > .001
                y = (volts[:, c]-center[c])*1000
                time = tr[mask]-tr[mask].mean()
                fits = {}
                for j, predictor in [(0, 'measured_IN_A1'), (1, 'measured_OUT_A2'), (c-1, 'preceding_ADC_channel')]:
                    xp = np.interp(tr, sample_t[:, j], volts[:, j])
                    fits[predictor], _ = fit_columns(y[mask], [time, xp[mask]-xp[mask].mean()])
                fits['time_only'], _ = fit_columns(y[mask], [time])
                base['reference']['A'+str(c+1)] = {
                    'pre_minus_center_mV': float((pre[c]-center[c])*1000),
                    'post_tail_minus_center_mV': float((post[c]-center[c])*1000),
                    'pre_to_post_tail_mV': float((post[c]-pre[c])*1000),
                    'block_mean_minus_center_mV': float((volts[:, c].mean()-center[c])*1000),
                    'apparent_mV_per_V_IN_step': float(1000*(post[c]-pre[c])/(post[0]-pre[0])),
                    'linear_basis_fits_with_time_trend': fits,
                    'fit_edge_exclusion_ms': 1.}
            if a3_ref:
                common = (volts[:, 2]+volts[:, 3])/2
                difference = volts[:, 3]-volts[:, 2]
                base['paired_REF'] = {'rowwise_correlation': float(np.corrcoef(volts[:, 2], volts[:, 3])[0, 1]),
                    'common_std_mV': float(np.std(common)*1000), 'difference_std_mV': float(np.std(difference)*1000),
                    'difference_step_delta_mV': float(((post[3]-pre[3])-(post[2]-pre[2]))*1000)}
        elif q['kind'] == 'SINE':
            frequency = q['frequency_millihz']/1000
            base.update(frequency_hz=frequency, harmonic={})
            for c in range(4):
                result, _ = harmonic(sample_t[:, c], (volts[:, c]-center[c])*1000, frequency)
                base['harmonic']['A'+str(c+1)] = result
            for c in refs:
                h = base['harmonic']['A'+str(c+1)]
                h.update(phase_minus_IN_deg=wrap(h['phase_deg']-base['harmonic']['A1']['phase_deg']),
                         phase_minus_OUT_deg=wrap(h['phase_deg']-base['harmonic']['A2']['phase_deg']),
                         phase_minus_A3_deg=wrap(h['phase_deg']-base['harmonic']['A3']['phase_deg']))
        waves.append(base)
    result = json.loads((p/'result.json').read_text())
    hypotheses = [e['payload'] for e in events if e['kind'] == 'component_hypotheses_fitted']
    return {'label': label, 'path': relative, 'pilot': True, 'excluded_from_evaluation': True,
            'terminal_event': events[-1]['kind'], 'stop_reason': result.get('error'),
            'completed_diagnosis_report': False, 'Spark_requests': result['http_requests'],
            'last_adequate_families': [r['id'] for r in hypotheses[-1]['hypotheses'] if r['status'] == 'adequate'],
            'last_effective_R1_ohm': next(r['fitted_parameters']['R1'] for r in hypotheses[-1]['hypotheses'] if r['id'] == 'changed:R1'),
            'waves': waves, 'holds': holds}, traces


def plots(out, all_traces):
    os.environ.setdefault('MPLCONFIGDIR', '/tmp/benchmate-ref-matplotlib')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'font.size': 10, 'axes.spines.top': False, 'axes.spines.right': False})
    tr = all_traces['pilot_2_A3_REF']['training_2_raw_capture']
    v, center, t = tr['volts'], tr['center'], tr['sample_t']
    edge = tr['t'][tr['packet']['step_index']]
    fig, ax = plt.subplots(3, 1, figsize=(10, 9), sharex=True, constrained_layout=True)
    for c, name in [(0, 'A1 measured IN'), (1, 'A2 measured OUT')]:
        ax[0].plot((t[:, c]-edge)*1000, v[:, c]-center[c], label=name)
    ax[0].set(ylabel='Change from center HOLD (V)', title='Pilot 2: rejected large-step capture — not an accepted diagnosis')
    ax[0].legend(loc='lower right')
    for c, color, name in [(2, '#c25216', 'A3 REF via A23'), (3, '#2862af', 'A4 REF via bridge / I50')]:
        x = (t[:, c]-edge)*1000; y = (v[:, c]-center[c])*1000
        ax[1].plot(x, y, color=color, alpha=.25, linewidth=.6)
        ax[1].plot(x, savgol_filter(y, 9, 2), color=color, label=name+' (9-frame display smoothing)')
    ax[1].axhline(0, color='gray', linewidth=.6)
    ax[1].set(ylabel='Reference change (mV)'); ax[1].legend(loc='lower right')
    n = tr['packet']['step_index']; pre = v[5:n-5].mean(axis=0); post = v[-100:].mean(axis=0)
    for c, name in [(0, 'IN shape'), (1, 'OUT RC shape')]:
        ax[2].plot((t[:, c]-edge)*1000, (v[:, c]-pre[c])/(post[c]-pre[c]), label=name)
    common = (v[:, 2]+v[:, 3])/2
    lo, hi = common[5:n-5].mean(), common[-100:].mean()
    ax[2].plot((tr['t']-edge)*1000, savgol_filter((common-lo)/(hi-lo), 9, 2), color='black', label='Mean REF shape (normalized)')
    ax[2].set(ylabel='Normalized pre / post levels', xlabel='Time from commanded step (ms)', xlim=(-25, 150)); ax[2].legend(loc='lower right')
    for a in ax: a.axvline(0, color='gray', linestyle=':', linewidth=.8); a.grid(alpha=.15)
    fig.savefig(out/'large-step-reference.png', dpi=170); plt.close(fig)

    tr = all_traces['pilot_1_A3_DRIVE']['training_3_raw_capture']
    v, center, t = tr['volts'], tr['center'], tr['sample_t']
    fig, ax = plt.subplots(2, 1, figsize=(10, 6), sharex=True, constrained_layout=True)
    for c, name in [(0, 'A1 measured IN'), (1, 'A2 measured OUT')]: ax[0].plot(t[:, c], v[:, c]-center[c], label=name)
    ax[0].set(ylabel='Change from center HOLD (V)', title='Pilot 1: 1 Hz training sine — A4 ripple is not captured by a block-mean-only test'); ax[0].legend()
    y = (v[:, 3]-center[3])*1000
    fit, pred = harmonic(t[:, 3], y, 1.)
    ax[1].plot(t[:, 3], y, color='#2862af', alpha=.35, linewidth=.7, label='A4 raw REF change')
    ax[1].plot(t[:, 3], pred, color='#2862af', label='1 Hz + linear trend fit')
    inp, _ = harmonic(t[:, 0], (v[:, 0]-center[0])*1000, 1.)
    phase = np.radians(inp['phase_deg'])
    ax[1].plot(t[:, 3], fit['amplitude_mV']*np.sin(2*np.pi*t[:, 3]+phase)+fit['coefficients'][0]+fit['linear_trend_mV_per_s']*(t[:, 3]-t[:, 3].mean()), color='black', linestyle='--', label='IN phase at the same plotted amplitude')
    ax[1].set(ylabel='Reference change (mV)', xlabel='Time (s)'); ax[1].legend(loc='lower right')
    for a in ax: a.grid(alpha=.15)
    fig.savefig(out/'sine-reference.png', dpi=170); plt.close(fig)


def main():
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('--output', required=True)
    args = p.parse_args(); out = Path(args.output); out.mkdir(parents=True, exist_ok=False)
    checks = self_checks(); results = []; traces = {}; sources = {}
    for label, relative, a3_ref in RUNS:
        result, tr = analyze_run(label, relative, a3_ref); results.append(result); traces[label] = tr
    for relative in [r[1] for r in RUNS]+CONTEXT:
        raw = ROOT/relative
        read_events(raw)
        for name in ('events.jsonl', 'result.json', 'protocol.json'):
            f = raw/name
            sources[str(f.relative_to(ROOT))] = hashlib.sha256(f.read_bytes()).hexdigest()
    own = Path(__file__).resolve(); sources[str(own.relative_to(ROOT))] = hashlib.sha256(own.read_bytes()).hexdigest()
    analysis = {'scope': 'Post-hoc descriptive instrument analysis of retained logs only.',
        'paid_requests': 0, 'hardware_commands': 0, 'runtime_or_guard_changes': False,
        'self_checks': checks, 'no_failed_capture_reclassified_as_passed': True,
        'linear_fit_R2_is_not_causal_evidence_or_statistical_confidence': True,
        'nominal_ADC_volts_are_not_independent_DMM_readings': True,
        'source_sha256': sources, 'diagnostic_pilots': results}
    (out/'metrics.json').write_text(json.dumps(analysis, indent=2, allow_nan=False)+'\n')
    plots(out, traces)
    print(json.dumps({'output': str(out), 'pilots': len(results), 'waveforms': sum(len(r['waves']) for r in results),
                      'paid_requests': 0, 'hardware_commands': 0, 'self_checks': checks}))


if __name__ == '__main__': main()
