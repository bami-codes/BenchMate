"""Isolated mock-only HTTP cost guard; protected benchmate sources stay intact."""
import fcntl
import json
import math
import time
import uuid
from pathlib import Path
import httpx

RATES = {'input': 1.25e-6, 'cached': .15e-6, 'output': 4.25e-6}

class Ledger:
    def __init__(self, path, cap=30., request_cap=176):
        self.path=Path(path); self.cap=cap; self.request_cap=request_cap
    def update(self, change):
        self.path.parent.mkdir(parents=True,exist_ok=True)
        with self.path.open('a+') as f:
            fcntl.flock(f,fcntl.LOCK_EX); f.seek(0); raw=f.read()
            d=json.loads(raw) if raw else {'schema':'mock-night-budget-v1','cap_usd':self.cap,
                'request_cap':self.request_cap,'requests':[],'rates':RATES}
            if d['cap_usd']!=self.cap or d['request_cap']!=self.request_cap:
                raise ValueError('Ledger limits changed; explicit new plan required')
            result=change(d); f.seek(0);f.truncate();json.dump(d,f,indent=2);f.flush()
            return result
    def reserve(self, job):
        def change(d):
            # $1 covers the frozen 128 kB / 8192 token text-only envelope.
            # It stays reserved after errors, absent usage, or interrupted requests.
            if len(d['requests'])>=self.request_cap or sum(x['charged_or_reserved_usd'] for x in d['requests'])+1>self.cap+1e-10:
                raise RuntimeError('Overnight request/cost cap reached before transmission')
            item={'id':uuid.uuid4().hex,'job':job,'at_unix':time.time(),
                  'status':'reserved_unknown','charged_or_reserved_usd':1.}
            d['requests'].append(item); return item['id']
        return self.update(change)
    def settle(self, request_id, usage, status):
        if not isinstance(usage,dict):return
        values=[usage.get('input_tokens'),usage.get('output_tokens')]
        cached=usage.get('input_tokens_details',{}).get('cached_tokens',0)
        if any(type(x) is not int or x<0 for x in values+[cached]) or cached>values[0]:return
        cost=(values[0]-cached)*RATES['input']+cached*RATES['cached']+values[1]*RATES['output']
        if not math.isfinite(cost):return
        def change(d):
            row=next(x for x in d['requests'] if x['id']==request_id)
            row.update(status='settled',http_status=status,usage=usage,charged_or_reserved_usd=round(cost,9))
        self.update(change)

class MeteredClient:
    def __init__(self, ledger, job, client=None):
        self.ledger,self.job=ledger,job
        self.inner=client or httpx.Client(timeout=90.,follow_redirects=False)
    def post(self,url,*,json,headers):
        import json as codec
        if (url!='https://api.meta.ai/v1/responses' or json.get('model')!='muse-spark-1.3'
            or json.get('max_output_tokens') not in (4096,8192)
            or len(codec.dumps(json).encode())>128000
            or any(t.get('type')!='function' for t in json.get('tools',[]))):
            raise ValueError('Only frozen bounded Meta text-tool requests are permitted')
        token=self.ledger.reserve(self.job)
        response=self.inner.post(url,json=json,headers=headers)
        try:self.ledger.settle(token,response.json().get('usage'),response.status_code)
        except (ValueError,TypeError,AttributeError):pass
        return response
    def close(self):self.inner.close()

def install(root,job):
    """Declared transport substitution, never an unnoticed source-code change."""
    from benchmate import providers
    import serial
    def denied(*a,**k):raise RuntimeError('Serial hardware is disabled for this overnight process')
    serial.Serial=denied
    base=providers.MetaToolSession
    ledger=Ledger(root/'.private/overnight-20261102-cost.json')
    # The existing $1/request bookkeeping remains active, in a separate file.
    # Actual dollars are independently guarded before every HTTP request above.
    providers.PROVIDERS['meta']={**providers.PROVIDERS['meta'],'cap_usd':176.}
    class NightSession(base):
        def __init__(self,**kwargs):
            if kwargs.get('client') is not None:raise ValueError('Nested client override refused')
            self.night_client=MeteredClient(ledger,job)
            kwargs.update(client=self.night_client,budget_path=root/'.private/overnight-20261102-bookkeeping.json')
            super().__init__(**kwargs)
            self.log.add('overnight_transport_guard',{'hardware_disabled':True,'mock_only':True,
                'cost_cap_usd':30,'global_request_cap':176,'request_reserve_usd':1,
                'settlement':'official standard token rates; reasoning already included in output',
                'source_files_unchanged':True,'runtime_client_override_declared':True,
                'legacy_reservation_metadata_is_not_billing':True})
        def close(self):self.night_client.close()
    providers.MetaToolSession=NightSession
    return ledger
