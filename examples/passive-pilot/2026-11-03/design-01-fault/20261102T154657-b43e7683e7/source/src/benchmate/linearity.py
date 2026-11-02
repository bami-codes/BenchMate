"""Training-only amplitude scaling diagnostic; no circuit topology is fitted."""
import numpy as np
from .noise import NoiseModel


def amplitude_scaling(captures,noise=NoiseModel()):
    checks=[]
    for i,small in enumerate(captures):
        a=small['settings']
        if a['kind']!='sine' or a['shunt_ohm']:continue
        geometry={k:v for k,v in a.items() if k!='amplitude_v'}
        for j,large in enumerate(captures):
            b=large['settings']
            if b['amplitude_v']<=a['amplitude_v'] or geometry!={k:v for k,v in b.items() if k!='amplitude_v'}:continue
            if small['source']!=large['source']:continue
            t=np.asarray(small['data']['time_s']);other=np.asarray(large['data']['time_s'])
            if t.shape!=other.shape or not np.allclose(t,other,atol=1e-9,rtol=0):continue
            ratio=b['amplitude_v']/a['amplitude_v'];scores={}
            for channel in ('in_v','out_v'):
                low=np.asarray(small['data'][channel])-small['data']['ref_v']
                high=np.asarray(large['data'][channel])-large['data']['ref_v']
                delta=(high-high.mean())-ratio*(low-low.mean())
                scores[channel]={'dc_removed_rms_mv':float(1000*np.sqrt(np.mean(delta**2))),
                    'normalized_rms':float(np.sqrt(np.mean(noise.whiten(delta,channel=channel)**2)/(1+ratio**2)))}
            input_matches=scores['in_v']['normalized_rms']<=noise.regional_limit
            output_matches=scores['out_v']['normalized_rms']<=noise.regional_limit
            checks.append({'training_capture_indices':[i,j],'settings_small':a,'settings_large':b,
                'amplitude_ratio':ratio,'channels':scores,
                'status':'input_scaling_mismatch' if not input_matches else 'scaling_consistent' if output_matches else 'output_scaling_mismatch',
                'development_limit':noise.regional_limit,'calibrated_false_positive_rate':False,
                'independent_verification':False,
                'scope':'Training-only diagnostic. Assumes matched timing, settled states and independent capture noise; DC offsets removed. Input scaling is checked. Output-path nonlinearity is not uniquely a DUT diode; fixture saturation must be excluded by calibration.'})
    return {'checks':checks,'topology_fitted':False,'data_role':'training_diagnostic'}
