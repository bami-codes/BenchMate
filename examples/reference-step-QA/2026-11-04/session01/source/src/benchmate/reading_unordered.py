"""Compare an unordered set without nearest-value labels or refitting.

Pure standard library. Bounds are supplied by a separately frozen forecast,
with meter allowances already included. This matcher cannot qualify a meter or
authorize a reading, and it never scores a printed label as electrical data.
"""
from itertools import permutations
import math


def _number(value):
    return type(value) in (float, int) and math.isfinite(value) and value >= 0


def compare_unordered(body_values, explanations):
    """Retain every bijection whose body values lie in all component intervals.

    Explanation: {id, role: active|reference, intervals: {component: [low, high]}}.
    A reference is never promoted to a survivor. Values and bounds must already
    describe the same observable and SI unit. high=None is an open upper bound.
    """
    if (not isinstance(body_values, dict) or not 1 <= len(body_values) <= 6
            or any(not isinstance(k, str) or not k or not _number(v) for k, v in body_values.items())):
        raise ValueError('One finite nonnegative value per retained body required (maximum six).')
    if not isinstance(explanations, list) or not explanations:
        raise ValueError('Frozen explanation intervals required.')
    seen = set()
    rows = []
    for e in explanations:
        if (not isinstance(e, dict) or set(e) != {'id', 'role', 'intervals'}
                or not isinstance(e['id'], str) or not e['id'] or e['id'] in seen
                or e['role'] not in ('active', 'reference')
                or not isinstance(e['intervals'], dict) or len(e['intervals']) != len(body_values)):
            raise ValueError('Unique explanations with exact group-sized intervals required.')
        seen.add(e['id'])
        for name, interval in e['intervals'].items():
            if (not isinstance(name, str) or not name or not isinstance(interval, list)
                    or len(interval) != 2 or not _number(interval[0])
                    or (interval[1] is not None and (not _number(interval[1]) or interval[1] < interval[0]))):
                raise ValueError('Finite lower bound and ordered finite/open upper bound required.')
        components = sorted(e['intervals'])
        matches = []
        for bodies in permutations(sorted(body_values)):
            if all(e['intervals'][c][0] <= body_values[b]
                   and (e['intervals'][c][1] is None or body_values[b] <= e['intervals'][c][1])
                   for c, b in zip(components, bodies)):
                matches.append(dict(zip(components, bodies)))
        rows.append({'explanation': e['id'], 'role': e['role'], 'assignments': matches})
    if not any(r['role'] == 'active' for r in rows):
        raise ValueError('At least one active explanation required; references cannot be survivors.')
    active = [r for r in rows if r['role'] == 'active' and r['assignments']]
    unique = active[0]['assignments'][0] if len(active) == 1 and len(active[0]['assignments']) == 1 else None
    return {'fits': [r['explanation'] for r in active],
            'ruled_out_by_reading': [r['explanation'] for r in rows if r['role'] == 'active' and not r['assignments']],
            'reference_fits': [r['explanation'] for r in rows if r['role'] == 'reference' and r['assignments']],
            'matches': rows, 'conditional_unique_binding': unique,
            'outcome': 'all_explanations_rejected' if not active else
                       'one_explanation_remains' if len(active) == 1 else 'indistinguishable',
            'body_identity_status': 'unique_under_surviving_forecast' if unique else 'unresolved',
            'nearest_value_assignment': False, 'refitted': False}
