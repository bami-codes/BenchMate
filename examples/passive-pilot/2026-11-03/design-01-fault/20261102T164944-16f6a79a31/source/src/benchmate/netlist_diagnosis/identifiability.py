"""Finite-menu electrical equivalence checks, independent of model decisions."""
from copy import deepcopy
import numpy as np

from .cases import CATALOGUE, LED, specimen
from .menu import MENU, template
from .simulation import simulate


def compare(a, b):
    result = {}
    for name, action in MENU.items():
        inp = template(action)
        ya = simulate(a, inp)['predicted_output_minus_ref_v']
        yb = simulate(b, inp)['predicted_output_minus_ref_v']
        result[name] = {'maximum_difference_mV': float(np.max(abs(np.asarray(ya)-yb))*1000),
                        'RMS_difference_mV': float(np.sqrt(np.mean((np.asarray(ya)-yb)**2))*1000)}
    return result


def evaluate():
    # Values differ but their literal terminal behavior is electrically tied.
    pin = CATALOGUE[0]
    effective = deepcopy(pin['design']); effective[0]['value'] = 24700.
    sensor_a, sensor_b = deepcopy(CATALOGUE[1]['design']), deepcopy(CATALOGUE[1]['design'])
    sensor_a[1]['value'] = 1.2e-6; sensor_b[2]['value'] = .3e-6
    timing_a, timing_b = deepcopy(CATALOGUE[2]['design']), deepcopy(CATALOGUE[2]['design'])
    timing_a[0]['value'] = 2200.; timing_b[1]['value'] = 2200.
    divider_a, divider_b = deepcopy(CATALOGUE[3]['design']), deepcopy(CATALOGUE[3]['design'])
    divider_a[0]['value'] *= 2; divider_b[1]['value'] /= 2
    contact_a, contact_b = deepcopy(CATALOGUE[4]['design']), deepcopy(CATALOGUE[4]['design'])
    contact_b[1]['value'] = 22000.; contact_b[2]['value'] = .47e-6
    pairs = [
        ('pin-output', 'External series R and increased R1 have the same terminal response.', specimen(pin), effective, 'all'),
        ('sensor-filter', 'Two parallel capacitors expose their sum, not individual changes in the overlapping positive range.', sensor_a, sensor_b, 'all'),
        ('timing-chain', 'RA and RB expose their series sum.', timing_a, timing_b, 'all'),
        ('unpowered-input', 'A divider ratio can tie unloaded; a known output load separates the scale.', divider_a, divider_b, 'unloaded_only'),
        ('contact-resistance', 'With an ideal IN-OUT connection, changing parallel R/C cannot change measured OUT conditional on IN.', contact_a, contact_b, 'all'),
    ]
    rows = []
    for case, explanation, a, b, expected in pairs:
        checks = compare(a, b)
        if expected == 'all':
            passed = all(v['maximum_difference_mV'] < .001 for v in checks.values())
        else:
            passed = (all(v['maximum_difference_mV'] < .001 for k, v in checks.items() if k.startswith('unloaded'))
                      and any(v['RMS_difference_mV'] > 9 for k, v in checks.items() if k.startswith('loaded')))
        rows.append({'case': case, 'explanation': explanation, 'models': [a, b],
                     'expected_relation': expected, 'menu_comparison': checks, 'matches_expectation': passed})
    return {'scope': 'Finite-menu, shared-ngspice numerical equivalence checks; not physical accuracy or a general identifiability proof.',
            'results': rows, 'all_expectations_met': all(r['matches_expectation'] for r in rows),
            'deferred': LED, 'paid_requests': 0, 'hardware_commands': 0}
