"""Preserve corrected high DMM displays and a failed watch; no hardware IO."""
from pathlib import Path
import hashlib
import json
from decimal import Decimal
from benchmate.records import Recorder, read_events

watch = Path('runs/hardware-minima-held-level-watch/20261029T082934-fd6fc27a85')
events = read_events(watch)
assert events[-1]['kind'] == 'run_failed'
pings = [e for e in events if e['kind'] == 'held_level_PING']
assert len(pings) == 240
log = Recorder('runs/hardware-minima-high-point-review', mode='DMM_only_after_failed_watch_no_ADC_pair')
(log.path / 'controller-source.py').write_bytes(Path(__file__).read_bytes())
kernel = Path('runs/minima-high-watch-kernel-review.json')
(log.path / 'minima-kernel-review.json').write_bytes(kernel.read_bytes())
log.add('operator_DMM_reports', {
    'original_report_verbatim': '1.63V / 0.96V / 0.96V / 0.96V / 0.96V / 1.63V',
    'corrected_report_verbatim': '1.629V / 0.975V / 0.975V / 0.974V / 0.975V / 1.629V 이거야.',
    'correction_supersedes_coarse_values_without_removing_them': True,
    'requested_range': 'DC 2 V',
    'range_separately_reconfirmed': False,
    'display_order': ['REF_to_GND_before', 'U1_pin5_minus_REF', 'D35_minus_REF', 'D40_minus_REF', 'D45_minus_REF', 'REF_to_GND_after'],
    'exact_displays_v': ['1.629', '0.975', '0.975', '0.974', '0.975', '1.629'],
    'measurement_timestamps_not_supplied': True,
    'USB_RESET_action_during_measurement': 'Asked, awaiting operator answer',
})
ref = Decimal('1.629')
absolute = {name: str(ref + Decimal(delta)) for name, delta in zip(
    ['U1_pin5', 'D35', 'D40', 'D45'], ['0.975', '0.975', '0.974', '0.975'])}
log.add('derived_DMM_absolute_voltages', {
    'volts_as_decimal_strings': absolute,
    'method': 'Add the common REF display to each sequential node-minus-REF display; REF before and after both read 1.629 V.',
    'not_direct_absolute_readings': True,
    'REF_display_change_v': 0,
    'limits': ['Equal bracketing displays do not establish zero drift between readings.',
               'Common REF error is shared by all derived voltages; meter accuracy is not established.',
               'Two displayed readings are combined; 0.001 V display increments are not an absolute accuracy bound.',
               'These values are not paired to an ADC block after the continuity failure.'],
})
log.add('watch_failure_review', {
    'record': str(watch), 'events_sha256': hashlib.sha256((watch / 'events.jsonl').read_bytes()).hexdigest(),
    'successful_PINGs': len(pings), 'last_successful_PING_utc': pings[-1]['timestamp'],
    'failure_utc': events[-1]['timestamp'], 'terminal_payload': events[-1]['payload'],
    'continuous_open_plus_periodic_PING_did_not_prevent_failure': True,
    'kernel_review': json.loads(kernel.read_text()),
    'OS_port_read_at_utc': '2026-10-29T08:45:23Z',
    'OS_port_still_listed': '/dev/cu.usbmodem3101',
    'OS_identity': {'VID': 9025, 'PID': 105, 'serial_number': '3612211F36323632E4B233334B572F52'},
    'no_further_serial_open_or_output_commands_after_failure': True,
    'root_cause_established': False,
})
log.add('run_completed', {
    'operator_high_DMM_retained': True, 'high_ADC_capture_requested': False,
    'high_ADC_pair_accepted': False, 'calibration_fit_performed': False,
    'output_return_to_REF_command_sent': False, 'output_state_not_confirmed_by_firmware_after_failure': True,
    'next_step': 'Await requested operator single RESET; verify new unarmed boot before explicit REF setup. Re-measure any later high ADC pair.',
})
print(json.dumps({'record': str(log.path), 'derived_absolute_v': absolute}))
