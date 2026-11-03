"""Active mock with evaluator-only current information; common capture schema."""
from copy import deepcopy
import numpy as np

from ..netlist_diagnosis.menu import MENU, RESERVED, template
from . import led


class LEDMockBench:
    source = 'mock'

    def __init__(self, truth, log, *, seed=271, noise_sd_v=.0005):
        self._truth = deepcopy(truth)
        self.log = log; self.count = 0; self.freeze = None
        self.rng = np.random.default_rng(seed); self.noise = noise_sd_v

    def bind_forecast(self, sha): self.freeze = sha

    def acquire(self, settings, role):
        allowed = list(MENU.values()) if role == 'training' else RESERVED if role == 'verification' else []
        if settings not in allowed or (role == 'verification' and self.freeze is None):
            raise ValueError('Unavailable active action or missing prior forecast.')
        inp = template(settings, source='mock_adc_input_only')
        prediction = led.simulate(self._truth, inp)
        # Not included in Session.snapshot(): these are simulator truth, not
        # measured current, optical brightness or evidence available to Spark.
        self.log.add('evaluator_only_active_metrics', {
            'source': 'mock', 'purpose': role,
            'mean_LED_current_a': float(np.mean(prediction['predicted_LED_supply_current_a'])),
            'peak_LED_current_a': prediction['peak_supply_current_a'],
            'measured_output_range_v': prediction['measured_output_range_v'],
            'transmitted_to_agent': False, 'optical_brightness_measured': False})
        y = np.asarray(prediction['predicted_output_minus_ref_v'])
        y += self.rng.normal(0, self.noise, len(y))
        self.count += 1
        return {'source': 'mock', 'voltage_basis': 'REF_relative_v1', 'purpose': role,
                'all_guards_passed': True, 'fresh_measurement': True, 'settings': deepcopy(settings),
                'input_template': inp, 'output_minus_ref_v': y.tolist(),
                'boot_id': 'mock-active-boot', 'reference_id': 'known-simulator-absolute-REF',
                'reference_method': 'known_simulator_absolute_REF', 'physical_measurements': 0,
                'truth_simulator': 'ngspice; shared-simulator development check'}

    def metadata(self):
        return {'source': 'mock', 'mock_acquisitions': self.count, 'physical_measurements': 0,
                'hardware_commands': 0, 'shared_simulator_validation': True}
