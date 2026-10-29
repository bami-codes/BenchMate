from pathlib import Path
import json
from benchmate.records import Recorder

log = Recorder('runs/hardware-minima-driver-mismatch', mode='operator_voltage_report_no_hardware_IO')
(log.path / 'controller-source.py').write_bytes(Path(__file__).read_bytes())
log.add('operator_report', {
    'raw_report': '1.62V /  3.4V / 1.64V',
    'nodes_order': ['B13_DAC_input', 'A11_U1_driver_output', 'D50_REF'],
    'voltage_displays_v': [1.62, 3.4, 1.64],
    'instructed_meter_range': 'DC 20 V',
    'instructed_reference': 'retained original blue-rail GND probe post',
    'instructed_USB_wiring_RESET_unchanged': True,
    'sequential_not_simultaneous': True,
    'measurement_accuracy_established': False,
    'fresh_supply_reading_supplied': False,
    'prior_recovery_record': 'runs/hardware-minima-probe-reset-recovery/20261029T064625-11722ff724',
})
log.add('assessment', {
    'driver_does_not_follow_input_in_reported_readings': True,
    'physical_output_recovery_not_established': True,
    'calibration_sweep_still_stopped': True,
    'use_as_calibration_point': False,
    'fault_location_not_yet_established': 'Check U1 input and feedback contact paths before attributing the mismatch to IC damage.',
    'earlier_USB_fault_cause_not_established': True,
})
log.add('next_physical_instruction', {
    'USB_disconnect_requested': True,
    'wait_for_power_LED_off': True,
    'red_5V_probe_post_stays_removed': True,
    'do_not_move_other_wiring_or_IC': True,
    'power_off_confirmation_received': False,
    'unpowered_feedback_check_planned': True,
})
log.add('run_completed', {
    'operator_report_recorded': True,
    'hardware_IO_performed': False,
    'output_or_firmware_changes': False,
    'ADC_capture_requested': False,
    'calibration_performed': False,
    'recovery_verified': False,
    'awaiting': 'USB disconnected and power LED off confirmation',
})
print(json.dumps({'record': str(log.path)}, ensure_ascii=False))
