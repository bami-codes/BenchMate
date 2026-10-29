"""Offline loaded-response diagnostics; never changes the frozen forecast score."""
from pathlib import Path
import hashlib,json,os
os.environ.setdefault('MPLCONFIGDIR','/private/tmp/benchmate-matplotlib')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from scipy.optimize import minimize_scalar
from benchmate.records import Recorder,read_events

source=Path('runs/hardware-b1-loaded-step/20261029T123058-a10873a74e')
events=read_events(source);assert events[-1]['kind']=='run_completed'
block=next(e['payload'] for e in events if e['kind']=='step_raw_capture')
rows=np.asarray(block['rows']);p=json.loads((source/'prediction.json').read_text())
score=json.loads((source/'prediction-comparison.json').read_text())
maps=p['voltage_conversion']['channels'];i=block['step_index']
times={name:(rows[:,0]+rows[:,j+6]-rows[i,0])*1e-6 for j,name in enumerate(['A1','A2','A3'])}
signals={name:rows[:,j+2]*maps[name]['gain_v_per_count']+maps[name]['offset_v'] for j,name in enumerate(['A1','A2','A3'])}
t=times['A2'];y=signals['A2'];u=signals['A1']
def solve(log_tau):
    X=np.column_stack([np.ones(len(t)),-np.expm1(-np.maximum(t,0)/np.exp(log_tau))])
    c=np.linalg.lstsq(X,y,rcond=None)[0];res=y-X@c
    return float(np.mean(res**2)),c,res
opt=minimize_scalar(lambda x:solve(x)[0],bounds=(np.log(.0001),np.log(.5)),method='bounded',options={'xatol':1e-12})
assert opt.success
mse,c,res=solve(opt.x);tau=float(np.exp(opt.x))
u_low=float(u[:i].mean());u_high=float(u[-100:].mean());gain=float(c[1]/(u_high-u_low))
assert 0<gain<1
load=p['load_resistor_ohm']
estimated_R=load*(1/gain-1)
estimated_C=tau/(estimated_R*load/(estimated_R+load))
forecast=np.asarray(p['predicted_A2_v']);prediction_residual=(y-forecast)*1000
assert abs(float(np.sqrt(np.mean(prediction_residual**2)))-score['RMS_mV'])<1e-10
conditional={'scope':'Post-observation estimates conditional on a single ideal RC and known load; no topology selection or confidence claim',
             'tau_s':tau,'fitted_output_plateaus_v':[float(c[0]),float(c.sum())],
             'measured_input_plateaus_v':[u_low,u_high],
             'input_plateau_windows':'all pre-step A1 samples; final 100 A1 samples',
             'output_to_input_step_gain':gain,'known_load_ohm':load,
             'estimated_R_ohm':estimated_R,'estimated_C_f':estimated_C,
             'formulas':{'R':'Rload*(1/gain-1)','C':'tau/(R || Rload)'},
             'known_B1_R_or_C_used_by_this_fit':False,
             'fit_RMS_mV':float(np.sqrt(mse)*1000),'tau_search_bounds_s':[.0001,.5],
             'samples_trimmed':0,'frozen_prediction_score_changed':False}
result={'source_record':str(source),'source_events_sha256':hashlib.sha256((source/'events.jsonl').read_bytes()).hexdigest(),
        'frozen_prediction_comparison':score,'conditional_RC_estimate':conditional,
        'limits':['The pre-observation forecast used known B1 resistance, so its success is engineering validation, not blind diagnosis.',
                  'The separate conditional fit uses only captured traces and the known added load; it assumes the one-state RC topology.',
                  'Supply-scaled provisional affine maps are not a new calibration or proof of absolute accuracy.',
                  'Input plateau averages, analog read-completion times, buffer input bias and REF stability retain unquantified uncertainty.',
                  'R/C estimates have no calibrated confidence intervals; full D2 acceptance and automated hardware diagnosis remain incomplete.']}
log=Recorder('runs/hardware-b1-loaded-analysis',mode='offline_loaded_RC_descriptive_fit_separate_from_frozen_forecast')
(log.path/'controller-source.py').write_bytes(Path(__file__).read_bytes())
(log.path/'analysis.json').write_text(json.dumps(result,indent=2)+'\n')
log.add('post_observation_conditional_analysis',result)
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False})
fig,(ax,ar)=plt.subplots(2,1,figsize=(11,7.4),gridspec_kw={'height_ratios':[3,1]},layout='constrained')
ax.plot(times['A1']*1000,u,color='#8492a6',lw=1,label='Measured IN (A1)')
ax.plot(t*1000,y,color='#125dcc',lw=1.4,label='New measured OUT (A2)')
ax.plot(np.asarray(p['nominal_A2_step_relative_time_s'])*1000,forecast,color='#dc7c19',ls='--',lw=1.5,label='Prediction saved before loaded capture')
ax.set_xlim(-10,70);ax.set_ylabel('Voltage (V; provisional scaled maps)');ax.set_xlabel('Time from step (ms) · transient detail')
ax.legend(loc='lower right');ax.grid(alpha=.15);ax.set_title('B1 + 9.99 kohm load • Half the swing, faster response',loc='left',fontweight='bold',fontsize=15)
ar.plot(t*1000,prediction_residual,color='#125dcc',lw=.8);ar.axhline(0,color='#8492a6',lw=.7);ar.grid(alpha=.15)
ar.set_xlim(float(t[0]*1000),float(t[-1]*1000));ar.set_ylabel('Prediction residual (mV)');ar.set_xlabel('Time from step (ms) · full capture, all 512 samples')
fig.suptitle(f'Frozen forecast RMS {score["RMS_mV"]:.2f} mV · mean {score["mean_residual_mV"]:+.2f} mV · no prediction refit\nSeparate descriptive fit: gain {gain:.4f}, tau {tau*1000:.2f} ms · known-specimen engineering check, not blind diagnosis',fontsize=10)
fig.savefig(log.path/'loaded-step.png',dpi=180);fig.savefig(log.path/'loaded-step.svg');plt.close(fig)
log.add('run_completed',{'hardware_IO':False,'frozen_prediction_score_changed':False,
                         'conditional_R_ohm':estimated_R,'conditional_C_f':estimated_C,
                         'full_D2_accepted':False,
                         'artifact_sha256':{name:hashlib.sha256((log.path/name).read_bytes()).hexdigest() for name in ['analysis.json','loaded-step.png','loaded-step.svg']}})
print(json.dumps({'record':str(log.path),'conditional_estimate':conditional}))
