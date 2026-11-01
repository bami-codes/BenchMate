from pathlib import Path
import json,sys
import httpx
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'experiments'))
import physical_budget as guard
from night_budget import Ledger,MeteredClient

class Log:
    def __init__(self):self.rows=[]
    def add(self,*args):self.rows.append(args)

def test_prepared_plan_and_read_only_check(capsys,monkeypatch):
    import serial
    monkeypatch.setattr(serial,'Serial',lambda *a,**k:(_ for _ in ()).throw(AssertionError('Hardware touched')))
    monkeypatch.setattr(sys,'argv',['physical_budget.py','check'])
    guard.main();d=json.loads(capsys.readouterr().out);assert d['hardware_commands']==d['api_calls']==0
    assert d['needs_fresh_real_operator_reports'] and d['request_cap']==32

def test_usage_guard_keeps_payload_and_separate_ledger(tmp_path):
    received=[]
    def handler(req):
        received.append(json.loads(req.content));return httpx.Response(200,json={'usage':{'input_tokens':200,'output_tokens':40}})
    ledger=Ledger(tmp_path/'new.json',cap=10.,request_cap=32)
    client=MeteredClient(ledger,'physical-test',client=httpx.Client(transport=httpx.MockTransport(handler)))
    payload={'model':'muse-spark-1.3','max_output_tokens':4096,'tools':[],'input':[{'role':'user','content':'synthetic test'}]}
    client.post('https://api.meta.ai/v1/responses',json=payload,headers={})
    assert received==[payload]
    assert json.loads((tmp_path/'new.json').read_text())['requests'][0]['status']=='settled'


def test_dispatch_preserves_original_parser_shapes(monkeypatch):
    captured=[]
    monkeypatch.setattr(guard,'install',lambda name:None)
    monkeypatch.setattr(guard.runpy,'run_path',lambda *a,**k:captured.append(list(sys.argv)))
    common=['run','--execute','--bench','physical','--provider','meta','--protocol','actual.json','--initial-report','actual-report.json','--publish-freeze']
    for mode in ('d01','b5'):
        monkeypatch.setattr(sys,'argv',['physical_budget.py',mode,'--',*common]);guard.main()
    assert captured[0][1:]==common
    assert captured[1][1:]==[a for a in common[1:] if a!='--execute']
    assert captured[0][0].endswith('physical_d01_repair.py')
    assert captured[1][0].endswith('b5_unloaded.py')
