"""After a completed persistent watch, verify a persistent REF DC hold for DMM calibration."""
from pathlib import Path
import argparse
import json
from serial.tools import list_ports
from benchmate.records import Recorder, read_events
from benchmate.instrument import InstrumentConfig, set_dc_level

p = argparse.ArgumentParser()
p.add_argument('--watch-record', required=True)
args = p.parse_args()
events = read_events(args.watch_record)
last = events[-1]
assert last['kind'] == 'run_completed'
result = last['payload']
assert result['duration_seconds'] >= 600 and result['successful_PINGs'] >= 290
config = InstrumentConfig(vref_v=4.86, ref_v=1.62)
assert result['held_code_at_final_check'] == config.ref_code
boot = result['boot_id']
log = Recorder('runs/hardware-minima-post-watch-ref', mode='same_boot_REF_DC_after_continuous_watch')
for source, name in [(Path(__file__), 'controller-source.py'), (Path('src/benchmate/instrument.py'), 'host-instrument.py')]:
    (log.path / name).write_bytes(source.read_bytes())
log.add('configuration', {
    'completed_watch_record': args.watch_record, 'expected_boot_id': boot,
    'nominal_target_v': 1.62, 'expected_code': config.ref_code,
    'supply_conversion_v': 4.86, 'no_new_ARM': True, 'ADC_capture_requested': False,
    'scope': 'Explicit same-level DC command includes firmware settling checks; no calibrated accuracy claim.',
})
print(json.dumps({'record': str(log.path), 'stage': 'preflight'}), flush=True)
try:
    ports = [p for p in list_ports.comports() if (p.vid, p.pid, p.serial_number) ==
             (9025, 105, '3612211F36323632E4B233334B572F52')]
    log.add('USB_preflight', {'matching_ports': [p.device for p in ports]})
    if len(ports) != 1:
        raise RuntimeError('Expected Minima absent or ambiguous')
    held_path, held = set_dc_level(ports[0].device, config, hold_v=1.62,
                                  expected_boot_id=boot, output='runs/hardware-minima-dc-hold')
    log.add('REF_DC_hold_completed', {'record': str(held_path), 'result': held})
    log.add('run_completed', {'boot_id': boot, 'DC_hold_record': str(held_path),
                              'held_code': held['held_code'], 'nominal_target_v': 1.62,
                              'DMM_readings_pending': True, 'ADC_block_acquired': False,
                              'calibration_performed': False})
    print(json.dumps({'record': str(log.path), 'stage': 'completed',
                      'hold_record': str(held_path), 'boot_id': boot}), flush=True)
except (Exception, KeyboardInterrupt) as exc:
    log.add('run_failed', {'error': str(exc) or type(exc).__name__,
                          'automatic_retry_or_rearm': False, 'calibration_performed': False})
    print(json.dumps({'record': str(log.path), 'stage': 'failed', 'error': str(exc)}), flush=True)
    raise SystemExit(1)
