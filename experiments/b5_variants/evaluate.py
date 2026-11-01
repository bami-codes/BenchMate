"""Final variant harness, locked until a completed physical B5 attempt exists.

No final evaluation is run by the overnight preparation. The physical log is a
local gate only: it is never sent to the model. Every grid case is retained.
"""
import argparse
from copy import deepcopy
import hashlib,json,sys,time,signal,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'experiments'))
from b5_variants.bench import IDS,VariantBench,seed,noiseless
from b5_variants.run import verify_manifest,generic_elements,save
from b5_variants.fitting import fit_proposal_start
from benchmate.b5_session import B5Session,PROMPT,TOOLS,CONTROL,TRAINING,RESERVED
from benchmate.b5_models import fit_linear,predict,score
from benchmate.b5_bench import observation
from benchmate.agent import drive_agent
from benchmate.providers import MetaToolSession
from benchmate import providers
from benchmate.records import Recorder,canonical,decode_events
from night_budget import Ledger,MeteredClient


def physical_gate(path):
    path=Path(path);path=path/'events.jsonl' if path.is_dir() else path
    events=decode_events(path.read_bytes())
    if events[0]['payload'].get('mode')!='meta_unloaded_B5_physical':
        raise ValueError('A completed physical B5 attempt is required; mocks do not unlock evaluation')
    return hashlib.sha256(path.read_bytes()).hexdigest()


def frozen_receipt(log,value,digest):
    save(log.path/'predictions.json',value)
    log.add('variant_local_publication',{'sha256':digest,'remote':False,'source':'mock'})
    return {'sha256':digest,'published':True,'remote':False}


def equivalence(model,variant,design):
    conditions=[RESERVED[0],RESERVED[1],*design['scoring']['equivalence_check']['conditions'][2:]]
    results=[]
    for settings in conditions:
        t,y=noiseless(variant,settings)
        c=observation('mock',settings,'verification','audit-only','audit-only',t,y)
        results.append({'settings':settings,**score(c,predict(model,t))})
    return results


def scripted(arm,bench,log,design):
    controls=[]
    for s in CONTROL:
        c=bench.acquire(s,'control');log.add('b5_observation',c);controls.append(score(c,c['input_template']['data']['input_relative_origin_v']))
    if not all(c['passed'] for c in controls):raise RuntimeError('Control failed')
    bench.prepare_specimen();training=[]
    for s in TRAINING:
        c=bench.acquire(s,'training');training.append(c);log.add('b5_observation',c)
    initial=fit_linear(training);log.add('b5_initial_assessment',initial)
    if initial['status']!='all_candidates_inadequate':return {'outcome':'gate_closed','model':None}
    if arm=='engine_only':return {'outcome':'abstained','model':None}
    fits=[]
    for candidate in IDS[:10]:
        attempts=[]
        for i,diode in enumerate(({'is_a':1e-9,'n':1.8},{'is_a':1e-10,'n':1.3},{'is_a':1e-8,'n':2.2})):
            try:
                fit=fit_proposal_start(generic_elements(candidate,i),training,diode);fit.pop('initial_generated_predictions',None)
                attempts.append(fit)
            except (ValueError,RuntimeError) as exc:attempts.append({'optimizer_converged':False,'error':str(exc)})
        log.add('oracle_candidate_attempts',{'candidate':candidate,'attempts':attempts})
        converged=[x for x in attempts if x.get('optimizer_converged')]
        if converged:fits.append(min(converged,key=lambda x:x['training_cost']))
    passing=[x for x in fits if x['training_passed']]
    if not passing:return {'outcome':'abstained','model':None}
    best=min(passing,key=lambda x:max(r['RMS_mV'] for c in x['checks'] for r in c['regions']))
    frozen={'source':'mock','model':best['model'],'reserved_output_samples_used':0}
    digest=hashlib.sha256(canonical(frozen)).hexdigest();log.add('oracle_prediction_frozen',frozen)
    frozen_receipt(log,frozen,digest)
    checks=[]
    for s in RESERVED:
        c=bench.acquire(s,'verification');log.add('b5_observation',c);checks.append(score(c,predict(best['model'],c['input_template'])))
    log.add('oracle_reserved_checks',checks)
    return {'outcome':'verified' if all(c['passed'] for c in checks) else 'abstained','model':best['model']}


def execute_one(arm,variant,repetition,output,design,classification,ledger):
    log=Recorder(output/arm/variant,mode='b5_variant_evaluation_'+arm)
    bench=VariantBench(log,variant,seed('eval',variant));model=None;session=None
    result={'variant':variant,'replicate':repetition,'arm':arm,'source':'mock','record':str(log.path.relative_to(ROOT)),
            'classification':classification['variants'][variant],'physical_measurements':0,'http_requests':0}
    old_handler=signal.getsignal(signal.SIGALRM)
    def timeout(*unused):raise TimeoutError('Registered 30-minute run timeout')
    signal.signal(signal.SIGALRM,timeout);signal.alarm(1800)
    try:
        if arm=='spark':
            session=B5Session(bench,log,lambda value,digest:frozen_receipt(log,value,digest))
            client=MeteredClient(ledger,f'variant-{variant}-{repetition}')
            model=MetaToolSession(prompt=PROMPT,tools=TOOLS,log=log,effort='max',env_path=ROOT/'.env',
                budget_path=ROOT/'.private/b5-variant-evaluation-bookkeeping.json',client=client,max_requests=8,
                max_output_tokens=8192,max_payload_bytes=128000)
            log.add('variant_transport_guard',{'isolated_budget':True,'hardware_disabled':True,'declared_client_override':True})
            state=drive_agent(session,model);result['http_requests']=model.requests
            gate_closed=session.initial is not None and session.initial['status']!='all_candidates_inadequate'
            verified=bool(session.report and session.report['verdict']=='verified')
            state={'outcome':'verified' if verified else 'gate_closed' if gate_closed else 'abstained',
                   'model':deepcopy(session.proposal['model']) if verified else None}
        else:state=scripted(arm,bench,log,design)
        result['outcome']=state['outcome']
        if state['outcome']=='verified':
            checks=equivalence(state['model'],variant,design);result['equivalence_checks']=checks
            result['outcome']='correct' if all(c['passed'] for c in checks) else 'wrong'
        events=decode_events(log.file.read_bytes(),require_terminal=False)
        result['unneeded_diode_proposals']=sum(any(x['kind']=='D' for x in e['payload']['elements']) for e in events
              if variant in ('L1','L2') and e['kind']=='b5_netlist_proposed')
        result['instrument']=bench.metadata();save(log.path/'result.json',result);log.add('run_completed',result)
    except Exception as exc:
        # Never replace a first attempt with a recovery success.
        result.update(outcome='abstained',error=type(exc).__name__+': '+str(exc),http_requests=model.requests if model else 0)
        events=decode_events(log.file.read_bytes(),require_terminal=False)
        result['unneeded_diode_proposals']=sum(any(x['kind']=='D' for x in e['payload']['elements']) for e in events if variant in ('L1','L2') and e['kind']=='b5_netlist_proposed')
        if session and session.report and session.report.get('verdict')=='verified':result['audit_status']='unresolved_after_verified_report'
        save(log.path/'result.json',result);log.add('run_failed',result)
    finally:
        signal.alarm(0);signal.signal(signal.SIGALRM,old_handler)
        if model:model.http.close()
    return result


def main(args):
    manifest=verify_manifest(ROOT)
    physical_sha=physical_gate(args.after_physical_b5)
    classification_path=Path(args.classification)
    expected=json.loads((ROOT/'examples/b5-variants/2026-11-02/selection-publication.json').read_text())
    if hashlib.sha256(classification_path.read_bytes()).hexdigest()!=expected['classification_sha256']:
        raise ValueError('Classification differs from the published selection')
    head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    remote=subprocess.check_output(['git','ls-remote','origin','refs/heads/main'],cwd=ROOT,text=True).split()[0]
    if head!=remote:raise ValueError('Evaluation requires committed, pushed current HEAD')
    for rel,digest in manifest['sha256'].items():
        blob=subprocess.check_output(['git','show',f'HEAD:{rel}'],cwd=ROOT)
        if hashlib.sha256(blob).hexdigest()!=digest:raise ValueError('Uncommitted evaluation dependency: '+rel)
    classification=json.loads(classification_path.read_text());design=json.loads((ROOT/'examples/b5-variants/2026-11-02/design.json').read_text())
    for rel,expected_blob in design['frozen_sources_at_cf33122']['git_blobs'].items():
        actual=subprocess.check_output(['git','hash-object',str(ROOT/rel)],text=True).strip()
        if actual!=expected_blob:raise ValueError('Spark-facing source changed: '+rel)
    if args.arm=='spark' and not args.execute:raise ValueError('Paid evaluation requires --execute')
    import serial
    serial.Serial=lambda *a,**k:(_ for _ in ()).throw(RuntimeError('Hardware disabled in synthetic evaluator'))
    providers.PROVIDERS['meta']={**providers.PROVIDERS['meta'],'cap_usd':184.}
    ledger=Ledger(ROOT/'.private/b5-variant-evaluation-cost.json',cap=30.,request_cap=184)
    out=ROOT/'runs/b5-variants/evaluation-v1';path=out/args.arm/'results.jsonl';path.parent.mkdir(parents=True,exist_ok=True)
    rows=[json.loads(x) for x in path.read_text().splitlines()] if path.exists() else []
    indexed={(ROOT/x['record']).resolve() for x in rows}
    if any(p.parent.resolve() not in indexed for p in path.parent.glob('*/*/events.jsonl')):
        raise RuntimeError('Interrupted unindexed record must be audited, not silently restarted')
    done={(x['variant'],x['replicate']) for x in rows}
    for variant in IDS:
        for repetition in range(1 if variant.startswith('G') or args.arm!='spark' else 2):
            if (variant,repetition) in done:continue
            row=execute_one(args.arm,variant,repetition,out,design,classification,ledger)
            row['physical_gate_sha256']=physical_sha
            with path.open('a') as f:f.write(json.dumps(row,allow_nan=False)+'\n')
            print(json.dumps({k:row.get(k) for k in ('variant','replicate','outcome','http_requests','error')}),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--arm',required=True,choices=['engine_only','oracle_library','spark'])
    p.add_argument('--after-physical-b5',required=True);p.add_argument('--classification',required=True);p.add_argument('--execute',action='store_true')
    main(p.parse_args())
