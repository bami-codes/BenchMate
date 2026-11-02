"""Development catalogue and evaluator truth, never imported by the session.

These are forum-inspired reduced circuits, not the forum participants' boards.
LED/BJT is explicitly deferred, not represented by an invented RC substitute.
"""
from copy import deepcopy

from .design import review, digest, CONFIRMATION


def part(name, kind, a, b, value=0.):
    return dict(name=name, kind=kind, a=a, b=b, value=float(value),
                model='generic_diode' if kind == 'D' else 'none')


CATALOGUE = [
    {'id': 'pin-output', 'source': 'https://forum.arduino.cc/t/oscilloscope-low-pass-filter-help/1098926',
     'design': [part('R1', 'R', 'IN', 'OUT', 4700), part('C1', 'C', 'OUT', 'REF', 1e-6)],
     'truth': [part('R1', 'R', 'N1', 'OUT', 4700), part('Rhidden', 'R', 'IN', 'N1', 20000),
               part('C1', 'C', 'OUT', 'REF', 1e-6)],
     'expected': {'verdict': 'changed', 'components': ['R1']},
     'interpretation': 'Effective series path resistance; cannot locate the extra R outside the board.',
     'changed': '10 ohm + approximate 40 ohm becomes 4.7k + 20k. No MCU pin is overloaded.'},
    {'id': 'sensor-filter', 'source': 'https://forum.arduino.cc/t/mpu6050-breakout-board-gy-521-wrong-capacitor-results-in-erratic-data/380339',
     'design': [part('R1', 'R', 'IN', 'OUT', 10000), part('Cfilter', 'C', 'OUT', 'REF', 1e-6),
                part('Cbypass', 'C', 'OUT', 'REF', .1e-6), part('Rload', 'R', 'OUT', 'REF', 22000)],
     'replace': {'Cfilter': .47e-6}, 'expected': {'verdict': 'changed', 'components': ['Cfilter']},
     'interpretation': 'Only Cfilter+Cbypass is electrically observable. This large decrease selects Cfilter under the single-fault, positive-C prior; smaller overlapping changes remain ambiguous.',
     'changed': 'Passive REGOUT-inspired loaded filter, no MPU6050/regulator stability or sensor-noise claim. 50x becomes about 2.13x.'},
    {'id': 'timing-chain', 'source': 'https://forum.allaboutcircuits.com/threads/555-blinking-led-one-cycle-and-stops.55255/',
     'design': [part('RA', 'R', 'IN', 'N1', 10000), part('RB', 'R', 'N1', 'OUT', 10000),
                part('C1', 'C', 'OUT', 'REF', 1e-6)],
     'replace': {'RA': 2200}, 'expected': {'verdict': 'indistinguishable', 'components': ['RA', 'RB']},
     'interpretation': 'Only RA+RB is measured. Photo markings may separately localize the wrong resistor.',
     'changed': 'Timing-chain segment only, no 555 oscillator. One R changed by 4.55x; original thread had two wrong resistors.'},
    {'id': 'unpowered-input', 'source': 'https://forum.arduino.cc/t/voltage-divider-is-not-giving-correct-voltage/884099?page=3',
     'design': [part('R1', 'R', 'IN', 'OUT', 4700), part('R2', 'R', 'OUT', 'REF', 22000)],
     'add': [part('Dhidden', 'D', 'OUT', 'REF')],
     'diode_truth': {'is_a': 3e-9, 'n': 1.9},
     'expected': {'verdict': 'structure_supported', 'components': []},
     'interpretation': 'Amplitude-dependent clamp, not a unique diagnosis of ESP32 internal circuitry.',
     'changed': 'One bounded diode to REF represents an unpowered-rail clamp; actual chip/rail dynamics omitted.'},
    {'id': 'contact-resistance', 'source': 'https://eevblog.com/forum/beginners/voltage-drop-at-breadboard',
     'design': [part('W1', 'W', 'IN', 'OUT'), part('Rload', 'R', 'OUT', 'REF', 10000),
                part('Cdecouple', 'C', 'OUT', 'REF', 1e-6)],
     'truth': [part('Rhidden', 'R', 'IN', 'OUT', 10000), part('Rload', 'R', 'OUT', 'REF', 10000),
               part('Cdecouple', 'C', 'OUT', 'REF', 1e-6)],
     'expected': {'verdict': 'structure_supported', 'components': []},
     'interpretation': 'A missing series impedance; cannot distinguish a jumper from a contact cause.',
     'changed': 'A REF-relative parallel decoupled load with exaggerated source impedance, not the original 5V power network.'},
]

LED = {'id': 'dim-led', 'source': 'https://forum.arduino.cc/t/bc547-base-resistor-checking/384293',
       'status': 'deferred_BJT_and_5V_harness',
       'parts': ['BC547', 'LED', 'Rbase', 'Rled'],
       'required': ['actual 5V/GND/REF boundaries', 'LM358 measurement range or attenuator',
                    'current limits and device pinout', 'BJT and LED model uncertainty',
                    'new firmware/protocol validation and separately approved upload'],
       'estimate_hours': [4, 8], 'simulated_accuracy_result': None}


def specimen(case, *, repaired=False):
    if repaired:
        return deepcopy(case['design'])
    if 'truth' in case:
        return deepcopy(case['truth'])
    result = deepcopy(case['design'])
    for e in result:
        if e['name'] in case.get('replace', {}):
            e['value'] = case['replace'][e['name']]
    return result + deepcopy(case.get('add', []))


def mock_review(case):
    return review(case['design'], source_sha256=digest(case['design']), confirmation=CONFIRMATION,
                  note='SOFTWARE DEVELOPMENT: schematic list substituted for an actual image reading.', simulated=True)
