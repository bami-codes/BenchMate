"""Unloaded observation-only tau fit: no specimen values or assembly files read."""
from pathlib import Path
import hashlib,json,os
os.environ.setdefault('MPLCONFIGDIR','/private/tmp/benchmate-matplotlib')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from scipy.optimize import minimize_scalar
from benchmate.records import Recorder,read_events
source=Path('runs/hardware-d01-unloaded-step/20261029T133852-ab118d1f72')
events=read_events(source)
assert events[-1]['kind']=='run_completed'
block=next(e['payload'] for e in events if e['kind']=='step_raw_capture')
profile=json.loads((source/'provisional-calibration.json').read_text())
rows=np.asarray(block['rows']); step_us=rows[block['step_index'],0]
signals={};times={}
for i,name in enumerate(['A1','A2','A3']):
 c=profile['channels'][name]
 signals[name]=rows[:,i+2]*c['gain_v_per_count']+c['offset_v']
 times[name]=(rows[:,0]+rows[:,i+6]-step_us)*1e-6
t=times['A2'];y=signals['A2']
def fit(mask):
 def solution(log_tau):
  basis=-np.expm1(-np.maximum(t,0)/np.exp(log_tau))
  X=np.column_stack((np.ones(len(t)),basis))
  levels=np.linalg.lstsq(X[mask],y[mask],rcond=None)[0]
  residual=y-X@levels
  return float(np.mean(residual[mask]**2)),levels,residual
 opt=minimize_scalar(lambda a:solution(a)[0],bounds=(np.log(.0001),np.log(.5)),method='bounded',options={'xatol':1e-12})
 if not opt.success: raise ValueError('Tau fit did not converge')
 mse,levels,residual=solution(opt.x)
 return {'tau_s':float(np.exp(opt.x)),'low_output_v':float(levels[0]),'high_output_v':float(levels.sum()),'fit_RMS_mV':float(np.sqrt(mse)*1000),'fitted_samples':int(mask.sum())},residual
primary,residual=fit(np.ones(len(t),dtype=bool));sensitivity,_=fit(t<=.05)
regions={}
for name,mask in [('pre_step',t<0),('0_to_5ms',(t>=0)&(t<.005)),('5_to_20ms',(t>=.005)&(t<.020)),('20_to_80ms',(t>=.020)&(t<.080)),('after_80ms',t>=.080)]:
 regions[name]={'samples':int(mask.sum()),'RMS_mV':float(np.sqrt(np.mean(residual[mask]**2))*1000),'max_abs_mV':float(np.max(abs(residual[mask]))*1000)}
tau=primary['tau_s']
result={'source_record':str(source),'raw_events_sha256':hashlib.sha256((source/'events.jsonl').read_bytes()).hexdigest(),'method':'Unweighted variable-projection exponential fit: offset, amplitude and log(tau); all 512 samples; no trimming','post_capture_training_fit':True,'tau_search_bounds_s':[.0001,.5],'step_origin':'Recorded DAC-write-completion frame; per-channel ADC read-completion timestamps','primary_fit':primary,'first_50ms_plus_prestep_sensitivity_fit':sensitivity,'residual_regions':regions,'identified':'Unloaded effective time constant only; R versus C remains unresolved','declared_design':{'R_ohm':10000,'C_f':1e-6},'illustrative_equal_tau_alternatives':[{'assumption':'nominal R retained','R_ohm':10000,'C_f':tau/10000},{'assumption':'nominal C retained','R_ohm':tau/1e-6,'C_f':1e-6}],'alternatives_are_not_separate_parameter_estimates':True,'component_truth_used_by_fit':False,'assembly_files_read':False,'new_data_independent_prediction_check':False,'full_D2_accepted':False,'hardware_automated_diagnosis_performed':False,'limits':['Provisional path calibration; A2 includes its buffer.','Read-completion times are not calibrated sample apertures.','No calibrated confidence, individual component conclusion, or unique topology identification.','Finite driver/buffer response and supply drift remain.','The fitting residual is not an independent verification score.']}
log=Recorder('runs/hardware-d01-unloaded-analysis',mode='observation_only_unloaded_tau_fit_R_C_unresolved')
(log.path/'controller-source.py').write_bytes(Path(__file__).read_bytes())
(log.path/'analysis.json').write_text(json.dumps(result,indent=2)+'\n');log.add('unloaded_response_analysis',result)
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False})
fig,(ax,ar)=plt.subplots(2,1,figsize=(11,7),gridspec_kw={'height_ratios':[3,1.1]},layout='constrained')
ax.plot(times['A1']*1000,signals['A1'],color='#8092a6',lw=.9,label='Measured IN (A1)')
ax.plot(t*1000,y,color='#125dcc',lw=1.1,label='Measured OUT (A2)')
ax.plot(t*1000,y-residual,color='#dc7c19',lw=1.5,ls='--',label=f'Exponential fit: tau = {tau*1000:.2f} ms')
ax.set_xlim(-10,130);ax.set_ylabel('Voltage (V; provisional calibration)');ax.set_xlabel('Time from commanded step (ms; detail)');ax.legend(loc='lower right');ax.grid(alpha=.15)
ax.set_title('D01 • Slower response observed; R or C still unresolved',loc='left',fontsize=15,fontweight='bold')
ar.plot(t*1000,residual*1000,color='#125dcc',lw=.7);ar.axhline(0,color='#8092a6',lw=.6);ar.set_xlim(t[0]*1000,t[-1]*1000);ar.set_ylabel('Fit residual (mV)');ar.set_xlabel('Full captured block (ms; every sample retained)');ar.grid(alpha=.15)
fig.suptitle('512 frames · 0.5 ms target interval · no overruns\nTraining fit only. The same unloaded time constant can come from different R and C values.',fontsize=10)
fig.savefig(log.path/'unloaded-step.png',dpi=170);fig.savefig(log.path/'unloaded-step.svg');plt.close(fig)
log.add('run_completed',{'hardware_IO':False,'unloaded_R_C_unresolved':True,'analysis_sha256':hashlib.sha256((log.path/'analysis.json').read_bytes()).hexdigest(),'independent_verification':False})
print(json.dumps({'record':str(log.path),'tau_ms':tau*1000,'fit_RMS_mV':primary['fit_RMS_mV'],'sensitivity_tau_ms':sensitivity['tau_s']*1000,'regions':regions,'illustrative_equal_tau_alternatives':result['illustrative_equal_tau_alternatives']}))
