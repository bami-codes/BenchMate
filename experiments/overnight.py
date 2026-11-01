"""One authorized mock-only job, or the fixed preregistered overnight sequence."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import runpy
import subprocess
import sys
import time
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'experiments'))
from night_budget import install

def freeze_check():
    p=json.loads((ROOT/'examples/overnight/2026-11-02/plan.json').read_text())
    for rel,digest in p['protected_sources'].items():
        if hashlib.sha256((ROOT/rel).read_bytes()).hexdigest()!=digest:
            raise RuntimeError('Protected source changed: '+rel)
    if not p['hardware_disabled']:raise RuntimeError('Mock-only plan required')
    return p

def job(name):
    freeze_check();install(ROOT,name)
    out=ROOT/'runs/overnight-20261102'/name
    if name=='d01':
        args=['scripts/physical_d01_repair.py','run','--bench','mock','--provider','meta','--execute','--output',str(out)]
    elif name.startswith('b5-') and name[3:] in ('1','2','3','4','5'):
        args=['scripts/b5_unloaded.py','--bench','mock','--provider','meta','--output',str(out)]
    elif name=='task-b':
        args=['scripts/benchmark_linear.py','run','--arm','spark_hidden','--task','B','--execute','--max-requests','128']
    else:raise ValueError('Unregistered job')
    if name!='task-b' and out.exists() and any(out.iterdir()):
        raise RuntimeError('Existing first attempt is preserved; no automatic restart')
    sys.argv=[str(ROOT/args[0]),*args[1:]]
    runpy.run_path(sys.argv[0],run_name='__main__')

def batch():
    freeze_check()
    directory=ROOT/'runs/overnight-20261102';directory.mkdir(parents=True,exist_ok=True)
    journal=directory/'batch.jsonl'
    if journal.exists():raise RuntimeError('Batch already started; audit before any resume')
    for name in ['d01',*[f'b5-{n}' for n in range(1,6)],'task-b']:
        began=time.time()
        with (directory/(name+'.console.txt')).open('w') as output:
            try:
                done=subprocess.run([sys.executable,__file__,'job',name],cwd=ROOT,stdout=output,stderr=subprocess.STDOUT,
                    env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'},timeout=10800 if name=='task-b' else 1800)
                status={'returncode':done.returncode}
            except subprocess.TimeoutExpired:status={'timed_out':True}
        with journal.open('a') as f:f.write(json.dumps({'job':name,'began':began,'elapsed_s':time.time()-began,**status})+'\n')
        print(json.dumps({'job_finished':name,**status}),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('mode',choices=['job','batch']);p.add_argument('name',nargs='?');a=p.parse_args()
    batch() if a.mode=='batch' else job(a.name)
