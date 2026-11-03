"""Commanded input waveforms, independent of any circuit hypothesis.

These are ideal development commands. Hardware predictions must eventually use
the calibrated actuator model and actual channel timing, not assume ideal drive.
"""
import numpy as np


def commanded_waveform(settings):
    if settings.kind == 'dc_pair':
        u = np.array([-settings.amplitude_v, settings.amplitude_v])
        return {'drive_v': (settings.ref_v+u).tolist(), 'ref_v': [settings.ref_v]*2}
    t = np.arange(0, settings.duration_s+settings.sample_period_s/2, settings.sample_period_s)
    u = (settings.amplitude_v*np.sin(2*np.pi*settings.frequency_hz*t)
         if settings.kind == 'sine' else
         np.where(t < settings.step_at_s, -settings.amplitude_v, settings.amplitude_v))
    return {'time_s': t.tolist(), 'drive_v': (settings.ref_v+u).tolist(),
            'ref_v': np.full(t.shape, settings.ref_v).tolist()}


def command_template(settings):
    return {'settings': settings.to_dict(), 'data': commanded_waveform(settings),
            'input_provenance': 'ideal_command_pending_hardware_actuator_calibration'}
