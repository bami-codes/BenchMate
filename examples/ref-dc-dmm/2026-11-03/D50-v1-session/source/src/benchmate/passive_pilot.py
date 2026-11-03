"""Passive pilot runtime: public 1 kΩ driver impedance, frozen v2 diagnosis.

Conditional predictions use measured IN. Command forecasts include the known
instrument resistor, including branches invisible under measured-IN conditioning.
No frozen runtime or firmware is changed.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

from .netlist_diagnosis.design import checked, digest
from .netlist_diagnosis.models import predict
from .netlist_diagnosis.protocol import prepare as base_prepare
from .netlist_diagnosis_v2.session import Session as V2Session, PROMPT as V2_PROMPT

ROOT = Path(__file__).resolve().parents[2]
INSTRUMENT = {'driver_series_ohm': 1000., 'placement': 'B28–B35, upstream of measured IN',
              'all_five_passive_cases_and_restored_runs': True,
              'command_forecast_source': 'Ideal buffered DAC plus declared 1 kΩ; not calibrated driver dynamics.',
              'conditional_source': 'Measured IN downstream of the instrument resistor',
              'D01_2026_10_30_configuration': 'Bypass jumper, different input drive path',
              'REF_is_GND': False}
PROMPT = V2_PROMPT + '''
This is a PHYSICAL PASSIVE PILOT, excluded from evaluation. The public instrument
has a fixed 1 kohm series resistor BEFORE measured IN, shared by every passive
case. It is not a DUT defect or a candidate to diagnose. The command forecasts
include that resistor and DUT loading with an ideal buffered DAC. Conditional
predictions use actual measured IN and exclude upstream instrument dynamics.
Never confuse the instrument resistor with an inferred resistance downstream
of IN. Command forecast failures remain visible separately from conditional
validation; neither establishes measured driver stability at unsampled times.
'''


def command_model(model):
    """Insert instrument impedance only for an unmeasured command forecast."""
    m = deepcopy(model); es = m['elements']
    names = {e['name'].lower() for e in es}
    instrument_name = next('Riso'+str(i) for i in range(7) if ('Riso'+str(i)).lower() not in names)
    if any(e['kind'] == 'W' for e in es):
        es = [e for e in es if e['kind'] != 'W']
        for e in es:
            for terminal in ('a', 'b'):
                if e[terminal] == 'IN': e[terminal] = 'OUT'
        downstream = 'OUT'
    else:
        used = {e[k] for e in es for k in ('a', 'b')}
        downstream = next((n for n in ('N2', 'N1') if n not in used), None)
        if downstream is None:
            raise ValueError('No bounded internal node remains for the instrument forecast')
        for e in es:
            for terminal in ('a', 'b'):
                if e[terminal] == 'IN': e[terminal] = downstream
    es.append(dict(name=instrument_name, kind='R', a='IN', b=downstream, value=1000., model='none'))
    if len(es) > 6:
        raise ValueError('Instrument forecast exceeds the bounded simulator grammar')
    m['elements'] = es
    return m


def source_hashes():
    old = json.loads((ROOT/'examples/netlist-diagnosis-v2/2026-11-02/summary.json').read_text())['source_sha256']
    for name, expected in old.items():
        if hashlib.sha256((ROOT/name).read_bytes()).hexdigest() != expected:
            raise ValueError('Frozen v2 source changed: '+name)
    names = set(old) | {'src/benchmate/passive_pilot.py', 'src/benchmate/netlist_intake.py',
                         'scripts/passive_pilot.py'}
    return {name: hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in sorted(names)}


def prepare(design):
    design = checked(design)
    p = base_prepare(design)
    p.update(pilot=True, excluded_from_evaluation=True, pilot_runtime_version='passive-pilot-v1',
             pilot_source_sha256=source_hashes(), instrument=deepcopy(INSTRUMENT),
             amendment_sha256=hashlib.sha256((ROOT/'docs/2026-11-02-passive-pilot-amendment.md').read_bytes()).hexdigest())
    p['api_plan']['prompt'] = PROMPT
    return p


class Session(V2Session):
    def _predict(self, model, inp):
        if self.active:
            raise ValueError('LED needs its separately qualified DC path')
        return predict(command_model(model) if inp['source'] == 'command_input_only' else model, inp)

    def snapshot(self):
        return {**super().snapshot(), 'instrument': deepcopy(INSTRUMENT),
                'pilot': True, 'excluded_from_evaluation': True}
