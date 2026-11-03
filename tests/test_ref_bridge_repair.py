import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pytest

path=Path(__file__).resolve().parents[1]/'experiments/check_ref_bridge_repair.py'
spec=importlib.util.spec_from_file_location('bridge_qa',path)
qa=importlib.util.module_from_spec(spec);spec.loader.exec_module(qa)
OLD='1'*32
NEW='2'*32


class Bench:
    def __init__(self,fail=None,boot=NEW):
        self.calls=[];self.fail=fail;self.boot=boot
        self.config=SimpleNamespace(arm_command=lambda boot:b'ARM '+boot.encode()+b'\n')
    def _ping(self,board,continuity,label,armed):
        continuity.boot_id=self.boot;self.calls.append(('ping',armed))
    def _request(self,*a):self.calls.append(('ARM',));return {'type':'armed'}
    def _hold(self,board,continuity,label):self.calls.append(('hold',))
    def _capture(self,board,continuity,label,settings):
        self.calls.append(('step',settings['amplitude_v']))
        if self.fail==settings['amplitude_v']:raise ValueError('guard failed')
        return []
    def _waveform_checks(self,*a):self.calls.append(('waveform_check',))


def test_first_guard_failure_prevents_large_step_and_no_retry():
    b=Bench(fail=.2)
    with pytest.raises(ValueError,match='guard'):qa.check(b,None,OLD)
    assert [c for c in b.calls if c[0]=='step']==[('step',.2)]
    assert b.calls.count(('ARM',))==1


def test_same_boot_cannot_rearm():
    b=Bench(boot=OLD)
    with pytest.raises(ValueError,match='New boot'):qa.check(b,None,OLD)
    assert b.calls==[('ping',False)]


def test_fixed_instrument_sequence_has_three_initial_holds_and_returns():
    b=Bench();assert qa.check(b,None,OLD)==NEW
    assert b.calls.count(('hold',))==5
    assert [c for c in b.calls if c[0]=='step']==[('step',.2),('step',.5)]
    assert b.calls[-1]==('ping',True)
