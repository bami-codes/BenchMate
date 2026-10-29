"""One controlled passive D01 variant observation: fresh boot, REF guard, small step. No retry.

This is the documented USB-off-wired passive RC exception, not the general
DUT connection workflow. Component truth is not used to choose or fit a model.
"""
from dataclasses import asdict
from pathlib import Path
import hashlib
import json
import time
import numpy as np
import serial
from serial.tools import list_ports
from benchmate.records import Recorder
from benchmate.instrument import (
    BootContinuity, InstrumentConfig, capture_command, receive_response,
    validate_block,
)


def main():
    previous_boot = '62718b65a2204d5c576563ddd04ed7f0'
    config = InstrumentConfig(vref_v=4.88, ref_v=1.635)
    profile = Path('examples/hardware-fixture-bringup/2026-10-29-followup/minima-three-point-analysis/provisional-calibration.json')
    log = Recorder('runs/hardware-d01-unloaded-step', mode='controlled_fault_unloaded_observation_not_blind_diagnosis')
    for source, name in [
        (Path(__file__), 'controller-source.py'),
        (Path('src/benchmate/instrument.py'), 'host-instrument.py'),
        (profile, 'provisional-calibration.json'),
        (Path('docs/d01-assembly.md'), 'assembly-guide.md'),
    ]:
        (log.path / name).write_bytes(source.read_bytes())
    log.add('operator_power_report', {
        'verbatim': 'USB 연결 / 4.88V / 1.635V',
        'supply_v': 4.88, 'REF_v': 1.635,
        'requested_ranges': {'supply': 'DC 20 V', 'REF': 'DC 2 V'},
        'precision_retained_as_reported': True,
        'supply_contact': 'large A3 divider resistor lead', 'REF_contact': 'large D50',
        'reference': 'existing blue rail GND',
        'hookup_record': 'runs/hardware-d01-assembly-confirmed/20261029T133812-892895783e',
        'IN': 'green large A35 to mini A3', 'OUT': 'blue large D30 to mini A8',
        'RET': 'gray large C50 to mini A13; buffered REF not GND',
        'calibration_bridge_15_removed': True,
        'shunt_bypass_11_and_aux_park_14_retained_per_instruction': True,
    })
    log.add('predeclared_configuration', {
        'configuration': asdict(config), 'previous_boot_id': previous_boot,
        'known_passive_RC_only_startup_exception': True,
        'startup_and_ARM_ramp_excluded_from_experiment_data': True,
        'startup_may_be_outside_REF_plus_minus_1V': True,
        'unknown_active_external_power_or_holdout_not_authorized_by_this_exception': True,
        'REF_guard_block': {'samples': 512, 'period_us': 2000},
        'step': {'samples': 512, 'period_us': 500, 'amplitude_v': 0.2,
                 'nominal_transition_v': 0.4, 'sample_rate_previously_exercised_on_B1': True},
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
        'component_truth_used_by_capture_controller': False,
        'output_load_disconnected_per_operator': True,
        'no_component_fault_selected_from_assembly': True,
        'capture_count_including_REF_guard': 2,
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
            result = {'boot_id': guard.boot_id, 'configuration': asdict(config),
                      'REF_guard': ref_summary, 'step': step_summary,
                      'output_parked_ref_code': config.ref_code,
                      'response_analysis_pending': True,
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
