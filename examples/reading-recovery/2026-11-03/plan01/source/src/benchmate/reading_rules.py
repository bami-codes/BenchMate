"""Source-aware operator readings. Pure standard library; no model or hardware.

An electrical value and a printed nominal value are different observables.
All intervals are conditional engineering allowances, never confidence claims.
"""
from copy import deepcopy
import hashlib
import math

from .records import canonical

VERSION = 'operator-reading-v1'
SOURCES = ('operator_dmm', 'operator_marking')
UNITS = {'ohm': ('ohm', 1.), 'kohm': ('ohm', 1000.), 'Mohm': ('ohm', 1e6),
         'F': ('F', 1.), 'uF': ('F', 1e-6), 'nF': ('F', 1e-9), 'pF': ('F', 1e-12)}


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def finite(value):
    return type(value) in (int, float) and math.isfinite(value)


def normalize(value, unit):
    if not finite(value) or value < 0 or unit not in UNITS:
        raise ValueError('Finite nonnegative numeric reading and supported unit required.')
    basis, scale = UNITS[unit]
    result = value * scale
    if not math.isfinite(result):
        raise ValueError('Reading conversion overflow.')
    return result, basis


def validate_forecast(value):
    required = {'schema', 'request', 'forecasts', 'catalog_sha256', 'rules_sha256',
                'observation_received', 'photo_received', 'scope'}
    if (not isinstance(value, dict) or set(value) != required
            or value['schema'] != VERSION or value['observation_received'] is not False
            or value['photo_received'] is not False):
        raise ValueError('Unread prospective forecast required.')
    request = value['request']
    if (set(request) != {'component', 'quantity', 'reason', 'chosen_by'}
            or request['chosen_by'] != 'muse_spark'
            or request['quantity'] not in ('resistance', 'capacitance')
            or not isinstance(request['reason'], str) or not request['reason'].strip()):
        raise ValueError('Spark must choose component and quantity before observation.')
    if not isinstance(value['forecasts'], list) or not value['forecasts']:
        raise ValueError('At least one explanation forecast required.')
    keys = set()
    for f in value['forecasts']:
        if set(f) != {'explanation', 'source', 'low', 'high', 'unit', 'rule', 'observable'}:
            raise ValueError('Unexpected forecast fields.')
        key = (f['explanation'], f['source'])
        if key in keys or f['source'] not in SOURCES:
            raise ValueError('Duplicate explanation/source or unsupported source.')
        keys.add(key)
        if (not isinstance(f['explanation'], str) or not f['explanation']
                or f['unit'] != ('ohm' if request['quantity'] == 'resistance' else 'F')
                or not finite(f['low']) or f['low'] < 0
                or (f['high'] is not None and (not finite(f['high']) or f['high'] < f['low']))
                or not isinstance(f['rule'], dict) or not isinstance(f['observable'], str)):
            raise ValueError('Invalid source-aware interval.')
    ids = {f['explanation'] for f in value['forecasts']}
    if any({source for identity, source in keys if identity == i} != set(SOURCES) for i in ids):
        raise ValueError('Every explanation needs forecasts for both allowed sources.')
    return deepcopy(value)


def make_forecast(request, catalog, rules):
    """Select a Spark-requested quantity, never a component selected by runner."""
    component = request['component']
    if component not in catalog['components']:
        raise ValueError('Requested component is absent from the reviewed design.')
    meta = catalog['components'][component]
    quantity = 'resistance' if meta['kind'] == 'R' else 'capacitance'
    if request['quantity'] != quantity:
        raise ValueError('Quantity does not match requested component.')
    unit = 'ohm' if quantity == 'resistance' else 'F'
    forecasts = []
    for explanation in catalog['explanations']:
        observation = explanation['components'][component]
        low, high = observation['electrical_interval']
        dmm = rules['dmm'][unit]
        ranges = []
        for meter_range, resolution in dmm['ranges']:
            absolute = dmm['digits_allowance'] * resolution
            ranges.append({'meter_range': meter_range, 'resolution': resolution,
                'low': max(0., low*(1-dmm['relative_allowance'])-absolute),
                'high': None if high is None else high*(1+dmm['relative_allowance'])+absolute})
        low = min(r['low'] for r in ranges)
        high = None if any(r['high'] is None for r in ranges) else max(r['high'] for r in ranges)
        forecasts.append(dict(explanation=explanation['id'], source='operator_dmm',
            low=low, high=high, unit=unit, observable='isolated electrical value',
            rule={'electrical_interval_rule': observation['interval_rule'],
                  'meter_allowance': dmm, 'intervals_by_meter_range': ranges,
                  'power_off': True, 'isolation_required': True,
                  'confidence_interval': False}))
        # A damaged part can keep ANY nominal label. Markings cannot reject
        # its actual-value-change explanation. No uncertainty tweak fixes that.
        nominal = observation['printed_nominal']
        tolerance = rules['nominal_tolerance_fraction']
        ml, mh = (0., None) if nominal is None else (nominal * (1-tolerance), nominal * (1+tolerance))
        forecasts.append(dict(explanation=explanation['id'], source='operator_marking',
            low=ml, high=mh, unit=unit, observable='printed nominal value, not electrical value',
            rule={'nominal_tolerance_fraction': tolerance,
                  'printed_value_unconstrained': nominal is None,
                  'actual_value_not_measured': True,
                  'why': 'Actual-value change can be damage or replacement; old label may remain.' if nominal is None else
                         'Unchanged intended component under this bounded explanation; nominal matching allowance only.'}))
    return validate_forecast({'schema': VERSION, 'request': request, 'forecasts': forecasts,
        'catalog_sha256': digest(catalog), 'rules_sha256': digest(rules),
        'observation_received': False, 'photo_received': False,
        'scope': 'Bounded explanations; engineering intervals, not probabilities or a universal diagnosis.'})


def score_reading(forecast, observed):
    f = validate_forecast(forecast)
    required = {'component', 'quantity', 'value', 'unit', 'source', 'photo',
                'power_off_confirmed', 'component_isolated_confirmed', 'meter_range', 'meter_resolution'}
    if not isinstance(observed, dict) or set(observed) != required:
        raise ValueError('Exact observation fields required; no explanation may be supplied.')
    if (observed['component'] != f['request']['component']
            or observed['quantity'] != f['request']['quantity'] or observed['source'] not in SOURCES):
        raise ValueError('Observation must answer the requested component and quantity.')
    if observed['source'] == 'operator_dmm' and (
            observed['power_off_confirmed'] is not True or observed['component_isolated_confirmed'] is not True):
        raise ValueError('DMM value needs power-off and component isolation confirmation.')
    photo = observed['photo']
    if (not isinstance(photo, dict) or set(photo) != {'file', 'sha256'}
            or not isinstance(photo['file'], str) or not photo['file']
            or not isinstance(photo['sha256'], str) or len(photo['sha256']) != 64
            or any(c not in '0123456789abcdef' for c in photo['sha256'])):
        raise ValueError('Evidence photo and SHA-256 required.')
    value, unit = normalize(observed['value'], observed['unit'])
    rows = [r for r in f['forecasts'] if r['source'] == observed['source']]
    if any(r['unit'] != unit for r in rows):
        raise ValueError('Reading unit has the wrong dimension.')
    intervals = rows
    if observed['source'] == 'operator_dmm':
        intervals = []
        for row in rows:
            if row['rule']['meter_allowance'].get('available') is not True:
                raise ValueError('This meter quantity is not qualified.')
            selected = next((r for r in row['rule']['intervals_by_meter_range']
                             if r['meter_range'] == observed['meter_range']), None)
            if selected is None or value >= selected['meter_range']:
                raise ValueError('Use a preregistered meter range; overrange is not a numeric reading.')
            if (not finite(observed['meter_resolution']) or observed['meter_resolution'] <= 0
                    or observed['meter_resolution'] > selected['resolution']):
                raise ValueError('Displayed meter resolution is coarser than the frozen allowance.')
            if abs(value/observed['meter_resolution'] - round(value/observed['meter_resolution'])) > 1e-7:
                raise ValueError('Reading precision exceeds the reported meter display resolution.')
            intervals.append({**row, **selected})
    elif observed['meter_range'] is not None or observed['meter_resolution'] is not None:
        raise ValueError('A marking observation has no meter range.')
    fits = [r['explanation'] for r in intervals if r['low'] <= value and (r['high'] is None or value <= r['high'])]
    return {'component': observed['component'], 'source': observed['source'],
            'normalized_value': value, 'unit': unit, 'fits': fits,
            'ruled_out_by_reading': [r['explanation'] for r in rows if r['explanation'] not in fits],
            'outcome': 'one_explanation_remains' if len(fits) == 1 else 'all_explanations_rejected' if not fits else 'indistinguishable',
            'forecast_sha256': digest(f), 'observation_sha256': digest(observed),
            'refitted': False, 'scope': f['scope']}
