import importlib.util
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from benchmate.instrument import InstrumentConfig

path=Path(__file__).resolve().parents[1]/'experiments/compare_adc_modes.py'
spec=importlib.util.spec_from_file_location('adc_comparison',path)
qa=importlib.util.module_from_spec(spec);spec.loader.exec_module(qa)


def packet(mode=1):
    return {'protocol':qa.PROTOCOL,'type':'pong','adc_qa_mode':mode,'adc_qa_failed':False,
            'adc_qa_single_channel':mode!=0,'adc_qa_discard_per_channel':int(mode==2)}


def test_validation_adapter_requires_new_identity_and_preserves_raw_packet():
    raw=packet();view=qa.validation_view(raw,1)
    assert raw['protocol']==qa.PROTOCOL
    assert view['protocol']=='benchmate-instrument-v2'
    with pytest.raises(ValueError):qa.validation_view({**raw,'protocol':'benchmate-instrument-v2'},1)
    with pytest.raises(ValueError):qa.validation_view(raw,2)
    with pytest.raises(ValueError):qa.validation_view({**raw,'adc_qa_failed':True},1)


@pytest.mark.parametrize('failed,continues', [
    ({'A4_block_mean_span'},True),({'stationary_path_mean_span'},True),
    ({'rails'},False),({'path_spread'},False),({'A4_block_mean_span','A4_envelope'},False)])
def test_only_declared_reference_failures_may_continue_QA(monkeypatch,failed,continues):
    def capture(self,*args):
        raise ValueError('Electrical/reference guard failed; no next stimulus')
    monkeypatch.setattr(qa.PhysicalBench,'_capture',capture)
    checks={k:k not in failed for k in ['A4_block_mean_span','stationary_path_mean_span','rails','path_spread','A4_envelope']}
    log=SimpleNamespace(last_guard={'label':'test','checks':checks},add=lambda *a:None)
    bench=qa.QABench({'configuration':{'vref_v':4.9,'ref_v':1.646}},log,None,initial_report={},previous_boot_id='1'*32)
    bench.last_raw={'rows':[[0,1376,5000,5000,5000,5000,10,20,30,40]]}
    if continues:
        assert bench.qa_capture(None,None,'test',{'kind':'hold'}).shape==(1,10)
    else:
        with pytest.raises(ValueError):bench.qa_capture(None,None,'test',{'kind':'hold'})


def test_DAC_code_check_uses_requested_amplitude_not_observed_last_code(monkeypatch):
    rows=np.array([[0,1375,5000,5000,5000,5000,10,20,30,40]]*16)
    rows[:,0]=np.arange(16)*500
    monkeypatch.setattr(qa.PhysicalBench,'_capture',lambda *a:rows)
    log=SimpleNamespace(add=lambda *a:None)
    bench=qa.QABench({'configuration':{'vref_v':4.9,'ref_v':1.646}},log,None,initial_report={},previous_boot_id='1'*32)
    with pytest.raises(ValueError,match='timing/code'):
        bench.qa_capture(None,SimpleNamespace(boot_id='1'*32),'bad_DAC',{'kind':'step','samples':16,'period_us':500,'amplitude_v':.5})
