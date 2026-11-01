import json,sys
from pathlib import Path
import httpx
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'experiments'))
from open_serial_tools import SingleToolClient
from night_budget import Ledger

class Log:
    def add(self,*args):pass

def test_request_forces_one_tool_without_mutating_original(tmp_path):
    seen=[]
    def handler(r):
        seen.append(json.loads(r.content));return httpx.Response(200,json={'usage':{'prompt_tokens':100,'completion_tokens':20},'choices':[]})
    ledger=Ledger(tmp_path/'cost.json',cap=3.,request_cap=96)
    c=SingleToolClient(ledger,'probe',Log(),lambda x:x,client=httpx.Client(transport=httpx.MockTransport(handler)))
    original={'model':'meta-models/muse-spark-open-1026','max_tokens':4096,'tools':[]}
    c.post('https://inference.baseten.co/v1/chat/completions',json=original,headers={})
    assert 'parallel_tool_calls' not in original
    assert seen==[{**original,'parallel_tool_calls':False}]
    assert json.loads((tmp_path/'cost.json').read_text())['requests'][0]['status']=='settled'
