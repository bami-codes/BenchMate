"""Explicitly reviewed R/C/D designs, including a visible ideal jumper.

No SPICE directives, file paths, hidden specimen labels or executable model text
are accepted from a model. A jumper is a fixed connection, not a fitted resistor.
"""
from copy import deepcopy
import hashlib
import math

from ..netlist import validate_netlist
from ..records import canonical

CONFIRMATION = 'I confirm the intended components, values, connections and ports.'


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def elements(value):
    if not isinstance(value, list) or not 1 <= len(value) <= 6:
        raise ValueError('An intended design needs 1–6 bounded elements.')
    wires = [e for e in value if isinstance(e, dict) and e.get('kind') == 'W']
    passive = [e for e in value if e not in wires]
    if passive:
        # A wire may complete the connectivity checked by the legacy validator.
        check = deepcopy(passive)
        for wire in wires:
            check.append(dict(name='Rwire' + str(len(check)), kind='R',
                              a=wire.get('a'), b=wire.get('b'), value=1000., model='none'))
        validate_netlist(check)
    elif not wires:
        raise ValueError('Empty circuit.')
    names = set()
    for e in value:
        if not isinstance(e, dict) or set(e) != {'name', 'kind', 'a', 'b', 'value', 'model'}:
            raise ValueError('Unexpected element fields.')
        if e['name'].lower() in names:
            raise ValueError('Duplicate element name.')
        names.add(e['name'].lower())
        if e['kind'] == 'W':
            if (e != dict(name='W1', kind='W', a='IN', b='OUT', value=0., model='none')
                    or len(wires) != 1):
                raise ValueError('Only the explicit fixed IN–OUT jumper W1 is supported.')
    if wires and any(e['a'] not in ('IN', 'OUT', 'REF') or e['b'] not in ('IN', 'OUT', 'REF') for e in value):
        raise ValueError('The explicit jumper adapter permits terminal branches only, no internal nodes.')
    return deepcopy(value)


def review(candidate, *, source_sha256, confirmation, note, simulated=False):
    """Local operator assertion. Does not make an image or electrical claim."""
    if confirmation != CONFIRMATION or not isinstance(note, str) or not note.strip():
        raise ValueError('Explicit intended-design confirmation and note required.')
    if (not isinstance(source_sha256, str) or len(source_sha256) != 64
            or any(c not in '0123456789abcdef' for c in source_sha256)):
        raise ValueError('The actual source image/reading SHA-256 is required.')
    return {'schema': 'benchmate.reviewed_netlist.v1', 'source_kind': 'intended_schematic',
            'elements': elements(candidate), 'source_sha256': source_sha256,
            'confirmation': confirmation, 'reviewer_note': note,
            'operator_review_simulated': bool(simulated), 'measurement_verified': False,
            'hardware_IO': False}


def from_transcription(result, *, source_sha256, confirmation, note):
    """Accept the existing Spark report_design output after human review."""
    if (result.get('source_kind') != 'intended_schematic'
            or result.get('status') != 'unverified_visual_candidate'):
        raise ValueError('A completed intended-schematic reading is required.')
    candidate = result['candidate']
    if candidate.get('status') != 'needs_review' or candidate.get('ambiguities'):
        raise ValueError('Resolve visual ambiguities before confirmation.')
    converted = []
    for c in candidate['components']:
        kind = c['kind']
        value = 0. if kind == 'D' else c['value_si']
        if kind != 'D' and (type(value) not in (int, float) or not math.isfinite(value)):
            raise ValueError('An intended component value is unresolved.')
        converted.append(dict(name=c['name'], kind=kind, a=c['a'], b=c['b'], value=value,
                              model='generic_diode' if kind == 'D' else 'none'))
    return review(converted, source_sha256=source_sha256, confirmation=confirmation, note=note)


def checked(value):
    required = {'schema', 'source_kind', 'elements', 'source_sha256', 'confirmation',
                'reviewer_note', 'operator_review_simulated', 'measurement_verified', 'hardware_IO'}
    if (not isinstance(value, dict) or set(value) != required
            or value['schema'] != 'benchmate.reviewed_netlist.v1'
            or value['source_kind'] != 'intended_schematic'
            or type(value['operator_review_simulated']) is not bool
            or value['measurement_verified'] is not False or value['hardware_IO'] is not False):
        raise ValueError('Explicit reviewed intended netlist required.')
    return review(value['elements'], source_sha256=value['source_sha256'],
                  confirmation=value['confirmation'], note=value['reviewer_note'],
                  simulated=value['operator_review_simulated'])
