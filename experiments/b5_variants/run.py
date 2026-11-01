"""Offline validation and preregistered selection; never invokes a model/board."""
import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys
import time
import numpy as np
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'experiments'))
from b5_variants.bench import IDS,truth_elements,captures,seed
from b5_variants.fitting import fit_linear_start,fit_proposal_start
from benchmate.b5_models import fit_linear,predict,score

def save(path,data):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix(path.suffix+'.tmp');tmp.write_text(json.dumps(data,indent=2,allow_nan=False)+'\n');tmp.replace(path)

def checked_fit(fit,training,reserved):
    fit={k:v for k,v in fit.items() if k!='initial_generated_predictions'}
    if not fit['optimizer_converged']:return {'status':'fit_failed','reason':'optimizer_not_converged','fit':fit}
    try:
        checks=[score(c,predict(fit['model'],c['input_template'])) for c in reserved]
    except (ValueError,RuntimeError) as exc:
        return {'status':'prediction_failed','reason':str(exc),'fit':fit}
    return {'status':'finished','fit':fit,'training_passed':fit['training_passed'],
            'reserved_checks':checks,'all_passed':fit['training_passed'] and all(c['passed'] for c in checks)}

def select_best(attempts,training,reserved):
    complete=[a for a in attempts if a.get('optimizer_converged')]
    if not complete:return {'status':'fit_failed','attempts':attempts}
    # Select only by training cost. Reserved outcomes do not choose a start.
    best=min(complete,key=lambda a:a['training_cost'])
    return {**checked_fit(best,training,reserved),'attempts':attempts}

def generic_elements(variant,index):
    values=(1.,.3,3.)
    result=truth_elements(variant)
    for e in result:
        if e['kind']=='R':e['value']=10000*values[index]
        if e['kind']=='C':e['value']=1e-6*values[index]
    return result

def classify(reps):
    if len(reps)!=3 or any(r.get('incomplete') for r in reps):return {'class':'selection_incomplete','primary':False}
    first_names=[x for x in reps[0]['alternatives'] if x.startswith('linear:')]
    adequate=[name for name in first_names if all(r['alternatives'][name].get('all_passed') for r in reps)]
    if adequate:return {'class':'linear_adequate','primary':False,'adequate_families':adequate}
    failed_fits=sorted({name for r in reps for name,a in r['alternatives'].items() if a['status']!='finished'})
    actual_gate=all(r['session_gate']['status']=='all_candidates_inadequate' and
                    all(c['optimizer_converged'] for c in r['session_gate']['candidates']) for r in reps)
    multi_gate=all(not r['alternatives'][name].get('training_passed') and r['alternatives'][name]['status']=='finished'
                   for r in reps for name in first_names)
    if not actual_gate or not multi_gate:return {'class':'borderline','primary':False,'fit_failures':failed_fits}
    variant=reps[0]['variant'];own='netlist:'+variant
    recoverable=all(r['alternatives'].get(own,{}).get('all_passed') for r in reps)
    if not recoverable:return {'class':'engine_unsolvable','primary':False,'fit_failures':failed_fits}
    confusable=sorted({name for r in reps for name,a in r['alternatives'].items() if name!=own and a.get('all_passed')})
    if failed_fits:return {'class':'distinguishability_unresolved','primary':False,'fit_failures':failed_fits,'confusable_with':confusable}
    return {'class':'confusable' if confusable else 'distinguishable','primary':not confusable,'confusable_with':confusable}

def replicate(variant,k,out,deadline):
    train,res=captures(variant,seed('select',variant,k))
    path=out/f'{variant}-{k}.json'
    result={'variant':variant,'replicate':k,'source':'mock','phase':'selection',
            'seed':seed('select',variant,k),'training':train,'reserved':res,'alternatives':{},'incomplete':True}
    result['session_gate']=fit_linear(train);save(path,result)
    linear={}
    for fraction in (.5,.25,.75):
        if time.monotonic()>deadline:save(path,result);return result
        for fit in fit_linear_start(train,fraction)['candidates']:
            linear.setdefault(fit['model']['family'],[]).append(fit)
    for name,attempts in linear.items():result['alternatives']['linear:'+name]=select_best(attempts,train,res)
    save(path,result)
    for name in IDS[:10]:
        attempts=[]
        for i,diode in enumerate(({'is_a':1e-9,'n':1.8},{'is_a':1e-10,'n':1.3},{'is_a':1e-8,'n':2.2})):
            if time.monotonic()>deadline:save(path,result);return result
            try:
                fit=fit_proposal_start(generic_elements(name,i),train,diode)
                fit.pop('initial_generated_predictions',None);attempts.append(fit)
            except (ValueError,RuntimeError) as exc:attempts.append({'optimizer_converged':False,'error':str(exc)})
        result['alternatives']['netlist:'+name]=select_best(attempts,train,res)
        save(path,result)
        print(json.dumps({'variant':variant,'replicate':k,'alternative':name,
            'status':result['alternatives']['netlist:'+name]['status']}),flush=True)
    result['incomplete']=False;save(path,result);return result

def verify_manifest(root):
    manifest=json.loads((root/'examples/b5-variants/2026-11-02/implementation.json').read_text())
    for name,digest in manifest['sha256'].items():
        if hashlib.sha256((root/name).read_bytes()).hexdigest()!=digest:raise ValueError('Frozen source changed: '+name)
    return manifest

def selection(out):
    verify_manifest(ROOT);out=Path(out)
    if out.exists() and any(out.iterdir()):raise RuntimeError('Existing selection preserved; no silent rerun')
    out.mkdir(parents=True,exist_ok=True);start=time.monotonic();deadline=start+10800
    summary={'source':'mock','phase':'selection','variants':{},'primary':[],'physical_measurements':0,'model_calls':0}
    for variant in IDS:
        reps=[]
        for k in (1,2,3):
            if time.monotonic()>=deadline:break
            reps.append(replicate(variant,k,out,deadline))
        summary['variants'][variant]=classify(reps)
        if summary['variants'][variant]['primary']:summary['primary'].append(variant)
        summary['elapsed_s']=time.monotonic()-start;save(out/'classification.json',summary)
        print(json.dumps({'variant_completed':variant,**summary['variants'][variant]}),flush=True)
    summary['complete']=all(x['class']!='selection_incomplete' for x in summary['variants'].values())
    summary['accuracy_claim']=None;save(out/'classification.json',summary)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('mode',choices=['select']);p.add_argument('--output',required=True);args=p.parse_args()
    selection(args.output)
