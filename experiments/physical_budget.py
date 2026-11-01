"""Optional, declared cost guard around unchanged physical runners.

--check only reads local preparation. It never opens a board or calls a model.
The run form must be invoked later, with genuine operator reports and --execute.
"""
import argparse,hashlib,json,runpy,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'experiments'));sys.path.insert(0,str(ROOT/'src'))
from night_budget import Ledger,MeteredClient
PLAN=ROOT/'examples/physical-budget/2026-11-02/plan.json'
RUNNERS={'d01':'scripts/physical_d01_repair.py','b5':'scripts/b5_unloaded.py'}

def verify():
    plan=json.loads(PLAN.read_text())
    for name,digest in plan['source_sha256'].items():
        if hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=digest:raise ValueError('Budget wrapper plan changed: '+name)
    return plan

def install(which):
    from benchmate import providers
    plan=verify();base=providers.MetaToolSession
    ledger=Ledger(ROOT/'.private/physical-20261102-cost.json',cap=10.,request_cap=32)
    providers.PROVIDERS['meta']={**providers.PROVIDERS['meta'],'cap_usd':32.}
    class BoundedPhysicalSession(base):
        def __init__(self,**kwargs):
            if kwargs.get('client') is not None:raise ValueError('Nested transport refused')
            if kwargs.get('max_requests')!=8:raise ValueError('Expected original eight-call physical limit')
            self.cost_client=MeteredClient(ledger,'physical-'+which)
            kwargs.update(client=self.cost_client,budget_path=ROOT/'.private/physical-20261102-bookkeeping.json')
            super().__init__(**kwargs)
            self.log.add('physical_cost_guard',{'plan_sha256':hashlib.sha256(PLAN.read_bytes()).hexdigest(),
                'source_sha256':plan['source_sha256'],'total_new_requests_max':32,'total_new_cost_max_usd':10,
                'per_run_max_requests':8,'reserve_before_request_usd':1,'unknown_usage_keeps_reservation':True,
                'legacy_allowance_is_not_billing':True,'original_shared_allowance_unchanged':True,
                'operator_boot_wiring_prediction_guards_unchanged':True,'runtime_transport_override_declared':True})
        def close(self):self.cost_client.close()
    providers.MetaToolSession=BoundedPhysicalSession

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('mode',choices=['check','d01','b5']);p.add_argument('runner_args',nargs=argparse.REMAINDER);a=p.parse_args();verify()
    if a.mode=='check':
        if a.runner_args:raise ValueError('Check does not accept run arguments')
        cost=ROOT/'.private/physical-20261102-cost.json'
        rows=json.loads(cost.read_text())['requests'] if cost.exists() else []
        print(json.dumps({'prepared_only':True,'hardware_commands':0,'api_calls':0,'requests_used':len(rows),
            'charged_or_reserved_usd':sum(x['charged_or_reserved_usd'] for x in rows),'request_cap':32,'cost_cap_usd':10,
            'needs_fresh_real_operator_reports':True}));return
    args=a.runner_args[1:] if a.runner_args[:1]==['--'] else a.runner_args
    for name,value in (('--bench','physical'),('--provider','meta')):
        if args.count(name)!=1 or args.index(name)+1>=len(args) or args[args.index(name)+1]!=value:
            raise ValueError('Explicit '+name+' '+value+' required')
    if args[:1]!=['run'] or args.count('--execute')!=1:raise ValueError('Explicit later physical run --execute required')
    # B5's original parser has neither subcommands nor an execute flag. The
    # wrapper requires those explicitly, then strips only its own two markers.
    forwarded=args if a.mode=='d01' else [x for x in args[1:] if x!='--execute']
    install(a.mode);sys.argv=[str(ROOT/RUNNERS[a.mode]),*forwarded]
    runpy.run_path(str(ROOT/RUNNERS[a.mode]),run_name='__main__')

if __name__=='__main__':main()
