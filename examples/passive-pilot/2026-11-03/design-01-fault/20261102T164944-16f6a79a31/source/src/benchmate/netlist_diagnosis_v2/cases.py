"""Evaluator catalogue: five preserved passive fixtures and one active fixture."""
from ..netlist_diagnosis.cases import CATALOGUE as PASSIVE_CASES, mock_review, specimen
from ..netlist_diagnosis.design import digest, CONFIRMATION
from . import led

LED_CASE = {'id': 'dim-led', 'source': 'https://forum.arduino.cc/t/bc547-base-resistor-checking/384293',
            'design': led.PARTS, 'harness': led.HARNESS,
            'operator_reported_parts': {'transistor': 'JCET BC547B, marking BC547 / B GLG, bent lead',
                                        'LED': 'red 5mm flat diffused'},
            'software_truth': led.model(rbase=1e6, beta=290., vf=2.),
            'software_repaired': led.model(rbase=4700., beta=290., vf=2.),
            'expected': {'verdict': 'indistinguishable', 'components': ['Q1', 'Rbase']},
            'changed': 'One low-current red LED instead of five LEDs. Rbase 4.7k to 1M, not the original 470-ohm repair. Explicit 47k/10k measurement divider loading included.',
            'interpretation': 'Insufficient effective base drive: large Rbase and very low transistor gain are electrically confounded at OUT. Photo markings can separately check Rbase. No optical measurement.'}
CATALOGUE = [*PASSIVE_CASES, LED_CASE]


def reviewed(case):
    if case['id'] == 'dim-led':
        return led.review(source_sha256=digest(case['design']), confirmation=CONFIRMATION,
                          note='SOFTWARE DEVELOPMENT ONLY: intended component list, not a new image reading or human review.', simulated=True)
    return mock_review(case)


def truth(case, repaired=False):
    return case['software_repaired' if repaired else 'software_truth'] if case['id'] == 'dim-led' else specimen(case, repaired=repaired)
