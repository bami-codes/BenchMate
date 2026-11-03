"""No serial/model: prove zero retry, fresh boot and ten-second ARM gate."""
from types import SimpleNamespace

import pytest

from benchmate.reading_recovery import check


class Bench:
    def __init__(self, boot='2'*32, fail_hold=None):
        self.boot = boot; self.fail_hold=fail_hold; self.calls=[]
        self.log=SimpleNamespace(add=lambda *a: None)
        self.config=SimpleNamespace(arm_command=lambda boot: b'ARM '+boot.encode())
        self.sleep=lambda seconds:self.calls.append(('sleep',seconds))

    def _ping(self, board, continuity, label, armed):
        continuity.boot_id=self.boot;self.calls.append(('ping',armed))

    def _request(self, *args):
        self.calls.append(('ARM',));return {'type':'armed'}

    def _hold(self, board, continuity, label):
        self.calls.append(('HOLD',))
        if self.fail_hold and sum(c[0]=='HOLD' for c in self.calls)==self.fail_hold:
            raise ValueError('firmware settling failed; test fixture')


def clock(elapsed=10.01):
    ticks=iter([100.,100.+elapsed]);return lambda:next(ticks)


def test_exact_three_holds_one_arm_after_ten_seconds():
    b=Bench();assert check(b,None,'1'*32,monotonic=clock())=='2'*32
    assert b.calls.count(('ARM',))==1 and b.calls.count(('HOLD',))==3
    assert b.calls.index(('sleep',10.)) < b.calls.index(('ARM',))
    assert b.calls[-1]==('ping',True)


def test_first_settling_error_has_no_second_capture_or_retry():
    b=Bench(fail_hold=1)
    with pytest.raises(ValueError,match='settling failed'):
        check(b,None,'1'*32,monotonic=clock())
    assert b.calls.count(('HOLD',))==1 and b.calls[-1]==('HOLD',)


def test_stale_boot_stops_before_wait_and_arm():
    b=Bench(boot='1'*32)
    with pytest.raises(ValueError,match='Fresh unarmed'):
        check(b,None,'1'*32,monotonic=clock())
    assert b.calls==[('ping',False)]


def test_short_wait_stops_before_arm():
    b=Bench()
    with pytest.raises(ValueError,match='Ten-second'):
        check(b,None,'1'*32,monotonic=clock(9.9))
    assert ('ARM',) not in b.calls and ('HOLD',) not in b.calls
