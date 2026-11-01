"""Bounded Spark Open development gate, then registered Task A; no hardware."""
import argparse,hashlib,importlib.util,json,os,subprocess,sys,time
from pathlib import Path
import httpx
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'experiments'))
from night_budget import Ledger

class OpenCostClient:
    def __init__(self,ledger,job,log,sanitize,client=None):
        self.ledger,self.job,self.log,self.sanitize=ledger,job,log,sanitize
        self.inner=client or httpx.Client(timeout=120.,follow_redirects=False)
    def post(self,url,*,json,headers):
        import json as codec
        if (url!='https://inference.baseten.co/v1/chat/completions' or
            json.get('model')!='meta-models/muse-spark-open-1026' or json.get('max_tokens')!=4096 or
            len(codec.dumps(json).encode())>128000 or any(t.get('type')!='function' for t in json.get('tools',[]))):
            raise ValueError('Only registered Spark Open text/function requests allowed')
        request=self.ledger.reserve(self.job)
        response=self.inner.post(url,json=json,headers=headers)
        try:
            body=response.json();usage=body.get('usage',{})
            if isinstance(usage,dict):
                converted={'input_tokens':usage.get('prompt_tokens'),'output_tokens':usage.get('completion_tokens'),
                    'input_tokens_details':{'cached_tokens':usage.get('prompt_tokens_details',{}).get('cached_tokens',0)}}
                self.ledger.settle(request,converted,response.status_code)
            choices=[]
            for choice in body.get('choices',[]):
                message=choice.get('message',{})
                choices.append({'finish_reason':choice.get('finish_reason'),
                    'message':{k:message[k] for k in ('role','content','tool_calls') if k in message}})
            self.log.add('spark_open_visible_reply',self.sanitize({'http_status':response.status_code,
                'id':body.get('id'),'model':body.get('model'),'usage':usage,'choices':choices,
                'error':body.get('error'),'hidden_reasoning_recorded':False}))
        except (ValueError,TypeError,AttributeError):pass
        return response
    def close(self):self.inner.close()

def install(job):
    import serial
    from benchmate import providers,providers_baseten
    from benchmate.config import load_keys,redact
    serial.Serial=lambda *a,**k:(_ for _ in ()).throw(RuntimeError('Hardware disabled in Spark Open benchmark'))
    ledger=Ledger(ROOT/'.private/open-night-20261102-cost.json',cap=10.,request_cap=256)
    providers.PROVIDERS['baseten']={**providers.PROVIDERS['baseten'],'cap_usd':256.}
    base=providers_baseten.BasetenToolSession;keys=load_keys(ROOT/'.env')
    class GuardedSession(base):
        def __init__(self,**kwargs):
            if kwargs.get('client') is not None:raise ValueError('Nested client refused')
            self.cost_client=OpenCostClient(ledger,job,kwargs['log'],lambda x:redact(x,keys))
            kwargs.update(client=self.cost_client,budget_path=ROOT/'.private/open-night-20261102-bookkeeping.json')
            super().__init__(**kwargs)
            self.log.add('spark_open_transport_guard',{'hardware_disabled':True,'synthetic_only':True,
                'cost_cap_usd':10.,'request_cap':256,'runtime_client_override_declared':True,
                'rates_source':'https://www.baseten.co/pricing/','reasoning':'provider default, not matched to Meta medium',
                'original_provider_source_unchanged':True,'legacy_allowance_is_not_billing':True})
        def close(self):self.cost_client.close()
    providers_baseten.BasetenToolSession=GuardedSession

def load_benchmark():
    spec=importlib.util.spec_from_file_location('registered_open_benchmark',ROOT/'scripts/benchmark_linear.py')
    bench=importlib.util.module_from_spec(spec);spec.loader.exec_module(bench);return bench

def job(name):
    plan=json.loads((ROOT/'examples/overnight/2026-11-02/open-plan.json').read_text())
    for rel,digest in plan['wrapper_sha256'].items():
        if hashlib.sha256((ROOT/rel).read_bytes()).hexdigest()!=digest:raise ValueError('Spark Open wrapper changed')
    if name not in ('dev-a','dev-b','task-a'):raise ValueError('Unknown job')
    install(name);bench=load_benchmark();dev=name.startswith('dev')
    bench.cmd_run(argparse.Namespace(arm='spark_open',execute=True,max_requests=16 if dev else 240,
        allowance_cap=None,task='B' if name=='dev-b' else 'A',rerun_transport=False,dev=dev,limit=1 if dev else 0))

def batch():
    out=ROOT/'runs/overnight-open-20261102';out.mkdir(parents=True,exist_ok=False)
    for name in ('dev-a','dev-b','task-a'):
        started=time.time()
        if name=='task-a':
            b=load_benchmark();_,rows=b.finished('spark_open',b.RUNS/'dev')
            passed={r['task'] for r in b.first_attempts(rows).values() if r.get('report_accepted') and r.get('outcome') in ('correct','rejected') and not r.get('error') and r.get('provider',{}).get('provider')=='baseten'}
            if passed!={'A','B'}:
                with (out/'batch.jsonl').open('a') as f:f.write(json.dumps({'job':name,'skipped':'Development gate not passed; no model substitution or retry'})+'\n')
                print('Development gate not passed; evaluation not run',flush=True);return
        with (out/(name+'.console.txt')).open('w') as stream:
            try:
                run=subprocess.run([sys.executable,__file__,'job',name],cwd=ROOT,stdout=stream,stderr=subprocess.STDOUT,
                    env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'},timeout=1800 if name.startswith('dev') else 5400)
                status={'returncode':run.returncode}
            except subprocess.TimeoutExpired:status={'timeout':True}
        record={'job':name,'began':started,'elapsed_s':time.time()-started,**status}
        with (out/'batch.jsonl').open('a') as f:f.write(json.dumps(record)+'\n')
        print(json.dumps(record),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('mode',choices=['job','batch']);p.add_argument('name',nargs='?');a=p.parse_args()
    batch() if a.mode=='batch' else job(a.name)
