"""Continuous experiment orchestration; only this boundary selects simulator truth."""
import numpy as np
from .simulation import FIXTURES, acquire
from .physics import RCModel
from .records import Recorder
from .config import load_keys, redact
from .continuous_agent import ContinuousSession, CONTINUOUS_PROMPT
from .menu import MenuConfig


def drive_engine(session):
    session.dispatch('inspect_experiment',{})
    while session.analysis['status']=='unresolved':
        affordable=[a for a in session.ranked if a['physical_acquisitions']<=3-session.diagnostic_acquisitions]
        if not affordable or affordable[0]['score']<=0:break
        session.dispatch('measure',{'action':affordable[0]['action'],'reason':'Engine-only predictive ranking; no model call.'})
    if session.analysis['status']=='verification_required':session.dispatch('verify_prediction',{})
    verified=session.analysis['status']=='verified_within_declared_candidates'
    session.dispatch('finish_report',{'verdict':'verified' if verified else 'abstained',
        'candidate':session.analysis['supported_candidates'][0] if verified else '',
        'current_explanation':'선언한 연속 RC 후보군에서 합성 관측을 분석했습니다.',
        'unresolved':'실물 계측과 후보군 밖 회로는 검증하지 않았습니다.',
        'next_observation':'D2 보정 후 동일한 조건을 실제 보드에서 측정합니다.'})
    return {**session.summary(),'llm_used':False,'mode':'continuous_engine_only'}


def run_experiment(case, *, mode='mystery', live=False, seed=1, output='runs', effort='medium',
                   env_path='.env', budget_path='.private/api-budget.json', client=None,
                   max_hz=100., r_scale=1., c_scale=1., max_requests=8):
    from .providers import MetaToolSession, ProviderError
    from .agent import drive_agent
    if case not in FIXTURES:
        raise ValueError('Unknown simulator fixture')
    base = FIXTURES[case]
    truth = RCModel(base.r_ohm*r_scale,base.c_f*c_scale,base.input_parallel_ohm)
    rng = np.random.default_rng(seed)
    log = Recorder(output,mode='continuous_live_agent' if live else 'continuous_engine_only')
    model = session = None
    try:
        session = ContinuousSession(lambda settings:acquire(truth,settings,rng=rng),log,
                                    mode=mode,menu_config=MenuConfig(max_hz=max_hz))
        if live:
            model = MetaToolSession(prompt=CONTINUOUS_PROMPT,tools=session.tools,log=log,effort=effort,
                                    env_path=env_path,budget_path=budget_path,client=client,max_requests=max_requests)
            result = {**drive_agent(session,model),**model.metadata()}
        else:
            result=drive_engine(session)
        result['menu_configuration'] = session.menu_config.to_dict()
        result = redact(result,load_keys(env_path))
        log.add('run_completed',result)
        return log.path,result
    except Exception as exc:
        safe = str(exc) if isinstance(exc,(ProviderError,ValueError)) else type(exc).__name__
        failure = {'error':safe,'source':'synthetic','llm_used':live}
        if session is not None:
            failure['partial_result'] = session.summary()
        if model is not None:
            failure.update(model.metadata())
        failure = redact(failure,load_keys(env_path))
        log.add('run_failed',failure)
        raise RuntimeError(f"Experiment failed ({failure['error']}); record: {log.path}") from None
    finally:
        if model is not None:
            model.close()
