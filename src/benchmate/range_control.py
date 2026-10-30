"""Independent DC anchors and fixed resistor-only wide-range control scores."""
import math
import numpy as np

CONTROL_WAVEFORMS = [
    {'kind':'sine','samples':512,'period_us':4000,'amplitude_v':.2,'frequency_hz':1.},
    {'kind':'step','samples':512,'period_us':500,'amplitude_v':.5},
    {'kind':'sine','samples':512,'period_us':4000,'amplitude_v':.8,'frequency_hz':1.},
]


def freeze_differential_anchor(hold_mean_counts,maps,dmm_input_minus_ref_v,dmm_output_minus_ref_v,*,ref_code,driver_v_per_code):
    means=np.asarray(hold_mean_counts,dtype=float)
    if means.shape!=(4,) or not np.isfinite(means).all():raise ValueError('Four finite HOLD channel means required')
    dmm=[dmm_input_minus_ref_v,dmm_output_minus_ref_v]
    if not all(type(v) in (int,float) and math.isfinite(v) and abs(v)<=.03 for v in dmm):
        raise ValueError('Independent DMM bias must be within 30 mV before the range control')
    if abs(dmm[0]-dmm[1])>.01:raise ValueError('Resistor-only DMM path difference exceeds 10 mV; investigate before stimulus')
    if type(ref_code) is not int or not 0<ref_code<4095 or not math.isfinite(driver_v_per_code) or not .0008<driver_v_per_code<.0015:
        raise ValueError('Frozen driver map and center code required')
    result={}
    for channel,index,value in [('A1',0,dmm[0]),('A2',1,dmm[1])]:
        gain=maps[channel]['gain_v_per_count']
        if not math.isfinite(gain) or not 0<gain<.001:raise ValueError('Invalid frozen channel gain')
        result[channel]={'gain_v_per_count':gain,'offset_to_physical_REF_v':float(value-means[index]*gain),
                         'independent_DMM_bias_v':value,'HOLD_mean_counts':float(means[index])}
    return {'channels':result,'ref_code':ref_code,'driver_v_per_code':driver_v_per_code,
            'scored_OUT_samples_used':0,'gain_fitted':False,'origin_is_not_assumed_zero':True}


def score_resistor_control(rows,settings,anchor):
    r=np.asarray(rows,dtype=float)
    if (settings not in CONTROL_WAVEFORMS or r.shape!=(512,10) or not np.isfinite(r).all()
        or np.any(np.diff(r[:,0])<=0)):
        raise ValueError('Matching fixed control waveform with valid frame timing required')
    values={ch:r[:,col]*anchor['channels'][ch]['gain_v_per_count']+anchor['channels'][ch]['offset_to_physical_REF_v']
            for ch,col in [('A1',2),('A2',3)]}
    residual=values['A2']-values['A1'];t=(r[:,0]+r[:,7])*1e-6
    command_prediction=anchor['channels']['A1']['independent_DMM_bias_v']+anchor['driver_v_per_code']*(r[:,1]-anchor['ref_code'])
    input_residual=values['A1']-command_prediction
    masks=[]
    if settings['kind']=='step':
        relative=t-settings['samples']//10*settings['period_us']*1e-6
        for name,lo,hi in [('pre',None,0),('0_to_5ms',0,5),('5_to_20ms',5,20),('20_to_80ms',20,80),('after_80ms',80,None)]:
            mask=np.ones(len(t),bool)
            if lo is not None:mask&=relative>=lo/1000
            if hi is not None:mask&=relative<hi/1000
            masks.append((name,mask))
    else:
        phase=np.floor(t*settings['frequency_hz']%1*8).astype(int)
        masks=[('phase_'+str(i),phase==i) for i in range(8)]
    regions=[{'name':name,'samples':int(m.sum()),'RMS_mV':float(np.sqrt(np.mean(residual[m]**2)))*1000} for name,m in masks]
    input_regions=[{'name':name,'RMS_mV':float(np.sqrt(np.mean(input_residual[m]**2)))*1000} for name,m in masks]
    rms=float(np.sqrt(np.mean(residual**2)))*1000
    input_rms=float(np.sqrt(np.mean(input_residual**2)))*1000
    a1_span=float(np.percentile(values['A1'],95)-np.percentile(values['A1'],5))
    expected_span=2*settings['amplitude_v']
    checks={'whole_RMS':rms<=9,'all_region_RMS':all(x['samples']>0 and x['RMS_mV']<=9 for x in regions),
            'input_command_RMS':input_rms<=9,'input_command_region_RMS':all(x['RMS_mV']<=9 for x in input_regions),
            'input_excursion':.85*expected_span<=a1_span<=1.05*expected_span,
            'physical_bias_envelope':bool(np.max(np.abs(np.r_[values['A1'],values['A2']]))<=settings['amplitude_v']+.06)}
    return {'RMS_mV':rms,'mean_residual_mV':float(residual.mean())*1000,'regions':regions,
            'input_command_RMS_mV':input_rms,'input_command_regions':input_regions,
            'input_5_to_95_percentile_span_v':a1_span,'checks':checks,'passed':all(checks.values()),
            'predicted_output_minus_REF_v':values['A1'].tolist(),'measured_output_minus_REF_v':values['A2'].tolist(),
            'scored_output_refitted':False,'scope':'Resistor-only range engineering check with independent DMM bias anchors.'}
