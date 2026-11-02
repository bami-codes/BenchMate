"""One-component training fits and literal topology proposals, with finite budgets."""
from copy import deepcopy
import time
import numpy as np
from scipy.optimize import least_squares

from ..b5_models import rank_info
from ..d01_repair import command_score
from ..netlist import DIODE_INITIAL, DIODE_BOUNDS
from ..physical_netlist import validate_input_template
from .design import elements as check_elements, digest
from .simulation import simulate


def validate_capture(capture, *, role=None):
    if (not isinstance(capture, dict) or capture.get('source') not in ('mock', 'physical')
            or capture.get('voltage_basis') != 'REF_relative_v1'
            or capture.get('all_guards_passed') is not True
            or capture.get('fresh_measurement') is not True
            or capture.get('purpose') not in ('training', 'verification')):
        raise ValueError('Fresh guarded REF-relative observation required.')
    if role is not None and capture['purpose'] != role:
        raise ValueError('Reserved outputs cannot enter training fitting.')
    expected = 'mock_adc_input_only' if capture['source'] == 'mock' else 'physical_input_only'
    if capture['input_template']['source'] != expected:
        raise ValueError('Input provenance mismatch.')
    s, t, u, di, do, cycle = validate_input_template(capture['input_template'])
    settings = capture.get('settings', {})
    expected_settings = {k: settings.get(k) for k in ('kind', 'samples', 'period_us', 'load_ohm')}
    expected_settings.update(frequency_hz=settings.get('frequency_hz'),
                             step_index=settings.get('samples', 0)//10 if settings.get('kind') == 'step' else None)
    if s != expected_settings:
        raise ValueError('Input template does not match the requested capture settings.')
    y = np.asarray(capture['output_minus_ref_v'], float)
    if y.shape != u.shape or not np.isfinite(y).all() or np.max(abs(y)) > 1.05:
        raise ValueError('Bounded finite OUT samples required.')
    if not capture.get('boot_id') or not capture.get('reference_id'):
        raise ValueError('Boot and independently anchored REF identity required.')
    return s, t, u, di, do, y


def score(capture, curve):
    s, t, u, di, do, y = validate_capture(capture)
    prediction = np.asarray(curve, float)
    if prediction.shape != y.shape or not np.isfinite(prediction).all():
        raise ValueError('Finite matching prediction required.')
    # Reuse the frozen whole/region scorer. It performs no fitting and makes no
    # provenance assumption; provenance is checked above, including for mocks.
    observation = {'settings': s, 'baseline': {'output_v': 0.},
                   'data': {'frame_time_s': t.tolist(), 'output_delay_s': do.tolist(), 'output_v': y.tolist()}}
    return {**command_score(observation, prediction), 'baseline': 'Independent REF; no scored OUT origin fit.',
            'source': capture['source'], 'purpose': capture['purpose']}


def predict(model, input_template, before_run=None):
    return simulate(model['elements'], input_template, diode=model.get('diode'),
                    before_run=before_run)['predicted_output_minus_ref_v']


class Fitter:
    def __init__(self, *, max_calls=240, max_seconds=45.):
        self.max_calls, self.max_seconds = max_calls, max_seconds
        self.calls = 0
        self.started = time.monotonic()
        self.cache = {}

    def consume(self):
        if self.calls >= self.max_calls or time.monotonic()-self.started > self.max_seconds:
            raise RuntimeError('Diagnosis simulator/time budget exhausted; this is not a rejected circuit.')
        self.calls += 1

    def curve(self, model, template):
        key = digest([model, template])
        if key not in self.cache:
            self.cache[key] = predict(model, template, self.consume)
        return self.cache[key]

    def fit(self, value, captures, *, hypothesis_id, changed=None, fit_names=(), fit_diode=False):
        if not captures:
            raise ValueError('At least one training observation is required.')
        for c in captures:
            validate_capture(c, role='training')
        if len({c['source'] for c in captures}) != 1:
            raise ValueError('Mock and physical training observations cannot be mixed.')
        nominal = check_elements(value)
        active = [i for i, e in enumerate(nominal) if e['name'] in fit_names]
        if len(active) != len(fit_names) or len(active) > 2:
            raise ValueError('At most two explicitly named R/C proposal values may be fitted.')
        names, initial, bounds = [], [], []
        for i in active:
            e = nominal[i]
            if e['kind'] not in ('R', 'C'):
                raise ValueError('Only R/C values may vary directly.')
            names.append(e['name']); initial.append(e['value'])
            bounds.append((1000., 100000.) if e['kind'] == 'R' else (1e-9, 1e-5))
        if fit_diode:
            if not any(e['kind'] == 'D' for e in nominal):
                raise ValueError('No diode in proposed structure.')
            names += ['diode_IS', 'diode_N']
            initial += list(DIODE_INITIAL.values()); bounds += list(DIODE_BOUNDS.values())

        def decode(x):
            result = {'elements': deepcopy(nominal), 'diode': dict(DIODE_INITIAL)}
            for i, v in zip(active, np.exp(x[:len(active)])):
                result['elements'][i]['value'] = float(v)
            if fit_diode:
                result['diode'] = dict(zip(DIODE_INITIAL, map(float, np.exp(x[-2:]))))
            return result

        def curves(x):
            model = decode(x)
            return [self.curve(model, c['input_template']) for c in captures]

        def residual(x):
            return np.concatenate([(np.asarray(c['output_minus_ref_v'])-p)/.009
                                   for c, p in zip(captures, curves(x), strict=True)])

        start = np.log(initial)
        if names:
            lo, hi = np.log(bounds).T
            def jac(x):
                base = residual(x)
                columns = []
                for i in range(len(x)):
                    step = 1e-3 if x[i]+1e-3 < hi[i] else -1e-3
                    shifted = x.copy(); shifted[i] += step
                    columns.append((residual(shifted)-base)/step)
                return np.column_stack(columns)
            result = least_squares(residual, start, jac=jac, bounds=(lo, hi), max_nfev=24,
                                   ftol=1e-7, xtol=1e-7, gtol=1e-7)
            rank = rank_info(result.jac)
            # Flat input branches must not acquire an arbitrary fitted value.
            x = start if rank['local_parameter_rank'] == 0 else result.x
            converged = bool(result.success)
            at_bound = bool(np.any(np.minimum(x-lo, hi-x) < .01))
        else:
            x = start; converged = True; at_bound = False
            rank = {'local_parameter_rank': 0, 'fitted_parameter_count': 0,
                    'parameters_identifiable': True, 'unique_physical_parameters_claimed': False}
        model = decode(x)
        checks = [score(c, p) for c, p in zip(captures, curves(x), strict=True)]
        adequate = converged and all(c['passed'] for c in checks)
        return {'id': hypothesis_id, 'changed_component': changed, 'model': model,
                'status': 'adequate' if adequate else 'inadequate', 'training_checks': checks,
                'optimizer_converged': converged, 'parameter_at_bound': at_bound,
                'fitted_parameters': dict(zip(names, map(float, np.exp(x)))), **rank,
                'training_observations': len(captures), 'verification_outputs_used': 0}


def assess(design_elements, captures, *, max_calls=1200, max_seconds=90.):
    # Invalid provenance is a protocol error, not a collection of failed fits.
    if not captures:
        raise ValueError('Training data required.')
    for capture in captures:
        validate_capture(capture, role='training')
    fitter = Fitter(max_calls=max_calls, max_seconds=max_seconds)
    rows = []
    specs = [('nominal', None)] + [('changed:' + e['name'], e['name'])
                                 for e in design_elements if e['kind'] in ('R', 'C')]
    for identity, changed in specs:
        try:
            row = fitter.fit(design_elements, captures, hypothesis_id=identity, changed=changed,
                             fit_names=[changed] if changed else [])
        except (RuntimeError, ValueError) as exc:
            row = {'id': identity, 'changed_component': changed, 'status': 'fit_error', 'error': str(exc)}
        rows.append(row)
    return {'hypotheses': rows, 'simulator_calls': fitter.calls,
            'all_inadequate': all(r['status'] == 'inadequate' for r in rows),
            'fitting_complete': not any(r['status'] == 'fit_error' for r in rows)}
