"""New passive acquisition adapter using the preserved guards and byte protocol.

No firmware changes, RESET, automatic retry or paid provider construction occur
in this module. Physical execution remains a separately authorized operation.
"""
from copy import deepcopy
import numpy as np

from ..physical_bench import PhysicalBench
from ..instrument import BootContinuity, validate_boot_id
from .design import digest, checked
from .menu import MENU, RESERVED
from .models import validate_capture
from .protocol import validate as validate_protocol

CHOICES = {
    'initial_unloaded': 'USB was off; I checked the intended circuit and IN/OUT/REF wiring, left the output load disconnected, removed probes, and reconnected the same USB port.',
    'initial_output_load': 'USB was off; I checked the intended circuit and IN/OUT/REF wiring, connected only the known 9.99 kohm OUT-to-REF load, removed probes, and reconnected the same USB port.',
    'connect_output_load': 'USB was off; I connected only the known 9.99 kohm OUT-to-REF load, retained the specimen and remaining wiring, removed probes, and reconnected the same USB port.',
    'remove_output_load': 'USB was off; I disconnected only the known output-load jumper, retained the specimen and remaining wiring, removed probes, and reconnected the same USB port.',
}


def operator_report(choice, *, fixture, design_sha256):
    if choice not in CHOICES:
        raise ValueError('Select an exact predefined English confirmation; free text is not accepted.')
    expected = 'output_load' if choice in ('initial_output_load', 'connect_output_load') else 'unloaded'
    if fixture != expected:
        raise ValueError('Confirmation and requested output-load state differ.')
    return {'choice': choice, 'fixture': fixture, 'reviewed_design_sha256': design_sha256,
            'USB_connected': True, 'USB_off_wiring_confirmed': True, 'verbatim': CHOICES[choice]}


class PhysicalNetlistBench(PhysicalBench):
    source = 'physical'

    def __init__(self, protocol, log, confirm_wiring, *, design, initial_report,
                 previous_boot_id, approved=False, **transport):
        if approved is not True:
            raise ValueError('Explicit physical execution authorization required before adapter construction.')
        design = checked(design)
        if design['operator_review_simulated']:
            raise ValueError('A real intended-schematic review is required.')
        validate_protocol(protocol, design)
        validate_boot_id(previous_boot_id)
        self.design_sha = digest(design)
        self.confirm = confirm_wiring
        self.freeze = None
        self._check_report(initial_report, initial_report.get('fixture') if isinstance(initial_report, dict) else None, initial=True)
        settings = [{k: v for k, v in s.items() if k != 'load_ohm'} for s in list(MENU.values()) + RESERVED]
        super().__init__(protocol, log, confirm_wiring, initial_report=initial_report,
                         previous_boot_id=previous_boot_id, settings_menu=settings, **transport)

    def _check_report(self, value, fixture, *, initial):
        if not isinstance(value, dict) or fixture not in ('unloaded', 'output_load'):
            raise ValueError('Structured output-load confirmation required.')
        allowed = ('initial_unloaded', 'initial_output_load') if initial else ('connect_output_load', 'remove_output_load')
        if value.get('choice') not in allowed:
            raise ValueError('Wrong operator-confirmation phase.')
        expected = operator_report(value['choice'], fixture=fixture, design_sha256=self.design_sha)
        if value != expected:
            raise ValueError('Exact fixed English choice and reviewed design must match.')

    def bind_forecast(self, sha):
        self.freeze = sha

    def acquire(self, settings, role):
        if self.stopped:
            raise RuntimeError('Physical adapter stopped; no automatic retry.')
        allowed = list(MENU.values()) if role == 'training' else RESERVED if role == 'verification' else []
        if settings not in allowed or (role == 'verification' and self.freeze is None):
            raise ValueError('Only the frozen menu and prospectively frozen verification are allowed.')
        fixture = 'output_load' if settings['load_ohm'] is not None else 'unloaded'
        waveform = {k: v for k, v in settings.items() if k != 'load_ohm'}
        fresh = fixture != self.fixture
        phase = role + '_' + str(self.acquisitions+1)
        try:
            if fresh:
                use_initial = self.fixture is None and self.initial_report['fixture'] == fixture
                report = self.initial_report if use_initial else self.confirm(fixture)
                self._check_report(report, fixture, initial=use_initial)
                self.log.add('operator_wiring_confirmation', report)
                if not use_initial:
                    self.human_interventions += 1
                self.reference_means = []
            self.log.add('netlist_physical_acquisition_plan', {'settings': settings, 'purpose': role,
                         'fixture': fixture, 'prediction_sha256': self.freeze,
                         'fresh_boot_required': fresh, 'previous_boot_id': self.boot_id})
            ports = [p for p in self.ports() if (p.vid, p.pid, p.serial_number) == tuple(self.p['USB_identity'])]
            if len(ports) != 1:
                raise ValueError('Expected Minima absent or ambiguous.')
            continuity = BootContinuity()
            previous = self.boot_id
            with self.serial_factory(ports[0].device, 115200, timeout=5, write_timeout=2) as board:
                self.sleep(2); board.reset_input_buffer()
                self._ping(board, continuity, phase+'_PING', not fresh)
                if fresh:
                    if continuity.boot_id == previous:
                        raise ValueError('New boot required after the USB-off intervention.')
                    packet = self._request(board, continuity, self.config.arm_command(continuity.boot_id), phase+'_ARM', 15)
                    if packet.get('type') != 'armed':
                        raise ValueError('ARM not acknowledged.')
                    self._ping(board, continuity, phase+'_armed', True)
                elif continuity.boot_id != previous:
                    raise ValueError('Unexpected boot change; no re-arm.')
                self.boot_id = continuity.boot_id
                hold = [self._hold(board, continuity, phase+'_origin_'+str(i)) for i in range(3)]
                means = np.asarray([r[:, 2:6].mean(axis=0) for r in hold]).mean(axis=0)
                maps = self.p['voltage_conversion']['channels']
                origins = {ch: float(means[i]*maps[ch]['gain_v_per_count']+maps[ch]['offset_v'])
                           for i, ch in enumerate(('A1', 'A2'))}
                reference = {'origins': origins, 'boot_id': self.boot_id, 'HOLD_frames': 1536,
                             'scored_OUT_used': 0, 'absolute_REF_calibrated': False}
                reference_id = digest(reference)
                self.log.add('netlist_reference_origins_frozen', {'sha256': reference_id, **reference})
                rows = self._capture(board, continuity, phase, waveform)
                self._waveform_checks(rows, waveform)
                self._hold(board, continuity, phase+'_return_REF')
                self._ping(board, continuity, phase+'_final', True)
            data = {'frame_time_s': (rows[:, 0]*1e-6).tolist(),
                    'input_delay_s': (rows[:, 6]*1e-6).tolist(), 'output_delay_s': (rows[:, 7]*1e-6).tolist(),
                    'input_minus_ref_v': (rows[:, 2]*maps['A1']['gain_v_per_count']+maps['A1']['offset_v']-origins['A1']).tolist()}
            inp = {'source': 'physical_input_only', 'settings': {k: settings[k] for k in ('kind', 'samples', 'period_us', 'load_ohm')} |
                   {'frequency_hz': settings.get('frequency_hz'), 'step_index': settings['samples']//10 if settings['kind'] == 'step' else None},
                   'data': data}
            capture = {'source': 'physical', 'voltage_basis': 'REF_relative_v1', 'purpose': role,
                       'all_guards_passed': True, 'fresh_measurement': True, 'settings': deepcopy(settings),
                       'input_template': inp, 'output_minus_ref_v':
                           (rows[:, 3]*maps['A2']['gain_v_per_count']+maps['A2']['offset_v']-origins['A2']).tolist(),
                       'boot_id': self.boot_id, 'reference_id': reference_id,
                       'reference_scope': self.p['reference_scope']}
            validate_capture(capture, role=role)
            self.fixture = fixture; self.acquisitions += 1
            return capture
        except BaseException:
            self.stopped = True
            raise
