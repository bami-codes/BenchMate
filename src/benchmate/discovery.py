"""Model-authored passive topology proposals with untouched verification data."""
from copy import deepcopy
import json
import time
import numpy as np
from scipy.optimize import least_squares

from .agent import function_tool, ToolRejected, TOOLS
from .inference import families_for, fit_family
from .netlist import ELEMENT_SCHEMA,validate_netlist,simulate_netlist,topology_fingerprint,render_proposal
from .noise import NoiseModel,adequacy,whitened_vector
from .physics import Acquisition,RCModel,predict


TRAINING = [Acquisition(),
            Acquisition(kind='sine',frequency_hz=1,amplitude_v=.2,duration_s=2,sample_period_s=.002),
            Acquisition(kind='sine',frequency_hz=1,amplitude_v=1,duration_s=2,sample_period_s=.002)]
# Development values, committed before proposal. Physical values freeze at D2.
VERIFICATION = [Acquisition(amplitude_v=.35),
                Acquisition(kind='sine',frequency_hz=1,amplitude_v=1,duration_s=2,sample_period_s=.002,load_ohm=10000)]

DISCOVERY_PROMPT = """You operate BenchMate's nonlinear hypothesis discovery on SYNTHETIC
observations. You do not know the specimen identity, topology or component values.
First inspect_residuals. The initial continuous RC families fail regional fit
checks; diagnose the pattern from measured input/output traces at two amplitudes.
Then propose_netlist with your own passive connectivity and a short Korean reason.
Allowed nodes: IN, OUT, REF, N1, N2. Every element has name, kind R/C/D, a, b,
value, model. For R/C, model=none and value is ohms/farads. For D, value=0,
model=generic_diode; a is anode, b cathode. The generic library is IS=1nA, N=1.8,
RS=1ohm at 27C. This is a development model, not a calibrated physical part.
Use 1–6 elements, at most 2 R/C parameters to fit; R in 1k–100k, C in 1n–10u.
Your exact nodes and diode orientation go into ngspice. The backend can refine
numeric R/C values using training data only, never replace your topology.
At most 2 proposals and a fixed simulator budget are allowed. If training passes,
call verify_proposal to freeze the netlist and predictions BEFORE two untouched
conditions are acquired. Do not request fitting on verification data. If checks
fail, abstain. Finish using finish_report with concise Korean explanation,
unresolved scope and next observation. Verdict verified and candidate proposed_netlist
are allowed only after BOTH independent checks pass; otherwise abstained with
empty candidate. Always state synthetic/development scope. No plain-text ending.
"""

DISCOVERY_TOOLS = [
    function_tool('inspect_residuals','Read training observations and failed initial RC fit checks.'),
    function_tool('propose_netlist','Propose the actual passive netlist to simulate; topology will not be replaced.',
                  {'elements':{'type':'array','items':ELEMENT_SCHEMA},'rationale':{'type':'string'}}),
    function_tool('verify_proposal','Freeze predictions then acquire two unused verification conditions; no refitting.'),
    deepcopy(next(t for t in TOOLS if t['name']=='finish_report')),
]


def trace_features(capture):
    data=capture['data'];idx=np.linspace(0,len(data['out_v'])-1,25).astype(int)
    return {'settings':capture['settings'],'source':'synthetic',
            'trace_samples':[{k:float(data[k][i]) for k in ('time_s','drive_v','ref_v','in_v','out_v')} for i in idx],
            'full_trace_recorded':True}


def fit_proposal(elements,captures,noise=NoiseModel()):
    elements=validate_netlist(elements)
    fitted=deepcopy(elements)
    active=[i for i,e in enumerate(elements) if e['kind'] in ('R','C')]
    if len(active)>2:
        raise ValueError('Development parameter-fitting budget supports at most two R/C elements')
    calls=0; first_metadata=[]
    def evaluate(log_values,record_initial=False):
        nonlocal calls
        for i,value in zip(active,np.exp(log_values)):fitted[i]['value']=float(value)
        residuals=[]
        for capture in captures:
            if calls>=80:raise ValueError('Proposal simulator budget exhausted')
            calls+=1
            prediction,meta=simulate_netlist(fitted,capture)
            if record_initial:first_metadata.append(meta)
            residuals.append(whitened_vector(prediction,capture,noise))
        return np.concatenate(residuals)
    start=np.log([elements[i]['value'] for i in active])
    evaluate(start,True)  # Literal generated values are simulated before fitting.
    if active:
        bounds=np.log([[1000,100000] if elements[i]['kind']=='R' else [1e-9,10e-6] for i in active]).T
        result=least_squares(evaluate,start,bounds=bounds,max_nfev=8,diff_step=1e-3,ftol=1e-5,xtol=1e-5,gtol=1e-5)
        for i,value in zip(active,np.exp(result.x)):fitted[i]['value']=float(value)
        converged=bool(result.success)
    else:converged=True
    gates=[]
    for capture in captures:
        if calls>=80:raise ValueError('Proposal simulator budget exhausted')
        calls+=1
        prediction,_=simulate_netlist(fitted,capture)
        gates.append(adequacy(prediction,capture,noise))
    if topology_fingerprint(elements)!=topology_fingerprint(fitted):
        raise RuntimeError('Parameter fitting changed generated topology')
    return fitted,{'training_passed':converged and all(g['passed'] for g in gates),
                   'optimizer_converged':converged,'checks':gates,'simulator_calls':calls,
                   'initial_generated_simulations':first_metadata,
                   'generated_topology_sha256':topology_fingerprint(elements),
                   'fitted_topology_sha256':topology_fingerprint(fitted),
                   'rendered_generated_proposal':render_proposal(elements),
                   'rendered_fitted_proposal':render_proposal(fitted)}


class DiscoverySession:
    def __init__(self,acquire,log):
        self.acquire,self.log=acquire,log
        self.start=time.monotonic();self.noise=NoiseModel()
        self.report=self.fitted=self.fit_result=self.verification=None
        self.proposals=0;self.inspected=False;self.verification_used=False
        log.add('discovery_configuration',{'training':[a.to_dict() for a in TRAINING],
                    'verification':[a.to_dict() for a in VERIFICATION],
                    'verification_status':'development_conditions_pending_D2_freeze',
                    'max_proposals':2,'max_simulator_calls_per_proposal':80,'noise':self.noise.to_dict()})
        self.captures=[]
        for settings in TRAINING:
            capture=acquire(settings)
            if capture.get('source')!='synthetic' or capture.get('settings')!=settings.to_dict():
                raise ValueError('Discovery requires matching synthetic observations')
            self.captures.append(capture);log.add('acquisition',capture)
        fits=[(family,fit_family(family,self.captures,self.noise)) for family in families_for('mystery')]
        self.initial={'status':'all_candidates_inadequate' if all(not f['fit_passed'] for _,f in fits) else 'initial_candidates_adequate',
                      'candidates':[{'name':family.name,'fit_passed':fit['fit_passed'],
                          'worst_normalized_residual':max(c['normalized_rms'] for g in fit['checks'] for c in g['checks'])} for family,fit in fits]}
        log.add('initial_family_assessment',self.initial)

    def dispatch(self,name,args):
        if self.report is not None:raise ToolRejected('Experiment already finished')
        schema=next((t['parameters'] for t in DISCOVERY_TOOLS if t['name']==name),None)
        if schema is None or not isinstance(args,dict) or set(args)!=set(schema['required']):
            raise ToolRejected('Unknown tool or invalid argument fields')
        if name=='inspect_residuals':
            self.inspected=True
            return {'source':'synthetic','initial_assessment':self.initial,
                    'training':[trace_features(c) for c in self.captures],
                    'verification_data_visible':False,'remaining_proposals':2-self.proposals}
        if not self.inspected:raise ToolRejected('Inspect observations before proposing')
        if name=='propose_netlist':
            if self.verification_used or self.proposals>=2 or self.initial['status']!='all_candidates_inadequate':
                raise ToolRejected('Proposal budget exhausted or discovery unavailable')
            if not isinstance(args['rationale'],str) or not 1<=len(args['rationale'])<=1600:
                raise ToolRejected('Provide a bounded rationale')
            self.proposals+=1
            self.log.add('netlist_proposed',args)
            self.fitted=self.fit_result=None
            try:
                self.fitted,self.fit_result=fit_proposal(args['elements'],self.captures,self.noise)
            except (ValueError,RuntimeError) as exc:
                self.log.add('proposal_rejected',{'error':str(exc),'attempt':self.proposals})
                return {'proposal_accepted':False,'error':str(exc),'remaining_proposals':2-self.proposals}
            self.log.add('proposal_fit',{'elements':self.fitted,**self.fit_result})
            return {'proposal_accepted':True,'training_passed':self.fit_result['training_passed'],
                    'fitted_elements':self.fitted,'topology_preserved':True,
                    'worst_normalized_residual':max(c['normalized_rms'] for g in self.fit_result['checks'] for c in g['checks']),
                    'remaining_proposals':2-self.proposals,'verification_data_visible':False}
        if name=='verify_proposal':
            if self.verification_used or not self.fit_result or not self.fit_result['training_passed']:
                raise ToolRejected('Verification needs a fitted adequate proposal and unused verification budget')
            self.verification_used=True
            predictions=[]
            for settings in VERIFICATION:
                template={'settings':settings.to_dict(),'data':predict(RCModel(10000,1e-6),settings)}
                prediction,meta=simulate_netlist(self.fitted,template)
                predictions.append(prediction)
                self.log.add('prediction_committed',{'elements':self.fitted,'settings':settings.to_dict(),'prediction':prediction,**meta})
            checks=[]
            for settings,prediction in zip(VERIFICATION,predictions):
                capture=self.acquire(settings)
                if capture.get('source')!='synthetic' or capture.get('settings')!=settings.to_dict():
                    raise ValueError('Mismatched verification provenance')
                self.log.add('verification_acquisition',capture)
                checks.append(adequacy(prediction,capture,self.noise))
            self.verification={'passed':all(c['passed'] for c in checks),'conditions':checks,'refitted_on_verification':False}
            self.log.add('verification',self.verification)
            return self.verification
        if any(not isinstance(v,str) or len(v)>1600 for v in args.values()):raise ToolRejected('Invalid report values')
        if args['verdict'] not in ('verified','abstained'):raise ToolRejected('Invalid report verdict')
        if args['verdict']=='verified' and (args['candidate']!='proposed_netlist' or not self.verification or not self.verification['passed']):
            raise ToolRejected('Cannot confirm without both independent verification checks')
        if args['verdict']=='abstained' and args['candidate']:raise ToolRejected('Abstention cannot confirm a candidate')
        if not all(args[k].strip() for k in ('current_explanation','unresolved','next_observation')):raise ToolRejected('Three report fields are required')
        self.report=args;self.log.add('agent_report',args)
        return {'accepted':True}

    def summary(self):
        return {'source':'synthetic','llm_used':True,'mode':'live_nonlinear_discovery',
                'initial_report':self.initial,'agent_report':self.report,'proposals':self.proposals,
                'fitted_netlist':self.fitted,'verification':self.verification,
                'total_physical_acquisitions':3+(2 if self.verification_used else 0),
                'requested_human_actions':0,'simulated_mountings':1 if self.verification_used else 0,
                'elapsed_s':time.monotonic()-self.start,
                'scope':'Synthetic generic-diode development case. Generated topology reaches ngspice; no physical or holdout generalization claim.'}


def run_discovery(*,seed=1,output='runs',effort='max',env_path='.env',budget_path='.private/api-budget.json',client=None):
    # Truth stays at this orchestration boundary; never enters prompts/proposals.
    from .nonlinear_simulation import acquire_nonlinear
    from .providers import MetaToolSession,ProviderError
    from .agent import drive_agent
    from .config import load_keys,redact
    from .records import Recorder
    log=Recorder(output,mode='live_nonlinear_discovery');model=session=None
    rng=np.random.default_rng(seed)
    try:
        session=DiscoverySession(lambda s:acquire_nonlinear(s,rng=rng),log)
        model=MetaToolSession(prompt=DISCOVERY_PROMPT,tools=DISCOVERY_TOOLS,log=log,effort=effort,
                             env_path=env_path,budget_path=budget_path,client=client,
                             max_output_tokens=8192,max_payload_bytes=128000)
        result={**drive_agent(session,model),**model.metadata()}
        result=redact(result,load_keys(env_path));log.add('run_completed',result)
        return log.path,result
    except Exception as exc:
        safe=str(exc) if isinstance(exc,(ProviderError,ValueError)) else type(exc).__name__
        failure={'error':redact(safe,load_keys(env_path))}
        if session is not None:failure['partial_result']=session.summary()
        if model is not None:failure.update(model.metadata())
        log.add('run_failed',redact(failure,load_keys(env_path)))
        raise RuntimeError(f"Discovery failed ({failure['error']}); record: {log.path}") from None
    finally:
        if model is not None:model.close()
