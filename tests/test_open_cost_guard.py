from pathlib import Path
import importlib.util,json,sys
import httpx,pytest

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'experiments'))
from open_benchmark import OpenCostClient
from night_budget import Ledger

class Log:
    def __init__(self):self.rows=[]
    def add(self,*args):self.rows.append(args)

def test_chat_usage_settlement_and_no_hidden_reasoning(tmp_path):
    log=Log();ledger=Ledger(tmp_path/'budget.json',cap=10.,request_cap=256)
    def handler(request):return httpx.Response(200,json={'usage':{'prompt_tokens':1000,'completion_tokens':200,'prompt_tokens_details':{'cached_tokens':400}},
       'choices':[{'finish_reason':'tool_calls','message':{'role':'assistant','content':None,'reasoning_content':'must-not-be-recorded','tool_calls':[]}}]})
    client=OpenCostClient(ledger,'test',log,lambda x:x,client=httpx.Client(transport=httpx.MockTransport(handler)))
    payload={'model':'meta-models/muse-spark-open-1026','max_tokens':4096,'tools':[]}
    client.post('https://inference.baseten.co/v1/chat/completions',json=payload,headers={})
    d=json.loads((tmp_path/'budget.json').read_text());assert d['requests'][0]['status']=='settled'
    assert d['requests'][0]['charged_or_reserved_usd']==pytest.approx(.00166)
    assert 'must-not-be-recorded' not in json.dumps(log.rows)
    with pytest.raises(ValueError):client.post('https://example.com',json=payload,headers={})
    assert len(json.loads((tmp_path/'budget.json').read_text())['requests'])==1

def test_missing_usage_keeps_reservation(tmp_path):
    ledger=Ledger(tmp_path/'budget.json',cap=10.,request_cap=256)
    client=OpenCostClient(ledger,'test',Log(),lambda x:x,client=httpx.Client(transport=httpx.MockTransport(lambda r:httpx.Response(503,json={'error':'unavailable'}))))
    client.post('https://inference.baseten.co/v1/chat/completions',json={'model':'meta-models/muse-spark-open-1026','max_tokens':4096,'tools':[]},headers={})
    d=json.loads((tmp_path/'budget.json').read_text());assert d['requests'][0]['charged_or_reserved_usd']==1.
