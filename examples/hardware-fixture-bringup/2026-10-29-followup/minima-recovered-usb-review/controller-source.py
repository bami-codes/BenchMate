from pathlib import Path
import ast
import hashlib
import json
from benchmate.records import Recorder

failed = Path('runs/hardware-minima-recovered-driver-low/20261029T073343-007202a5ac')
review = json.loads((failed / 'minima-kernel-review.json').read_text())
watch = Path('runs/minima_persistent_ref_watch.py')
ast.parse(watch.read_text())
log = Recorder('runs/hardware-minima-recovered-usb-review', mode='USB_failure_review_and_diagnostic_preparation_no_stimulus')
(log.path / 'controller-source.py').write_bytes(Path(__file__).read_bytes())
(log.path / 'minima-kernel-review.json').write_bytes((failed / 'minima-kernel-review.json').read_bytes())
(log.path / 'prepared-watch-source.py').write_bytes(watch.read_bytes())
log.add('failed_low_attempt', {
    'record': str(failed), 'initial_PING_received_no_bytes': True,
    'low_DC_command_sent': False, 'new_ARM_sent': False,
    'midpoint_physical_report': 'U1 pins 5/6/7 and D50 all 1.62 V',
    'current_physical_output_not_remeasured_after_failed_PING': True,
})
log.add('USB_kernel_review', review)
log.add('read_only_host_observations', {
    'port_list_time_KST': '2026-10-29T16:34:52.130718+09:00',
    'Minima_port_listed': '/dev/cu.usbmodem3101',
    'VID': 9025, 'PID': 105, 'serial_number': '3612211F36323632E4B233334B572F52',
    'pmset_query_window_KST': '2026-10-29 16:20–16:35',
    'matching_sleep_wake_events': [],
    'pmset_filter': 'timestamp within window and Sleep/DarkWake/Wake followed by Entering/DarkWake/Wake/from',
    'limits': 'No matching sleep/wake entries in this filtered read; no specific host/board/cable fault cause established.',
})
log.add('prepared_diagnostic', {
    'source_sha256': hashlib.sha256(watch.read_bytes()).hexdigest(),
    'syntax_parse_passed': True, 'hardware_execution_performed': False,
    'requires_new_operator_single_RESET_confirmation': True,
    'duration_seconds': 600, 'PING_interval_seconds': 2,
    'single_serial_connection_held_open': True,
    'explicit_REF_ARM_after_verified_new_unarmed_boot': True,
    'output_changes_after_ARM': False, 'ADC_capture': False,
    'automatic_retry_or_rearm_after_failure': False,
    'comparison_limit': 'Continuous-open plus periodic PING changes both connection lifetime and status traffic; success would not isolate a unique cause.',
})
log.add('run_completed', {
    'evidence_and_preparation_recorded': True,
    'calibration_still_incomplete': True, 'fault_cause_established': False,
    'awaiting': 'Operator single RESET confirmation before persistent-connection test',
})
print(json.dumps({'record': str(log.path)}))
