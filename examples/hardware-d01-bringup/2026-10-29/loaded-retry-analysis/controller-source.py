"""Post-observation loaded RC fit; frozen voltage-check failures remain failures."""
from pathlib import Path
import hashlib,json,os
os.environ.setdefault('MPLCONFIGDIR','/private/tmp/benchmate-matplotlib')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from scipy.optimize import minimize_scalar
from benchmate.records import Recorder,read_events
source=Path('runs/hardware-d01-loaded-step-retry/20261029T140554-4e082f6c06');events=read_events(source)
assert events[-1]['kind']=='run_completed'
b=next(e['payload'] for e in events if e['kind']=='step_raw_capture');rows=np.asarray(b['rows']);i=b['step_index']
p=json.loads((source/'prediction.json').read_text());score=json.loads((source/'prediction-comparison.json').read_text());maps=p['voltage_conversion']['channels']
times={ch:(rows[:,0]+rows[:,j+6]-rows[i,0])*1e-6 for j,ch in enumerate(['A1','A2','A3'])}
signals={ch:rows[:,j+2]*maps[ch]['gain_v_per_count']+maps[ch]['offset_v'] for j,ch in enumerate(['A1','A2','A3'])}
t=times['A2'];y=signals['A2'];u=signals['A1']
def solve(logtau):
 X=np.column_stack([np.ones(len(t)),-np.expm1(-np.maximum(t,0)/np.exp(logtau))]);c=np.linalg.lstsq(X,y,rcond=None)[0];res=y-X@c
 return float(np.mean(res**2)),c,res
opt=minimize_scalar(lambda a:solve(a)[0],bounds=(np.log(.0001),np.log(.5)),method='bounded',options={'xatol':1e-12})
assert opt.success
mse,c,res=solve(opt.x);tau=float(np.exp(opt.x));ulo=float(u[:i].mean());uhi=float(u[-100:].mean());gain=float(c[1]/(uhi-ulo));assert 0<gain<1
load=p['load_resistor_ohm'];R=load*(1/gain-1);C=tau/(R*load/(R+load))
residuals={name:(y-np.asarray(model['predicted_A2_v']))*1000 for name,model in p['models'].items()}
for name,r in residuals.items(): assert abs(float(np.sqrt(np.mean(r*r)))-score['model_scores'][name]['RMS_mV'])<1e-10
range_checks={}
for name,model in p['models'].items():
 r=model['conditional_ranges'];range_checks[name]={'gain_within_predeclared_range':bool(r['gain_range'][0]<=gain<=r['gain_range'][1]),'tau_within_predeclared_range':bool(r['loaded_tau_range_s'][0]<=tau<=r['loaded_tau_range_s'][1])}
conditional={'scope':'Descriptive estimates conditional on ideal RC and measured fixture load; not calibrated confidence or topology proof','tau_s':tau,'gain':gain,'R_ohm':R,'C_f':C,'fit_RMS_mV':float(np.sqrt(mse)*1000),'fitted_output_plateaus_v':[float(c[0]),float(c.sum())],'measured_input_plateaus_v':[ulo,uhi],'input_windows':'all pre-step A1 samples; final 100 A1 samples','tau_search_bounds_s':[.0001,.5],'known_specimen_R_C_used':False,'assembly_files_read':False,'trimmed_samples':0}
result={'source_record':str(source),'events_sha256':hashlib.sha256((source/'events.jsonl').read_bytes()).hexdigest(),'frozen_comparison':score,'conditional_RC_estimate':conditional,'conditional_feature_range_checks':range_checks,'representative_prediction_passed':bool(score['passing_representative_points']),'frozen_score_changed':False,'posthoc_centered_residual_RMS_mV':{name:float(np.std(r)) for name,r in residuals.items()},'centered_residual_is_diagnostic_only_not_a_rescore':True,'status':'Second development attempt: C-change representative point passed all predeclared voltage checks; R-change point did not. First failed attempt remains separate and unchanged. REF/path alignment precedes repair verification.','full_D2_accepted':False,'Spark_invoked':False,'limits':['No loaded trace used to change either frozen forecast.','This is a development repeat after a failure and new reference report, not an untouched holdout or a first-attempt success.','Provisional cross-channel gains affect inferred R and C; no calibrated intervals are given.','Mean residual could reflect reference drift or fixture/calibration error; no physical cause is established.']}
log=Recorder('runs/hardware-d01-loaded-retry-analysis',mode='descriptive_repeat_fit_first_failure_preserved_separately')
(log.path/'controller-source.py').write_bytes(Path(__file__).read_bytes());(log.path/'analysis.json').write_text(json.dumps(result,indent=2)+'\n');log.add('post_observation_analysis',result)
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False})
fig,(ax,ar)=plt.subplots(2,1,figsize=(11,7.4),gridspec_kw={'height_ratios':[3,1.2]},layout='constrained')
colors={'nominal_R_changed_C':'#125dcc','changed_R_nominal_C':'#87909e'}
labels={'nominal_R_changed_C':'C-change prediction (checks passed)','changed_R_nominal_C':'R-change prediction (check failed)'}
ax.plot(t*1000,y,color='#dc7c19',lw=1.4,label='New observed OUT')
for name,model in p['models'].items():
 ax.plot(np.asarray(p['nominal_A2_step_relative_time_s'])*1000,model['predicted_A2_v'],ls='--',lw=1.4,color=colors[name],label=labels[name])
 ar.plot(t*1000,residuals[name],color=colors[name],lw=.8,label=name.split('_')[0])
ax.set_xlim(-10,80);ax.set_ylabel('Voltage (V; provisional path maps)');ax.set_xlabel('Time from step (ms; transient detail)');ax.legend(loc='lower right',fontsize=9);ax.grid(alpha=.15)
ax.set_title('D01 + load, attempt 2 • C prediction passes; R prediction fails',loc='left',fontweight='bold',fontsize=13)
ar.axhline(0,color='#777',lw=.6);ar.set_xlim(t[0]*1000,t[-1]*1000);ar.set_ylabel('Prediction residual (mV)');ar.set_xlabel('Full captured block (ms; all 512 samples)');ar.grid(alpha=.15)
fig.suptitle(f'C prediction RMS {score["model_scores"]["nominal_R_changed_C"]["RMS_mV"]:.2f} mV; R prediction RMS {score["model_scores"]["changed_R_nominal_C"]["RMS_mV"]:.2f} mV\nC passed whole and regional checks; R failed. Predictions unchanged; first attempt retained.',fontsize=10)
fig.savefig(log.path/'loaded-comparison.png',dpi=170);fig.savefig(log.path/'loaded-comparison.svg');plt.close(fig)
log.add('run_completed',{'hardware_IO':False,'frozen_validation_passed':bool(score['passing_representative_points']),'repair_requested':False,'artifact_sha256':{name:hashlib.sha256((log.path/name).read_bytes()).hexdigest() for name in ['analysis.json','loaded-comparison.png','loaded-comparison.svg']}})
print(json.dumps({'record':str(log.path),'conditional':conditional,'range_checks':range_checks,'centered_residual_RMS_mV':result['posthoc_centered_residual_RMS_mV']}))
