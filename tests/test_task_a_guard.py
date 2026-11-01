import importlib.util,json
from pathlib import Path
import httpx
from benchmate import providers
from benchmate.records import Recorder

ROOT=Path(__file__).resolve().parents[1]

def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path);out=importlib.util.module_from_spec(spec);spec.loader.exec_module(out);return out

def test_no_tool_http_is_metered_and_shared_ledger_untouched(tmp_path,monkeypatch):
    import serial
    wrapper=module('task_a_test',ROOT/'experiments/task_a.py')
    bench=module('task_a_benchmark_test',ROOT/'scripts/benchmark_linear.py')
    monkeypatch.setattr(wrapper,'ROOT',tmp_path);monkeypatch.setattr(bench,'ROOT',tmp_path)
    (tmp_path/'.env').write_text('MODEL_API_KEY=test-task-a-not-a-real-key\n')
    original_client=httpx.Client;requests=[]
    def handle(request):
        requests.append(request)
        return httpx.Response(200,json={'status':'completed','usage':{'input_tokens':100,'output_tokens':30},
          'output':[{'type':'message','content':[{'type':'output_text','text':'{"answer":"nominal","reason":"Test response"}'}]}]})
    monkeypatch.setattr(httpx,'Client',lambda **kwargs:original_client(transport=httpx.MockTransport(handle),**kwargs))
    # Register originals with monkeypatch so install's direct assignments are reverted.
    monkeypatch.setattr(providers,'reserve_budget',providers.reserve_budget)
    monkeypatch.setitem(providers.PROVIDERS,'meta',dict(providers.PROVIDERS['meta']))
    monkeypatch.setattr(serial,'Serial',serial.Serial)
    wrapper.install('no_tool')
    log=Recorder(tmp_path/'records',mode='test');attempts={'requests':0}
    answer,count=bench.ask_no_tool({'task':'A','r_ohm':10000,'c_f':1e-6},{'live':{'effort':'medium'}},log,attempts)
    assert answer=='nominal' and count==attempts['requests']==len(requests)==1
    ledger=json.loads((tmp_path/'.private/task-a-20261102-cost.json').read_text())
    assert len(ledger['requests'])==1 and ledger['requests'][0]['status']=='settled'
    assert ledger['requests'][0]['charged_or_reserved_usd']<.001
    assert not (tmp_path/'.private/api-budget.json').exists()
    assert 'test-task-a-not-a-real-key' not in log.file.read_text()
