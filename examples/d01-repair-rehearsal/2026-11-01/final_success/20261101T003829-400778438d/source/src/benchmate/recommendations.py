"""Fixture-checked future measurements; rationale never supplies settings."""
from .menu import mounting_instruction

UNAVAILABLE = {
    'adjustable_reference': 'an adjustable, calibrated reference source; the fixture REF is fixed near 1.6 V',
    'temperature_control': 'a temperature-controlled fixture and calibrated temperature sensing',
    'extended_waveform': 'a waveform source and acquisition path validated beyond the configured menu',
}

NEXT_PROMPT = """
For next_observation, return a structured choice, never free-text instructions.
Use kind=menu_action, an exact action ID from the configured menu, requirement="",
and a short reason explaining the scientific question. Settings come only from
that action. REF is fixed near 1.6 V, not software-adjustable. For an experiment
outside current capabilities use kind=unavailable, action="", and a declared
requirement ID. This records a missing capability, never permission to execute.
The reason is commentary only: do not introduce different settings there.
This is a suggestion for a future run, not an additional acquisition in this run.
Menu membership does not establish hardware calibration or scientific usefulness.
"""


def next_schema(menu):
    properties = {
        'kind': {'type': 'string', 'enum': ['menu_action', 'unavailable']},
        'action': {'type': 'string', 'enum': ['', *menu]},
        'requirement': {'type': 'string', 'enum': ['', *UNAVAILABLE]},
        'reason': {'type': 'string'},
    }
    return {'type': 'object', 'properties': properties, 'required': list(properties),
            'additionalProperties': False}


def recommendation_context():
    return {'reference': 'Fixed fixture REF, nominal 1.6 V; no software adjustment.',
            'hardware_calibrated': False, 'menu_scope': 'Configured synthetic menu; physical limits freeze after D2.',
            'next_measurement_scope': 'Future run only; no acquisition or budget extension.',
            'unavailable_requirements': UNAVAILABLE}


def validate_next(value, menu):
    if not isinstance(value, dict) or set(value) != {'kind', 'action', 'requirement', 'reason'}:
        raise ValueError('next_observation must select a menu action or declared unavailable requirement')
    if any(not isinstance(v, str) for v in value.values()) or not 1 <= len(value['reason'].strip()) <= 320:
        raise ValueError('Provide a short rationale of 1–320 characters')
    kind, action, requirement = value['kind'], value['action'], value['requirement']
    common = {**value, 'checked_by': 'engine', 'execution': 'not_scheduled', 'hardware_calibrated': False}
    if kind == 'unavailable' and action == '' and requirement in UNAVAILABLE:
        return {**common, 'status': 'unavailable',
                'instruction': 'Unavailable with this fixture: requires ' + UNAVAILABLE[requirement] + '.'}
    if kind != 'menu_action' or action not in menu or requirement != '':
        raise ValueError('Choose an exact configured action, or an unavailable requirement; no custom settings')
    s = menu[action]
    if s.ref_v != 1.6:
        raise ValueError('Configured action attempts to change the fixed fixture REF')
    waveform = (f'{s.frequency_hz:g} Hz sine, ±{s.amplitude_v:g} V' if s.kind == 'sine' else
                f'DC pair, ±{s.amplitude_v:g} V' if s.kind == 'dc_pair' else f'Step, ±{s.amplitude_v:g} V')
    load = f'{s.load_ohm/1000:g} kΩ load' if s.load_ohm else 'no load'
    series = '1 kΩ shunt' if s.shunt_ohm else '0 Ω jumper'
    return {**common, 'status': 'menu_checked', 'settings': s.to_dict(),
            'physical_acquisitions_if_run': s.physical_acquisitions,
            'instruction': f'{waveform} at fixed REF (~1.6 V), with {load} and the {series}.',
            'connections': mounting_instruction(s)}
