"""Private-to-the-simulator development truth, independent Shockley solver.

Not imported by proposal validation or the agent controller. No holdouts here.
"""
import numpy as np
from scipy.optimize import brentq
from .stimulus import commanded_waveform


def acquire_nonlinear(settings, *, rng, r_ohm=10000., noise_sd_v=.001,
                      isat_a=3e-9, ideality=1.9):
    if not (np.isfinite(isat_a) and np.isfinite(ideality) and isat_a>0 and ideality>0):
        raise ValueError('Invalid simulator diode')
    data=commanded_waveform(settings)
    u=np.asarray(data['drive_v'])-data['ref_v']
    # Simulator truth deliberately differs from the proposal library start.
    thermal=8.617333262145e-5*300.15
    isat,n,rs=isat_a,ideality,1.
    gl=0 if settings.load_ohm is None else 1/settings.load_ohm
    def output(vin):
        def balance(vd):
            current=isat*np.expm1(vd/(n*thermal))
            out=vd+rs*current
            return (vin-out)/(r_ohm+settings.shunt_ohm)-gl*out-current
        vd=brentq(balance,min(vin,0)-.001,max(vin,0)+.001,xtol=1e-14)
        return vd+rs*isat*np.expm1(vd/(n*thermal))
    out=np.array([output(v) for v in u])
    current=(u-out)/(r_ohm+settings.shunt_ohm)
    data['in_v']=(np.asarray(data['drive_v'])-settings.shunt_ohm*current+rng.normal(0,noise_sd_v,len(u))).tolist()
    data['out_v']=(np.asarray(data['ref_v'])+out+rng.normal(0,noise_sd_v,len(u))).tolist()
    return {'schema_version':1,'source':'synthetic','settings':settings.to_dict(),
            'physical_acquisitions':1,'data':data}
