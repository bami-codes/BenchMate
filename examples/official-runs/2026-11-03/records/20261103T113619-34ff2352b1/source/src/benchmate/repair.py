"""D01 synthetic repair: diagnose, commit repaired prediction, replace, remeasure."""
from copy import copy
import numpy as np
from .physics import Acquisition,RCModel
from .simulation import FIXTURES,acquire
from .continuous_agent import ContinuousSession,CONTINUOUS_PROMPT
from .experiments import drive_engine
from .inference import mean_prediction
from .noise import adequacy
from .records import Recorder
from .config import load_keys,redact


def run_repair(case,*,output='runs',seed=1,live=False,c_scale=1.,r_scale=1.,
               repair_succeeds=True,env_path='.env',budget_path='.private/api-budget.json',client=None):
    from .providers import MetaToolSession,ProviderError
    from .agent import drive_agent
    if case not in ('d01-r','d01-c'):raise ValueError('Select a declared D01 development fixture')
    base=FIXTURES[case]
    state=RCModel(base.r_ohm*r_scale,base.c_f*c_scale)
    rng=np.random.default_rng(seed)
    log=Recorder(output,mode='synthetic_repair_with_live_agent' if live else 'synthetic_repair_engine_only')
    model=session=None
    try:
        session=ContinuousSession(lambda settings:acquire(state,settings,rng=rng),log,mode='repair')
        if live:
            model=MetaToolSession(prompt=CONTINUOUS_PROMPT,tools=session.tools,log=log,env_path=env_path,
                                 budget_path=budget_path,client=client)
            diagnosis={**drive_agent(session,model),**model.metadata()}
        else:diagnosis=drive_engine(session)
        log.add('diagnostic_phase_completed',diagnosis)
        if diagnosis['agent_report']['verdict']!='verified':
            summary={'source':'synthetic','llm_used':live,'diagnosis':diagnosis,'repair_success':False,
                     'repair_attempted':False,'status':'diagnosis_abstained'}
        else:
            candidate=diagnosis['agent_report']['candidate']
            if candidate not in ('r_changed','c_changed'):
                raise ValueError('No supported component replacement in declared repair scenario')
            part='R' if candidate=='r_changed' else 'C'
            value=10000. if part=='R' else 1e-6
            winner=next(p for p in session.posteriors if p.family.name==candidate)
            repaired=copy(winner);repaired.models=winner.models.copy()
            repaired.models[:,0 if part=='R' else 1]=value
            plan={'component':part,'replacement_value':value,'source':'declared_design',
                  'execution':'simulated','physical_human_action':False}
            log.add('repair_requested',plan)
            settings=[Acquisition(),Acquisition(load_ohm=10000)]
            predictions=[]
            for setting in settings:
                p=mean_prediction(repaired,setting,noise=session.noise);predictions.append(p)
                log.add('repair_prediction_committed',{'repair':plan,'settings':setting.to_dict(),'prediction':p})
            # Simulator applies only the requested part change, never chooses a
            # repair from fixture identity. Failed-repair injection is test-only.
            if repair_succeeds:
                state=RCModel(value if part=='R' else state.r_ohm,value if part=='C' else state.c_f)
            log.add('repair_applied',{**plan,'simulated_replacement_applied':repair_succeeds})
            checks=[]
            for setting,prediction in zip(settings,predictions):
                observed=acquire(state,setting,rng=rng)
                log.add('repair_verification_acquisition',observed)
                checks.append(adequacy(prediction['mean'],observed,session.noise,prediction['parameter_whitened_sd']))
            verification={'passed':all(c['passed'] for c in checks),'conditions':checks,'refitted_on_verification':False}
            log.add('repair_verification',verification)
            summary={'source':'synthetic','llm_used':live,'diagnosis':diagnosis,'repair':plan,
                     'repair_attempted':True,'repair_success':verification['passed'],'verification':verification,
                     'status':'repair_verified' if verification['passed'] else 'repair_not_verified',
                     'diagnostic_acquisitions_total':diagnosis['total_physical_acquisitions'],
                     'repair_verification_acquisitions':2,
                     'total_physical_acquisitions':diagnosis['total_physical_acquisitions']+2,
                     'requested_human_actions':0,'simulated_component_replacements':1,
                     'budget_note':'Repair confirmation is a separate, explicitly counted phase after the diagnostic budget.',
                     'scope':'Synthetic D01 workflow only; no physical replacement or hardware repair demonstrated.'}
        summary=redact(summary,load_keys(env_path));log.add('run_completed',summary)
        return log.path,summary
    except Exception as exc:
        safe=str(exc) if isinstance(exc,(ValueError,ProviderError)) else type(exc).__name__
        failure={'error':redact(safe,load_keys(env_path)),'source':'synthetic'}
        if model is not None:failure.update(model.metadata())
        log.add('run_failed',failure)
        raise RuntimeError(f"Repair failed ({failure['error']}); record: {log.path}") from None
    finally:
        if model is not None:model.close()
