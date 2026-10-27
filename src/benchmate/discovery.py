"""Model-authored passive topology proposals with untouched verification data."""
from copy import deepcopy
import json
import time
import numpy as np
from scipy.optimize import least_squares

from .agent import function_tool, ToolRejected, TOOLS
from .inference import families_for, fit_family
from .netlist import ELEMENT_SCHEMA,validate_netlist,simulate_netlist,topology_fingerprint,render_proposal,render_diode,DIODE_INITIAL,DIODE_BOUNDS
from .noise import NoiseModel,adequacy,whitened_vector
from .physics import Acquisition
from .stimulus import command_template
from .comparison import best_linear_comparison, frozen_linear_prediction, prediction_separation, verification_comparison
from .linearity import amplitude_scaling
from .menu import MenuConfig, measurement_menu, mounting_instruction
from .recommendations import NEXT_PROMPT, next_schema, validate_next, recommendation_context


TRAINING = [Acquisition(),
            Acquisition(kind='sine',frequency_hz=1,amplitude_v=.2,duration_s=2,sample_period_s=.002),
            Acquisition(kind='sine',frequency_hz=1,amplitude_v=1,duration_s=2,sample_period_s=.002),
            Acquisition(kind='sine',frequency_hz=1,amplitude_v=1,duration_s=2,sample_period_s=.002,load_ohm=4700)]
# Development values, committed before proposal. Physical values freeze at D2.
VERIFICATION = [Acquisition(amplitude_v=.35),
                Acquisition(kind='sine',frequency_hz=1,amplitude_v=1,duration_s=2,sample_period_s=.002,load_ohm=10000)]

DISCOVERY_PROMPT = """You operate BenchMate's structure discovery on SYNTHETIC
observations. You do not know the specimen identity, topology or component values.
First inspect_residuals. Review the observations, acquisition settings and fit
checks. If the initial families are inadequate, propose_netlist with your own
passive connectivity and a short English rationale grounded in the observations.
Allowed nodes: IN, OUT, REF, N1, N2. Every element has name, kind R/C/D, a, b,
value, model. For R/C, model=none and value is ohms/farads. For D, value=0,
model=generic_diode; a is anode, b cathode. The library starts at IS=1nA, N=1.8.
IS (0.1–100nA) and N (1–2.5) are fitted only from training data when D is used.
RS=1ohm and 27C are fixed development assumptions, not calibrated physical parts.
Use 1–6 elements, at most 2 R/C parameters plus shared IS/N (4 parameters total).
R is bounded to 1k–100k and C to 1n–10u.
Your exact nodes and diode orientation go into ngspice. The backend can refine
numeric values using training data only, never replace your topology.
At most 2 proposals and a fixed simulator budget are allowed. If training passes,
call verify_proposal to freeze the netlist and predictions BEFORE two untouched
conditions are acquired. Do not request fitting on verification data. If checks
fail, abstain. Finish using finish_report with concise English explanation,
unresolved scope and next observation. Verdict verified and candidate proposed_netlist
are allowed only after BOTH independent checks pass; otherwise abstained with
empty candidate. Always state synthetic/development scope. No plain-text ending.
Keep each report field under 45 words. Report only numbers supported by the
tools; do not invent detection limits, parameter uncertainty or validity ranges.
Use plain English: explain what the circuit does instead of listing component
parameters already in the evidence. For the next observation, describe one
understandable change and what it would test in one sentence.
Next observations must respect REF +/-1V and transitions no larger than 1V.
"""
DISCOVERY_PROMPT += NEXT_PROMPT + '\nUse measurement_details to read any future menu action. Frequency IDs f0..f5 refer to the configured grid, not literal Hz.\n'
DISCOVERY_MENU = measurement_menu()

DISCOVERY_TOOLS = [
    function_tool('inspect_residuals','Read training observations, amplitude scaling and initial linear-family checks.'),
    function_tool('propose_netlist','Propose the actual passive netlist to simulate; topology will not be replaced.',
                  {'elements':{'type':'array','items':ELEMENT_SCHEMA},'rationale':{'type':'string'}}),
    function_tool('verify_proposal','Freeze predictions then acquire two unused verification conditions; no refitting.'),
    deepcopy(next(t for t in TOOLS if t['name']=='finish_report')),
    function_tool('measurement_details','Inspect a configured future measurement; does not acquire data.',
                  {'action':{'type':'string','enum':list(DISCOVERY_MENU)}}),
]
next(t for t in DISCOVERY_TOOLS if t['name']=='finish_report')['parameters']['properties']['next_observation'] = next_schema(DISCOVERY_MENU)


def trace_features(capture):
    data=capture['data'];idx=np.linspace(0,len(data['out_v'])-1,25).astype(int)
    return {'settings':capture['settings'],'source':'synthetic',
            'trace_samples':[{k:float(data[k][i]) for k in ('time_s','drive_v','ref_v','in_v','out_v')} for i in idx],
            'full_trace_recorded':True}


MAX_SIMULATOR_CALLS = 420
MAX_FIT_SECONDS = 60


def fit_proposal(elements,captures,noise=NoiseModel()):
    elements=validate_netlist(elements)
    fitted=deepcopy(elements)
    active=[i for i,e in enumerate(elements) if e['kind'] in ('R','C')]
    has_diode=any(e['kind']=='D' for e in elements)
    if len(active)>2:
        raise ValueError('Development fitting supports at most two R/C values plus shared diode IS/N')
    names=[elements[i]['name'] for i in active]+(['diode_IS','diode_N'] if has_diode else [])
    bounds=[[1000,100000] if elements[i]['kind']=='R' else [1e-9,10e-6] for i in active]
    initial=[elements[i]['value'] for i in active]
    if has_diode:
        initial+=list(DIODE_INITIAL.values());bounds+=list(DIODE_BOUNDS.values())
    calls=0;cache_hits=0;cache={};first_metadata=[];began=time.monotonic();diode=dict(DIODE_INITIAL)

    def decode(log_values):
        for i,value in zip(active,np.exp(log_values[:len(active)])):
            fitted[i]['value']=float(value)
        if has_diode:
            diode.update(zip(DIODE_INITIAL,map(float,np.exp(log_values[-2:]))))

    def consume_run():
        nonlocal calls
        if calls>=MAX_SIMULATOR_CALLS or time.monotonic()-began>MAX_FIT_SECONDS:
            raise ValueError('Proposal simulator budget exhausted')
        calls+=1

    def simulate(capture):
        nonlocal cache_hits
        if time.monotonic()-began>MAX_FIT_SECONDS:raise ValueError('Proposal simulator budget exhausted')
        key=(id(capture),tuple(e['value'] for e in fitted),tuple(diode.values()))
        if key in cache:
            cache_hits+=1
            prediction,meta=cache[key]
            return prediction,{**meta,'reused_within_proposal':True}
        result=simulate_netlist(fitted,capture,diode=diode,before_run=consume_run)
        cache[key]=result
        return result

    def evaluate(log_values,record_initial=False):
        decode(log_values)
        residuals=[]
        for capture in captures:
            prediction,meta=simulate(capture)
            if record_initial:first_metadata.append(meta)
            residuals.append(whitened_vector(prediction,capture,noise))
        return np.concatenate(residuals)

    start=np.log(initial)
    evaluate(start,True)  # Literal generated values and starting library run first.
    if initial:
        # Absolute steps in log coordinates avoid IS-dependent finite differences.
        def jacobian(x):
            base=evaluate(x);columns=[];limits=np.log(bounds).T
            for i in range(len(x)):
                step=1e-3 if x[i]+1e-3<limits[1,i] else -1e-3
                shifted=x.copy();shifted[i]+=step
                columns.append((evaluate(shifted)-base)/step)
            return np.column_stack(columns)
        result=least_squares(evaluate,start,bounds=np.log(bounds).T,jac=jacobian,
                             max_nfev=18,ftol=1e-6,xtol=1e-6,gtol=1e-6)
        decode(result.x)
        converged=bool(result.success)
        singular=np.linalg.svd(result.jac,compute_uv=False)
        condition=float(singular[0]/max(singular[-1],1e-12))
        identifiable=bool(singular[-1]>1 and condition<1e5)
    else:
        converged=identifiable=True;condition=None
    gates=[];training_predictions=[]
    for capture in captures:
        prediction,_=simulate(capture)
        gates.append(adequacy(prediction,capture,noise))
        training_predictions.append({'settings':capture['settings'],'time_s':prediction['time_s'],
                                     'out_v':prediction['out_v']})
    if topology_fingerprint(elements)!=topology_fingerprint(fitted):
        raise RuntimeError('Parameter fitting changed generated topology')
    return fitted,{'training_passed':converged and identifiable and all(g['passed'] for g in gates),
                   'optimizer_converged':converged,'parameters_identifiable':identifiable,
                   'log_parameter_jacobian_condition':condition,'fitted_parameter_names':names,
                   'diode_parameters':dict(diode),'diode_parameter_bounds':DIODE_BOUNDS,
                   'diode_fixed_assumptions':{'rs_ohm':1.,'temperature_c':27.},
                   'checks':gates,'simulator_calls':calls,'simulation_cache_hits':cache_hits,'training_predictions':training_predictions,
                   'initial_generated_simulations':first_metadata,
                   'generated_topology_sha256':topology_fingerprint(elements),
                   'fitted_topology_sha256':topology_fingerprint(fitted),
                   'rendered_generated_proposal':render_proposal(elements),
                   'rendered_fitted_proposal':render_proposal(fitted),
                   'rendered_fitted_diode':render_diode(diode)}


class DiscoverySession:
    def __init__(self,acquire,log):
        self.acquire,self.log=acquire,log
        self.start=time.monotonic();self.noise=NoiseModel()
        self.report=self.fitted=self.fit_result=self.verification=None
        self.proposals=0;self.inspected=False;self.verification_used=False
        self.families=families_for('mystery')
        log.add('discovery_configuration',{'training':[a.to_dict() for a in TRAINING],
                    'verification':[a.to_dict() for a in VERIFICATION],
                    'verification_status':'development_conditions_pending_D2_freeze',
                    'max_proposals':2,'max_simulator_calls_per_proposal':MAX_SIMULATOR_CALLS,
                    'max_fit_seconds':MAX_FIT_SECONDS,'max_fitted_parameters':4,
                    'acquisition_budget':{'exploration':1,'diagnostic':3,'verification':2},
                    'noise':self.noise.to_dict(),'families':[f.to_dict() for f in self.families],
                    'menu':MenuConfig().to_dict(),'instrument_capabilities':recommendation_context(),
                    'comparison_scope':'declared_linear_families_v2'})
        self.captures=[]
        for settings in TRAINING:
            capture=acquire(settings)
            if capture.get('source')!='synthetic' or capture.get('settings')!=settings.to_dict():
                raise ValueError('Discovery requires matching synthetic observations')
            self.captures.append(capture);log.add('acquisition',capture)
        fits=[(family,fit_family(family,self.captures,self.noise)) for family in self.families]
        self.initial={'status':'all_candidates_inadequate' if all(not f['fit_passed'] for _,f in fits) else 'initial_candidates_adequate',
                      'candidates':[{'name':family.name,'fit_passed':fit['fit_passed'],
                          'worst_normalized_residual':max(c['normalized_rms'] for g in fit['checks'] for c in g['checks'])} for family,fit in fits]}
        self.initial['amplitude_scaling']=amplitude_scaling(self.captures,self.noise)
        self.linear_comparison=best_linear_comparison(fits,self.captures)
        log.add('initial_family_assessment',{**self.initial,'training_comparison':self.linear_comparison})

    def dispatch(self,name,args):
        if self.report is not None:raise ToolRejected('Experiment already finished')
        schema=next((t['parameters'] for t in DISCOVERY_TOOLS if t['name']==name),None)
        if schema is None or not isinstance(args,dict) or set(args)!=set(schema['required']):
            raise ToolRejected('Unknown tool or invalid argument fields')
        if name=='inspect_residuals':
            self.inspected=True
            return {'source':'synthetic','initial_assessment':self.initial,
                    'training':[trace_features(c) for c in self.captures],
                    'verification_data_visible':False,'remaining_proposals':2-self.proposals,
                    'menu_configuration':MenuConfig().to_dict(),'instrument_capabilities':recommendation_context()}
        if not self.inspected:raise ToolRejected('Inspect observations before proposing')
        if name=='measurement_details':
            action=args['action']
            if not isinstance(action,str) or action not in DISCOVERY_MENU:raise ToolRejected('Choose a configured menu action')
            settings=DISCOVERY_MENU[action]
            return {'settings':settings.to_dict(),'instruction':mounting_instruction(settings),
                    'physical_acquisitions':settings.physical_acquisitions,'execution':'not_scheduled'}
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
                    'fitted_diode_parameters':self.fit_result['diode_parameters'],
                    'parameters_identifiable':self.fit_result['parameters_identifiable'],
                    'worst_normalized_residual':max(c['normalized_rms'] for g in self.fit_result['checks'] for c in g['checks']),
                    'remaining_proposals':2-self.proposals,'verification_data_visible':False}
        if name=='verify_proposal':
            if self.verification_used or not self.fit_result or not self.fit_result['training_passed']:
                raise ToolRejected('Verification needs a fitted adequate proposal and unused verification budget')
            self.verification_used=True
            predictions=[];baselines=[]
            for settings in VERIFICATION:
                template=command_template(settings)
                prediction,meta=simulate_netlist(self.fitted,template,diode=self.fit_result['diode_parameters'])
                predictions.append(prediction)
                baseline=frozen_linear_prediction(self.linear_comparison,settings.to_dict());baselines.append(baseline)
                comparison={'prediction':baseline,'parameters':self.linear_comparison['parameters'],
                            'family':self.linear_comparison['family'],'training_frozen':True,
                            'comparison_scope':self.linear_comparison['comparison_scope'],
                            'separation':prediction_separation(baseline,prediction)}
                self.log.add('prediction_committed',{'elements':self.fitted,'settings':settings.to_dict(),'prediction':prediction,
                    'baseline_comparison':comparison,'input_provenance':template['input_provenance'],**meta})
            checks=[];comparisons=[]
            for settings,prediction,baseline in zip(VERIFICATION,predictions,baselines):
                capture=self.acquire(settings)
                if capture.get('source')!='synthetic' or capture.get('settings')!=settings.to_dict():
                    raise ValueError('Mismatched verification provenance')
                self.log.add('verification_acquisition',capture)
                checks.append(adequacy(prediction,capture,self.noise))
                comparisons.append(verification_comparison(baseline,prediction,capture,self.noise))
            self.verification={'passed':all(c['passed'] for c in checks),'conditions':checks,
                               'comparison_conditions':comparisons,'refitted_on_verification':False}
            self.log.add('verification',self.verification)
            return self.verification
        if any(not isinstance(v,str) or len(v)>1600 for k,v in args.items() if k!='next_observation'):raise ToolRejected('Invalid report values')
        if args['verdict'] not in ('verified','abstained'):raise ToolRejected('Invalid report verdict')
        if args['verdict']=='verified' and (args['candidate']!='proposed_netlist' or not self.verification or not self.verification['passed']):
            raise ToolRejected('Cannot confirm without both independent verification checks')
        if args['verdict']=='abstained' and args['candidate']:raise ToolRejected('Abstention cannot confirm a candidate')
        if not all(args[k].strip() for k in ('current_explanation','unresolved')):raise ToolRejected('Three report fields are required')
        try:recommendation=validate_next(args['next_observation'],DISCOVERY_MENU)
        except ValueError as exc:raise ToolRejected(str(exc)) from None
        self.report={**args,'next_observation':recommendation['instruction'],'next_measurement':recommendation}
        self.log.add('agent_report',self.report)
        return {'accepted':True}

    def summary(self):
        return {'source':'synthetic','llm_used':True,'mode':'live_structure_discovery',
                'initial_report':self.initial,'agent_report':self.report,'proposals':self.proposals,
                'fitted_netlist':self.fitted,'fitted_diode_parameters':self.fit_result['diode_parameters'] if self.fit_result else None,'verification':self.verification,
                'total_physical_acquisitions':len(self.captures)+(2 if self.verification_used else 0),
                'requested_human_actions':0,'simulated_mountings':1+(1 if self.verification_used else 0),
                'elapsed_s':time.monotonic()-self.start,
                'scope':'Synthetic mismatched-diode development case. Generated topology reaches ngspice; IS/N fitted on training only; no physical or holdout generalization claim.'}


def run_discovery(*,seed=1,output='runs',effort='max',env_path='.env',budget_path='.private/api-budget.json',client=None):
    # Truth stays at this orchestration boundary; never enters prompts/proposals.
    from .nonlinear_simulation import acquire_nonlinear
    from .providers import MetaToolSession,ProviderError
    from .agent import drive_agent
    from .config import load_keys,redact
    from .records import Recorder
    log=Recorder(output,mode='live_structure_discovery');model=session=None
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
