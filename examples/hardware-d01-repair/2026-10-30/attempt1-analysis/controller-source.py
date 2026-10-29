"""Descriptive repair dynamics; does not alter the frozen validation failures."""
from pathlib import Path
import os,sys,json,hashlib
os.environ.setdefault('MPLCONFIGDIR','/private/tmp/benchmate-matplotlib')
ROOT=Path('/Users/bami/Documents/metaai');sys.path.insert(0,str(ROOT/'src'))
import numpy as np
from scipy.optimize import minimize_scalar
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from benchmate.records import Recorder,read_events

source=Path((ROOT/'runs/d01-repair-capture-path.txt').read_text().strip())
events=read_events(source);assert events[-1]['kind']=='run_completed'
p=json.loads((source/'prediction.json').read_text());validation=json.loads((source/'result.json').read_text())
step=next(e['payload'] for e in events if e['kind']=='step_raw_capture')
rows=np.asarray(step['rows']);index=step['step_index'];maps=p['voltage_conversion']['channels']
t=(rows[:,0]+rows[:,7]-rows[index,0])*1e-6
y=rows[:,3]*maps['A2']['gain_v_per_count']+maps['A2']['offset_v']
u=rows[:,2]*maps['A1']['gain_v_per_count']+maps['A1']['offset_v']
def fit(mask):
    tt=t[mask];yy=y[mask]
    def solve(logtau):
        X=np.column_stack([np.ones(len(tt)),-np.expm1(-np.maximum(tt,0)/np.exp(logtau))])
        c=np.linalg.lstsq(X,yy,rcond=None)[0];r=yy-X@c
        return float(np.mean(r*r)),c
    opt=minimize_scalar(lambda x:solve(x)[0],bounds=(np.log(.0001),np.log(.5)),method='bounded',options={'xatol':1e-12})
    assert opt.success
    mse,c=solve(opt.x)
    return {'tau_s':float(np.exp(opt.x)),'low_output_v':float(c[0]),'high_output_v':float(c.sum()),'fit_RMS_mV':float(np.sqrt(mse)*1000)}
full=fit(np.ones(len(t),dtype=bool));early=fit(t<=.050)
ulo=float(u[:index].mean());uhi=float(u[-100:].mean())
gain=(full['high_output_v']-full['low_output_v'])/(uhi-ulo)
plan=json.loads((ROOT/p['model_plan']).read_text());load=plan['load_ohm']
R=load*(1/gain-1);C=full['tau_s']/(R*load/(R+load))
diagnostic={}
for waveform in p['waveforms']:
    kind=waveform['settings']['kind'];raw=next(e['payload'] for e in events if e['kind']==kind+'_raw_capture')
    data=np.asarray(raw['rows']);observed=data[:,3]*maps['A2']['gain_v_per_count']+maps['A2']['offset_v']
    residual=(observed-np.asarray(waveform['predictions']['repair_to_declared_nominal_C']['predicted_A2_v']))*1000
    saved=validation['scores'][kind]['models']['repair_to_declared_nominal_C']
    assert abs(np.sqrt(np.mean(residual**2))-saved['RMS_mV'])<1e-10
    diagnostic[kind]={'mean_residual_mV':float(residual.mean()),'mean_centered_RMS_mV':float(residual.std()),
        'mean_centering_diagnostic_only':True,'original_passed':saved['passed'],'original_RMS_mV':saved['RMS_mV']}
result={'source_record':str(source.relative_to(ROOT)),'events_sha256':hashlib.sha256((source/'events.jsonl').read_bytes()).hexdigest(),
    'original_repair_engineering_check_passed':validation['repair_engineering_check_passed'],'frozen_scores_changed':False,
    'descriptive_step_fit':full,'first_50ms_fit':early,'input_plateaus_v':[ulo,uhi],
    'conditional_gain':gain,'conditional_R_ohm':R,'conditional_C_f':C,
    'repair_predicted_tau_s':plan['models']['repair_to_declared_nominal_C']['loaded_tau_s'],
    'pre_repair_tau_s':plan['models']['no_repair_counterfactual']['loaded_tau_s'],
    'posthoc_residual_diagnostics':diagnostic,'A4_mean_span_mV':validation['A4_mean_span_mV'],
    'no_trimmed_samples':True,'fit_used_for_original_score':False,'full_D2_accepted':False,'Spark_invoked':False,
    'interpretation':'Report descriptive dynamics separately from the failed absolute-voltage forecasts. A mean offset does not establish its physical cause and is not a permitted retrospective correction.'}
log=Recorder(ROOT/'runs/hardware-d01-repair-analysis',mode='offline_descriptive_repair_dynamics_original_scores_unchanged')
(log.path/'controller-source.py').write_bytes(Path(__file__).read_bytes())
(log.path/'analysis.json').write_text(json.dumps(result,indent=2)+'\n');log.add('descriptive_analysis',result)
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False})
fig,axes=plt.subplots(2,2,figsize=(12.5,7),gridspec_kw={'height_ratios':[3,1.3]},layout='constrained')
colors={'repair_to_declared_nominal_C':'#1458b6','no_repair_counterfactual':'#7b8392'}
for col,w in enumerate(p['waveforms']):
    kind=w['settings']['kind'];raw=next(e['payload'] for e in events if e['kind']==kind+'_raw_capture');rr=np.asarray(raw['rows'])
    tt=(rr[:,0]+rr[:,7])*1e-6;nominal=np.asarray(w['nominal_A2_time_s'])
    if kind=='step':tt-=w['settings']['samples']//10*w['settings']['period_us']*1e-6;nominal-=w['settings']['samples']//10*w['settings']['period_us']*1e-6
    yy=rr[:,3]*maps['A2']['gain_v_per_count']+maps['A2']['offset_v']
    ax=axes[0,col];ar=axes[1,col]
    ax.plot(tt*1000,yy,color='#b65b16',lw=1,label='Observed OUT')
    for name,m in w['predictions'].items():
        label='Frozen repair model' if name.startswith('repair') else 'Frozen no-repair model'
        ax.plot(nominal*1000,m['predicted_A2_v'],ls='--',color=colors[name],lw=1.2,label=label)
        ar.plot(tt*1000,(yy-np.asarray(m['predicted_A2_v']))*1000,color=colors[name],lw=.7)
    ax.set_title(('Step' if kind=='step' else '5 Hz sine')+' | absolute forecast failed',loc='left',fontweight='bold')
    ax.set_ylabel('Voltage (V; provisional conversion)');ax.grid(alpha=.15);ax.legend(fontsize=8)
    if kind=='step':ax.set_xlim(-10,80)
    ar.axhline(0,color='#999',lw=.7);ar.grid(alpha=.15);ar.set_xlabel('Time (ms; all captured samples below)');ar.set_ylabel('Residual (mV)')
fig.suptitle('D01 physical repair, attempt 1 | frozen scores retained\nRepair RMS: step 12.03 mV, sine 13.12 mV; 9 mV limits exceeded. No offset or parameter refit in scores.',fontsize=12)
fig.savefig(log.path/'repair-attempt1.png',dpi=170);fig.savefig(log.path/'repair-attempt1.svg');plt.close(fig)
log.add('run_completed',{'hardware_IO':False,'frozen_scores_changed':False,'original_repair_engineering_check_passed':False})
(ROOT/'runs/d01-repair-analysis-path.txt').write_text(str(log.path)+'\n')
print(json.dumps({'record':str(log.path),'tau_ms':full['tau_s']*1000,'early_tau_ms':early['tau_s']*1000,'gain':gain,'R_ohm':R,'C_uF':C*1e6,'fit_RMS_mV':full['fit_RMS_mV'],'residual_diagnostics':diagnostic}))
