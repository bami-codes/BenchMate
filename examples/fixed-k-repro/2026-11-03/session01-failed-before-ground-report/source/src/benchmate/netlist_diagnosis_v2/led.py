"""A literal four-part LED circuit plus a declared external measurement harness.

The red-LED and BC547B parameters are development families, not characterized
parameters of the operator's parts. The measured output is the attenuated node,
never an unbuffered 5 V collector fed to the old measurement input.
"""
from copy import deepcopy
from pathlib import Path
import math
import shutil
import subprocess
import tempfile
import time

import numpy as np
from scipy.optimize import least_squares

from ..b5_models import rank_info
from ..netlist import ngspice_version
from ..physical_netlist import validate_input_template
from ..netlist_diagnosis.design import digest, CONFIRMATION
from ..netlist_diagnosis.models import validate_capture, score

THERMAL_V = 8.617333262145e-5 * 300.15
PARTS = [
    {'name': 'Rbase', 'kind': 'R', 'nodes': ['IN', 'BASE'], 'value': 4700., 'model': 'none'},
    {'name': 'Rled', 'kind': 'R', 'nodes': ['VCC', 'ANODE'], 'value': 1000., 'model': 'none'},
    {'name': 'D1', 'kind': 'D', 'nodes': ['ANODE', 'COL'], 'value': None, 'model': 'red_LED_uncharacterized'},
    {'name': 'Q1', 'kind': 'Q', 'nodes': ['COL', 'BASE', 'GND'], 'value': None, 'model': 'BC547B_uncharacterized'},
]
HARNESS = {'version': 'led-attenuated-collector-v1', 'supply_v': 5., 'reference_v': 1.646,
           'collector_to_OUT_ohm': 47000., 'OUT_to_REF_ohm': 10000.,
           'max_supply_current_a': .005, 'max_input_current_a': .003,
           'measured_output': 'OUT after the declared 47k/10k collector-to-REF divider',
           'output_basis': 'Calibrated A2 minus independently anchored physical REF; retain DC.',
           'required_connections': ['IN', 'OUT', 'REF', '5V', 'GND'],
           'old_firmware_range_expansion_required': False,
           'physical_calibration_and_wiring_approved': False}
ASSUMPTIONS = {'Q1_BF_healthy': [200., 450.], 'Q1_IS_a': 1e-14, 'Q1_BR': 3.,
               'LED_Vf_at_1mA_v': [1.7, 2.3], 'LED_N': 2., 'LED_RS_ohm': 2.,
               'temperature_c': 27., 'junction_capacitances_modelled': False,
               'bounds_are_device_characterization': False}


def review(*, source_sha256, confirmation, note, simulated=False, parts=None, harness=None):
    if confirmation != CONFIRMATION or not isinstance(note, str) or not note.strip():
        raise ValueError('Explicit intended design confirmation required.')
    if (not isinstance(source_sha256, str) or len(source_sha256) != 64
            or any(c not in '0123456789abcdef' for c in source_sha256)):
        raise ValueError('Source SHA-256 required.')
    candidate = deepcopy(PARTS if parts is None else parts)
    if candidate != PARTS:
        raise ValueError('This bounded active profile supports only the declared four-part BC547B/red-LED layout and values.')
    h = deepcopy(HARNESS if harness is None else harness)
    if h != HARNESS:
        raise ValueError('Use the declared attenuated-collector development harness; raw collector acquisition is unsupported.')
    return {'schema': 'benchmate.reviewed_active_netlist.v2', 'source_kind': 'intended_schematic',
            'elements': candidate, 'harness': h, 'device_assumptions': deepcopy(ASSUMPTIONS),
            'source_sha256': source_sha256, 'confirmation': confirmation, 'reviewer_note': note,
            'operator_review_simulated': bool(simulated), 'measurement_verified': False, 'hardware_IO': False}


def checked(value):
    if (not isinstance(value, dict) or value.get('schema') != 'benchmate.reviewed_active_netlist.v2'
            or value.get('source_kind') != 'intended_schematic'
            or value.get('device_assumptions') != ASSUMPTIONS
            or value.get('measurement_verified') is not False or value.get('hardware_IO') is not False
            or type(value.get('operator_review_simulated')) is not bool):
        raise ValueError('A reviewed active netlist and declared device/harness assumptions are required.')
    result = review(source_sha256=value['source_sha256'], confirmation=value['confirmation'],
                    note=value['reviewer_note'], simulated=value['operator_review_simulated'],
                    parts=value['elements'], harness=value['harness'])
    if set(result) != set(value):
        raise ValueError('Unexpected active-design fields.')
    return result


def model(*, rbase=4700., rled=1000., beta=300., vf=2.):
    values = [rbase, rled, beta, vf]
    bounds = [(1000., 2e6), (1000., 10000.), (.25, 800.), (1.2, 3.4)]
    if (any(type(v) not in (int, float) or not math.isfinite(v) for v in values)
            or any(not lo*(1-1e-12) <= v <= hi*(1+1e-12) for v, (lo, hi) in zip(values, bounds))):
        raise ValueError('Active model exceeds the bounded development parameters.')
    rbase, rled, beta, vf = [float(np.clip(v, lo, hi)) for v, (lo, hi) in zip(values, bounds)]
    return {'profile': 'BC547B_red_LED_v1', 'Rbase_ohm': float(rbase), 'Rled_ohm': float(rled),
            'Q1_BF': float(beta), 'LED_Vf_1mA_v': float(vf), 'harness': deepcopy(HARNESS)}


def simulate(value, input_template, before_run=None):
    if (not isinstance(value, dict) or set(value) != set(model())
            or value.get('profile') != 'BC547B_red_LED_v1' or value.get('harness') != HARNESS):
        raise ValueError('A bounded active model and exact measurement harness are required.')
    model(rbase=value['Rbase_ohm'], rled=value['Rled_ohm'], beta=value['Q1_BF'], vf=value['LED_Vf_1mA_v'])
    s, t, u, di, do, cycle = validate_input_template(input_template)
    executable = shutil.which('ngspice')
    if not executable:
        raise RuntimeError('ngspice is required.')
    version = ngspice_version(executable)
    h = HARNESS
    absolute_input = h['reference_v'] + u
    if np.min(absolute_input) < .5 or np.max(absolute_input) > 2.8:
        raise ValueError('Active input exceeds the retained low-voltage drive window.')
    # This declared low-frequency model has no energy-storage elements; the
    # initial DC operating point is the first measured input, with no warmup fit.
    edge = 1e-8
    points = [(0., float(absolute_input[0]))]
    for i in range(1, len(t)):
        points += [(float(t[i]-edge), float(absolute_input[i-1])), (float(t[i]), float(absolute_input[i]))]
    stop = float(t[-1]+do[-1]+1e-7)
    points.append((stop, float(absolute_input[-1])))
    led_is = .001 / np.expm1(value['LED_Vf_1mA_v']/(2*THERMAL_V))
    lines = ['BenchMate bounded BC547B and red LED with explicit measurement loading', 'Vdrive in 0 PWL(']
    lines += [f'+ {a:.12g} {b:.12g}' for a, b in points]
    lines += ['+ )', f'Vsupply vcc 0 {h["supply_v"]}', f'Vreference ref 0 {h["reference_v"]}',
              f'Rbase in base {value["Rbase_ohm"]:.12g}', f'Rled vcc anode {value["Rled_ohm"]:.12g}',
              'Dled anode col BM_RED', 'Qled col base 0 BM_NPN',
              f'Rattenuator col out {h["collector_to_OUT_ohm"]}', f'Rbias out ref {h["OUT_to_REF_ohm"]}',
              f'.model BM_NPN NPN(IS=1e-14 BF={value["Q1_BF"]:.12g} BR=3 NF=1 NR=1)',
              f'.model BM_RED D(IS={led_is:.12g} N=2 RS=2)', '.temp 27',
              '.options reltol=1e-7 abstol=1e-14 vntol=1e-8 minbreak=1e-12']
    if s['load_ohm'] is not None:
        lines += [f'RfixtureLoad out ref {s["load_ohm"]:.12g}']
    lines += [f'.tran {s["period_us"]*1e-6/4:.12g} {stop:.12g}', '.control', 'set wr_singlescale',
              'set numdgt=15', 'run', 'wrdata output.dat v(out) v(col) v(base) i(Vdrive) i(Vsupply)',
              'quit', '.endc', '.end']
    raw_netlist = '\n'.join(lines)+'\n'
    if before_run:
        before_run()
    with tempfile.TemporaryDirectory(prefix='benchmate-active-') as directory:
        p = Path(directory); (p/'active.cir').write_text(raw_netlist)
        result = subprocess.run([executable, '-b', 'active.cir'], cwd=p, capture_output=True, text=True, timeout=15)
        if result.returncode or not (p/'output.dat').exists():
            raise ValueError('ngspice rejected the active circuit or failed to converge.')
        table = np.loadtxt(p/'output.dat')
    if table.ndim != 2 or table.shape[1] != 6 or not np.isfinite(table).all():
        raise ValueError('Invalid active simulator output.')
    if table[0, 0] > 1e-12 or table[-1, 0] < stop-1e-9:
        raise ValueError('Incomplete active simulation.')
    peak_input, peak_supply = float(np.max(abs(table[:, 4]))), float(np.max(abs(table[:, 5])))
    if peak_input > h['max_input_current_a'] or peak_supply > h['max_supply_current_a']:
        raise ValueError('Simulated active current exceeds the development envelope.')
    if (np.min(table[:, 1]) < 1.0 or np.max(table[:, 1]) > 2.7
            or np.min(table[:, 2]) < -.05 or np.max(table[:, 2]) > 5.1):
        raise ValueError('Declared measurement attenuation or collector envelope failed.')
    sampled = np.column_stack([np.interp(t+do, table[:, 0], table[:, i]) for i in range(1, 6)])
    return {'predicted_output_minus_ref_v': (sampled[:, 0]-h['reference_v']).tolist(),
            'predicted_collector_v': sampled[:, 1].tolist(), 'predicted_base_v': sampled[:, 2].tolist(),
            'predicted_base_source_current_a': (-sampled[:, 3]).tolist(),
            'predicted_LED_supply_current_a': (-sampled[:, 4]).tolist(),
            'peak_input_current_a': peak_input, 'peak_supply_current_a': peak_supply,
            'measured_output_range_v': [float(np.min(table[:, 1])), float(np.max(table[:, 1]))],
            'simulator': 'ngspice', 'simulator_version': version, 'harness_sha256': digest(h),
            'netlist_sha256': digest(raw_netlist), 'scored_output_samples_used': 0,
            'model_refitted': False, 'optical_brightness_measured': False,
            'device_parameters_characterized': False}


def predict(value, input_template, before_run=None):
    return simulate(value, input_template, before_run)['predicted_output_minus_ref_v']


class Fitter:
    def __init__(self, *, max_calls=1000, max_seconds=120.):
        self.calls = 0; self.max_calls = max_calls; self.max_seconds = max_seconds
        self.began = time.monotonic(); self.cache = {}

    def consume(self):
        if self.calls >= self.max_calls or time.monotonic()-self.began > self.max_seconds:
            raise RuntimeError('Active fit simulator/time budget exhausted; not a rejected component.')
        self.calls += 1

    def curves(self, value, captures):
        result = []
        for c in captures:
            key = digest([value, c['input_template']])
            if key not in self.cache:
                self.cache[key] = predict(value, c['input_template'], self.consume)
            result.append(self.cache[key])
        return result

    def fit(self, captures, changed=None):
        for c in captures:
            validate_capture(c, role='training')
        if not captures or len({c['source'] for c in captures}) != 1:
            raise ValueError('One provenance and at least one training capture required.')
        names = ['Q1_BF', 'LED_Vf_1mA_v']
        lo, hi, start = [200., 1.7], [450., 2.3], [300., 2.]
        if changed == 'Rbase':
            names += ['Rbase_ohm']; lo += [1000.]; hi += [2e6]; start += [4700.]
        elif changed == 'Rled':
            names += ['Rled_ohm']; lo += [1000.]; hi += [10000.]; start += [1000.]
        elif changed == 'Q1':
            lo[0], hi[0] = .25, 800.
        elif changed == 'D1':
            lo[1], hi[1] = 1.2, 3.4
        elif changed is not None:
            raise ValueError('Unknown intended active component.')
        lower, upper, initial = np.log(lo), np.log(hi), np.log(start)

        def decode(x):
            p = dict(zip(names, map(float, np.exp(x))))
            return model(rbase=p.get('Rbase_ohm', 4700.), rled=p.get('Rled_ohm', 1000.),
                         beta=p['Q1_BF'], vf=p['LED_Vf_1mA_v'])

        def residual(x):
            return np.concatenate([(np.asarray(c['output_minus_ref_v'])-p)/.009
                                   for c, p in zip(captures, self.curves(decode(x), captures), strict=True)])

        # Saturation is a flat region: use a fixed public coarse grid so a
        # local optimizer does not need a hidden truth-derived starting value.
        candidates = [initial]
        index = names.index('Rbase_ohm') if changed == 'Rbase' else 0 if changed == 'Q1' else None
        if index is not None:
            for v in np.linspace(lower[index], upper[index], 8):
                x = initial.copy(); x[index] = v; candidates.append(x)
        initial = min(candidates, key=lambda x: float(np.sum(residual(x)**2)))

        def jac(x):
            base = residual(x); columns = []
            for i in range(len(x)):
                step = 1e-3 if x[i]+1e-3 < upper[i] else -1e-3
                y = x.copy(); y[i] += step
                columns.append((residual(y)-base)/step)
            return np.column_stack(columns)
        fit = least_squares(residual, initial, jac=jac, bounds=(lower, upper), max_nfev=36,
                            ftol=1e-7, xtol=1e-7, gtol=1e-7)
        fitted = decode(fit.x)
        checks = [score(c, p) for c, p in zip(captures, self.curves(fitted, captures), strict=True)]
        result = {'id': 'nominal' if changed is None else 'changed:'+changed,
                'changed_component': changed, 'model': fitted,
                'status': ('adequate' if all(c['passed'] for c in checks) else 'inadequate') if fit.success else 'fit_error',
                'training_checks': checks, 'optimizer_converged': bool(fit.success),
                'fitted_parameters': dict(zip(names, map(float, np.exp(fit.x)))),
                'nuisance_parameters': ['Q1_BF', 'LED_Vf_1mA_v'],
                **rank_info(fit.jac), 'physical_parameters_unique': False,
                'parameter_at_bound': bool(np.any(np.minimum(fit.x-lower, upper-fit.x) < .01)),
                'verification_outputs_used': 0, 'device_assumptions': deepcopy(ASSUMPTIONS)}
        if not fit.success:
            result['error'] = 'Optimizer did not converge; this is not an inadequate circuit hypothesis.'
        return result


def assess(design, captures):
    checked(design)
    for c in captures:
        validate_capture(c, role='training')
    fitter = Fitter(); rows = []
    for name in (None, 'Rbase', 'Rled', 'D1', 'Q1'):
        try:
            row = fitter.fit(captures, name)
        except (ValueError, RuntimeError) as exc:
            row = {'id': 'nominal' if name is None else 'changed:'+name,
                   'changed_component': name, 'status': 'fit_error', 'error': str(exc)}
        rows.append(row)
    return {'hypotheses': rows, 'simulator_calls': fitter.calls,
            'all_inadequate': all(r['status'] == 'inadequate' for r in rows),
            'fitting_complete': not any(r['status'] == 'fit_error' for r in rows),
            'interpretation': 'BC547B and red-LED development families; current-gain and base-resistance ambiguity is retained.'}
