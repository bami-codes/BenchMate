"""Offline, provisional three-point path calibration; never controls hardware."""
from pathlib import Path
import hashlib
import json
import numpy as np
from benchmate.records import Recorder, read_events

paths = [
    'runs/hardware-minima-dc-point/20261029T093232-05cacd76d7',
    'runs/hardware-minima-dc-point/20261029T092622-5bcb408c46',
    'runs/hardware-minima-dc-point/20261029T102615-1c03dab283',
]
log = Recorder('runs/hardware-minima-three-point-analysis', mode='offline_provisional_end_to_end_DC_calibration')
(log.path/'controller-source.py').write_bytes(Path(__file__).read_bytes())
data = []
for path in paths:
    events = read_events(path)
    assert events[-1]['kind'] == 'run_completed'
    report = next(e['payload'] for e in events if e['kind'] == 'operator_report')
    analysis = next(e['payload'] for e in events if e['kind'] == 'raw_point_analysis')
    assert analysis['samples_per_channel'] == 512 and analysis['overruns'] == 0
    capture = read_events(analysis['raw_capture_record'])
    raw = next(e['payload'] for e in capture if e['kind'] == 'raw_capture')
    rows = np.asarray(raw['rows'])
    data.append((report, analysis, rows))
    log.add('input_record', {'point': report['point'], 'record': path,
                            'events_sha256': hashlib.sha256((Path(path)/'events.jsonl').read_bytes()).hexdigest(),
                            'boot_id': analysis['boot_id'],
                            'signal_reference_v': report['end_to_end_calibration_method']['common_signal_reference_v'],
                            'REF_DMM_v': report['dmm_nodes_v'][3],
                            'high_voltage_derived': 'derived_D45' in report})
y = np.array([r['end_to_end_calibration_method']['common_signal_reference_v'] for r,a,rows in data])
assert np.all(np.diff(y) > 0)
channels = {}
for i, name in enumerate(['A1', 'A2', 'A3']):
    x = np.array([a['channels'][name]['mean_counts'] for r,a,rows in data])
    gain, offset = np.linalg.lstsq(np.column_stack([x, np.ones(3)]), y, rcond=None)[0]
    assert gain > 0
    residual = gain*x+offset-y
    endpoint_mid = y[0] + (x[1]-x[0])/(x[2]-x[0])*(y[2]-y[0]) - y[1]
    noise = []
    for report, analysis, rows in data:
        samples = rows[:, i+2].astype(float)*gain+offset
        centered = samples - samples.mean()
        rho = float(np.dot(centered[:-1], centered[1:])/np.dot(centered[:-1], centered[:-1]))
        noise.append({'point': report['point'], 'sample_sd_mV': float(samples.std(ddof=1)*1000),
                      'lag1_least_squares_rho_descriptive': rho,
                      'max_absolute_deviation_mV': float(np.max(np.abs(centered))*1000),
                      'samples_trimmed': 0})
    channels[name] = {'gain_v_per_count': float(gain), 'offset_v': float(offset),
                      'mean_counts_low_mid_high': x.tolist(),
                      'fit_residual_mV_low_mid_high': (residual*1000).tolist(),
                      'max_abs_fit_residual_mV': float(np.max(np.abs(residual))*1000),
                      'midpoint_error_using_endpoints_only_mV': float(endpoint_mid*1000),
                      'noise_diagnostics': noise,
                      'scope': 'Input-to-buffer-to-ADC path referred to OUT' if name=='A2' else 'Common fixture signal to ADC path'}
nominal_gain = 4.88/16383
ref_y = np.array([r['dmm_nodes_v'][3] for r,a,rows in data])
ref_x = np.array([a['channels']['A4']['mean_counts'] for r,a,rows in data])
needed_offsets = ref_y - nominal_gain*ref_x
offset = float(needed_offsets.mean())
ref_residual = nominal_gain*ref_x+offset-ref_y
codes = np.array([a['held_code_before_capture'] for r,a,rows in data])
dac_gain, dac_offset = np.linalg.lstsq(np.column_stack([codes,np.ones(3)]), y, rcond=None)[0]
old_mid = data[1][1]
recovery = 'runs/hardware-minima-high-recovery/20261029T102344-1f1ac62ab2'
new_mid = next(e['payload'] for e in read_events(recovery) if e['kind']=='midpoint_gross_check_analysis')
profile = {
    'status': 'provisional_DC_coefficients_not_full_D2_acceptance',
    'instrument_serial': '3612211F36323632E4B233334B572F52',
    'nominal_supply_conversion_v': 4.88,
    'fixture': '100.8 kohm B13–E16; A4 direct REF jumper; shunt bypass and IN–OUT bridge; no DUT',
    'reference_values_v_low_mid_high': y.tolist(), 'fit': 'Unweighted affine least squares on three block means; no uncertainty weights inferred',
    'formula': 'volts = gain_v_per_count * raw_count + offset_v',
    'channels': channels,
    'A4_fixed_REF_only': {'gain_v_per_count_assumed': nominal_gain, 'candidate_offset_v': offset,
                          'required_offsets_mV_low_mid_high': (needed_offsets*1000).tolist(),
                          'candidate_offset_residual_mV_low_mid_high': (ref_residual*1000).tolist(),
                          'max_abs_candidate_residual_mV': float(np.max(np.abs(ref_residual))*1000),
                          'gain_calibrated': False, 'do_not_extrapolate_outside_REF_neighborhood': True},
    'DAC_to_driver_path': {'gain_v_per_code': float(dac_gain), 'offset_v': float(dac_offset),
                           'codes_low_mid_high': codes.tolist(),
                           'max_abs_fit_residual_mV': float(np.max(np.abs(dac_gain*codes+dac_offset-y))*1000),
                           'applied_to_firmware_or_stimulus_limits': False},
    'reset_boundary': {'low_mid_boot': data[0][1]['boot_id'], 'high_boot': data[2][1]['boot_id'],
                       'manual_RESET_with_USB_and_wiring_retained': True,
                       'same_REF_code_mean_count_change': {k: new_mid['channels'][k]['mean_counts']-old_mid['channels'][k]['mean_counts'] for k in ['A1','A2','A3','A4']},
                       'new_physical_midpoint_DMM_not_supplied': True,
                       'scope': 'Explicitly combine unchanged-fixture points across a reset for provisional fit; not a single-boot run.'},
    'validation': {'independent_condition_test_completed': False, 'dynamic_fixture_test_completed': False,
                   'full_D2_calibration_accepted': False, 'hardware_inference_enabled': False},
    'limits': ['DMM accuracy is unknown; 1 mV display increments are not a 1 mV accuracy claim.',
               'High D45 combines REF and differential displays with shared reference error and unknown drift.',
               'DMM and ADC are sequential; supplied values have no exact measurement timestamps.',
               'Three fitted points and the endpoint midpoint diagnostic are not independent validation.',
               'A2 includes its buffer, so these coefficients are not ADC-only calibration.',
               'A4 is observed only near fixed REF; its gain is not calibrated and variation is retained.',
               'Descriptive lag-1 coefficients do not establish an adequate AR(1) noise model.',
               'Raw tails are retained; no samples were trimmed and no SD/sqrt(N) accuracy claim is made.',
               'USB reliability and the physical cause of earlier failures remain unestablished.'],
}
(log.path/'provisional-calibration.json').write_text(json.dumps(profile,indent=2)+'\n')
log.add('provisional_calibration_computed', profile)
log.add('run_completed', {'hardware_IO': False, 'profile': 'provisional-calibration.json',
                          'three_DC_points_available': True, 'full_D2_calibration_accepted': False,
                          'hardware_inference_enabled': False})
print(json.dumps({'record':str(log.path),'max_path_fit_residual_mV':max(x['max_abs_fit_residual_mV'] for x in channels.values()),
                  'A4_max_candidate_residual_mV':profile['A4_fixed_REF_only']['max_abs_candidate_residual_mV']}))
