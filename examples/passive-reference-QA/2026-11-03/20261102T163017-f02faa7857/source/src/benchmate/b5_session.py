"""One tool API for the mock and physical unloaded discovery benches."""
from copy import deepcopy
import hashlib
import json
import numpy as np
from .agent import function_tool, ToolRejected
from .netlist import ELEMENT_SCHEMA, render_proposal, render_diode
from .records import canonical
from .b5_models import validate, score, fit_linear, fit_proposal, predict

CONTROL=[dict(kind='sine',samples=512,period_us=4000,amplitude_v=.2,frequency_hz=1.),
         dict(kind='step',samples=512,period_us=500,amplitude_v=.5),
         dict(kind='sine',samples=512,period_us=4000,amplitude_v=.8,frequency_hz=1.)]
TRAINING=deepcopy(CONTROL)
RESERVED=[dict(kind='step',samples=512,period_us=500,amplitude_v=.35),
          dict(kind='sine',samples=512,period_us=2000,amplitude_v=.65,frequency_hz=5.)]
PROTOCOL={
    'version':'b5-unloaded-adc-v2','control':CONTROL,'training':TRAINING,'reserved':RESERVED,
    'load_ohm':None,'same_boot_and_origin_for_training_and_reserved':True,
    'A4_block_mean_span_mV_max':3,'stationary_path_mean_span_mV_max':3,
    'whole_and_each_region_RMS_mV_max':9,'reference_nuisance_bound_v':.08,
    'differential_output_offset_bound_v':.01,'proposal_limit':2,
    'claims':['unloaded predictive adequacy on two held-out inputs'],
    'excluded_claims':['unique R or IS','unique topology','absolute REF calibration','loaded extrapolation'],
    'supersedes':'Loaded physical B5 plan prospectively; its untouched load checks remain pending.'}

TOOLS=[function_tool('inspect_bench','Read the source, scope, menus and initial candidate families.'),
       function_tool('measure','Choose a bounded control or training experiment.',{
           'action':{'type':'string','enum':['resistor_control','amplitude_sweep','repeat_small']},'reason':{'type':'string'}}),
       function_tool('prepare_specimen','Request the operator to prepare the unlabelled passive specimen. Assembly details stay local.'),
       function_tool('propose_netlist','Propose passive connectivity outside the inadequate initial families.',{
           'elements':{'type':'array','items':ELEMENT_SCHEMA},'rationale':{'type':'string'}}),
       function_tool('verify_proposal','Freeze models and command-based forecasts, publish them, then acquire two held-out conditions.'),
       function_tool('finish_report','Report only what the completed checks support.',{
           'verdict':{'type':'string','enum':['verified','abstained']},'explanation':{'type':'string'},'limits':{'type':'string'}})]

PROMPT="""Operate BenchMate using only its tools. inspect_bench first. Source is
reported by the bench; never confuse a mock rehearsal with physical evidence.
Run the resistor_control, then prepare_specimen (the operator handles assembly),
then select an informative training action. amplitude_sweep measures three fixed
amplitudes/waveforms; repeat_small only repeats the low-amplitude observation.
Reasons must explain what can be learned. Five initial linear families are RC,
RC plus input branch, resistor, resistor plus input branch, resistor plus output
leak. If all are inadequate, propose your own passive netlist from evidence.
Allowed nodes IN, OUT, REF, N1, N2; 1–6 R/C/D elements, at most two R/C values.
Each element has name, kind, a, b, value, model. R:1k–100k ohm; C:1n–10u F;
R/C model=none. D: value=0, model=generic_diode, a=anode, b=cathode.
The engine simulates your literal topology; it only refines numbers from training.
Shared diode IS starts 1nA (0.1–100nA), N=1.8 (1–2.5), RS=1ohm, temp=27C.
Every family has the same bounded constant reference and output-bias nuisance
parameters. All are frozen before reserved data. ADC coordinates are provisional,
not absolute REF. R, IS and REF can be confounded: do not claim unique parts or
topology. Input branches can remain invisible. At most two proposals.
After a training pass, verify_proposal freezes/publishes parameters and command
input forecasts BEFORE capture. Conditional comparisons use newly measured IN,
never reserved OUT for fitting. The two kinds of prediction have separate scores.
Both held-out conditional checks must pass whole AND every region at 9mV.
If either fails, abstain; do not refit/retry. Finish using finish_report, under
50 English words per field, explicitly identifying mock/physical and unloaded
scope. No plain-text ending. You have at most eight API calls in total.
"""


def template(settings,source='command_input_only',origin_input=0.):
    n=settings['samples'];t=np.arange(n)*settings['period_us']/1e6
    u=settings['amplitude_v']*(np.where(np.arange(n)<n//10,-1.,1.) if settings['kind']=='step'
         else np.sin(2*np.pi*settings['frequency_hz']*t))+origin_input
    return {'source':source,'settings':{k:settings[k] for k in ('kind','samples','period_us')}|
            {'frequency_hz':settings.get('frequency_hz'),'step_index':n//10 if settings['kind']=='step' else None,'load_ohm':None},
            'data':{'frame_time_s':t.tolist(),'input_relative_origin_v':u.tolist(),
                    'input_delay_s':[50e-6]*n,'output_delay_s':[105e-6]*n}}


def features(c):
    s,t,u,di,do,y=validate(c);indices=np.linspace(0,len(t)-1,25).astype(int)
    return {'source':c['source'],'purpose':c['purpose'],'settings':c['settings'],
            'voltage_basis':c['voltage_basis'],
            'samples':[{'t_s':float(t[i]),'in_v':float(u[i]),'out_v':float(y[i])} for i in indices]}


class B5Session:
    def __init__(self,bench,log,publish_freeze):
        self.bench,self.log,self.publish=bench,log,publish_freeze
        self.tools=TOOLS;self.report=None;self.inspected=False;self.control_passed=False
        self.prepared=False;self.training=[];self.initial=None;self.proposal=None
        self.proposals=0;self.verification=None;self.verification_used=False;self.repeats=0
        log.add('b5_protocol_frozen',PROTOCOL)

    def _capture(self,settings,role):
        c=self.bench.acquire(deepcopy(settings),role)
        validate(c,role)
        if c['source']!=self.bench.source or c['settings']!=settings:raise ValueError('Acquisition source/settings mismatch')
        if role!='control' and self.training:
            if (c['boot_id'],c['origin_id'])!=(self.training[0]['boot_id'],self.training[0]['origin_id']):
                raise ValueError('Boot or origin changed after training began')
        self.log.add('b5_observation',c)
        return c

    def dispatch(self,name,args):
        schema=next((t['parameters'] for t in self.tools if t['name']==name),None)
        if self.report or schema is None or not isinstance(args,dict) or set(args)!=set(schema['required']):raise ToolRejected('Invalid tool or fields')
        for key in ('reason','rationale','explanation','limits'):
            if key in args and (not isinstance(args[key],str) or not 1<=len(args[key])<=1600):raise ToolRejected('Bounded nonempty text required')
        if name=='inspect_bench':
            self.inspected=True
            return {'source':self.bench.source,'protocol':PROTOCOL,'initial_families':['rc','rc_input_branch','resistor','resistor_input_branch','resistor_output_leak'],
                    'assembly_truth_visible':False,'verification_outputs_visible':False}
        if not self.inspected:raise ToolRejected('Inspect the bench first')
        if name=='measure':
            action=args['action']
            if action=='resistor_control':
                if self.control_passed or self.prepared:raise ToolRejected('Control already completed')
                checks=[]
                for settings in CONTROL:
                    c=self._capture(settings,'control');u=c['input_template']['data']['input_relative_origin_v']
                    check=score(c,u);checks.append(check)
                    self.log.add('b5_control_check',check)
                    if not check['passed']:raise ValueError('ADC path control failed; no next amplitude or specimen installation')
                self.control_passed=True
                return {'source':self.bench.source,'control_passed':True,'checks':checks,'absolute_calibration':False}
            if not self.prepared or self.initial is not None or self.verification_used:raise ToolRejected('Training not available in this state')
            if action=='repeat_small':
                if self.repeats:raise ToolRejected('One low-amplitude repeat maximum')
                self.repeats+=1;c=self._capture(TRAINING[0],'training')
                self.training.append(c)
                return {'observation':features(c),'assessment':'A small signal alone may not reveal amplitude-dependent behavior.'}
            if action!='amplitude_sweep':raise ToolRejected('Choose a configured action')
            for settings in TRAINING:self.training.append(self._capture(settings,'training'))
            self.initial=fit_linear(self.training);self.log.add('b5_initial_assessment',self.initial)
            return {'source':self.bench.source,'initial_assessment':self.initial,'training':[features(c) for c in self.training]}
        if name=='prepare_specimen':
            if not self.control_passed or self.prepared:raise ToolRejected('Passed control required; one installation only')
            self.bench.prepare_specimen();self.prepared=True
            return {'source':self.bench.source,'ready':True,'assembly_details_disclosed':False,'next':'Choose a training action.'}
        if name=='propose_netlist':
            if not self.initial or self.initial['status']!='all_candidates_inadequate' or self.verification_used or self.proposals>=2:
                raise ToolRejected('Discovery unavailable or proposal budget exhausted')
            self.proposals+=1;self.proposal=None
            self.log.add('b5_netlist_proposed',args)
            try:self.proposal=fit_proposal(args['elements'],self.training)
            except (ValueError,RuntimeError) as exc:
                self.log.add('b5_proposal_rejected',{'error':str(exc),'attempt':self.proposals})
                return {'accepted':False,'error':str(exc),'remaining_proposals':2-self.proposals}
            self.log.add('b5_proposal_fit',self.proposal)
            return {k:v for k,v in self.proposal.items() if k!='initial_generated_predictions'}|{'remaining_proposals':2-self.proposals}
        if name=='verify_proposal':
            if self.verification_used or not self.proposal or not self.proposal['training_passed']:raise ToolRejected('A passing unused proposal is required')
            self.verification_used=True
            model=deepcopy(self.proposal['model']);linear=[deepcopy(c['model']) for c in self.initial['candidates']]
            forecasts=[{'settings':s,'input_template':template(s),'predicted_output_relative_origin_v':predict(model,template(s))} for s in RESERVED]
            frozen={'protocol':PROTOCOL,'proposal':model,'linear_alternatives':linear,'command_forecasts':forecasts,
                    'boot_id':self.training[0]['boot_id'],'origin_id':self.training[0]['origin_id'],
                    'source':self.bench.source,'reserved_output_samples_used':0,
                    'forecast_label':'Before-measurement forecast assuming commanded input and nominal channel timing',
                    'conditional_label':'After-input-acquisition comparison; parameters fixed, measured IN supplied afterward',
                    'netlist':render_proposal(model['elements'])+'\n'+render_diode(model['diode'])}
            digest=hashlib.sha256(canonical(frozen)).hexdigest()
            self.log.add('b5_predictions_frozen',{'sha256':digest,**frozen})
            receipt=self.publish(frozen,digest)
            if receipt.get('sha256')!=digest or receipt.get('published') is not True:raise ValueError('Prediction publication not acknowledged; no reserved capture')
            if self.bench.source=='physical' and (receipt.get('remote') is not True or not receipt.get('commit')):
                raise ValueError('Physical verification requires a remote commit receipt')
            self.log.add('b5_prediction_publication',receipt)
            checks=[]
            for s,forecast in zip(RESERVED,forecasts):
                c=self._capture(s,'verification')
                conditional=predict(model,c['input_template'])
                check={'settings':s,'conditional':score(c,conditional),'command_forecast':score(c,forecast['predicted_output_relative_origin_v']),
                       'linear_alternatives':[{'family':m['family'],**score(c,predict(m,c['input_template']))} for m in linear],
                       'conditional_prediction':conditional,'frozen_sha256':digest}
                checks.append(check);self.log.add('b5_reserved_check',check)
                if not check['conditional']['passed']:break
            self.verification={'passed':len(checks)==2 and all(c['conditional']['passed'] for c in checks),
                               'checks':checks,'refitted':False,'source':self.bench.source,'frozen_sha256':digest}
            self.log.add('b5_verification',self.verification)
            return {'source':self.bench.source,'passed':self.verification['passed'],'refitted':False,
                    'checks':[{k:v for k,v in c.items() if k!='conditional_prediction'} for c in checks]}
        if name=='finish_report':
            if args['verdict'] not in ('verified','abstained'):raise ToolRejected('Invalid verdict')
            if args['verdict']=='verified' and not (self.verification and self.verification['passed']):raise ToolRejected('Two successful held-out checks required')
            self.report={**args,'source':self.bench.source,'scope':'Unloaded behavior only; no unique parameters/topology or loaded extrapolation.'}
            self.log.add('agent_report',self.report);return self.report
        raise ToolRejected('Unknown tool')

    def summary(self):
        return {'agent_report':self.report,'source':self.bench.source,'reserved_check_passed':bool(self.verification and self.verification['passed']),
                'proposals':self.proposals,'instrument':self.bench.metadata()}
