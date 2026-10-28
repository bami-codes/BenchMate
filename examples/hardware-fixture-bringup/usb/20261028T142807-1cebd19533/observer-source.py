"""One supervised fixed-output USB observation during ordinary DMM probing. No auto recovery."""
import argparse
import ctypes
import json
import re
import subprocess
import time
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import serial
from serial.tools import list_ports
from benchmate.dac_loopback import validate_state
from benchmate.records import Recorder


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', required=True)
    args = parser.parse_args()
    duration = 600
    log = Recorder('runs/hardware-usb-review', mode='fixed_dac_ordinary_probing_usb_watch')
    hold_attempted = False
    started = None
    watch_wall = None
    samples = 0
    max_gap = 0.0
    max_cpu_busy = 0.0
    memory_previous = None
    memory_errors = 0
    libc = ctypes.CDLL('/usr/lib/libSystem.B.dylib')
    libc.mach_host_self.restype = ctypes.c_uint
    libc.host_statistics.argtypes = [ctypes.c_uint, ctypes.c_int,
                                    ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_uint)]
    libc.host_statistics.restype = ctypes.c_int
    host = libc.mach_host_self()

    def ticks():
        values = (ctypes.c_int * 4)()
        count = ctypes.c_uint(4)
        status = libc.host_statistics(host, 3, values, ctypes.byref(count))
        if status or count.value != 4:
            raise RuntimeError('CPU tick read failed')
        return [int(v) & 0xffffffff for v in values]

    def present():
        return any(p.device == args.port and p.vid == 9025 and p.pid == 4098
                   and p.serial_number == '68EE8F6B2D68' for p in list_ports.comports())

    def exchange(board, command, kind, level=None):
        log.add('serial_command', {'ascii': command})
        board.write((command + '\n').encode('ascii'))
        board.flush()
        raw = board.read_until(b'\n', size=8192)
        log.add('serial_response_raw', {'ascii': raw.decode('ascii', errors='backslashreplace')})
        packet = json.loads(raw)
        validate_state(packet, kind, level)
        if kind == 'pong' and (packet.get('adc_bits') != 14 or packet.get('dac_bits') != 12):
            raise ValueError('Unexpected converter resolution')
        return packet

    def memory(elapsed):
        nonlocal memory_previous, memory_errors
        try:
            raw = subprocess.check_output(['/usr/bin/vm_stat'], text=True, timeout=3)
            all_counts = {m.group(1).strip(): int(m.group(2))
                          for m in re.finditer(r'^([^:\n]+):\s+(\d+)\.', raw, re.M)}
            counts = {k: all_counts[k] for k in ('Swapins', 'Swapouts', 'Compressions',
                      'Decompressions', 'Pages free', 'Pages occupied by compressor') if k in all_counts}
            swap = subprocess.check_output(['/usr/sbin/sysctl', 'vm.swapusage'], text=True, timeout=3)
            delta = None if memory_previous is None else {
                k: counts[k] - memory_previous[k] for k in ('Swapins', 'Swapouts')
                if k in counts and k in memory_previous}
            log.add('host_memory', {'elapsed_s': elapsed, 'vm_counters': counts,
                                   'swap_page_deltas_since_previous_sample': delta,
                                   'swap_usage': swap.strip()})
            memory_previous = counts
        except Exception as exc:
            memory_errors += 1
            log.add('host_memory_read_failed', {'elapsed_s': elapsed, 'error': type(exc).__name__})

    def kernel_log():
        if watch_wall is None:
            return
        predicate = 'eventMessage CONTAINS[c] "UNO WiFi R4" OR eventMessage CONTAINS[c] "68EE8F6B2D68"'
        command = ['/usr/bin/log', 'show', '--style', 'compact', '--info', '--start',
                   watch_wall.astimezone(ZoneInfo('Asia/Seoul')).strftime('%Y-%m-%d %H:%M:%S'),
                   '--predicate', predicate]
        try:
            result = subprocess.run(command, capture_output=True, text=True, timeout=20)
            (log.path / 'usb-kernel.log').write_text(result.stdout)
            log.add('kernel_log_saved', {'file': 'usb-kernel.log', 'returncode': result.returncode,
                                        'stderr': result.stderr, 'predicate': predicate})
        except Exception as exc:
            log.add('kernel_log_read_failed', {'error': type(exc).__name__})

    log.add('watch_configuration', {
        'port': args.port, 'duration_s': duration, 'poll_interval_s': 1,
        'operator_report': 'Original R4 WiFi and same fixture/cable; prior hands-off interval confirmed; ordinary probing prepared; no new USB reconnection requested',
        'operator_handling_is_not_independently_observed': True,
        'nominal_level_mv': 600, 'requested_dac_code': 501,
        'driver_pull_down_ohm_displayed': 999, 'dut_connected': False,
        'firmware': 'benchmate-dac-loopback-v1', 'boot_id_available': False,
        'serial_closed_during_observation': True, 'periodic_ping_during_observation': False,
        'cpu_tick_sampling': 'Mach HOST_CPU_LOAD_INFO deltas', 'memory_interval_s': 15,
        'research_processes_unchanged': True, 'automatic_reconnect_or_rearm': False})
    print(json.dumps({'record': str(log.path), 'state': 'preflight'}), flush=True)
    try:
        if not present():
            raise RuntimeError('Expected original R4 WiFi USB device absent before setup')
        with serial.Serial(args.port, 115200, timeout=3, write_timeout=2) as board:
            time.sleep(2)
            board.reset_input_buffer()
            initial = exchange(board, 'PING', 'pong')
            # No power cycle was requested between phases: require the retained state.
            validate_state(initial, 'pong', 600)
            hold_attempted = True
            exchange(board, 'HOLD 600', 'holding', 600)
            time.sleep(0.5)
            exchange(board, 'PING', 'pong', 600)
        watch_wall = datetime.now(timezone.utc)
        started = time.monotonic()
        last_sample = started
        last_ticks = ticks()
        log.add('ordinary_probing_window_started', {'duration_s': duration, 'serial_port_closed': True})
        print(json.dumps({'state': 'watch_started', 'record': str(log.path),
                          'start_kst': watch_wall.astimezone(ZoneInfo('Asia/Seoul')).isoformat(),
                          'planned_end_kst': (watch_wall + timedelta(seconds=duration)).astimezone(ZoneInfo('Asia/Seoul')).isoformat()}), flush=True)
        for index in range(duration + 1):
            time.sleep(max(0, started + index - time.monotonic()))
            now = time.monotonic()
            gap = now - last_sample
            elapsed = now - started
            max_gap = max(max_gap, gap)
            this_ticks = ticks()
            changes = [(b-a) & 0xffffffff for a, b in zip(last_ticks, this_ticks)]
            total = sum(changes)
            busy = None if total == 0 else 100 * (total-changes[2]) / total
            if busy is not None:
                max_cpu_busy = max(max_cpu_busy, busy)
            last_ticks = this_ticks
            last_sample = now
            seen = present()
            samples += 1
            log.add('passive_sample', {'index': index, 'elapsed_s': elapsed, 'sample_gap_s': gap,
                                      'usb_device_present': seen, 'host_cpu_busy_percent': busy})
            if not seen:
                print(json.dumps({'state': 'usb_lost', 'elapsed_s': round(elapsed, 3),
                                  'record': str(log.path)}), flush=True)
                tree = subprocess.run(['/usr/sbin/ioreg', '-p', 'IOUSB', '-w', '0'],
                                      capture_output=True, text=True, timeout=3)
                (log.path/'usb-tree-at-loss.txt').write_text(tree.stdout)
                memory(elapsed)
                raise RuntimeError('Expected USB device absent during ordinary-probing comparison')
            if index % 15 == 0:
                memory(elapsed)
            if index and index % 30 == 0:
                print(json.dumps({'state': 'watch_progress', 'elapsed_s': round(elapsed, 1),
                                  'usb_device_present': True, 'max_sample_gap_s': round(max_gap, 3),
                                  'cpu_busy_now_percent': None if busy is None else round(busy, 1)}), flush=True)
        log.add('ordinary_probing_window_completed', {'duration_s': time.monotonic()-started,
                                               'usb_samples_present': samples})
        with serial.Serial(args.port, 115200, timeout=3, write_timeout=2) as board:
            time.sleep(2)
            board.reset_input_buffer()
            exchange(board, 'PING', 'pong', 600)
        kernel_log()
        result = {'ordinary_probing_window_passed': True, 'usb_samples_present': samples,
                  'max_sample_gap_s': max_gap, 'max_observed_cpu_busy_percent': max_cpu_busy,
                  'memory_read_errors': memory_errors, 'post_window_pong_verified': True,
                  'output_remains_driven': True, 'cause_identified': False}
        log.add('run_completed', result)
        print(json.dumps({'state': 'completed', 'record': str(log.path), **result}), flush=True)
    except (Exception, KeyboardInterrupt) as exc:
        kernel_log()
        result = {'error': str(exc) or type(exc).__name__, 'error_type': type(exc).__name__,
                  'elapsed_s': None if started is None else time.monotonic()-started,
                  'samples': samples, 'max_sample_gap_s': max_gap,
                  'max_observed_cpu_busy_percent': max_cpu_busy, 'memory_read_errors': memory_errors,
                  'hold_attempted': hold_attempted, 'output_may_remain_driven': hold_attempted,
                  'automatic_recovery_attempted': False}
        log.add('run_failed', result)
        print(json.dumps({'state': 'failed', 'record': str(log.path), **result}), flush=True)
        raise SystemExit(1)


if __name__ == '__main__':
    main()
