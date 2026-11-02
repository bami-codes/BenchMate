"""Vectorized one-state predictions for numerical integration.

Rows are R, C, Rp, optional Rout (parallel values of 0 mean absent).
C=0 is an algebraic resistor circuit, not a tiny-capacitance approximation.
The observed DRIVE/REF are the inputs.
Fast step/sine paths are only used when those inputs match the declared waveform.
"""
import numpy as np
from .physics import Acquisition


def predict_many(models, capture):
    models = np.atleast_2d(np.asarray(models, dtype=float))
    if models.shape[1] not in (3,4) or not np.all(np.isfinite(models)) or np.any(models[:, 0] <= 0) or np.any(models[:, 1:] < 0):
        raise ValueError("Invalid model rows")
    acq = Acquisition(**capture["settings"])
    data = capture["data"]
    r, c, rp = models[:,:3].T
    rout=models[:,3] if models.shape[1]==4 else np.zeros(len(models))
    gp = np.divide(1, rp, out=np.zeros_like(rp), where=rp > 0)
    gl = np.divide(1,rout,out=np.zeros_like(rout),where=rout>0)+(0 if acq.load_ohm is None else 1/acq.load_ohm)
    if acq.shunt_ohm:
        gs = 1/acq.shunt_ohm
        denom = gs + 1/r + gp
        ku, kx = gs/denom, (1/r)/denom
    else:
        ku, kx = np.ones_like(r), np.zeros_like(r)
    # Safe placeholder for algebraic rows; their exact node solution replaces x.
    dynamic=c>0;safe_c=np.where(dynamic,c,1.)
    a, b = (kx-1)/(r*safe_c)-gl/safe_c, ku/(r*safe_c)
    gain = -b/a
    drive = np.asarray(data["drive_v"], dtype=float)
    ref = np.asarray(data["ref_v"], dtype=float)
    if drive.ndim != 1 or ref.shape != drive.shape or not np.all(np.isfinite(drive+ref)):
        raise ValueError("Invalid observed input")
    u = drive-ref
    if acq.kind == "dc_pair":
        x = gain[:, None]*u
    else:
        t = np.asarray(data["time_s"], dtype=float)
        if t.shape != u.shape or len(t)<2 or not np.all(np.isfinite(t)) or not np.all(np.diff(t)>0):
            raise ValueError("Invalid observed time axis")
        ideal = acq.amplitude_v*np.sin(2*np.pi*acq.frequency_hz*t) if acq.kind == "sine" else np.where(t < acq.step_at_s, -acq.amplitude_v, acq.amplitude_v)
        regular = np.allclose(np.diff(t), acq.sample_period_s, rtol=1e-9, atol=1e-12)
        if np.allclose(u, ideal, atol=1e-13, rtol=0) and regular:
            if acq.kind == "step":
                # The first high DRIVE sample starts the ZOH transition.
                change = t[np.flatnonzero(t >= acq.step_at_s)[0]]
                elapsed = np.maximum(0, t-change)
                x = gain[:, None]*(-acq.amplitude_v + 2*acq.amplitude_v*(-np.expm1(a[:, None]*elapsed)))
            else:
                decay = np.exp(a*acq.sample_period_s)
                phase = np.exp(-2j*np.pi*acq.frequency_hz*acq.sample_period_s)
                h = gain*(1-decay)*phase/(1-decay*phase)
                x = acq.amplitude_v*np.imag(h[:, None]*np.exp(2j*np.pi*acq.frequency_hz*t))
        else:
            x = np.empty((len(models),len(t)))
            x[:, 0] = gain*u[0]
            if acq.kind == "sine":
                decay = np.exp(a*acq.sample_period_s)
                phase = np.exp(-2j*np.pi*acq.frequency_hz*acq.sample_period_s)
                x[:, 0] = acq.amplitude_v*np.imag(gain*(1-decay)*phase/(1-decay*phase))
            for i, dt in enumerate(np.diff(t), 1):
                decay = np.exp(a*dt)
                x[:, i] = decay*x[:, i-1] + gain*(1-decay)*u[i-1]
    vin = ku[:, None]*u + kx[:, None]*x
    if np.any(~dynamic):
        divider=1+r[~dynamic]*gl[~dynamic]
        input_gain=1/(1+acq.shunt_ohm*(gp[~dynamic]+gl[~dynamic]/divider))
        vin[~dynamic]=input_gain[:,None]*u
        x[~dynamic]=vin[~dynamic]/divider[:,None]
    result = {"in_v": ref+vin, "out_v": ref+x}
    if acq.kind == "dc_pair":
        result["shunt_drop_v"] = u-vin
    return result
