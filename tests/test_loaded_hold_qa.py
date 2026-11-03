"""Check the bounded maintenance sequence without serial access or APIs."""
import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pytest


def module():
    spec = importlib.util.spec_from_file_location('loaded_hold_test',
        Path(__file__).resolve().parents[1] / 'experiments/loaded_hold_qa.py')
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def bench(*, boot='2' * 32, fail_at=None, arm_type='armed'):
    calls = []
    def ping(board, continuity, label, armed):
        continuity.boot_id = boot
        calls.append(('PING', label, armed))
    def request(board, continuity, command, label, timeout):
        calls.append(('ARM', label))
        return {'type': arm_type}
    def hold(board, continuity, label):
        calls.append(('HOLD', label))
        if fail_at == sum(x[0] == 'HOLD' for x in calls):
            raise ValueError('Injected original guard failure')
    b = SimpleNamespace(_ping=ping, _request=request, _hold=hold,
                        config=SimpleNamespace(arm_command=lambda boot: b'ARM\n'))
    return b, calls


def test_only_twelve_HOLDs_and_one_ARM():
    m = module(); b, calls = bench()
    assert m.check(b, None, '1' * 32) == '2' * 32
    assert sum(x[0] == 'ARM' for x in calls) == 1
    assert sum(x[0] == 'HOLD' for x in calls) == 12
    assert calls[-1] == ('PING', 'loaded_QA_final_PING', True)


def test_first_failure_prevents_next_HOLD_and_final_ping():
    m = module(); b, calls = bench(fail_at=3)
    with pytest.raises(ValueError, match='guard failure'):
        m.check(b, None, '1' * 32)
    assert sum(x[0] == 'HOLD' for x in calls) == 3
    assert calls[-1] == ('HOLD', 'loaded_QA_HOLD_3')


def test_old_boot_stops_before_ARM():
    m = module(); b, calls = bench(boot='1' * 32)
    with pytest.raises(ValueError, match='New USB-off boot'):
        m.check(b, None, '1' * 32)
    assert len(calls) == 1 and calls[0][0] == 'PING'


def test_bad_ARM_stops_before_any_HOLD():
    m = module(); b, calls = bench(arm_type='error')
    with pytest.raises(ValueError, match='ARM not acknowledged'):
        m.check(b, None, '1' * 32)
    assert all(x[0] != 'HOLD' for x in calls)
