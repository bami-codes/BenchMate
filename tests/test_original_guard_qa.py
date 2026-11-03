import importlib.util
from pathlib import Path

import pytest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('original_qa',ROOT/'experiments/original_guard_qa.py')
qa=importlib.util.module_from_spec(spec);spec.loader.exec_module(qa)


class Bench:
    def __init__(self,fail=None):self.calls=[];self.fail=fail
    def _ping(self,board,c,label,armed):
        assert armed is True;self.calls.append('PING')
        if self.fail=='initial':raise ValueError('unexpected boot')
    def _hold(self,board,c,label):self.calls.append('HOLD')
    def _capture(self,board,c,label,settings):
        self.calls.append(label)
        if self.fail=='first_wave':raise ValueError('original guard failed')
        return []
    def _waveform_checks(self,*a):self.calls.append('waveform_check')


def test_full_sequence_uses_original_guard_and_has_no_ARM():
    b=Bench();qa.check(b,None,'b'*32)
    assert b.calls.count('HOLD')==10
    assert b.calls.count('waveform_check')==7
    assert b.calls.count('PING')==2


@pytest.mark.parametrize('fault,count',[('initial',1),('first_wave',5)])
def test_first_failure_stops_without_next_wave_or_rearm(fault,count):
    b=Bench(fault)
    with pytest.raises(ValueError):qa.check(b,None,'b'*32)
    assert len(b.calls)==count
