"""Post-evaluation development probe of one-tool transport, isolated from scoring."""
import argparse,hashlib,json,os,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'experiments'))
from night_budget import Ledger
from open_benchmark import OpenCostClient,load_benchmark

class SingleToolClient(OpenCostClient):
    def post(self,url,*,json,headers):
        if 'parallel_tool_calls' in json:raise ValueError('Unexpected existing parallel setting')
        return super().post(url,json={**json,'parallel_tool_calls':False},headers=headers)

def install(condition,case):
    import serial
    from benchmate import providers,providers_baseten
    from benchmate.config import load_keys,redact
    serial.Serial=lambda *a,**k:(_ for _ in ()).throw(RuntimeError('Hardware disabled in development transport probe'))
    keys=load_keys(ROOT/'.env');ledger=Ledger(ROOT/'.private/open-single-tool-probe-cost.json',cap=3.,request_cap=96)
    providers.PROVIDERS['baseten']={**providers.PROVIDERS['baseten'],'cap_usd':96.}
    original=providers_baseten.BasetenToolSession
    class ProbeSession(original):
        def __init__(self,**kwargs):
            if kwargs.get('client') is not None:raise ValueError('Nested transport refused')
            cls=SingleToolClient if condition=='single' else OpenCostClient
            self.probe_client=cls(ledger,f'{condition}-{case}',kwargs['log'],lambda x:redact(x,keys))
            kwargs.update(client=self.probe_client,budget_path=ROOT/'.private/open-single-tool-probe-bookkeeping.json')
            super().__init__(**kwargs)
            self.log.add('development_transport_probe',{'post_evaluation':True,'not_a_replacement_for_first_evaluation':True,
                'hardware_disabled':True,'condition':condition,'parallel_tool_calls':False if condition=='single' else 'omitted (provider default)',
                'case':case,'development_specimens_only':True,'cap_usd':3.,'request_cap':96,
                'prompt_tools_engine_provider_source_unchanged':True})
        def close(self):self.probe_client.close()
    providers_baseten.BasetenToolSession=ProbeSession

def verify():
    plan=json.loads((ROOT/'examples/overnight/2026-11-02/open-single-tool-plan.json').read_text())
    for name,digest in plan['source_sha256'].items():
        if hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=digest:raise ValueError('Registered probe changed')

def job(condition,index):
    verify();bench=load_benchmark();protocol=bench.load_protocol();bench.validate_freeze(protocol,publication=False)
    specs=[s for s in bench.load_specimens(protocol,True) if s['task']=='A'][:6];case=specs[index]
    if condition not in ('default','single'):raise ValueError('Unknown condition')
    dest=ROOT/'runs/open-single-tool-probe'/condition
    if (dest/'spark_open'/case['id']).exists():raise ValueError('First attempt already exists; no retry')
    install(condition,case['id']);row=bench.run_one(case,'spark_open',0,protocol,bench.sha256(bench.PROTOCOL),dest)
    row.update(study='post_evaluation_development_transport_probe',condition=condition,not_confirmatory=True)
    with (dest/'results.jsonl').open('a') as f:f.write(json.dumps(row,allow_nan=False)+'\n')
    print(json.dumps({k:row.get(k) for k in ('specimen','condition','outcome','error','provider_requests')}),flush=True)

def batch():
    verify();out=ROOT/'runs/open-single-tool-probe';out.mkdir(exist_ok=False)
    for i in range(6):
        for condition in (('default','single') if i%2==0 else ('single','default')):
            start=time.time()
            with (out/f'{i+1}-{condition}.console.txt').open('w') as f:
                try:
                    p=subprocess.run([sys.executable,__file__,'job',condition,str(i)],cwd=ROOT,stdout=f,stderr=subprocess.STDOUT,
                        env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'},timeout=300)
                    result={'returncode':p.returncode}
                except subprocess.TimeoutExpired:result={'timeout':True}
            row={'case_index':i,'condition':condition,'elapsed_s':time.time()-start,**result}
            with (out/'batch.jsonl').open('a') as f:f.write(json.dumps(row)+'\n')
            print(json.dumps(row),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('mode',choices=['job','batch']);p.add_argument('condition',nargs='?');p.add_argument('index',nargs='?',type=int);a=p.parse_args()
    batch() if a.mode=='batch' else job(a.condition,a.index)
