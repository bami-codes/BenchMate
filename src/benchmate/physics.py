"""Exact one-state RC predictions for the declared day-one circuit family.

Voltages are absolute relative to board ground; the capacitor connects to REF.
An optional resistor connects IN to REF, a shunt connects DRIVE to IN, and an
optional output load connects OUT to REF. This is not a full fixture model.
"""

from dataclasses import dataclass, asdict, replace
import math
import numpy as np


@dataclass(frozen=True)
class RCModel:
    r_ohm: float
    c_f: float
    input_parallel_ohm: float | None = None

    def __post_init__(self):
        for v in (self.r_ohm, self.c_f, self.input_parallel_ohm):
            if v is not None and (not math.isfinite(v) or v <= 0):
                raise ValueError("Circuit values must be finite and positive")


@dataclass(frozen=True)
class Acquisition:
    kind: str = "step"
    shunt_ohm: float = 0.0
    load_ohm: float | None = None
    amplitude_v: float = 0.5  # half excursion: -amplitude to +amplitude
    ref_v: float = 1.6
    duration_s: float = 0.3
    sample_period_s: float = 0.0005
    step_at_s: float = 0.02

    def __post_init__(self):
        if self.kind not in ("step", "dc_pair"):
            raise ValueError("Unsupported acquisition")
        numeric = [self.shunt_ohm, self.amplitude_v, self.ref_v,
                   self.duration_s, self.sample_period_s, self.step_at_s]
        if not all(math.isfinite(v) for v in numeric):
            raise ValueError("Non-finite acquisition setting")
        if self.shunt_ohm not in (0.0, 1000.0):
            raise ValueError("Only jumper or declared 1 kohm shunt is supported")
        if self.load_ohm is not None and self.load_ohm not in (10000.0, 4700.0):
            raise ValueError("Unsupported output load")
        if not 0 < self.amplitude_v <= 1.0:
            raise ValueError("Stimulus envelope is REF +/- 1 V")
        if not 0 <= self.ref_v-self.amplitude_v < self.ref_v+self.amplitude_v <= 5:
            raise ValueError("Stimulus outside board voltage range")
        if self.kind == "step" and 2*self.amplitude_v > 1.0:
            raise ValueError("A single transition must not exceed 1 V")
        if self.kind == "dc_pair" and self.shunt_ohm == 0:
            raise ValueError("DC current observation requires a shunt")
        if not 0 < self.step_at_s < self.duration_s or self.sample_period_s <= 0:
            raise ValueError("Invalid time window")
        if self.duration_s / self.sample_period_s > 10000:
            raise ValueError("Capture exceeds development sample limit")

    def to_dict(self):
        return asdict(self)

    @property
    def physical_acquisitions(self):
        return 2 if self.kind == "dc_pair" else 1


def coefficients(model: RCModel, acq: Acquisition):
    """Return dx/dt = a*x + b*(DRIVE-REF), vin = ku*u + kx*x."""
    r, c = model.r_ohm, model.c_f
    gp = 0.0 if model.input_parallel_ohm is None else 1/model.input_parallel_ohm
    gl = 0.0 if acq.load_ohm is None else 1/acq.load_ohm
    if acq.shunt_ohm == 0:
        ku, kx = 1.0, 0.0
    else:
        gs = 1/acq.shunt_ohm
        denom = gs + 1/r + gp
        ku, kx = gs/denom, (1/r)/denom
    a, b = (kx-1)/(r*c)-gl/c, ku/(r*c)
    return a, b, ku, kx


def response_properties(model: RCModel, acq: Acquisition):
    a, b, _, _ = coefficients(model, acq)
    return {"gain": -b/a, "tau_s": -1/a}


def predict(model: RCModel, acq: Acquisition, time_s=None, drive_v=None, ref_v=None):
    a, b, ku, kx = coefficients(model, acq)
    gain = -b/a
    if acq.kind == "dc_pair":
        # Physical implementation must pass through REF and settle at each level.
        u = np.array([-acq.amplitude_v, acq.amplitude_v])
        x = gain*u
        vin = ku*u + kx*x
        return {"drive_v": (acq.ref_v+u).tolist(),
                "ref_v": [acq.ref_v]*2,
                "in_v": (acq.ref_v+vin).tolist(),
                "out_v": (acq.ref_v+x).tolist(),
                "shunt_drop_v": (u-vin).tolist()}
    t = np.asarray(time_s if time_s is not None else
                   np.arange(0, acq.duration_s+acq.sample_period_s/2,
                             acq.sample_period_s), dtype=float)
    refs = np.asarray(ref_v if ref_v is not None else np.full(t.shape, acq.ref_v))
    drives = np.asarray(drive_v if drive_v is not None else
                       refs+np.where(t < acq.step_at_s, -acq.amplitude_v, acq.amplitude_v))
    if len(t) < 2 or t.shape != refs.shape or t.shape != drives.shape:
        raise ValueError("Mismatched waveform dimensions")
    if not np.all(np.isfinite(t)) or not np.all(np.diff(t)>0):
        raise ValueError("Time must be finite and strictly increasing")
    if not np.all(np.isfinite(refs)) or not np.all(np.isfinite(drives)):
        raise ValueError("Non-finite input waveform")
    u = drives-refs
    x = np.empty_like(u)
    x[0] = gain*u[0]  # acquisition starts from a settled initial level
    for i in range(1,len(t)):
        decay = math.exp(a*(t[i]-t[i-1]))
        x[i] = decay*x[i-1]+gain*(1-decay)*u[i-1]
    vin = ku*u+kx*x
    return {"time_s": t.tolist(), "drive_v": drives.tolist(), "ref_v": refs.tolist(),
            "in_v": (refs+vin).tolist(), "out_v": (refs+x).tolist()}


def observation_vector(prediction: dict, kind: str):
    keys = ("shunt_drop_v",) if kind == "dc_pair" else ("in_v", "out_v")
    return np.concatenate([np.asarray(prediction[k],dtype=float) for k in keys])


ACTION_MENU = {
    "attach_10k_load": Acquisition(load_ohm=10000),
    "attach_shunt_dc_pair": Acquisition(kind="dc_pair",shunt_ohm=1000,amplitude_v=1.0),
}


def confirmation_for(acq: Acquisition):
    # A fresh acquisition at a different amplitude, not a refit of that acquisition.
    return replace(acq, kind="step", amplitude_v=0.3)
