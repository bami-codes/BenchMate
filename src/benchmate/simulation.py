"""Development-only truth fixtures. Never imported by the diagnosis module."""
from dataclasses import asdict
import numpy as np
from .physics import RCModel, Acquisition, predict

FIXTURES = {
    "b1": RCModel(10000,1e-6),
    "b6": RCModel(10000,1e-6,10000),
    "d01-r": RCModel(20000,1e-6),
    "d01-c": RCModel(10000,2e-6),
}


def acquire(model: RCModel, acq: Acquisition, *, rng, noise_sd_v=0.001):
    if not np.isfinite(noise_sd_v) or noise_sd_v < 0:
        raise ValueError("Invalid synthetic noise")
    data = predict(model, acq)
    # First implementation: ideal observed DRIVE/REF, independent Gaussian sensor noise.
    # These assumptions must not be substituted for a calibrated hardware likelihood.
    for key in ("in_v", "out_v"):
        data[key] = (np.asarray(data[key])+rng.normal(0,noise_sd_v,len(data[key]))).tolist()
    if acq.kind == "dc_pair":
        data["shunt_drop_v"] = (np.asarray(data["drive_v"])-data["in_v"]).tolist()
    return {"schema_version":1,"source":"synthetic","settings":asdict(acq),
            "physical_acquisitions":acq.physical_acquisitions,
            "synthetic_noise_sd_v":noise_sd_v,"data":data}

