"""Supplemental Task A execution; frozen benchmark and physical sources unchanged."""
from pathlib import Path
import argparse,importlib.util,json,sys,time,subprocess,os,hashlib
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'experiments'))
from night_budget import Ledger,MeteredClient


def install(job):
    import httpx,serial
    from benchmate import providers
    serial.Serial=lambda *a,**k:(_ for _ in ()).throw(RuntimeError('Hardware disabled in Task A batch'))
    ledger=Ledger(ROOT/'.private/task-a-20261102-cost.json',cap=10.,request_cap=270)
    providers.PROVIDERS['meta']={**providers.PROVIDERS['meta'],'cap_usd':270.}
    original_reserve=providers.reserve_budget
    def reserve(path,provider,amount):
        if provider!='meta':raise ValueError('Only Meta permitted')
        return original_reserve(ROOT/'.private/task-a-20261102-bookkeeping.json',provider,amount)
    providers.reserve_budget=reserve
    marker={'hardware_disabled':True,'mock_only':True,'supplemental_task':'A',
       'cap_usd':10.,'request_cap':270,'request_reserve_usd':1.,'runtime_client_override_declared':True,
       'prompts_tools_scoring_source_unchanged':True,'legacy_allowance_is_not_billing':True}
    if job=='spark':
        base=providers.MetaToolSession
        class CostGuardSession(base):
            def __init__(self,**kwargs):
                if kwargs.get('client') is not None:raise ValueError('Nested client override refused')
                kwargs.update(client=MeteredClient(ledger,'task-a-spark'),budget_path=ROOT/'.private/task-a-20261102-bookkeeping.json')
                super().__init__(**kwargs);self.log.add('task_a_transport_guard',marker)
        providers.MetaToolSession=CostGuardSession
    else:
        original_client=httpx.Client
        class NoToolClient(MeteredClient):
            def __init__(self,**kwargs):super().__init__(ledger,'task-a-no-tool',client=original_client(**kwargs))
            def __enter__(self):return self
            def __exit__(self,*unused):self.close()
        httpx.Client=NoToolClient
    return marker


def job(name):
    if name not in ('no_tool','spark'):raise ValueError('Unknown job')
    plan=json.loads((ROOT/'examples/overnight/2026-11-02/task-a-plan.json').read_text())
    for rel,digest in plan['wrapper_sha256'].items():
        if hashlib.sha256((ROOT/rel).read_bytes()).hexdigest()!=digest:raise RuntimeError('Supplemental wrapper changed')
    marker=install(name)
    spec=importlib.util.spec_from_file_location('registered_linear_benchmark',ROOT/'scripts/benchmark_linear.py')
    benchmark=importlib.util.module_from_spec(spec);spec.loader.exec_module(benchmark)
    original=benchmark.ask_no_tool
    def guarded(*args):
        args[2].add('task_a_transport_guard',marker);return original(*args)
    benchmark.ask_no_tool=guarded
    benchmark.cmd_run(argparse.Namespace(arm=name,execute=True,max_requests=30 if name=='no_tool' else 240,
        allowance_cap=None,task='A',rerun_transport=False,dev=False,limit=0))


def batch():
    out=ROOT/'runs/overnight-task-a-20261102';out.mkdir(parents=True,exist_ok=False)
    for name in ('no_tool','spark'):
        started=time.time()
        with (out/(name+'.console.txt')).open('w') as stream:
            try:
                done=subprocess.run([sys.executable,__file__,'job',name],cwd=ROOT,stdout=stream,stderr=subprocess.STDOUT,
                    env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'},timeout=5400)
                result={'returncode':done.returncode}
            except subprocess.TimeoutExpired:result={'timeout':True}
        record={'job':name,'began':started,'elapsed_s':time.time()-started,**result}
        with (out/'batch.jsonl').open('a') as stream:stream.write(json.dumps(record)+'\n')
        print(json.dumps(record),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('mode',choices=['job','batch']);p.add_argument('name',nargs='?');a=p.parse_args()
    batch() if a.mode=='batch' else job(a.name)
