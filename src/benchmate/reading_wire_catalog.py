"""Training-only localization alternatives for a replaced ideal IN-OUT wire.

The terminal model identifies a series path, not its physical location. This
adapter adds explicit bounded on-board versus external path explanations for
an isolated resistance reading; it never selects that reading for Spark.
"""
from copy import deepcopy

from .reading_rules import digest

LOW_PATH_MAX_OHM = 10.


def series_part(design, model):
    wires = [e for e in design['elements'] if e['kind'] == 'W']
    if len(wires) != 1 or set((wires[0]['a'], wires[0]['b'])) != {'IN', 'OUT'}:
        return None
    intended = {e['name']: e for e in design['elements'] if e['kind'] != 'W'}
    actual = {e['name']: e for e in model['elements']}
    if not intended.keys() <= actual.keys():
        return None
    for name, before in intended.items():
        after = actual[name]
        if (any(before[k] != after[k] for k in ('kind', 'value', 'model'))
                or {before['a'], before['b']} != {after['a'], after['b']}):
            return None
    added = [e for e in model['elements'] if e['name'] not in intended]
    if (len(added) != 1 or added[0]['kind'] != 'R'
            or {added[0]['a'], added[0]['b']} != {'IN', 'OUT'}):
        return None
    return added[0]['name']


def extend(catalog, design, frozen, verification, captures):
    if not captures or any(c['purpose'] != 'training' for c in captures):
        raise ValueError('Only training captures may determine W1 reading intervals.')
    if not verification or not verification['survivors']:
        raise ValueError('Reserved-validated terminal model required.')
    rows = [r for r in frozen['models'] if r['id'] in verification['survivors']]
    if not rows or any(series_part(design, r['model']) is None for r in rows):
        return None
    from .reading_catalog import profile
    wire = next(e for e in design['elements'] if e['kind'] == 'W')
    output = deepcopy(catalog)
    output.update(schema='benchmate.wire_localization_catalog.v1',
                  parent_catalog_sha256=digest(catalog), design_sha256=digest(design),
                  wire=wire['name'], low_path_max_ohm=LOW_PATH_MAX_OHM,
                  observable='isolated power-off mini-board IN-OUT path resistance with W1 and its contacts retained',
                  wire_reading_setup={'isolation': 'Disconnect all three mini-board leads from the large fixture, keep their mini-board ends installed.',
                      'DMM_terminals': 'Free metal ends of the disconnected IN and OUT leads.',
                      'W1_installed': True, 'parallel_R_C_installed': True,
                      'REF_lead': 'Disconnected from the large fixture and left floating.',
                      'no_alternate_IN_OUT_path': 'IN has only W1; the parallel OUT-REF branches end at the floating REF port.',
                      'included_contacts': 'Mini-board wire, sockets and IN/OUT leads retained in the measured path.',
                      'USB_off': True, 'discharge_wait_s': 10},
                  terminal_location_identified=False, reserved_OUT_used_for_intervals=0)
    # R is the numeric measurement dimension for the existing source-aware
    # forecast engine. physical_kind remains W; no resistor is added to design.
    output['components'][wire['name']] = {**deepcopy(wire), 'kind': 'R', 'physical_kind': 'W',
        'numeric_observable_adapter': 'wire_path_resistance_ohm', 'value': 0.}
    explanations = []
    for row in rows:
        added = series_part(design, row['model'])
        numeric_row = {**row, 'changed_component': added}
        interval, rule = profile(numeric_row, added, captures, .05)
        base = next(e for e in catalog['explanations'] if e['id'] == row['id'])
        for placement in ('on_board_path', 'external_path'):
            e = deepcopy(base)
            e.update(id=placement + ':' + row['id'], basis_model_id=row['id'],
                description=('The isolated mini-board IN-OUT path, including W1 and its contacts, accounts for the fitted resistance.'
                             if placement == 'on_board_path' else
                             'The isolated mini-board IN-OUT path is near-short; the fitted resistance is external.'),
                location_hypothesis=True,
                equivalence={'algebra': 'R_series_total = R_board_path + R_external',
                             'shared_terminal_model': True, 'new_parameters_fitted': 0,
                             'physical_location_not_observed': True})
            e['components'][wire['name']] = {
                'electrical_interval': interval if placement == 'on_board_path' else [0., LOW_PATH_MAX_OHM],
                'interval_rule': rule if placement == 'on_board_path' else {
                    'kind': 'declared_near_short_path_engineering_category',
                    'low_ohm': 0., 'high_ohm': LOW_PATH_MAX_OHM,
                    'not_a_beeper_threshold': True, 'not_exact_zero_proof': True},
                'printed_nominal': None}
            explanations.append(e)
    output['explanations'] = explanations
    output['scope'] = ('Bounded physical placements of the same validated terminal series path. '
        'W1 <=10ohm is a predeclared near-short category, not exact zero or meter calibration. '
        'The wire and external contributions may coexist outside these alternatives; a reading can reject both. '
        'A printed wire marking is unconstrained and cannot localize resistance.')
    return output
