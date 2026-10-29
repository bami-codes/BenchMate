from pathlib import Path
import json
from benchmate.records import Recorder

log = Recorder('runs/hardware-minima-contact-clarification', mode='operator_contact_clarification_no_hardware_IO')
(log.path / 'controller-source.py').write_bytes(Path(__file__).read_bytes())
log.add('operator_clarification', {
    'raw_report': '13·A11 기둥은 어젯밤에 뺐어. 아까 B13·A11 값은 칩1 5번·7번 다리에서 직접 잰 거야. 그래서 ①②는 건너뛰고 ③만 했어. USB 분리·LED 꺼짐 B12↔D11 삐(피드백 정상). 배선 문제 아니니까 칩이 걸린 상태로 보여.',
    'prior_voltage_record': 'runs/hardware-minima-driver-mismatch/20261029T065746-47b8578b22',
    'B13_and_A11_probe_posts_removed_previous_night_reported': True,
    'actual_contacts_for_prior_voltage_report': ['U1_pin_5_E13', 'U1_pin_7_E11', 'D50_REF'],
    'prior_voltage_displays_v': [1.62, 3.4, 1.64],
    'new_voltage_measurements_supplied': False,
    'USB_disconnected_and_power_LED_off_confirmed': True,
})
log.add('continuity_report', {
    'actual_tested_endpoints': ['B12', 'D11'],
    'result': 'beep',
    'numeric_resistance_supplied': False,
    'actual_U1_pin_6_to_pin_7_test_confirmed': False,
    'scope': 'Reported continuity of breadboard feedback nodes; package pin 6 contact remains unchecked.',
    'latched_state_or_IC_damage_established': False,
})
log.add('next_physical_instruction', {
    'keep_USB_disconnected_and_LED_off': True,
    'requested_actual_metal_pin_endpoints': ['U1_pin_6_E12', 'U1_pin_7_E11'],
    'avoid_probe_tips_touching_each_other': True,
    'report_if_pins_not_accessible': True,
    'no_wiring_or_IC_change_requested': True,
    'USB_reconnection_not_yet_requested': True,
})
log.add('run_completed', {
    'operator_clarification_recorded': True,
    'original_voltage_record_preserved': True,
    'hardware_IO_performed': False,
    'calibration_sweep_still_stopped': True,
    'fault_cause_established': False,
    'awaiting': 'Actual U1 pin 6 to pin 7 continuity result',
})
print(json.dumps({'record': str(log.path)}))
