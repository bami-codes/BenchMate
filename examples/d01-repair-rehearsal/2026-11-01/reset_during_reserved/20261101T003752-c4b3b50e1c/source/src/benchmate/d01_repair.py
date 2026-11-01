"""Bounded diagnosis → model-directed repair → prospective checks.

Only the reviewed 10k/1uF development fixture is supported. Restoring C is the
only implemented physical intervention; other diagnoses must abstain.
"""
from copy import deepcopy
import hashlib
import math
import numpy as np
from .agent import ToolRejected,function_tool
from .instrument import InstrumentConfig,capture_command
from .known_design import nominal_rc
from .measured_input import predict_incremental_rc
from .physical_rc import PhysicalRCSession,STEP,SINE,TOOLS as DIAGNOSTIC_TOOLS,score_models,compact_scores,transfer_models
from .records import canonical

REPAIR_SINE={'kind':'sine','samples':512,'period_us':2000,'amplitude_v':.10,'frequency_hz':4.}
POLICY={'version':'d01-reviewed-design-repair-v1','nominal_design':{'R_ohm':10000.,'C_f':1e-6,'tau_s':.01},
    'load_ohm':9990.,'repair_action':'restore_nominal_capacitance','repair_checks':[STEP,REPAIR_SINE],
    'RMS_mV_allowance':9.,'whole_and_every_region':True,'scored_OUT_refit':False,
    'verdict_basis':'Both restored-model measured-IN conditional checks pass; unchanged model fails at least one.',
    'command_forecast':'Before-measurement incremental forecast, commanded DAC and nominal timing assumed; retained and scored separately.',
    'repair_new_boot_required':True,'post_repair_checks_same_boot':True,'automatic_retry':False,
    'supported_scope':'Known passive RC development fixture with provisional calibration; no general topology or unique component identification.'}

TOOLS=deepcopy(DIAGNOSTIC_TOOLS[:-1])+[
    function_tool('request_repair','Request restoration to reviewed nominal capacitance after a verified C-change diagnosis. Predictions must publish before the human acts.',{
        'action':{'type':'string','enum':['restore_nominal_capacitance']},'reason':{'type':'string'}}),
    function_tool('verify_repair','Measure the repaired loaded step and unused 0.10 V / 4 Hz sine with frozen models; no refit.'),
    function_tool('finish_report','Record the checked repair result or abstain.',{
        'verdict':{'type':'string','enum':['repair_verified','abstained']},
        'current_explanation':{'type':'string'},'unresolved':{'type':'string'},'next_observation':{'type':'string'}})]

PROMPT='''You direct a bounded BenchMate RC diagnosis and repair workflow.
The runtime's inspect_experiment result states whether this is MOCK or PHYSICAL;
never present a mock, scripted rehearsal or replay as a new physical experiment.
Start with inspect_experiment. Its nominal design comes from a separately
reviewed intended-schematic reading, not a photograph's hidden wiring or a
previous specimen result. You receive summaries only, not assembly truth.

Select the available unloaded step, then an informative available measurement.
Unloaded tau alone does not identify R and C separately. Explain the purpose of
your choice in Korean. A physical fixture change waits for the human operator.
If a unique declared alternative passes the loaded step, use verify_prediction
to test the frozen alternatives on the diagnostic 0.15 V / 5 Hz sine.

Only if C change is supported by both diagnostic checks may you call
request_repair(action=restore_nominal_capacitance, reason=your Korean rationale).
This asks a human to restore the reviewed nominal C. You do not know the hidden
assembly or which lead/hole realizes this; the local operator guide handles it.
Other diagnoses have no implemented repair here: abstain. Never invent one.
The system freezes/publishes repaired and unchanged models and command-input
forecasts BEFORE manual intervention. After the matching USB-off repair report,
call verify_repair. It requires a new boot and runs a step and a new 0.10 V / 4 Hz
sine on that same boot, with independent HOLD origins and no scored-OUT refit.

finish_report may use repair_verified only if the runtime says repair_verified.
Otherwise abstain. Concisely report what is supported, what is unresolved and
the next observation, in Korean. Distinguish prior command-based forecasts from
measured-IN conditional comparisons; report any command-forecast disagreement.
The 9 mV whole-waveform AND regional allowance is engineering acceptance, not
calibrated confidence. No absolute calibration, blind/general accuracy or
automatic physical manipulation is established. Finish with a tool call.
'''

def reviewed_design(value):
    if (value.get('schema')!='benchmate.reviewed_nominal_rc.v1'
        or value.get('source')!='operator_reviewed_image_transcription'
        or not isinstance(value.get('reviewer_note'),str) or not value['reviewer_note'].strip()
        or value.get('measurement_verified') is not False or value.get('hardware_IO') is not False):
        raise ValueError('Explicit reviewed nominal image design required, not a measurement')
    nominal=nominal_rc(value['candidate'],'intended_schematic')
    if nominal!=value.get('nominal_design') or nominal!=POLICY['nominal_design']:
        raise ValueError('This frozen repair fixture supports reviewed 10 kohm / 1 uF only')
    return deepcopy(nominal),hashlib.sha256(canonical(value)).hexdigest()

def command_template(config,settings):
    """Quantized DAC deltas including firmware sine warmup phase; no measured IN."""
    command=capture_command(config,boot_id='1'*32,**settings);amp=int(command.split()[5])
    n=settings['samples'];period=settings['period_us'];i=np.arange(n)
    if settings['kind']=='step':delta=np.where(i<n//10,-amp,amp)
    else:
        warmup=math.ceil(max(config.settle_ms*1000,2e6/settings['frequency_hz'])/period)
        raw=amp*np.sin(2*math.pi*settings['frequency_hz']*(i+warmup)*period/1e6)
        delta=np.where(raw>=0,np.floor(raw+.5),np.ceil(raw-.5))
    return {'frame_time_s':(i*period*1e-6).tolist(),'input_v':(delta*config.vref_v/4095).tolist(),
            'input_delay_s':[50e-6]*n,'output_delay_s':[105e-6]*n}

def forecast(config,settings,model):
    data=command_template(config,settings)
    curve=predict_incremental_rc(**data,**model,baseline_input_v=0.,baseline_output_v=0.,
        kind=settings['kind'],step_index=settings['samples']//10 if settings['kind']=='step' else None,
        frequency_hz=settings.get('frequency_hz'))
    return {'settings':deepcopy(settings),'command_input_relative_origin_v':data['input_v'],
            'predicted_output_relative_origin_v':curve['predicted_output_v'],
            'nominal_output_delay_s':105e-6,'label':POLICY['command_forecast']}

def command_score(observation,frozen_curve):
    # Reuse the exact region masks, then replace only the prediction curve.
    from .physical_rc import REGIONS
    settings=observation['settings'];d=observation['data'];b=observation['baseline']
    residual=np.array(d['output_v'])-b['output_v']-np.array(frozen_curve)
    t=np.array(d['frame_time_s'])+np.array(d['output_delay_s']);masks=[]
    if settings['kind']=='step':
        relative=t-settings['samples']//10*settings['period_us']*1e-6
        for name,lo,hi in REGIONS:
            mask=np.ones(len(t),dtype=bool)
            if lo is not None:mask&=relative>=lo/1000
            if hi is not None:mask&=relative<hi/1000
            masks.append((name,mask))
    else:
        phase=np.floor((t*settings['frequency_hz']%1)*8).astype(int)
        masks=[('phase_'+str(i),phase==i) for i in range(8)]
    rms=float(np.sqrt(np.mean(residual**2)))*1000
    regions=[{'name':name,'samples':int(mask.sum()),'RMS_mV':float(np.sqrt(np.mean(residual[mask]**2)))*1000} for name,mask in masks]
    return {'RMS_mV':rms,'regions':regions,'passed':rms<=9 and all(x['samples'] and x['RMS_mV']<=9 for x in regions),
            'refitted':False,'baseline':'Independent new-boot HOLD output origin; no scored OUT used'}

class D01RepairSession:
    def __init__(self,bench,log,design,publish,*,actor='muse_spark'):
        self.design,self.design_sha=reviewed_design(design);self.bench=bench;self.log=log;self.publish=publish
        self.actor=actor;self.tools=TOOLS;self.report=None;self.fatal=False;self.inspected=False
        self.diagnostic=PhysicalRCSession(bench.acquire,log,source=bench.source,actor=actor)
        self.repair_attempted=False;self.repair_confirmed=False;self.verification_attempted=False
        self.repair_verified=False;self.frozen=None;self.receipt=None;self.checks=[]
        log.add('repair_design_loaded',{'nominal_design':self.design,'reviewed_design_sha256':self.design_sha,
            'source_kind':'intended_schematic','operator_review_simulated':bench.source=='mock','hardware_IO':False})

    def snapshot(self):
        diagnostic=self.diagnostic.snapshot()
        if self.repair_attempted:diagnostic={**diagnostic,'allowed_measurements':[],'verification_available':False}
        return {'source':self.bench.source,'decision_actor':self.actor,'nominal_design':self.design,
            'reviewed_design_sha256':self.design_sha,'diagnostic':diagnostic,
            'repair_available':self.diagnostic.verified and self.diagnostic.supported==['c_changed'] and not self.repair_attempted,
            'repair_requested':self.repair_attempted,'repair_confirmed_by_operator':self.repair_confirmed,
            'repair_verified':self.repair_verified,'repair_verification_available':self.repair_confirmed and not self.verification_attempted,
            'checks':self.checks,'prediction_published':bool(self.receipt),'scope':POLICY['supported_scope'],
            'mock_notice':'No human or instrument acted' if self.bench.source=='mock' else None}

    def dispatch(self,name,args):
        if self.report is not None or self.fatal:raise ToolRejected('Session stopped')
        schema=next((t['parameters'] for t in self.tools if t['name']==name),None)
        if schema is None or not isinstance(args,dict) or set(args)!=set(schema['required']):raise ToolRejected('Unknown tool or fields')
        for key,value in args.items():
            spec=schema['properties'][key]
            if not isinstance(value,str) or len(value)>1600 or ('enum' in spec and value not in spec['enum']):raise ToolRejected('Invalid argument')
        if name=='inspect_experiment':
            self.inspected=True;self.diagnostic.dispatch(name,args);return self.snapshot()
        if not self.inspected:raise ToolRejected('Inspect the experiment first')
        if name=='finish_report':return self.finish(**args)
        if name in ('measure','verify_prediction') and self.repair_attempted:raise ToolRejected('Diagnostic phase closed')
        # Rejected model choices do not change state; external faults stop permanently.
        try:
            if name in ('measure','verify_prediction'):self.diagnostic.dispatch(name,args)
            elif name=='request_repair':self.request_repair(**args)
            elif name=='verify_repair':self.verify_repair()
        except ToolRejected:raise
        except Exception:self.fatal=True;raise
        return self.snapshot()

    def request_repair(self,action,reason):
        if not self.snapshot()['repair_available'] or not reason.strip():raise ToolRejected('Verified C diagnosis and reason required')
        self.repair_attempted=True
        point={'restored_nominal':{'R_ohm':self.design['R_ohm'],'C_f':self.design['C_f']},
               'unchanged':deepcopy(self.diagnostic.models['c_changed'])}
        models=transfer_models(point,9990.)
        self.frozen={'policy':POLICY,'source':self.bench.source,'decision_actor':self.actor,
            'nominal_design':self.design,'reviewed_design_sha256':self.design_sha,'action':action,'reason':reason,
            'point_models':point,'transfer_models':models,'before_repair_boot_id':self.bench.boot_id,
            'forecasts':[{key:forecast(self.bench.config,s,model) for key,model in models.items()} for s in POLICY['repair_checks']],
            'post_repair_scored_OUT_used':0}
        digest=hashlib.sha256(canonical(self.frozen)).hexdigest()
        self.log.add('repair_prediction_frozen',{'sha256':digest,**self.frozen})
        receipt=self.publish(deepcopy(self.frozen),digest)
        if (receipt.get('sha256')!=digest or receipt.get('published') is not True
            or (self.bench.source=='physical' and receipt.get('remote') is not True)):
            raise ValueError('Remote prediction publication required before physical repair')
        self.receipt=deepcopy(receipt);self.log.add('repair_prediction_publication',receipt)
        self.bench.prepare_repair(digest,receipt)
        self.repair_confirmed=True

    def verify_repair(self):
        if not self.snapshot()['repair_verification_available']:raise ToolRejected('Confirmed published repair and unused checks required')
        self.verification_attempted=True
        models=deepcopy(self.frozen['transfer_models']);boot=None
        for index,s in enumerate(POLICY['repair_checks']):
            obs=self.bench.acquire(s,deepcopy(models),'output_load','repair_step' if index==0 else 'repair_reserved_sine')
            if (obs.get('source')!=self.bench.source or obs.get('fresh_measurement') is not True
                or obs.get('all_guards_passed') is not True or obs.get('settings')!=s or obs.get('fixture')!='output_load'):
                raise ValueError('Fresh guarded matching repair observation required')
            current=obs.get('boot_id')
            if not isinstance(current,str) or not current or current==self.frozen['before_repair_boot_id'] or (boot is not None and current!=boot):
                raise ValueError('Repair must use a new boot, then preserve it across both checks')
            boot=current
            scores=score_models(obs,models)
            commands={key:command_score(obs,f['predicted_output_relative_origin_v']) for key,f in self.frozen['forecasts'][index].items()}
            self.log.add('repair_prediction_comparison',{'settings':s,'conditional':scores,'command_forecast':commands,
                'boot_id':boot,'scored_OUT_refitted':False,'prediction_sha256':self.receipt['sha256']})
            self.checks.append({'settings':s,'conditional':compact_scores(scores),'command_forecast':commands})
        restored=all(x['conditional']['restored_nominal']['passed'] for x in self.checks)
        differs=any(not x['conditional']['unchanged']['passed'] for x in self.checks)
        self.repair_verified=restored and differs
        self.log.add('repair_verification_completed',{'passed':self.repair_verified,'restored_passes_both':restored,
            'unchanged_rejected_at_least_once':differs,'command_forecasts_pass':all(x['command_forecast']['restored_nominal']['passed'] for x in self.checks),
            'scored_OUT_refitted':False,'source':self.bench.source})

    def finish(self,verdict,current_explanation,unresolved,next_observation):
        if verdict=='repair_verified' and not self.repair_verified:raise ToolRejected('Both frozen repair checks and change contrast must pass')
        if not all(x.strip() for x in (current_explanation,unresolved,next_observation)):raise ToolRejected('All report fields required')
        self.report={'verdict':verdict,'current_explanation':current_explanation,'unresolved':unresolved,
            'next_observation':next_observation,'source':self.bench.source,'decision_actor':self.actor,
            'repair_intervention_reported':self.repair_confirmed,'repair_verified':self.repair_verified,
            'scope':POLICY['supported_scope'],'physical_repair_demonstrated':self.bench.source=='physical' and self.repair_verified}
        self.log.add('agent_report',self.report);return {'accepted':True}

    def summary(self):
        return {'source':self.bench.source,'llm_used':self.actor=='muse_spark','agent_report':self.report,
            'diagnosis_verified':self.diagnostic.verified,'repair_verified':self.repair_verified,'checks':self.checks,
            'publication':self.receipt,'instrument':self.bench.metadata(),'scored_OUT_refitted':False}
