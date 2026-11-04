"""Frame-anchored measured-IN prediction on recorded channel completion times.

No OUT, fitted delay, gain or offset enters this module. Command templates keep
their original DAC zero-order hold semantics; measured templates use one fixed
piecewise-linear reconstruction, with endpoint holds. Completion times remain
proxies for aperture times, not a calibration claim.
"""
import hashlib
import math
from pathlib import Path
import shutil
import subprocess
import tempfile

import numpy as np

from .physical_netlist import validate_input_template
from .netlist import (render_proposal, diode_parameters, render_diode,
                      ngspice_version, SETTLING_TOLERANCE_V,
                      MAX_WARMUP_SECONDS, MAX_STIMULUS_POINTS)
from .netlist_diagnosis.design import elements as check_elements, digest
from .netlist_diagnosis.simulation import conditional_elements, simulate as old_simulate

VERSION = 'frame-anchored-channel-timing-v4'
MEASURED = {'physical_input_only', 'adc_input_only', 'mock_adc_input_only'}


def stimulus(template, cycles=0):
    """Hold to recorded DAC-write frames; interpolate only after those frames."""
    s, t, u, di, do, cycle = validate_input_template(template)
    if template['source'] not in MEASURED:
        raise ValueError('Measured channel timestamps required.')
    if type(cycles) is not int or cycles < 0 or (cycles and cycle is None):
        raise ValueError('Nonnegative whole sine history cycles required.')
    warmup = cycles*t[cycle] if cycles else 0.
    if warmup > MAX_WARMUP_SECONDS or cycles*(cycle or 0)+len(t) > MAX_STIMULUS_POINTS:
        raise ValueError('Measured-cycle settling exceeds bounded simulator horizon')
    if np.any(di <= 0):
        raise ValueError('Positive measured A1 completion delays required for frame-anchored ramps.')
    if cycles:
        frames = np.r_[np.concatenate([t[:cycle]+j*t[cycle] for j in range(cycles)]), t+warmup]
        values = np.r_[np.tile(u[:cycle], cycles), u]
        delays = np.r_[np.tile(di[:cycle], cycles), di]
    else:
        frames, values, delays = t.copy(), u.copy(), di.copy()
    actual = frames+delays
    if np.any(np.diff(actual) <= 0):
        raise ValueError('IN channel completion times must strictly increase.')
    knots = [(0., float(values[0]))]
    for i in range(len(frames)):
        # Firmware writes a sine DAC code at every frame. For a step, its
        # level changes only at the declared step index. A1 is read afterward.
        transition = i > 0 and (s['kind'] == 'sine' or i == s['step_index'])
        if transition:
            knots.append((float(frames[i]), float(values[i-1])))
        knots.append((float(actual[i]), float(values[i])))
    times, values = np.asarray(knots, float).T
    if np.any(np.diff(times) <= 0):
        raise ValueError('Frame-anchored IN timing is not monotone.')
    sample_times = t+warmup+do
    stop = float(sample_times[-1]+1e-7)
    if stop > times[-1]:
        times, values = np.r_[times, stop], np.r_[values, values[-1]]
    return s, t, u, di, do, cycle, times, values, sample_times, stop


def simulate(elements, template, *, diode=None, before_run=None):
    """Same bounded R/C/D/W topology, fixed timing rule for every passive design."""
    checked = check_elements(elements)
    if template.get('source') == 'command_input_only':
        # DAC writes really are frame-held commands. Do not smooth predictions
        # published before measurements or invent future ADC channel timing.
        return {**old_simulate(checked, template, diode=diode, before_run=before_run),
                'timing_model_version': VERSION, 'timing_source': 'preserved_DAC_command_hold'}
    kept, removed = conditional_elements(checked)
    wired = any(e['kind'] == 'W' for e in kept)
    executable = shutil.which('ngspice')
    if not executable:
        raise RuntimeError('ngspice is required.')
    version = ngspice_version(executable)
    dp = diode_parameters(diode)
    invocations = []
    internal = sorted({e[k].lower() for e in kept for k in ('a', 'b') if e[k] in ('N1', 'N2')})
    vectors = ['v(in)', 'v(out)', *['v('+n+')' for n in internal], 'i(Vdrive)']

    def run(cycles):
        s, t, u, di, do, cycle, times, values, samples, stop = stimulus(template, cycles)
        lines = ['BenchMate frame-anchored channel times v4', 'Vdrive in 0 PWL(']
        lines.extend(f'+ {a:.12g} {b:.12g}' for a, b in zip(times, values, strict=True))
        lines.append('+ )')
        if wired:
            lines.append('Vwire out in 0')
        else:
            if s['load_ohm'] is not None:
                lines.append(f'RfixtureLoad out 0 {s["load_ohm"]:.12g}')
            lines.extend([render_proposal(kept), render_diode(dp)])
        lines.extend(['.temp 27', '.options reltol=1e-7 abstol=1e-14 vntol=1e-8 minbreak=1e-12'])
        dt = float(np.min(np.diff(t))) / 4
        lines.extend([f'.tran {dt:.12g} {stop:.12g} 0 {dt:.12g}', '.control',
                      'set wr_singlescale', 'set numdgt=15', 'run',
                      'wrdata output.dat '+' '.join(vectors), 'quit', '.endc', '.end'])
        netlist = '\n'.join(lines) + '\n'
        if before_run:
            before_run()
        with tempfile.TemporaryDirectory(prefix='benchmate-channel-v4-') as directory:
            path = Path(directory)
            (path/'circuit.cir').write_text(netlist)
            proc = subprocess.run([executable, '-b', 'circuit.cir'], cwd=path,
                                  capture_output=True, text=True, timeout=15)
            if proc.returncode or not (path/'output.dat').exists():
                raise ValueError('ngspice rejected the channel-timing circuit')
            raw = np.loadtxt(path/'output.dat')
        if raw.ndim != 2 or raw.shape[1] != len(vectors)+1 or not np.isfinite(raw).all():
            raise ValueError('Invalid channel-timing simulator output')
        peak = float(np.max(np.abs(raw[:, -1])))
        if peak > .01 or np.max(np.abs(raw[:, 1:-1])) > 1.05:
            raise ValueError('Proposed circuit exceeds development current/voltage limits')
        if raw[0, 0] > 1e-12 or raw[-1, 0] < stop-1e-9:
            raise ValueError('Incomplete simulator time span')
        sampled = np.column_stack([np.interp(samples, raw[:, 0], raw[:, i]) for i in range(1, len(vectors))])
        invocations.append({'warmup_cycles': cycles, 'source_knots': len(times),
                            'peak_source_current_a': peak,
                            'harness_sha256': hashlib.sha256(netlist.encode()).hexdigest()})
        return sampled

    s, t, u, di, do, cycle = validate_input_template(template)
    dynamic_sine = not wired and s['kind'] == 'sine' and any(e['kind'] == 'C' for e in kept)
    init = {'method': 'first_measured_IN_endpoint_hold', 'OUT_used': False}
    if dynamic_sine:
        rc = sum(e['value'] for e in kept if e['kind'] == 'R') * sum(e['value'] for e in kept if e['kind'] == 'C')
        cycles = max(1, math.ceil(10*rc/t[cycle]))
        previous = run(cycles)
        while True:
            cycles *= 2
            sampled = run(cycles)
            difference = float(np.max(np.abs(sampled-previous)))
            if difference <= SETTLING_TOLERANCE_V:
                break
            previous = sampled
        init = {'method': 'repeated_first_measured_input_cycle', 'warmup_cycles': cycles,
                'max_node_difference_v': difference, 'numerical_convergence': True,
                'physical_history_measured': False, 'OUT_used': False}
    else:
        sampled = run(0)
    return {'predicted_output_minus_ref_v': sampled[:, 1].tolist(),
            'predicted_input_minus_ref_v': sampled[:, 0].tolist(),
            'timing_model_version': VERSION, 'timing_source': 'recorded_channel_completion_times',
            'input_interpolation': 'hold_to_DAC_frame_then_linear_to_A1_and_between_no_change_frames',
            'output_sampling': 'frame_plus_A2_delay', 'fitted_timing_parameters': [],
            'initialization': init, 'simulator_invocations': invocations,
            'simulator': 'ngspice', 'simulator_version': version,
            'declared_topology_sha256': digest(checked),
            'unobservable_input_branches': [e['name'] for e in removed],
            'conditional_source_current_is_not_total_DUT_current': bool(removed),
            'scored_output_samples_used': 0, 'model_refitted': False,
            'scope': 'Fixed interpolation of measured IN; completion timestamps are not calibrated aperture times.'}


def predict(model, template, before_run=None):
    return simulate(model['elements'], template, diode=model.get('diode'),
                    before_run=before_run)['predicted_output_minus_ref_v']


from .netlist_diagnosis import models as preserved_models


class Fitter(preserved_models.Fitter):
    """Reuse all original component fitting; substitute only IN reconstruction."""
    def curve(self, model, template):
        key = digest([model, template])
        if key not in self.cache:
            self.cache[key] = predict(model, template, self.consume)
        return self.cache[key]


def assess(elements, captures, *, max_calls=1200, max_seconds=90.):
    if not captures:
        raise ValueError('Training data required.')
    for c in captures:
        preserved_models.validate_capture(c, role='training')
    fitter = Fitter(max_calls=max_calls, max_seconds=max_seconds)
    rows = []
    for identity, changed in [('nominal', None)] + [('changed:'+e['name'], e['name']) for e in elements if e['kind'] in ('R', 'C')]:
        try:
            row = fitter.fit(elements, captures, hypothesis_id=identity, changed=changed,
                             fit_names=[changed] if changed else [])
        except (ValueError, RuntimeError) as exc:
            row = {'id': identity, 'changed_component': changed, 'status': 'fit_error', 'error': str(exc)}
        rows.append(row)
    return {'hypotheses': rows, 'simulator_calls': fitter.calls,
            'all_inadequate': all(r['status'] == 'inadequate' for r in rows),
            'fitting_complete': not any(r['status'] == 'fit_error' for r in rows)}
