"""A deliberately labelled mock and a callback boundary for guarded acquisition."""
from copy import deepcopy
import numpy as np

from .design import elements
from .menu import MENU, RESERVED, template
from .simulation import simulate


class MockBench:
    source = 'mock'

    def __init__(self, truth, log, *, seed=271, noise_sd_v=.0005, diode=None):
        self._truth = elements(truth)
        self._diode = diode
        self.log = log
        self.rng = np.random.default_rng(seed)
        self.noise = noise_sd_v
        self.count = 0
        self.freeze = None

    def bind_forecast(self, sha256):
        self.freeze = sha256

    def acquire(self, settings, role):
        if role not in ('training', 'verification'):
            raise ValueError('Unknown acquisition role.')
        allowed = list(MENU.values()) if role == 'training' else RESERVED
        if settings not in allowed or (role == 'verification' and self.freeze is None):
            raise ValueError('Action is unavailable or prospective forecast is missing.')
        inp = template(settings, source='mock_adc_input_only')
        y = np.asarray(simulate(self._truth, inp, diode=self._diode)['predicted_output_minus_ref_v'])
        y += self.rng.normal(0, self.noise, len(y))
        self.count += 1
        result = {'source': 'mock', 'voltage_basis': 'REF_relative_v1', 'all_guards_passed': True,
                  'fresh_measurement': True, 'purpose': role, 'settings': deepcopy(settings),
                  'input_template': inp, 'output_minus_ref_v': y.tolist(),
                  'boot_id': 'mock-boot', 'reference_id': 'mock-known-zero-ref',
                  'physical_measurements': 0, 'truth_simulator': 'ngspice; shared-simulator development check'}
        return result

    def metadata(self):
        return {'source': 'mock', 'mock_acquisitions': self.count, 'physical_measurements': 0,
                'hardware_commands': 0, 'shared_simulator_validation': True}


class GuardedCallbackBench:
    """No serial access is constructed here; the approved adapter supplies it.

    This boundary cannot turn an arbitrary callback into validated hardware.
    A physical run must additionally bind the actual protocol, sources, REF
    calibration, wiring reports and publication receipt in its runner.
    """
    source = 'physical'

    def __init__(self, acquire, log, *, protocol, approved=False):
        if approved is not True or protocol.get('version') != 'netlist-diagnosis-v1':
            raise ValueError('A separately approved, frozen physical protocol is required.')
        self._acquire = acquire
        self.protocol = deepcopy(protocol)
        self.log = log
        self.count = 0
        self.stopped = False
        self.freeze = None

    def bind_forecast(self, sha256):
        self.freeze = sha256

    def acquire(self, settings, role):
        if self.stopped:
            raise ValueError('Physical acquisition stopped; no retry.')
        allowed = list(MENU.values()) if role == 'training' else RESERVED if role == 'verification' else []
        if settings not in allowed or (role == 'verification' and self.freeze is None):
            raise ValueError('Action outside the frozen menu or forecast not frozen.')
        try:
            result = self._acquire(deepcopy(settings), role)
            from .models import validate_capture
            validate_capture(result, role=role)
            if result['source'] != 'physical' or result['settings'] != settings:
                raise ValueError('Physical callback source/settings mismatch.')
            self.count += 1
            return result
        except BaseException:
            self.stopped = True
            raise

    def metadata(self):
        return {'source': 'physical', 'accepted_captures': self.count, 'stopped': self.stopped,
                'adapter': 'externally supplied guarded callback; not a serial implementation'}
