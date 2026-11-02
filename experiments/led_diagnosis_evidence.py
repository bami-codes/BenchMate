"""Retained offline active-profile envelope/equivalence checks; no API or USB."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from benchmate.netlist_diagnosis.menu import MENU, RESERVED, template
from benchmate.netlist_diagnosis_v2 import led
from benchmate.netlist_diagnosis_v2.protocol import source_hashes


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    out = Path(args.output)
    if out.exists(): raise ValueError('Use a new output file; do not overwrite first results.')
    equivalence = []
    for name, settings in list(MENU.items()) + [('reserved_'+str(i), s) for i, s in enumerate(RESERVED)]:
        inp = template(settings)
        a = led.simulate(led.model(rbase=1e6, beta=290.), inp)
        b = led.simulate(led.model(rbase=4700., beta=1.363), inp)
        delta = np.asarray(a['predicted_output_minus_ref_v'])-b['predicted_output_minus_ref_v']
        equivalence.append({'action': name, 'settings': settings,
                            'maximum_difference_mV': float(np.max(abs(delta))*1000),
                            'RMS_difference_mV': float(np.sqrt(np.mean(delta**2))*1000),
                            'both_measurement_output_range_v': [a['measured_output_range_v'], b['measured_output_range_v']]})
    envelope = []
    for beta in [200., 450.]:
        for vf in [1.7, 2.3]:
            for rbase in [4700., 1e6]:
                for name in ['unloaded_sine_1hz_large', 'loaded_step_large']:
                    m = led.model(rbase=rbase, beta=beta, vf=vf)
                    s = MENU[name]; r = led.simulate(m, template(s))
                    lo, hi = r['measured_output_range_v']
                    envelope.append({'model': m, 'action': name,
                                     'measurement_output_range_v': [lo, hi],
                                     'collector_range_v': [min(r['predicted_collector_v']), max(r['predicted_collector_v'])],
                                     'mean_LED_supply_current_a': float(np.mean(r['predicted_LED_supply_current_a'])),
                                     'peak_supply_current_a': r['peak_supply_current_a'],
                                     'peak_input_current_a': r['peak_input_current_a'],
                                     'within_original_development_window': max(abs(lo-1.646), abs(hi-1.646)) < .95})
    result = {'scope': 'Shared-ngspice finite-menu development checks, no physical qualification or optical measurement.',
              'equivalent_models': [led.model(rbase=1e6, beta=290.), led.model(rbase=4700., beta=1.363)],
              'equivalence': equivalence, 'envelope': envelope,
              'all_equivalence_differences_below_1mV': all(x['maximum_difference_mV'] < 1 for x in equivalence),
              'all_envelope_checks_passed': all(x['within_original_development_window'] for x in envelope),
              'source_sha256': source_hashes(),
              'evidence_producer_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'paid_requests': 0, 'hardware_commands': 0}
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps({'output': str(out), 'equivalence_checks': len(equivalence), 'envelope_checks': len(envelope),
                      'passed': result['all_equivalence_differences_below_1mV'] and result['all_envelope_checks_passed']}))
    raise SystemExit(0 if result['all_equivalence_differences_below_1mV'] and result['all_envelope_checks_passed'] else 1)


if __name__ == '__main__': main()
