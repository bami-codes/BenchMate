from pathlib import Path
import json
from benchmate.records import Recorder, read_events

held = 'runs/hardware-minima-dc-hold/20261029T082914-3ac1b9a56a'
result = read_events(held)[-1]
assert result['kind'] == 'run_completed'
log = Recorder('runs/hardware-minima-high-DMM-protocol', mode='high_point_DMM_instruction_before_data_no_hardware_IO')
(log.path / 'controller-source.py').write_bytes(Path(__file__).read_bytes())
log.add('held_level_context', {'hold_record': held, 'boot_id': result['payload']['boot_id'],
                              'held_code': result['payload']['held_code'], 'nominal_target_v': 2.60,
                              'high_DMM_data_received': False})
log.add('measurement_instruction', {
    'meter_range': 'DC 2 V for all six displays',
    'ordered_readings': ['REF_to_GND_before', 'U1_pin5_minus_REF', 'D35_minus_REF',
                         'D40_minus_REF', 'D45_minus_REF', 'REF_to_GND_after'],
    'first_and_last_probe_positions': {'black': 'blue-rail GND', 'red': 'D50 fixed REF'},
    'middle_probe_positions': {'black': 'D50 fixed REF', 'red_in_order': ['U1 actual pin5 E13', 'D35', 'D40', 'D45']},
    'only_meter_probes_move': True, 'no_GND_to_REF_jumper': True,
    'USB_wiring_RESET_unchanged': True, 'output_and_firmware_unchanged_during_reading': True,
    'purpose': 'Use the 2 V display resolution for high-point differences; bracket the differential readings with REF-to-GND readings.',
    'interpretation': 'Store raw differences and both REF readings; any absolute high voltage is derived by adding a measured REF and must retain shared-reference and sequential-measurement uncertainty.',
    'meter_accuracy_established': False,
})
log.add('run_completed', {'instruction_recorded_before_high_DMM_data': True,
                          'hardware_IO_performed': False, 'calibration_performed': False,
                          'awaiting': 'Six high-point DMM displays including REF before/after'})
print(json.dumps({'record': str(log.path)}))
