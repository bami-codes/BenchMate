"""One known-passive loaded B1 check: frozen forecast, fresh boot, REF, small step.

This is the documented USB-off-wired passive RC exception, not the general
DUT connection workflow. The frozen prediction explicitly uses the known assembly resistance.
"""
from dataclasses import asdict
from pathlib import Path
import hashlib
import json
import time
import numpy as np
import serial
from serial.tools import list_ports
from benchmate.records import Recorder, read_events
from benchmate.instrument import (
    BootContinuity, InstrumentConfig, capture_command, receive_response,
    validate_block,
)


def main():
    prediction_path = Path('runs/hardware-b1-loaded-prediction/20261029T122903-49389477e9/prediction.json')
    freeze_events = read_events(prediction_path.parent)
    assert freeze_events[-1]['kind'] == 'run_completed'
    freeze = next(e['payload'] for e in freeze_events if e['kind'] == 'prediction_frozen')
    assert hashlib.sha256(prediction_path.read_bytes()).hexdigest() == freeze['sha256']
    prediction = json.loads(prediction_path.read_text())
    previous_boot = prediction['previous_boot_id']
    config = InstrumentConfig(**prediction['configuration'])
    profile = Path('examples/hardware-fixture-bringup/2026-10-29-followup/minima-three-point-analysis/provisional-calibration.json')
    log = Recorder('runs/hardware-b1-loaded-step', mode='known_passive_loaded_RC_frozen_prediction_check')
    for source, name in [
        (Path(__file__), 'controller-source.py'),
        (prediction_path, 'prediction.json'),
        (Path('src/benchmate/instrument.py'), 'host-instrument.py'),
        (profile, 'provisional-calibration.json'),
        (Path('docs/b1-assembly.md'), 'assembly-guide.md'),
    ]:
        (log.path / name).write_bytes(source.read_bytes())
    log.add('operator_power_report', {
        'verbatim': prediction['operator_power_report'], 'supply_v': 4.87, 'REF_v': 1.627,
        'requested_ranges': {'supply': 'DC 20 V', 'REF': 'DC 2 V'},
        'load_hookup_record': prediction['hookup_record'],
        'load': 'D55-D60 9.99 kohm; OUT E30-A55; REF C23-A60 through jumper 14',
        'jumper14_and_existing_B1_retained_per_instruction': True,
        'USB_reconnected_after_unpowered_load_installation': True,
        'spare_0_998uF_capacitor_not_installed_per_instruction': True,
    })
    log.add('frozen_prediction_reference', {
        'source': str(prediction_path), 'sha256': freeze['sha256'],
        'known_series_resistance_used': True, 'no_loaded_refit_for_prediction_score': True,
        'limits': prediction['engineering_limits'],
        'ADC_affine_maps_scaled_by_reported_supply_ratio': prediction['voltage_conversion']['reported_supply_ratio'],
        'REF_guard_cannot_change_prediction': True,
    })
    log.add('predeclared_configuration', {
        'configuration': asdict(config), 'previous_boot_id': previous_boot,
        'known_passive_RC_only_startup_exception': True,
        'startup_and_ARM_ramp_excluded_from_experiment_data': True,
        'startup_may_be_outside_REF_plus_minus_1V': True,
        'unknown_active_external_power_or_holdout_not_authorized_by_this_exception': True,
        'REF_guard_block': {'samples': 512, 'period_us': 2000},
        'step': {'samples': 512, 'period_us': 500, 'amplitude_v': 0.2,
                 'nominal_transition_v': 0.4, 'sample_rate_previously_passed_one_B1_step': True},
        'REF_guard_limits': {'mean_delta_from_REF_v': 0.100,
                             'any_sample_delta_from_REF_v': 0.150,
                             'mean_channel_spread_v': 0.050,
                             'raw_rails_exclusive': [16, 16367]},
        'step_guard_limits': {'all_signal_samples_within_REF_v': 0.350,
                              'all_A4_samples_within_REF_v': 0.150,
                              'raw_rails_exclusive': [16, 16367]},
        'voltage_guards_use_nominal_counts_not_final_calibration': True,
        'provisional_profile_sha256': hashlib.sha256(profile.read_bytes()).hexdigest(),
        'firmware_source_sha256': hashlib.sha256(Path('firmware/instrument/instrument.ino').read_bytes()).hexdigest(),
        'single_serial_connection': True, 'automatic_retry_or_rearm': False,
        'firmware_upload_requested': False, 'hardware_diagnosis_enabled': False,
        'component_truth_used_by_frozen_prediction': True,
        'blind_diagnosis': False,
    })
    print(json.dumps({'record': str(log.path), 'stage': 'preflight'}), flush=True)
    guard = BootContinuity()
    stage = 'preflight'

    def check_ping(packet, *, armed):
        guard.check(packet)
        expected = config.ref_code if armed else 0
        if (packet.get('type') != 'pong' or packet.get('armed') is not armed
                or packet.get('dc_hold_supported') is not True
                or packet.get('adc_sample_state_channels') != [0, 1, 2, 21]
                or packet.get('adc_sample_states_readback') != [255] * 4
                or packet.get('current_code') != expected
                or packet.get('ref_code') != expected
                or (armed and packet.get('max_jump_code') != config.max_jump)):
            raise ValueError('Unexpected firmware, ADC sampling state or held output')

    def command(board, request, kind, timeout):
        log.add('serial_command', {'request': request.decode().strip()})
        board.timeout = timeout
        if board.write(request) != len(request):
            raise RuntimeError('Incomplete serial write; no retry')
        return receive_response(board, log, kind)

    def capture(board, kind, **kwargs):
        request = capture_command(config, boot_id=guard.boot_id, kind=kind, **kwargs)
        block = command(board, request, kind + '_raw_capture', 30)
        guard.check(block)
        validate_block(block, expected_command=request)
        if block.get('parked_ref_code') != config.ref_code:
            raise ValueError('Capture did not report REF parking')
        check_ping(command(board, b'PING\n', kind + '_postcheck', 5), armed=True)
        return block

    def describe(block):
        rows = np.asarray(block['rows'], dtype=np.int64)
        counts = rows[:, 2:6]
        volts = counts * config.vref_v / 16383
        summary = {
            'samples': len(rows), 'overruns': block['overruns'],
            'frame_interval_us_min': int(np.diff(rows[:, 0]).min()),
            'frame_interval_us_max': int(np.diff(rows[:, 0]).max()),
            'channel_read_completion_offset_us_min': rows[:, 6:10].min(axis=0).tolist(),
            'channel_read_completion_offset_us_max': rows[:, 6:10].max(axis=0).tolist(),
            'channels': {name: {'mean_counts': float(counts[:, i].mean()),
                                'min_counts': int(counts[:, i].min()),
                                'max_counts': int(counts[:, i].max()),
                                'nominal_mean_v': float(volts[:, i].mean())}
                         for i, name in enumerate(block['channels'])},
        }
        return counts, volts, summary

    try:
        ports = [p for p in list_ports.comports() if (p.vid, p.pid, p.serial_number) ==
                 (9025, 105, '3612211F36323632E4B233334B572F52')]
        log.add('USB_preflight', {'matching_ports': [p.device for p in ports]})
        if len(ports) != 1:
            raise RuntimeError('Expected Minima absent or ambiguous')
        with serial.Serial(ports[0].device, 115200, timeout=5, write_timeout=2) as board:
            time.sleep(2)
            board.reset_input_buffer()
            stage = 'startup_PING'
            check_ping(command(board, b'PING\n', stage, 5), armed=False)
            if guard.boot_id == previous_boot:
                raise ValueError('Fresh boot not established after USB-off hookup')
            print(json.dumps({'stage': 'fresh_unarmed_boot_verified', 'boot_id': guard.boot_id}), flush=True)
            stage = 'explicit_REF_ARM'
            arm = command(board, config.arm_command(guard.boot_id), 'ARM_response', 15)
            guard.check(arm)
            if arm.get('type') != 'armed':
                raise ValueError('ARM not acknowledged')
            check_ping(command(board, b'PING\n', 'post_ARM_PING', 5), armed=True)
            stage = 'REF_capture_and_guard'
            block = capture(board, 'hold', hold_v=config.ref_v, samples=512, period_us=2000)
            counts, volts, ref_summary = describe(block)
            means = volts.mean(axis=0)
            checks = {
                'raw_not_at_rails': bool(((counts > 16) & (counts < 16367)).all()),
                'means_near_REF': bool((np.abs(means - config.ref_v) <= .100).all()),
                'all_samples_near_REF': bool((np.abs(volts - config.ref_v) <= .150).all()),
                'channel_mean_spread': bool(np.ptp(means) <= .050),
            }
            log.add('REF_guard_result', {'summary': ref_summary, 'checks': checks})
            if not all(checks.values()):
                raise ValueError('REF guard failed; no step stimulus sent')
            print(json.dumps({'stage': 'REF_guard_passed', 'nominal_means_v': means.tolist()}), flush=True)
            stage = 'small_step_capture_and_guard'
            step = capture(board, 'step', amplitude_v=.2, samples=512, period_us=500)
            counts, volts, step_summary = describe(step)
            checks = {
                'raw_not_at_rails': bool(((counts > 16) & (counts < 16367)).all()),
                'signal_envelope': bool((np.abs(volts[:, :3] - config.ref_v) <= .350).all()),
                'REF_envelope': bool((np.abs(volts[:, 3] - config.ref_v) <= .150).all()),
            }
            log.add('step_guard_result', {'summary': step_summary, 'checks': checks})
            if not all(checks.values()):
                raise ValueError('Step wiring/saturation guard failed; no response fit accepted')
            stage = 'frozen_loaded_prediction_comparison'
            rows = np.asarray(step['rows'])
            coeff = prediction['voltage_conversion']['channels']['A2']
            observed = rows[:, 3]*coeff['gain_v_per_count']+coeff['offset_v']
            forecast = np.asarray(prediction['predicted_A2_v'])
            residual = observed-forecast
            t = np.asarray(prediction['nominal_A2_step_relative_time_s'])
            regional = []
            for name, low_ms, high_ms in prediction['regions_ms']:
                mask = np.ones(len(t), dtype=bool)
                if low_ms is not None: mask &= t >= low_ms/1000
                if high_ms is not None: mask &= t < high_ms/1000
                regional.append({'region': name, 'samples': int(mask.sum()),
                    'RMS_mV': float(np.sqrt(np.mean(residual[mask]**2))*1000),
                    'max_abs_mV': float(np.max(abs(residual[mask]))*1000)})
            rms = float(np.sqrt(np.mean(residual**2))*1000)
            actual_t = (rows[:, 0]+rows[:, 7])*1e-6
            time_error = float(np.max(abs(actual_t-np.asarray(prediction['nominal_A2_time_s'])))*1e6)
            code_error = int(np.max(abs(rows[:, 1]-np.asarray(prediction['expected_DAC_codes']))))
            limits = prediction['engineering_limits']
            prediction_checks = {
                'whole_trace_RMS': rms <= limits['whole_trace_RMS_mV_max'],
                'all_regional_RMS': all(x['RMS_mV'] <= limits['each_region_RMS_mV_max'] for x in regional),
                'prediction_timing': time_error <= limits['max_prediction_time_error_us'],
                'DAC_codes_match': code_error <= limits['DAC_code_error_max'],
            }
            comparison = {
                'prediction_sha256': freeze['sha256'], 'RMS_mV': rms,
                'mean_residual_mV': float(np.mean(residual)*1000),
                'max_absolute_residual_mV': float(np.max(abs(residual))*1000),
                'regions': regional, 'max_prediction_time_error_us': time_error,
                'max_DAC_code_difference': code_error, 'checks': prediction_checks,
                'engineering_check_passed': all(prediction_checks.values()),
                'loaded_samples_used_for_refit': 0, 'truth_resistance_used_in_prediction': True,
                'full_D2_accepted': False, 'blind_diagnosis_performed': False,
            }
            (log.path/'prediction-comparison.json').write_text(json.dumps(comparison, indent=2)+'\n')
            log.add('frozen_prediction_comparison', comparison)
            result = {'boot_id': guard.boot_id, 'configuration': asdict(config),
                      'REF_guard': ref_summary, 'step': step_summary,
                      'output_parked_ref_code': config.ref_code,
                      'response_analysis_pending': True,
                      'frozen_prediction_comparison': comparison,
                      'full_D2_accepted': False, 'hardware_diagnosis_performed': False}
            (log.path / 'capture-summary.json').write_text(json.dumps(result, indent=2) + '\n')
        log.add('run_completed', {**result, 'serial_connection_closed': True})
        print(json.dumps({'record': str(log.path), 'stage': 'completed', **result}), flush=True)
    except (Exception, KeyboardInterrupt) as exc:
        log.add('run_failed', {'stage': stage, 'error': str(exc) or type(exc).__name__,
                              'valid_for_response_analysis': False, 'accepted_samples': 0,
                              'automatic_retry_or_rearm': False,
                              'output_state_now_confirmed': False})
        print(json.dumps({'record': str(log.path), 'stage': 'failed',
                          'error': str(exc) or type(exc).__name__}), flush=True)
        raise SystemExit(1)


if __name__ == '__main__':
    main()
