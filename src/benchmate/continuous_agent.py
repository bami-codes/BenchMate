"""Live tools on common continuous priors and a configurable measurement menu."""
from copy import deepcopy
import time
import numpy as np
from .agent import ExperimentSession, ToolRejected, TOOLS, observation_summary
from .inference import infer, families_for, mean_prediction
from .menu import MenuConfig, measurement_menu, mounting_instruction
from .noise import NoiseModel, adequacy, channels
from .physics import Acquisition, RCModel, predict, confirmation_for
from .vector import predict_many


CONTINUOUS_PROMPT = """You operate BenchMate on a SYNTHETIC instrument with continuous RC
parameter inference. No physical hardware is connected. You never receive the
specimen ID, hidden values or answer. First call inspect_experiment. Read the
current candidate support, identifiability, numerical evidence and ranked menu.
Select measure(action, reason) to resolve structure or remaining parameter
ambiguity. Explain the choice briefly in English. Frequency names f0..f5 refer
to the configured grid, not literal Hz. Call measurement_details if needed.

The budget is 1 common exploration, 3 diagnostic acquisitions, 1 independent
confirmation. A shunt DC pair costs 2 diagnostic acquisitions; every other menu
item costs 1. Mounting changes and stabilization are simulated, not performed
by a human. The same mystery priors apply to every specimen. Repair mode priors
are declared schematic knowledge and must not be confused with mystery mode.

Without loading or transient shunt observations, only tau=RC is separately
observed; prior-driven R/C intervals are not identification. Continue measuring
when one structure fits but parameters remain unresolved. Only when the engine
reports verification_required call verify_prediction. It freezes a posterior
prediction before collecting a fresh, reserved intermediate-amplitude step.
No verification data is refitted. Conditional model probability alone is not
confirmation. If all candidates fail or numerical integration is unresolved,
report abstention rather than claiming a unique circuit.

Finish using finish_report, with three concise English fields:
current_explanation, unresolved, next_observation. Verdict verified requires
matching independent verification and the supported candidate name. Otherwise
use abstained with an empty candidate. State the synthetic and declared-family
scope. Never finish only with plain text. Tool errors may be corrected within
the API request limit. Temperature is provider default.
Keep each report field under 45 words. Never invent measured precision or
detection limits. Recommend only observations within the declared stimulus limits.
"""


def continuous_tools(menu):
    from .agent import function_tool
    tools = deepcopy(TOOLS)
    next(t for t in tools if t['name']=='measure')['parameters']['properties']['action']['enum'] = list(menu)
    tools.append(function_tool('measurement_details','Read the full settings of any listed action.',
                               {'action':{'type':'string','enum':list(menu)}}))
    return tools


def representative_rows(posterior, n=32):
    index = np.searchsorted(np.cumsum(posterior.weights),(np.arange(n)+.5)/n).clip(max=len(posterior.models)-1)
    return posterior.models[index]


def rank_measurements(posteriors, menu, last_settings, noise):
    live = [p for p in posteriors if p.fit['fit_passed']]
    if not live:
        return []
    rows = [representative_rows(p) for p in live]
    ranked = []
    for name, settings in menu.items():
        base = predict(RCModel(10000,1e-6),settings)
        template = {'settings':settings.to_dict(),'data':base}
        predictions = [predict_many(r,template) for r in rows]
        means, variances = [], []
        for predicted in predictions:
            whitened = np.concatenate([noise.whiten(predicted[k],independent=settings.kind=='dc_pair',channel=k) for k in channels(template)],axis=-1)
            means.append(whitened.mean(axis=0)); variances.append(whitened.var(axis=0))
        between = max((float(np.mean((means[i]-means[j])**2/(1+variances[i]+variances[j])))
                       for i in range(len(live)) for j in range(i)), default=0.)
        within = float(np.mean(np.log1p(np.mean(variances,axis=0))))
        mounts = int(settings.shunt_ohm != last_settings.shunt_ohm) + int(settings.load_ohm != last_settings.load_ohm)
        # Explicit engineering cost, not measured human timing or exact entropy.
        cost = settings.physical_acquisitions + 2*mounts + settings.duration_s
        score = (between if len(live)>1 else within) / cost
        ranked.append({'action':name,'settings':settings.to_dict(),'score':score,
                       'structure_separation':between,'parameter_spread_score':within,
                       'development_cost':cost,'mounting_changes':mounts,
                       'physical_acquisitions':settings.physical_acquisitions,
                       'score_kind':'posterior_predictive_separation_proxy_not_exact_information_gain'})
    return sorted(ranked,key=lambda x:x['score'],reverse=True)


def concise_analysis(analysis):
    result = {k:v for k,v in analysis.items() if k!='candidates'}
    result['candidates'] = []
    for candidate in analysis['candidates']:
        row = {k:v for k,v in candidate.items() if k!='regional_checks'}
        checks = [c for capture in candidate['regional_checks'] for c in capture['checks']]
        row['worst_normalized_residual'] = max(c['normalized_rms'] for c in checks)
        row['failed_regions'] = [f"{c['channel']}:{c['region']}" for c in checks if not c['passed']]
        result['candidates'].append(row)
    return result


class ContinuousSession(ExperimentSession):
    def __init__(self, acquire, log, *, mode='mystery', noise=NoiseModel(), menu_config=MenuConfig()):
        self.mode, self.noise = mode, noise
        self.families = families_for(mode)
        self.menu_config = menu_config
        self.menu = measurement_menu(menu_config)
        self.tools = continuous_tools(self.menu)
        self.acquire, self.log = acquire, log
        self.start = time.monotonic()
        self.captures = []
        self.diagnostic_acquisitions = self.confirmation_acquisitions = self.simulated_mountings = 0
        self.inspected = False
        self.verification = self.report = None
        self.actions = []
        self.last_settings = Acquisition()
        log.add('inference_configuration',{'mode':mode,'families':[f.to_dict() for f in self.families],
                 'noise':noise.to_dict(),'menu':menu_config.to_dict(),
                 'regional_windows_s':[[0,.005],[.005,.020],[.020,.080]],
                 'quadrature_orders':[4,7,10],'log_evidence_tolerance':.05})
        self._acquire(self.last_settings,'acquisition')
        self.update_analysis()
        self.initial_analysis = deepcopy(self.analysis)

    def update_analysis(self):
        self.analysis,self.posteriors = infer(self.captures,self.families,self.noise)
        self.log.add('diagnosis',self.analysis)
        self.ranked = rank_measurements(self.posteriors,self.menu,self.last_settings,self.noise)
        self.log.add('action_ranking',self.ranked)

    def snapshot(self):
        remaining = 3-self.diagnostic_acquisitions
        ranked = [{**r,'affordable':r['physical_acquisitions']<=remaining} for r in self.ranked]
        return {'source':'synthetic','mode':self.mode,'analysis':concise_analysis(self.analysis),
                'observations':[observation_summary(c) for c in self.captures],
                'action_ranking':ranked[:5], 'menu_size':len(self.menu),'menu_configuration':self.menu_config.to_dict(),
                'ranking_note':'Top five shown; measurement_details exposes every tool-enumerated action.',
                'budget':{'exploration_used':1,'diagnostic_used':self.diagnostic_acquisitions,
                          'diagnostic_remaining':remaining,'confirmation_used':self.confirmation_acquisitions,'confirmation_limit':1},
                'verification':self.verification}

    def dispatch(self,name,arguments):
        if name=='measurement_details':
            if self.report is not None or not self.inspected or not isinstance(arguments,dict) or set(arguments)!={'action'} or arguments['action'] not in self.menu:
                raise ToolRejected('Inspect first and choose a valid action')
            settings = self.menu[arguments['action']]
            return {'settings':settings.to_dict(),'instruction':mounting_instruction(settings),
                    'physical_acquisitions':settings.physical_acquisitions}
        return super().dispatch(name,arguments)

    def measure(self,action,reason):
        if self.analysis['status']!='unresolved':
            raise ToolRejected('Measure only while unresolved; otherwise verify or report')
        if not reason.strip():
            raise ToolRejected('Explain the measurement choice')
        settings = self.menu[action]
        if self.diagnostic_acquisitions+settings.physical_acquisitions>3:
            raise ToolRejected('Diagnostic acquisition budget exhausted')
        self.log.add('instrument_request',{'action':action,'reason':reason,'instruction':mounting_instruction(settings),
                     'settings':settings.to_dict(),
                     'execution':'simulated','physical_human_action':False,'selected_by':'controller'})
        self.simulated_mountings += int(settings.shunt_ohm!=self.last_settings.shunt_ohm)+int(settings.load_ohm!=self.last_settings.load_ohm)
        self.diagnostic_acquisitions += settings.physical_acquisitions
        self.last_settings = settings
        self.actions.append(action)
        self._acquire(settings,'acquisition')
        self.update_analysis()
        return self.snapshot()

    def verify(self):
        if self.analysis['status']!='verification_required' or self.confirmation_acquisitions:
            raise ToolRejected('Verification requires an identified supported candidate and unused confirmation budget')
        winner = next(p for p in self.posteriors if p.family.name==self.analysis['supported_candidates'][0])
        settings = confirmation_for(self.last_settings)
        prediction = mean_prediction(winner,settings,noise=self.noise)
        self.log.add('prediction_committed',{'candidate':winner.family.name,'settings':settings.to_dict(),
                     'prediction':prediction,'posterior_frozen':True})
        self.confirmation_acquisitions += 1
        capture = self._acquire(settings,'verification_acquisition')
        self.verification = {**adequacy(prediction['mean'],capture,self.noise,prediction['parameter_whitened_sd']),
                             'refitted_on_verification':False}
        self.log.add('verification',self.verification)
        self.analysis = {**self.analysis,'status':'verified_within_declared_candidates' if self.verification['passed'] else 'prediction_failed'}
        return self.snapshot()

    def summary(self):
        return {**super().summary(),'mode':'continuous_agent_with_synthetic_instrument','diagnostic_mode':self.mode,
                'scope':'Continuous declared one-state families with regional AR(1)-ready checks; synthetic development only. Numerical evidence and predictive checks are approximate and require D2 calibration for hardware.'}
