"""Freeze two voltage forecasts from the already committed repair model."""
from pathlib import Path
from dataclasses import asdict
import sys,json,hashlib,math
import numpy as np
ROOT=Path('/Users/bami/Documents/metaai')
sys.path.insert(0,str(ROOT/'src'))
from benchmate.records import Recorder,read_events
from benchmate.instrument import InstrumentConfig,capture_command

MODEL=ROOT/'examples/hardware-d01-repair/2026-10-30/model-freeze/20261029T151250-08a588f6dc/plan.json'
PROFILE=ROOT/'examples/hardware-fixture-bringup/2026-10-29-followup/minima-three-point-analysis/provisional-calibration.json'
model=json.loads(MODEL.read_text());profile=json.loads(PROFILE.read_text())
model_sha=hashlib.sha256(MODEL.read_bytes()).hexdigest()
assert read_events(MODEL.parent)[-1]['payload']['plan_sha256']==model_sha
assert hashlib.sha256(PROFILE.read_bytes()).hexdigest()==model['source_hashes'][str(PROFILE.relative_to(ROOT))]
config=InstrumentConfig(vref_v=4.89,ref_v=1.637)
ratio=config.vref_v/profile['nominal_supply_conversion_v']
actuator=profile['DAC_to_driver_path']
slope=actuator['gain_v_per_code']*ratio;offset=actuator['offset_v']
maps={ch:{'gain_v_per_count':v['gain_v_per_count']*ratio,'offset_v':v['offset_v']*ratio} for ch,v in profile['channels'].items()}
waveforms=[]
for settings in model['settings']:
    kind=settings['kind'];n=settings['samples'];period=settings['period_us'];dt=period*1e-6
    kwargs={k:settings[k] for k in ['kind','samples','period_us','amplitude_v']}
    if kind=='sine': kwargs['frequency_hz']=settings['frequency_hz']
    command=capture_command(config,boot_id='1'*32,**kwargs)
    amplitude=int(command.split()[5]);warmup=settings.get('warmup_frames',0)
    all_codes=[]
    for i in range(warmup+n):
        if kind=='step': code=config.ref_code+(-amplitude if i<settings['step_index'] else amplitude)
        else:
            x=amplitude*math.sin(2*math.pi*settings['frequency_hz']*i*dt)
            code=config.ref_code+int(math.floor(x+.5) if x>=0 else math.ceil(x-.5))
        all_codes.append(code)
    predictions={}
    for name,m in model['models'].items():
        gain=m['gain'];tau=m['loaded_tau_s']
        equilibrium=lambda code: config.ref_v+gain*(slope*code+offset-config.ref_v)
        state=equilibrium(all_codes[0] if kind=='step' else config.ref_code)
        curve=[]
        for i,code in enumerate(all_codes):
            eq=equilibrium(code)
            sample=eq+(state-eq)*math.exp(-105e-6/tau)
            state=eq+(state-eq)*math.exp(-dt/tau)
            if i>=warmup:curve.append(sample)
        predictions[name]={'gain':gain,'tau_s':tau,'predicted_A2_v':curve}
        if kind=='step':
            t=(np.arange(n)*period+105)*1e-6-settings['step_index']*dt
            low=equilibrium(config.ref_code-amplitude);high=equilibrium(config.ref_code+amplitude)
            independent=low+(high-low)*(-np.expm1(-np.maximum(t,0)/tau))
            assert np.max(abs(independent-np.asarray(curve)))<1e-12
    assert max(abs(np.diff(all_codes)))<=config.max_jump
    waveforms.append({'settings':kwargs,'warmup_frames':warmup,
        'expected_DAC_codes':all_codes[warmup:],'nominal_A2_time_s':[(i*period+105)*1e-6 for i in range(n)],
        'predictions':predictions})

p={'scope':model['scope'],'configuration':asdict(config),'previous_boot_id':'a09aa39f4755ba059967f31ac9221cd3',
   'operator_removal_report':'USB 분리 / 추가 C 제거 / 원래 C·나머지 배선 유지',
   'operator_power_report':'USB 연결 / 전원 4.89 V / REF 1.637 V',
   'model_plan':str(MODEL.relative_to(ROOT)),'model_plan_sha256':model_sha,'model_commit_before_reconnection':'291043784c2dc83602c2df74542d4f3aa85905bb',
   'provisional_profile_sha256':hashlib.sha256(PROFILE.read_bytes()).hexdigest(),
   'voltage_conversion':{'reported_supply_ratio':ratio,'channels':maps},
   'actuator':{'driver_v_per_code':slope,'driver_offset_v':offset},
   'waveforms':waveforms,'engineering_limits':model['engineering_limits'],'decision':model['decision'],
   'all_predictions_saved_before_post_repair_ADC':True,'no_post_repair_parameter_offset_phase_or_gain_fit':True,
   'automatic_A4_tracking':False,'automatic_retry_or_rearm':False,
   'known_passive_RC_startup_exception':True,'startup_and_ARM_ramp_excluded':True,
   'guard_captures':{'count':3,'samples':512,'period_us':2000,'positions':['before step','between step and sine','after sine']},
   'guard_limits':{'REF_mean_delta_v_max':.100,'REF_any_sample_delta_v_max':.150,'REF_channel_mean_spread_v_max':.050,
                   'signal_envelope_v':.350,'A4_envelope_v':.150,'raw_rails_exclusive':[16,16367]},
   'all_capture_attempts_counted':True,'full_D2_accepted':False,'Spark_invoked':False}
log=Recorder(ROOT/'runs/hardware-d01-repair-voltage',mode='two_absolute_repair_forecasts_frozen_before_new_ADC')
for path,name in [(Path(__file__),'controller-source.py'),(MODEL,'model-plan.json'),(PROFILE,'provisional-calibration.json')]:
    (log.path/name).write_bytes(path.read_bytes())
(log.path/'prediction.json').write_text(json.dumps(p,ensure_ascii=False,indent=2)+'\n')
sha=hashlib.sha256((log.path/'prediction.json').read_bytes()).hexdigest()
log.add('operator_removal_confirmed',{'verbatim':p['operator_removal_report'],'extra_capacitor_removed_only':True,'output_load_retained_per_report':True})
log.add('operator_power_report',{'verbatim':p['operator_power_report'],'supply_v':config.vref_v,'REF_v':config.ref_v})
log.add('both_predictions_frozen',{'sha256':sha,'model_plan_sha256':model_sha,'waveforms':[w['settings'] for w in waveforms],'before_any_post_repair_ADC':True})
log.add('run_completed',{'hardware_IO':False,'prediction_sha256':sha,'post_repair_acquisition_pending':True})
(ROOT/'runs/d01-repair-voltage-path.txt').write_text(str(log.path/'prediction.json')+'\n')
print(json.dumps({'record':str(log.path),'ref_code':config.ref_code,'prediction_sha256':sha,'waveforms':[w['settings'] for w in waveforms],'step_forecast_analytic_crosscheck':True}))
