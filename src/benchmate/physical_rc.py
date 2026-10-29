"""Bounded physical RC tools with separate training and reserved observations.

Only measured unloaded tau is fitted. All later loaded predictions retain that
tau and nominal design alternatives; separate HOLD origins remove DC offsets.
This is point-model engineering evidence, not calibrated statistical inference.
"""
from copy import deepcopy
import math
import numpy as np
from scipy.optimize import minimize_scalar
from .agent import ToolRejected, function_tool
from .measured_input import predict_incremental_rc

STEP = {'kind':'step','samples':512,'period_us':500,'amplitude_v':.2}
SINE = {'kind':'sine','samples':512,'period_us':2000,'amplitude_v':.15,'frequency_hz':5.}
REGIONS = [('pre_step',None,0),('0_to_5ms',0,5),('5_to_20ms',5,20),
           ('20_to_80ms',20,80),('after_80ms',80,None)]
SCOPE = ('Physical known-passive RC; measured-IN conditional incremental response, '
         'nominal-design point alternatives and provisional calibration. '
         'Not absolute voltage accuracy, blinded diagnosis, full D2 or calibrated confidence.')
PROMPT = '''You control BenchMate's first bounded physical RC experiment.
These are NEW physical measurements, never synthetic or replay. You receive
nominal design knowledge (R=10 kohm, C=1 uF) and measured observations, never
specimen identity, assembly truth, previous specimen results or private files.
The declared alternatives are nominal RC, R changed with C nominal, and C
changed with R nominal. The engineering allowance is fixed at 9 mV RMS for
the whole waveform AND every region. It is not a calibrated confidence bound.

First call inspect_experiment, then select measure with a Korean reason.
The first available action is unloaded_step. It identifies tau, not R and C
separately. Subsequent options are attach_output_load_step (9.99 kohm OUT-REF)
or repeat_unloaded_step. Explain why a load can distinguish the alternatives
and avoid an uninformative repeat if a useful allowed action exists.
Physical rewiring pauses for the operator. Never claim mounting was automatic.
You cannot choose arbitrary voltage, firmware, paths, commands or components.

When one declared alternative is supported by a loaded step, call
verify_prediction. It tests the SAME frozen models on a new 0.15 V, 5 Hz sine
with a separate pre-stimulus HOLD origin. No scored verification OUT is fitted.
Only after that check may finish_report use verdict verified and the matching
candidate. Otherwise abstain with an empty candidate. Report in concise Korean
what is supported, what remains unresolved, and the next observation.
Always state the limited physical RC/incremental/provisional scope. Do not
claim absolute calibration, holdout success, a completed repair or reliability.
Finish by calling finish_report, never by returning a plain text final answer.
'''

TOOLS = [function_tool('inspect_experiment','Inspect physical evidence and the allowed menu.'),
    function_tool('measure','Select a new physical measurement; mounting pauses for a human.',{
        'action':{'type':'string','enum':['unloaded_step','attach_output_load_step','repeat_unloaded_step']},
        'reason':{'type':'string'}}),
    function_tool('verify_prediction','Acquire a new lower-amplitude sine for the frozen loaded models.'),
    function_tool('finish_report','Record an evidence-checked report.',{
        'verdict':{'type':'string','enum':['verified','abstained']},'candidate':{'type':'string'},
        'current_explanation':{'type':'string'},'unresolved':{'type':'string'},'next_observation':{'type':'string'}})]


def conditional_curve(observation, model):
    s=observation['settings'];d=observation['data'];b=observation['baseline']
    return predict_incremental_rc(d['frame_time_s'],d['input_v'],d['input_delay_s'],d['output_delay_s'],
        gain=model['gain'],tau_s=model['tau_s'],baseline_input_v=b['input_v'],baseline_output_v=b['output_v'],
        kind=s['kind'],step_index=s['samples']//10 if s['kind']=='step' else None,frequency_hz=s.get('frequency_hz'))


def score_models(observation,models):
    s=observation['settings'];d=observation['data'];t=np.asarray(d['frame_time_s'])+np.asarray(d['output_delay_s'])
    masks=[]
    if s['kind']=='step':
        relative=t-s['samples']//10*s['period_us']*1e-6
        for name,lo,hi in REGIONS:
            mask=np.ones(len(t),dtype=bool)
            if lo is not None:mask&=relative>=lo/1000
            if hi is not None:mask&=relative<hi/1000
            masks.append((name,mask))
    else:
        phase=np.floor((t*s['frequency_hz']%1)*8).astype(int)
        masks=[('phase_'+str(i),phase==i) for i in range(8)]
    results={}
    for name,model in models.items():
        prediction=conditional_curve(observation,model);residual=np.asarray(d['output_v'])-prediction['predicted_output_v']
        regions=[{'name':name,'samples':int(mask.sum()),'RMS_mV':float(np.sqrt(np.mean(residual[mask]**2)))*1000}
                 for name,mask in masks]
        rms=float(np.sqrt(np.mean(residual**2)))*1000
        results[name]={'RMS_mV':rms,'regions':regions,'passed':rms<=9 and all(r['samples']>0 and r['RMS_mV']<=9 for r in regions),
                       'prediction':prediction,'scored_OUT_refitted':False}
    return results


def train_unloaded(observation):
    """Fit only one tau from the first physical training trace, never gain/offset."""
    if observation['settings']!=STEP:raise ValueError('Initial training requires the fixed unloaded step')
    y=np.asarray(observation['data']['output_v'])
    def objective(log_tau):
        curve=conditional_curve(observation,{'gain':1.,'tau_s':math.exp(log_tau)})['predicted_output_v']
        return float(np.mean((y-curve)**2))
    bounds=(math.log(.002),math.log(.08))
    fit=minimize_scalar(objective,bounds=bounds,method='bounded',options={'xatol':1e-10})
    if not fit.success or min(fit.x-bounds[0],bounds[1]-fit.x)<.01:
        raise ValueError('Unloaded training fit failed or reached the declared tau bound')
    tau=math.exp(fit.x)
    models={'nominal_rc':{'R_ohm':10000.,'C_f':1e-6},
            'r_changed':{'R_ohm':tau/1e-6,'C_f':1e-6},
            'c_changed':{'R_ohm':10000.,'C_f':tau/10000.}}
    training_score=score_models(observation,{'fitted_tau':{'gain':1.,'tau_s':tau}})['fitted_tau']
    return {'tau_s':tau,'training_RMS_mV':training_score['RMS_mV'],'training_adequate':training_score['passed'],
            'training_frames':len(y),'fit_parameters':['tau_s'],'gain_fixed':1.,'offset_from_separate_HOLD':True,
            'individual_R_C_identified':False,'point_models':models}


def transfer_models(point_models,load_ohm):
    result={}
    for name,m in point_models.items():
        r,c=m['R_ohm'],m['C_f'];gain=1. if load_ohm is None else load_ohm/(load_ohm+r)
        result[name]={'gain':gain,'tau_s':r*c*gain}
    return result


def compact_scores(scores):
    return {name:{k:v for k,v in score.items() if k!='prediction'} for name,score in scores.items()}


class PhysicalRCSession:
    """The acquisition callback is trusted local code; Spark only chooses enums."""
    def __init__(self,acquire,log):
        self.acquire=acquire;self.log=log;self.tools=TOOLS;self.report=None;self.inspected=False
        self.training=None;self.models=None;self.loaded=False;self.verified=False;self.verification_attempted=False
        self.supported=[];self.observations=[];self.actions=[];self.diagnostic_used=0;self.fatal=False

    def snapshot(self):
        if self.training is None:allowed=['unloaded_step']
        elif self.training['training_adequate'] and not self.loaded and self.diagnostic_used<2:
            allowed=['attach_output_load_step','repeat_unloaded_step']
        else:allowed=[]
        return {'source':'physical','scope':SCOPE,'nominal_design':{'R_ohm':10000.,'C_f':1e-6},
                'training':self.training,'observations':self.observations,'supported_candidates':self.supported,
                'allowed_measurements':allowed,'load_ohm':9990.,'diagnostic_remaining':2-self.diagnostic_used,
                'verification_available':self.loaded and len(self.supported)==1 and not self.verification_attempted,
                'verified':self.verified,'automatic_wiring':False,'repair_performed':False}

    def _observe(self,settings,models,fixture,reason,phase):
        self.log.add('physical_measurement_selected',{'settings':settings,'fixture':fixture,'reason':reason,
                     'phase':phase,'selected_by':'muse_spark','models_frozen':models,'scope':SCOPE})
        try:
            observation=self.acquire(deepcopy(settings),deepcopy(models),fixture,phase)
            if (observation.get('source')!='physical' or observation.get('settings')!=settings
                or observation.get('fixture')!=fixture or observation.get('all_guards_passed') is not True
                or observation.get('fresh_measurement') is not True):
                raise ValueError('Expected a fresh guarded physical capture matching the request')
        except Exception:
            self.fatal=True
            raise
        self.actions.append(phase)
        return observation

    def dispatch(self,name,arguments):
        if self.report is not None or self.fatal:raise ToolRejected('Session already stopped')
        schema=next((t['parameters'] for t in self.tools if t['name']==name),None)
        if schema is None or not isinstance(arguments,dict) or set(arguments)!=set(schema['required']):
            raise ToolRejected('Unknown tool or invalid fields')
        for key,value in arguments.items():
            spec=schema['properties'][key]
            if not isinstance(value,str) or len(value)>1600 or ('enum' in spec and value not in spec['enum']):
                raise ToolRejected('Invalid argument: '+key)
        if name=='inspect_experiment':self.inspected=True;return self.snapshot()
        if not self.inspected:raise ToolRejected('Inspect the experiment before acting')
        if name=='measure':return self.measure(**arguments)
        if name=='verify_prediction':return self.verify()
        return self.finish(**arguments)

    def measure(self,action,reason):
        if action not in self.snapshot()['allowed_measurements'] or not reason.strip():
            raise ToolRejected('Measurement is unavailable or lacks a reason')
        first=self.training is None;loaded=action=='attach_output_load_step';fixture='output_load' if loaded else 'unloaded'
        models={} if first else transfer_models(self.models,9990. if loaded else None)
        if not first:self.diagnostic_used+=1
        observation=self._observe(STEP,models,fixture,reason,action)
        if first:
            self.training=train_unloaded(observation);self.models=deepcopy(self.training['point_models'])
            self.log.add('unloaded_training_completed',self.training)
            self.log.add('loaded_point_models_frozen',{'source':'first_unloaded_training_only','models':transfer_models(self.models,9990.),'scored_loaded_OUT_used':0})
            self.observations.append({'phase':action,'tau_s':self.training['tau_s'],'training_RMS_mV':self.training['training_RMS_mV'],
                                      'individual_R_C_identified':False})
        else:
            scores=score_models(observation,models);self.log.add('physical_model_comparison',{'phase':action,'scores':scores})
            supported=[name for name,score in scores.items() if score['passed']]
            self.observations.append({'phase':action,'scores':compact_scores(scores),'supported':supported})
            if loaded:self.loaded=True;self.supported=supported
        return self.snapshot()

    def verify(self):
        if not self.snapshot()['verification_available']:raise ToolRejected('A unique loaded candidate and unused verification are required')
        self.verification_attempted=True;models=transfer_models(self.models,9990.)
        observation=self._observe(SINE,models,'output_load','Independent lower-amplitude waveform with frozen models','reserved_sine')
        scores=score_models(observation,models);supported=[name for name,score in scores.items() if score['passed']]
        self.verified=supported==self.supported
        self.log.add('physical_verification',{'scores':scores,'passed':self.verified,'refitted_on_verification':False})
        self.observations.append({'phase':'reserved_sine','scores':compact_scores(scores),'supported':supported,'passed':self.verified})
        return self.snapshot()

    def finish(self,verdict,candidate,current_explanation,unresolved,next_observation):
        if verdict=='verified' and (not self.verified or self.supported!=[candidate]):
            raise ToolRejected('A matching successful reserved check is required')
        if verdict=='abstained' and candidate:raise ToolRejected('Abstention must have an empty candidate')
        if not all(s.strip() for s in [current_explanation,unresolved,next_observation]):
            raise ToolRejected('All report fields are required')
        self.report={'verdict':verdict,'candidate':candidate,'current_explanation':current_explanation,
                     'unresolved':unresolved,'next_observation':next_observation,'scope':SCOPE,'repair_performed':False}
        self.log.add('agent_report',self.report);return {'accepted':True,'verified':self.verified}

    def summary(self):
        return {'source':'physical','llm_used':True,'mode':'live_spark_with_physical_RC','scope':SCOPE,
                'agent_report':self.report,'selected_actions':self.actions,'observations':self.observations,
                'training':self.training,'reserved_check_passed':self.verified,'scored_capture_count':len(self.actions),
                'repair_performed':False,'absolute_voltage_validation':False,'full_D2_accepted':False}
