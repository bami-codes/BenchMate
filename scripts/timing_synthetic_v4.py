#!/usr/bin/env python3
"""Independent analytic source-R / DUT-R / shunt-RC timing controls.

The truth generator does not call either prediction engine. It solves each DAC
hold interval analytically, including the declared 1kohm instrument resistor,
then samples IN/OUT 53us apart. This is simulation, never physical evidence.
"""
import argparse
import json
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT/'src')]
from benchmate.channel_timing_v4 import predict as new_predict
from benchmate.netlist_diagnosis.models import predict as old_predict, score
from benchmate.netlist_diagnosis.menu import MENU, RESERVED, template


def element(name, kind, a, b, value):
    return dict(name=name, kind=kind, a=a, b=b, value=value, model='none')


def specimens():
    return [
        ('05_direct_input_cap', 0., 10000., 1e-6, [
            element('W1', 'W', 'IN', 'OUT', 0.), element('R1', 'R', 'OUT', 'REF', 10000.),
            element('C1', 'C', 'OUT', 'REF', 1e-6)]),
        ('01_nominal_RC', 4700., None, 1e-6, [element('R1', 'R', 'IN', 'OUT', 4700.), element('C1', 'C', 'OUT', 'REF', 1e-6)]),
        ('01_fault_series_path', 24700., None, 1e-6, [element('R1', 'R', 'IN', 'OUT', 24700.), element('C1', 'C', 'OUT', 'REF', 1e-6)]),
        ('02_nominal_parallel_C', 10000., 20000., 1.1e-6, [element('R1', 'R', 'IN', 'OUT', 10000.),
            element('R2', 'R', 'OUT', 'REF', 20000.), element('C1', 'C', 'OUT', 'REF', 1e-6), element('C2', 'C', 'OUT', 'REF', .1e-6)]),
        ('02_fault_parallel_C', 10000., 20000., .57e-6, [element('R1', 'R', 'IN', 'OUT', 10000.),
            element('R2', 'R', 'OUT', 'REF', 20000.), element('C1', 'C', 'OUT', 'REF', .47e-6), element('C2', 'C', 'OUT', 'REF', .1e-6)]),
        ('03_series_R_chain_control', 20000., None, 1e-6, [element('R1', 'R', 'IN', 'N1', 10000.),
            element('R2', 'R', 'N1', 'OUT', 10000.), element('C1', 'C', 'OUT', 'REF', 1e-6)]),
        ('04_restored_divider', 4700., 20000., 0., [element('R1', 'R', 'IN', 'OUT', 4700.), element('R2', 'R', 'OUT', 'REF', 20000.)]),
    ]


def analytic_capture(settings, rdut, rshunt, capacitance, *, skew=53e-6):
    inp = template(settings, source='mock_adc_input_only')
    d = inp['data']; t = np.asarray(d['frame_time_s']); command = np.asarray(d['input_relative_origin_v'])
    di = np.full(len(t), 50e-6); do = di + skew
    rsource = 1000.; series = rsource + rdut
    effective_load = settings['load_ohm']
    if rshunt is not None:
        effective_load = rshunt if effective_load is None else 1/(1/rshunt+1/effective_load)
    gain = 1. if effective_load is None else effective_load/(series+effective_load)
    tau = series*capacitance if effective_load is None else (series*effective_load/(series+effective_load))*capacitance
    period = settings['period_us']*1e-6
    if tau == 0.:
        output = gain*command
        input_values = (rdut*command+rsource*output)/series
    else:
        decay = np.exp(-period/tau)
        if settings['kind'] == 'sine':
            cycle = round(1/(settings['frequency_hz']*period))
            b = 0.
            for v in command[:cycle]:
                b = gain*v + (b-gain*v)*decay
            state = b/(1-decay**cycle)
        else:
            state = gain*command[0]
        inputs, outputs = [], []
        for v, a, b in zip(command, di, do, strict=True):
            y_at_input = gain*v+(state-gain*v)*np.exp(-a/tau)
            outputs.append(gain*v+(state-gain*v)*np.exp(-b/tau))
            inputs.append((rdut*v+rsource*y_at_input)/series)
            state = gain*v+(state-gain*v)*decay
        input_values, output = np.array(inputs), np.array(outputs)
    d.update(input_delay_s=di.tolist(), output_delay_s=do.tolist(), input_relative_origin_v=input_values.tolist())
    return {'source': 'mock', 'voltage_basis': 'REF_relative_v1', 'purpose': 'verification',
            'all_guards_passed': True, 'fresh_measurement': True, 'settings': settings,
            'input_template': inp, 'output_minus_ref_v': output.tolist(),
            'boot_id': 'analytic-simulation-not-hardware', 'reference_id': 'independent-analytic-zero'}


def run():
    settings = list(MENU.items()) + [('reserved_step', RESERVED[0]), ('reserved_sine', RESERVED[1])]
    rows = []
    for name, r, rl, c, elements in specimens():
        for action, s in settings:
            capture = analytic_capture(s, r, rl, c)
            result = dict(specimen=name, action=action, completion_skew_us=53., independently_generated_truth=True)
            for label, fn in [('old', old_predict), ('new', new_predict)]:
                try:
                    check = score(capture, fn({'elements': elements}, capture['input_template']))
                    result[label] = {'passed': check['passed'], 'RMS_mV': check['RMS_mV'],
                                     'worst_region_RMS_mV': max(x['RMS_mV'] for x in check['regions'])}
                except (ValueError, RuntimeError) as exc:
                    result[label] = {'passed': False, 'error': str(exc)}
            rows.append(result)
    target = next(x for x in rows if x['specimen'] == '05_direct_input_cap' and x['action'] == 'reserved_step')
    return {'schema': 'benchmate.channel_timing_synthetic.v4', 'source': 'independent_analytic_simulation',
            'physical_evidence': False, 'API_requests': 0, 'hardware_commands': 0,
            'timing_parameters_fitted': [], 'instrument_series_ohm': 1000.,
            '05_old_fail_new_pass': not target['old']['passed'] and target['new']['passed'],
            'other_design_flips': [x for x in rows if x['specimen'] != '05_direct_input_cap' and x['old']['passed'] != x['new']['passed']],
            'rows': rows}


def main():
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('--output', required=True)
    args = p.parse_args(); value = run(); target = Path(args.output)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open('x') as f:json.dump(value, f, indent=2, allow_nan=False);f.write('\n')
    print(json.dumps({'checks': len(value['rows']), '05_old_fail_new_pass': value['05_old_fail_new_pass'],
                      'other_design_flips': len(value['other_design_flips'])}))


if __name__ == '__main__':main()
