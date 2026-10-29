from pathlib import Path
import json
from benchmate.records import Recorder

log = Recorder('runs/hardware-minima-pin-feedback', mode='operator_unpowered_continuity_no_hardware_IO')
(log.path / 'controller-source.py').write_bytes(Path(__file__).read_bytes())
log.add('operator_continuity_report', {
    'raw_report': '삐 소리 났어',
    'instruction_endpoints': ['U1_actual_metal_pin_6_E12', 'U1_actual_metal_pin_7_E11'],
    'result': 'beep',
    'USB_disconnected_LED_off_per_prior_confirmation_and_instruction': True,
    'numeric_resistance_supplied': False,
    'prior_contact_clarification': 'runs/hardware-minima-contact-clarification/20261029T070759-af02817dbc',
})
log.add('assessment', {
    'actual_feedback_pin_continuity_reported': True,
    'powered_function_not_yet_verified': True,
    'latched_state_or_IC_damage_not_established': True,
    'no_wiring_or_IC_change_requested': True,
    'calibration_sweep_still_stopped': True,
})
log.add('next_physical_instruction', {
    'change_meter_to_DC_20V_before_power': True,
    'reconnect_Minima_same_cable_and_Mac_port': True,
    'ground_probe': 'retained blue-rail GND post',
    'supply_contact': 'existing first divider resistor A3-side lead on breadboard, not Arduino A3',
    'REF_contact': 'D50 jumper',
    'red_5V_probe_post_stays_removed': True,
    'fresh_supply_and_REF_readings_requested': True,
    'DAC_not_yet_commanded': True,
    'do_not_measure_driver_until_explicit_DAC_setting': True,
})
log.add('run_completed', {
    'operator_continuity_recorded': True,
    'hardware_IO_performed': False,
    'calibration_performed': False,
    'awaiting': 'USB reconnect confirmation and fresh supply/REF displays',
})
print(json.dumps({'record': str(log.path)}))
