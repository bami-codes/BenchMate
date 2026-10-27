"""Private-to-the-simulator development truth, independent Shockley solver.

Not imported by proposal validation or the agent controller. No holdouts here.
"""
import numpy as np
from scipy.optimize import brentq
from .physics import RCModel,predict


def acquire_nonlinear(settings, *, rng, r_ohm=10000., noise_sd_v=.001):
    data=predict(RCModel(10000,1e-6),settings)
    u=np.asarray(data['drive_v'])-data['ref_v']
    # Generic library diode at 27 C: IS=1nA, N=1.8, RS=1 ohm.
    thermal=8.617333262145e-5*300.15
    isat,n,rs=1e-9,1.8,1.
    gl=0 if settings.load_ohm is None else 1/settings.load_ohm
    def output(vin):
        def balance(vd):
            current=isat*np.expm1(vd/(n*thermal))
            out=vd+rs*current
            return (vin-out)/r_ohm-gl*out-current
        vd=brentq(balance,min(vin,0)-.001,max(vin,0)+.001,xtol=1e-14)
        return vd+rs*isat*np.expm1(vd/(n*thermal))
    out=np.array([output(v) for v in u])
    data['in_v']=(np.asarray(data['drive_v'])+rng.normal(0,noise_sd_v,len(u))).tolist()
    data['out_v']=(np.asarray(data['ref_v'])+out+rng.normal(0,noise_sd_v,len(u))).tolist()
    return {'schema_version':1,'source':'synthetic','settings':settings.to_dict(),
            'physical_acquisitions':1,'data':data}
