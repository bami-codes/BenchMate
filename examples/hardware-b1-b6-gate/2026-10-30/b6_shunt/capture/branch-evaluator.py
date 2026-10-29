"""Two declared input-branch alternatives from settled shunt voltage contrast."""
import math
import numpy as np


def settled_branch_evidence(frame_time_s, input_v, drive_v, *, step_index,
                            shunt_ohm, branch_ohm, limit_v=.009,
                            minimum_drive_excursion_v=.30):
    frames, inputs, drive = [np.asarray(v,dtype=float) for v in (frame_time_s,input_v,drive_v)]
    if (any(v.ndim!=1 or not np.isfinite(v).all() for v in [frames,inputs,drive])
            or len(frames)!=len(inputs) or len(frames)!=len(drive)
            or type(step_index) is not int or not 1<=step_index<len(frames)-100):
        raise ValueError('Finite matching arrays and separate low/high windows required')
    if np.any(np.diff(frames)<=0) or frames[-100]-frames[step_index]<.150:
        raise ValueError('High window must start at least 150 ms after the step')
    if (not all(math.isfinite(v) for v in [shunt_ohm,branch_ohm,limit_v,minimum_drive_excursion_v])
            or shunt_ohm<0 or branch_ohm<=0 or limit_v<=0 or minimum_drive_excursion_v<=0):
        raise ValueError('Invalid declared resistance or engineering limit')
    low=slice(0,step_index);high=slice(-100,None)
    path=drive-inputs
    low_drop=float(path[low].mean());high_drop=float(path[high].mean())
    drive_delta=float(drive[high].mean()-drive[low].mean())
    observed=high_drop-low_drop
    if drive_delta<minimum_drive_excursion_v:
        raise ValueError('Measured DRIVE excursion too small or reversed')
    predictions={'no_input_branch':0.,'input_branch':drive_delta*shunt_ohm/(shunt_ohm+branch_ohm)}
    scores={name:{'predicted_contrast_v':predicted,'residual_mV':(observed-predicted)*1000,
                  'passed':bool(abs(observed-predicted)<=limit_v)} for name,predicted in predictions.items()}
    return {'scope':'Two declared branch alternatives; engineering thresholds, not calibrated confidence.',
            'drive_excursion_v':drive_delta,'observed_drop_contrast_v':observed,
            'normalized_drop_contrast':observed/drive_delta,
            'low_drop_mean_v':low_drop,'high_drop_mean_v':high_drop,
            'low_path_sample_SD_mV':float(path[low].std(ddof=1))*1000 if step_index>1 else None,
            'high_path_sample_SD_mV':float(path[high].std(ddof=1))*1000,
            'low_samples':step_index,'high_samples':100,'trimmed_samples':0,
            'two_levels_in_one_step_block':True,'independent_DC_blocks':0,
            'shunt_ohm':shunt_ohm,'branch_ohm':branch_ohm,'absolute_error_limit_mV':limit_v*1000,
            'scores':scores,'supported_alternatives':[name for name,s in scores.items() if s['passed']]}
