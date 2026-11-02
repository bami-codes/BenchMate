"""One likelihood for fitting, evidence and regional adequacy checks.

AR(1) sigma is the marginal standard deviation, not innovation SD. Development
defaults are not a hardware calibration or a calibrated false-positive rate.
"""
from dataclasses import dataclass, asdict
import numpy as np


@dataclass(frozen=True)
class NoiseModel:
    sigma_v: float = 0.003
    rho: float = 0.0
    model_floor_v: float = 0.0
    regional_limit: float = 3.0
    provenance: str = "synthetic_development"
    channel_sigma_v: dict | None = None
    channel_rho: dict | None = None

    def __post_init__(self):
        values = [self.sigma_v, self.rho, self.model_floor_v, self.regional_limit]
        if not all(np.isfinite(values)) or self.sigma_v <= 0 or self.model_floor_v < 0:
            raise ValueError("Invalid noise scale")
        if abs(self.rho) >= 0.99 or self.regional_limit <= 0:
            raise ValueError("Invalid AR(1) coefficient or regional threshold")
        for mapping,kind in ((self.channel_sigma_v,'sigma'),(self.channel_rho,'rho')):
            if mapping is None:continue
            if not isinstance(mapping,dict) or not set(mapping)<={'in_v','out_v','shunt_drop_v'}:
                raise ValueError('Invalid per-channel noise keys')
            if any(not np.isfinite(v) or (v<=0 if kind=='sigma' else abs(v)>=.99) for v in mapping.values()):
                raise ValueError('Invalid per-channel noise value')

    def whiten(self, residual, *, independent=False, channel=None):
        r = np.asarray(residual, dtype=float)
        if r.shape[-1] == 0 or not np.all(np.isfinite(r)):
            raise ValueError("Invalid residual")
        scale = np.hypot((self.channel_sigma_v or {}).get(channel,self.sigma_v), self.model_floor_v)
        rho = 0.0 if independent else (self.channel_rho or {}).get(channel,self.rho)
        z = np.empty_like(r)
        z[..., 0] = r[..., 0] / scale
        z[..., 1:] = (r[..., 1:] - rho * r[..., :-1]) / (scale * np.sqrt(1 - rho*rho))
        return z

    def to_dict(self):
        return asdict(self)


def channels(capture):
    return ("shunt_drop_v",) if capture["settings"]["kind"] == "dc_pair" else ("in_v", "out_v")


def regions(capture):
    """Fixed stimulus-relative regions; never selected from residual magnitude."""
    n = len(capture["data"][channels(capture)[0]])
    masks = {"full": np.ones(n, dtype=bool)}
    settings = capture["settings"]
    if settings["kind"] == "step":
        t = np.asarray(capture["data"]["time_s"]) - settings["step_at_s"]
        for lo, hi in [(0, .005), (.005, .020), (.020, .080)]:
            mask = (t >= lo) & (t < hi)
            if mask.sum() >= 3:
                masks[f"transient_{lo:g}_{hi:g}s"] = mask
    elif settings["kind"] == "sine":
        phase = (np.asarray(capture["data"]["time_s"]) * settings["frequency_hz"]) % 1
        for i in range(8):
            mask = (phase >= i/8) & (phase < (i+1)/8)
            if mask.sum() >= 3:
                masks[f"phase_bin_{i}"] = mask
    return masks


def whitened_vector(prediction, capture, noise):
    independent = capture["settings"]["kind"] == "dc_pair"
    return np.concatenate([noise.whiten(np.asarray(capture["data"][k]) - prediction[k], independent=independent,channel=k)
                           for k in channels(capture)], axis=-1)


def adequacy(prediction, capture, noise=NoiseModel(), predictive_whitened_sd=None):
    checks = []
    independent = capture["settings"]["kind"] == "dc_pair"
    for key in channels(capture):
        residual = np.asarray(capture["data"][key]) - prediction[key]
        z = noise.whiten(residual, independent=independent,channel=key)
        if predictive_whitened_sd is not None:
            sd = np.asarray(predictive_whitened_sd[key])
            if sd.shape != z.shape or not np.all(np.isfinite(sd)) or np.any(sd < 0):
                raise ValueError("Invalid predictive uncertainty")
            z = z / np.sqrt(1+sd*sd)
        for name, mask in regions(capture).items():
            score = float(np.sqrt(np.mean(z[mask]**2)))
            checks.append({"channel": key, "region": name, "samples": int(mask.sum()),
                           "normalized_rms": score, "passed": score <= noise.regional_limit})
    return {"passed": all(c["passed"] for c in checks), "checks": checks,
            "regional_limit": noise.regional_limit, "calibrated_false_positive_rate": False,
            "predictive_uncertainty": "marginal_gaussian_approximation" if predictive_whitened_sd is not None else "none"}
