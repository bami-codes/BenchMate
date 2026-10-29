"""Fixed RC predictions conditioned on measured input, independent of scored OUT.

The pre-stimulus HOLD supplies a separate input/output origin. This verifies
incremental response, not absolute voltage calibration. Samples reconstruct
the held input level for each command frame; this is an offline conditional
prediction, not a waveform known before the input was observed.
"""
import math
import numpy as np


def predict_incremental_rc(frame_time_s, input_v, input_delay_s, output_delay_s, *,
                           gain, tau_s, baseline_input_v, baseline_output_v,
                           kind, step_index=None, frequency_hz=None):
    """Predict all OUT samples without accepting any scored OUT values.

    STEP starts from equilibrium of the measured pre-step IN mean, following
    the instrument's settled low-level start. SINE uses the first complete IN
    cycle to solve the periodic initial state analytically. No output value
    selects or fits either initial state. Both rules must be declared before
    acquisition, along with the separately acquired HOLD baseline.
    """
    arrays = [np.asarray(x, dtype=float) for x in
              (frame_time_s, input_v, input_delay_s, output_delay_s)]
    frames, measured, input_delays, output_delays = arrays
    if (any(x.ndim != 1 for x in arrays) or len(frames) < 16
            or any(len(x) != len(frames) or not np.isfinite(x).all() for x in arrays)):
        raise ValueError('Finite matching one-dimensional arrays with at least 16 frames required')
    if not all(math.isfinite(x) for x in (gain, tau_s, baseline_input_v, baseline_output_v)):
        raise ValueError('Model and baseline must be finite')
    if not 0 < gain <= 1 or tau_s <= 0:
        raise ValueError('Positive tau and passive RC gain required')
    periods = np.diff(frames)
    if (frames[0] < 0 or np.any(periods <= 0)
            or np.any(input_delays < 0) or np.any(output_delays < input_delays)):
        raise ValueError('Invalid frame or channel timing')
    nominal_period = float(np.median(periods))
    durations = np.r_[periods, nominal_period]
    if np.any(output_delays >= durations):
        raise ValueError('OUT timestamp must precede the next command frame')
    equilibrium = gain * (measured - baseline_input_v)
    if kind == 'step':
        if type(step_index) is not int or not 1 <= step_index < len(frames):
            raise ValueError('A declared interior step index is required')
        state = float(equilibrium[:step_index].mean())
        initialization = {
            'method': 'settled_pre_step_input_mean',
            'input_samples_used': step_index,
            'initial_output_change_v': state,
        }
    elif kind == 'sine':
        if frequency_hz is None or not math.isfinite(frequency_hz) or frequency_hz <= 0:
            raise ValueError('Positive declared sine frequency required')
        cycle_samples = round(1 / (frequency_hz * nominal_period))
        if not 20 <= cycle_samples < len(frames):
            raise ValueError('Need a complete input cycle with at least 20 samples')
        cycle_duration = frames[cycle_samples] - frames[0]
        if abs(cycle_duration - 1 / frequency_hz) > max(25e-6, .001 / frequency_hz):
            raise ValueError('Measured input cycle timing does not match the declared sine')
        affine_offset = 0.
        for eq, dt in zip(equilibrium[:cycle_samples], periods[:cycle_samples]):
            alpha = math.exp(-dt / tau_s)
            affine_offset = alpha * affine_offset + (-math.expm1(-dt / tau_s)) * eq
        one_minus_decay = -math.expm1(-cycle_duration / tau_s)
        state = float(affine_offset / one_minus_decay)
        initialization = {
            'method': 'periodic_first_complete_input_cycle',
            'input_samples_used': cycle_samples,
            'cycle_duration_s': float(cycle_duration),
            'initial_output_change_v': state,
            'assumption': 'The captured first input cycle represents the preceding settled periodic drive.',
        }
    else:
        raise ValueError('Only predeclared step and sine checks are supported')

    prediction = []
    for eq, dt, delay in zip(equilibrium, durations, output_delays):
        prediction.append(baseline_output_v + eq + (state - eq) * math.exp(-delay / tau_s))
        state = eq + (state - eq) * math.exp(-dt / tau_s)
    return {
        'predicted_output_v': prediction,
        'initialization': initialization,
        'scope': 'Measured-IN-conditioned incremental RC response; no absolute-voltage accuracy claim.',
        'scored_output_samples_used_for_prediction': 0,
        'all_input_samples_retained': True,
        'model_refitted': False,
    }
