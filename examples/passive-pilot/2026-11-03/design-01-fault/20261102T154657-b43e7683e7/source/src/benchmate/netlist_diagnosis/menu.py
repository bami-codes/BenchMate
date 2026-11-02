"""One public action menu for every R/C/D case; the agent chooses each action."""
from copy import deepcopy
import numpy as np

LOAD_OHM = 9990.


def action(kind, amplitude, *, frequency=None, loaded=False):
    return {'kind': kind, 'samples': 512, 'period_us': 500 if kind == 'step' else
            (4000 if frequency == 1 else 2000), 'amplitude_v': amplitude,
            **({'frequency_hz': frequency} if kind == 'sine' else {}),
            'load_ohm': LOAD_OHM if loaded else None}


MENU = {
    'unloaded_step_small': action('step', .2),
    'loaded_step_small': action('step', .2, loaded=True),
    'unloaded_step_large': action('step', .5),
    'loaded_step_large': action('step', .5, loaded=True),
    'unloaded_sine_1hz_small': action('sine', .2, frequency=1),
    'unloaded_sine_1hz_large': action('sine', .8, frequency=1),
    'unloaded_sine_5hz_small': action('sine', .15, frequency=5),
    'loaded_sine_5hz_small': action('sine', .15, frequency=5, loaded=True),
}
RESERVED = [action('step', .35), action('sine', .65, frequency=5)]
POLICY = {'version': 'netlist-diagnosis-v1', 'training_menu': MENU,
          'reserved': RESERVED, 'max_training_actions': 3, 'max_proposals': 2,
          'allowance_mV': 9., 'whole_and_every_region': True,
          'training_only_fitting': True, 'automatic_retry': False,
          'component_hypotheses': 'nominal or one R/C value changed',
          'limits': 'Conditional terminal behavior; no unique topology, hidden-part location or general accuracy claim.'}


def template(settings, *, source='command_input_only', bias=0.):
    """Input-only held-level command, not a future measured-input claim."""
    s = deepcopy(settings)
    n, period = s['samples'], s['period_us'] * 1e-6
    t = np.arange(n) * period
    if s['kind'] == 'step':
        u = s['amplitude_v'] * np.where(np.arange(n) < n // 10, -1., 1.)
    else:
        # Firmware captures after at least two complete sine periods.
        warmup = int(np.ceil(max(1.2, 2 / s['frequency_hz']) / period))
        u = s['amplitude_v'] * np.sin(2 * np.pi * s['frequency_hz'] * (np.arange(n) + warmup) * period)
    key = 'input_minus_ref_v' if source == 'physical_input_only' else 'input_relative_origin_v'
    return {'source': source, 'settings': {k: s[k] for k in ('kind', 'samples', 'period_us')} |
            {'frequency_hz': s.get('frequency_hz'), 'step_index': n // 10 if s['kind'] == 'step' else None,
             'load_ohm': s['load_ohm']},
            'data': {'frame_time_s': t.tolist(), key: (u + bias).tolist(),
                     'input_delay_s': [50e-6] * n, 'output_delay_s': [105e-6] * n}}
