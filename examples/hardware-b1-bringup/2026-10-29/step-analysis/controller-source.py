"""Offline descriptive step fit, followed by a frozen engineering sine forecast."""
from pathlib import Path
import hashlib
import json
import os
os.environ.setdefault('MPLCONFIGDIR', '/private/tmp/benchmate-matplotlib')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from scipy.optimize import minimize_scalar
from benchmate.records import Recorder, read_events
from benchmate.instrument import InstrumentConfig, capture_command

source = Path('runs/hardware-b1-first-step/20261029T113934-a5eb22cf7d')
events = read_events(source)
assert events[-1]['kind'] == 'run_completed'
block = next(e['payload'] for e in events if e['kind'] == 'step_raw_capture')
profile = json.loads((source/'provisional-calibration.json').read_text())
rows = np.asarray(block['rows']); index = block['step_index']
step_origin_us = rows[index, 0]
signals = {}; times = {}
for i, name in enumerate(['A1', 'A2', 'A3']):
    c = profile['channels'][name]
    signals[name] = rows[:, i+2]*c['gain_v_per_count']+c['offset_v']
    times[name] = (rows[:, 0]+rows[:, i+6]-step_origin_us)*1e-6
t=times['A2']; y=signals['A2']

def fit(mask):
    def solution(log_tau):
        basis = -np.expm1(-np.maximum(t, 0)/np.exp(log_tau))
        X = np.column_stack((np.ones(len(t)), basis))
        levels = np.linalg.lstsq(X[mask], y[mask], rcond=None)[0]
        residual = y-X@levels
        return float(np.mean(residual[mask]**2)), levels, residual
    optimum=minimize_scalar(lambda a:solution(a)[0], bounds=(np.log(.0001),np.log(.5)),
                            method='bounded', options={'xatol':1e-12})
    if not optimum.success: raise ValueError('Tau fit did not converge')
    mse, levels, residual=solution(optimum.x)
    return {'tau_s':float(np.exp(optimum.x)), 'low_output_v':float(levels[0]),
            'high_output_v':float(levels.sum()), 'fit_RMS_mV':float(np.sqrt(mse)*1000),
            'fitted_samples':int(mask.sum())}, residual

primary,residual=fit(np.ones(len(t),dtype=bool))
sensitivity,_=fit(t<=.05)
regions={}
for name, mask in [('pre_step',t<0),('0_to_5ms',(t>=0)&(t<.005)),
                   ('5_to_20ms',(t>=.005)&(t<.020)),('20_to_80ms',(t>=.020)&(t<.080)),
                   ('0_to_50ms',(t>=0)&(t<=.050)),('after_80ms',t>=.080)]:
    regions[name]={'samples':int(mask.sum()),'RMS_mV':float(np.sqrt(np.mean(residual[mask]**2))*1000),
                   'max_abs_mV':float(np.max(np.abs(residual[mask]))*1000)}
reference_tau=.00983016  # Assembly/evaluation comparison only, after unconstrained fit.
result={'source_record':str(source),'raw_events_sha256':hashlib.sha256((source/'events.jsonl').read_bytes()).hexdigest(),
        'method':'Unweighted variable-projection exponential step fit: offset, amplitude and log(tau); no sample trimming',
        'post_capture_exploratory_analysis':True,'tau_search_bounds_s':[.0001,.5],
        'step_origin':'Recorded DAC-write-completion frame at commanded transition; A2 read-completion time used',
        'primary_fit':primary,'first_50ms_plus_prestep_sensitivity_fit':sensitivity,'residual_regions':regions,
        'component_reference_comparison':{'reported_R_ohm':9990,'reported_C_f':.984e-6,
            'RC_reference_s':reference_tau,'tau_difference_percent':100*(primary['tau_s']/reference_tau-1),
            'component_truth_used_by_fit':False,'meter_accuracy_known':False},
        'identified':'Effective unloaded time constant only; R and C are not separately identified',
        'full_D2_accepted':False,'blind_diagnosis_or_repair_verification':False,
        'limits':['A1-A3 affine calibration is provisional; A2 includes its buffer.',
                  'Per-channel read-completion timestamps are not calibrated ADC sample apertures.',
                  'Fitted residual is training fit, not independent validation or an accuracy certificate.',
                  'Supply/reference drift, finite fixture response and meter uncertainty remain.',
                  'No individual R/C conclusion or calibrated confidence interval is asserted.']}
log=Recorder('runs/hardware-b1-step-analysis',mode='offline_exploratory_tau_fit_and_pre_observation_sine_forecast')
(log.path/'controller-source.py').write_bytes(Path(__file__).read_bytes())
(log.path/'analysis.json').write_text(json.dumps(result,indent=2)+'\n')
log.add('step_fit_analysis',result)

# A new engineering condition, not an unopened final evaluation specimen.
# Freeze the output's DC-equilibrium-vs-DAC relation from the step fit and
# tau before acquiring sine data. No later amplitude/offset/phase refit.
config=InstrumentConfig(**events[-1]['payload']['configuration'])
boot=events[-1]['payload']['boot_id']
request=capture_command(config,boot_id=boot,kind='sine',frequency_hz=5,amplitude_v=.2,samples=512,period_us=2000)
amplitude=int(request.split()[5]); period=.002; warmup=600
low_code=int(rows[0,1]); high_code=int(rows[-1,1])
slope=(primary['high_output_v']-primary['low_output_v'])/(high_code-low_code)
intercept=primary['low_output_v']-slope*low_code
tau=primary['tau_s']; state=slope*config.ref_code+intercept
forecast=[]; codes=[]
for n in range(warmup+512):
    x=amplitude*np.sin(2*np.pi*5*n*period)
    rounded=int(np.floor(x+.5) if x>=0 else np.ceil(x-.5))
    code=config.ref_code+rounded; equilibrium=slope*code+intercept
    sample=equilibrium+(state-equilibrium)*np.exp(-.000105/tau)
    state=equilibrium+(state-equilibrium)*np.exp(-period/tau)
    if n>=warmup: forecast.append(float(sample)); codes.append(code)
prediction={'scope':'Frozen-parameter B1 engineering check on a new waveform; not formal evaluation or full D2 acceptance',
            'source_step_record':str(source),'boot_id':boot,'configuration':events[-1]['payload']['configuration'],
            'command':request.decode().strip(),'kind':'sine','frequency_hz':5,'amplitude_v':.2,'samples':512,
            'period_us':2000,'warmup_frames':warmup,'A2_read_completion_offset_us_assumed':105,
            'tau_s':tau,'output_equilibrium_v_per_DAC_code':slope,'output_equilibrium_intercept_v':intercept,
            'nominal_sample_time_s':[(i*2000+105)*1e-6 for i in range(512)],
            'expected_DAC_codes':codes,'predicted_A2_v':forecast,
            'provisional_profile_sha256':hashlib.sha256((source/'provisional-calibration.json').read_bytes()).hexdigest(),
            'no_validation_parameter_or_phase_refit':True,'fixed_phase_bins':8,
            'engineering_limits':{'all_sample_RMS_mV_max':9.0,'each_phase_bin_RMS_mV_max':9.0,
                                  'sample_time_error_us_max':25,'DAC_code_difference_max':1},
            'threshold_basis':'Existing developmental 3 x 3mV engineering allowance, not a calibrated statistical test',
            'all_samples_retained':True}
(log.path/'frozen-sine-prediction.json').write_text(json.dumps(prediction,indent=2)+'\n')
log.add('sine_prediction_frozen',{'file':'frozen-sine-prediction.json','sha256':hashlib.sha256((log.path/'frozen-sine-prediction.json').read_bytes()).hexdigest(),
                                'verification_observation_not_acquired':True,'parameters':{k:prediction[k] for k in ['tau_s','output_equilibrium_v_per_DAC_code','output_equilibrium_intercept_v','engineering_limits']}})
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False})
fig,(ax,ar)=plt.subplots(2,1,figsize=(11,6.8),sharex=True,gridspec_kw={'height_ratios':[3,1]},layout='constrained')
ax.plot(times['A1']*1000,signals['A1'],color='#8492a6',lw=1,label='Measured IN (A1)')
ax.plot(t*1000,y,color='#125dcc',lw=1.3,label='Measured OUT (A2)')
ax.plot(t*1000,y-residual,color='#dc7c19',lw=1.6,ls='--',label=f'Exponential fit: tau = {primary["tau_s"]*1000:.2f} ms')
ax.set_ylabel('Voltage (V; provisional path calibration)');ax.legend(loc='lower right');ax.grid(alpha=.15)
ax.set_title('B1 • First physical RC step response',loc='left',fontweight='bold',fontsize=16)
ar.plot(t*1000,residual*1000,color='#125dcc',lw=.8);ar.axhline(0,color='#8492a6',lw=.6)
ar.set_ylabel('Fit residual (mV)');ar.set_xlabel('Time from commanded step (ms)');ar.set_xlim(-25,110);ar.grid(alpha=.15)
fig.suptitle('512 frames · 0.5 ms target interval · no overruns · all samples retained\nTraining fit only. Component-reading reference: 9.83 ms; R and C are not separately identified.',fontsize=10)
fig.savefig(log.path/'first-step.png',dpi=180);fig.savefig(log.path/'first-step.svg');plt.close(fig)
log.add('run_completed',{'offline_analysis_only':True,'hardware_IO':False,'sine_prediction_frozen':True,
                         'sine_observation_pending':True,'analysis_sha256':hashlib.sha256((log.path/'analysis.json').read_bytes()).hexdigest()})
print(json.dumps({'record':str(log.path),'tau_ms':tau*1000,'reference_difference_percent':result['component_reference_comparison']['tau_difference_percent'],
                  'RMS_mV':primary['fit_RMS_mV'],'regional_residuals':regions,'frozen_prediction':str(log.path/'frozen-sine-prediction.json')}))
