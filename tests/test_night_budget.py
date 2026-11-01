import importlib.util
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('night_budget',ROOT/'experiments/night_budget.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

def test_failures_keep_reservation_and_cap_prevents_send(tmp_path):
    ledger=m.Ledger(tmp_path/'x.json',cap=2,request_cap=10)
    ledger.reserve('first');ledger.reserve('second')
    with pytest.raises(RuntimeError):ledger.reserve('third')

def test_settlement_releases_unused_reserve_and_counts_reasoning_once(tmp_path):
    ledger=m.Ledger(tmp_path/'x.json',cap=1.1,request_cap=2)
    token=ledger.reserve('one')
    ledger.settle(token,{'input_tokens':1000,'input_tokens_details':{'cached_tokens':500},
        'output_tokens':2000,'output_tokens_details':{'reasoning_tokens':1000}},200)
    data=ledger.update(lambda d:d)
    assert data['requests'][0]['charged_or_reserved_usd']==pytest.approx(.0092)
    ledger.reserve('two')
    with pytest.raises(RuntimeError):ledger.reserve('three')

def test_wrong_destination_rejected_before_network_or_reservation(tmp_path):
    class NoNetwork:
        def post(self,*a,**kw):raise AssertionError('No network permitted')
    ledger=m.Ledger(tmp_path/'x.json');client=m.MeteredClient(ledger,'test',NoNetwork())
    with pytest.raises(ValueError):client.post('https://other.invalid',json={},headers={})
    assert not ledger.path.exists()
