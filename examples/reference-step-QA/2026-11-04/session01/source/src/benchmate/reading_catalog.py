"""Training-only interval profiles and terminal-equivalent localization candidates.

The catalog is hypothesis generation, not selection of an operator reading.
Spark selects the component/quantity. No photograph, operator value or truth is
accepted here. Reserved OUT can validate the algebraic equivalent, never fit it.
"""
from copy import deepcopy
import numpy as np

from .netlist_diagnosis.models import predict, score


def profile(row, component, captures, nominal_tolerance):
    element = next(e for e in row['model']['elements'] if e['name'] == component)
    if row.get('changed_component') != component:
        v = element['value']
        return [v*(1-nominal_tolerance), v*(1+nominal_tolerance)], {'kind': 'unchanged_design_tolerance', 'fraction': nominal_tolerance}
    bounds = (1000., 100000.) if element['kind'] == 'R' else (1e-9, 1e-5)
    grid = sorted(set(np.geomspace(*bounds, 33).tolist() + [element['value']]))
    passing = []
    for v in grid:
        m = deepcopy(row['model'])
        next(e for e in m['elements'] if e['name'] == component)['value'] = v
        passing.append(all(score(c, predict(m, c['input_template']))['passed'] for c in captures))
    hits = [i for i, ok in enumerate(passing) if ok]
    if not hits:
        raise ValueError('Training profile does not contain its fitted model.')
    first, last = min(hits), max(hits)
    # Include adjacent rejected grid points as conservative numerical brackets.
    interval = [0. if first == 0 else grid[first-1], None if last == len(grid)-1 else grid[last+1]]
    return interval, {'kind': 'training_only_bounded_grid_envelope', 'grid': grid,
        'passed': passing, 'whole_and_region_limit_mV': 9., 'reserved_OUT_used': 0,
        'other_parameters_held_fixed': True, 'statistical_confidence_interval': False,
        'disjoint_regions_enclosed': any(not x for x in passing[first:last+1]),
        'boundary_pass_uses_open_end': first == 0 or last == len(grid)-1}


def build_catalog(design, frozen, verification, captures, *, nominal_tolerance=.05):
    if not verification or not verification['survivors']:
        raise ValueError('Verified surviving explanations required before reading selection.')
    if not captures or any(c['purpose'] != 'training' for c in captures):
        raise ValueError('Only training observations may determine reading intervals.')
    components = {e['name']: deepcopy(e) for e in design['elements'] if e['kind'] in ('R', 'C')}
    rows = [r for r in frozen['models'] if r['id'] in verification['survivors']]
    explanations = []
    for row in rows:
        es = {e['name']: e for e in row['model']['elements']}
        if not set(components) <= set(es):
            raise ValueError('A proposed structure omitted an intended component.')
        observed = {}
        for name, intended in components.items():
            interval, rule = profile(row, name, captures, nominal_tolerance)
            changed = row.get('changed_component') == name
            observed[name] = {'electrical_interval': interval, 'interval_rule': rule,
                'printed_nominal': None if changed else intended['value']}
        explanations.append({'id': row['id'], 'basis_model_id': row['id'],
            'description': 'Actual component value changed; damage and replacement are not distinguished.' if row.get('changed_component') else
                           'Verified terminal model; physical uniqueness is not established.',
            'components': observed, 'model': deepcopy(row['model'])})
        # Exact series/parallel identities expose the existing location ambiguity.
        # They are generated for every suitable intended R/C, not by case label.
        changed = row.get('changed_component')
        if changed not in components:
            continue
        intended, actual = components[changed], es[changed]
        extra = actual['value'] - intended['value']
        if extra <= 0:
            continue
        model = deepcopy(row['model']); used = {e[n] for e in model['elements'] for n in ('a', 'b')}
        node = next((n for n in ('N1', 'N2') if n not in used), None)
        names = {e['name'] for e in model['elements']}
        added_name = next((intended['kind']+'x'+str(i) for i in range(9) if intended['kind']+'x'+str(i) not in names), None)
        if len(model['elements']) >= 6 or not added_name:
            continue
        target = next(e for e in model['elements'] if e['name'] == changed)
        target['value'] = intended['value']
        if intended['kind'] == 'R':
            if node is None or extra < 1000:
                continue
            original = target['a']; target['a'] = node
            added = dict(name=added_name, kind='R', a=original, b=node, value=extra, model='none')
            placement = 'series resistance outside the photographed board'
        else:
            if extra < 1e-9:
                continue
            added = dict(name=added_name, kind='C', a=target['a'], b=target['b'], value=extra, model='none')
            placement = 'parallel capacitance outside the photographed board'
        model['elements'].append(added)
        differences = [float(np.max(np.abs(np.asarray(predict(model, c['input_template'])) -
                                         np.asarray(predict(row['model'], c['input_template']))))) for c in captures]
        if max(differences) > .0001:
            continue
        alternative = deepcopy(observed)
        alternative[changed] = {'electrical_interval': [intended['value']*(1-nominal_tolerance), intended['value']*(1+nominal_tolerance)],
            'interval_rule': {'kind': 'unchanged_design_tolerance', 'fraction': nominal_tolerance},
            'printed_nominal': intended['value']}
        explanations.append({'id': 'external_equivalent:'+row['id'], 'basis_model_id': row['id'],
            'description': 'Intended component unchanged plus '+placement+'. This is an explanation, not observed truth.',
            'components': alternative, 'model': model,
            'equivalence': {'algebra': 'series_sum' if intended['kind'] == 'R' else 'parallel_sum',
                            'training_max_difference_v': max(differences), 'new_parameters_fitted': 0}})
    return {'schema': 'benchmate.reading_catalog.v1', 'components': components,
            'explanations': explanations, 'training_only_intervals': True,
            'terminal_verification_sha256': verification['frozen_sha256'],
            'photograph_received': False, 'operator_reading_received': False,
            'scope': 'Bounded single-value and exact-equivalent explanations; no claim of exhaustive physical causes.'}
