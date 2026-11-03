"""Verify the no-ARM bounded QA and its wait without operating any hardware."""
import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pytest


def module():
    spec = importlib.util.spec_from_file_location('A3_QA_test',
        Path(__file__).resolve().parents[1] / 'experiments/a3_reference_qa.py')
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    return m


def fake_bench(*, fail_at=None):
    calls = []; captures = [0]
    def ping(board, continuity, label, armed):
        calls.append(('PING', armed))
    def capture(board, continuity, label, settings):
        captures[0] += 1; calls.append(('CAPTURE', settings['kind']))
        if captures[0] == fail_at:
            raise ValueError('Injected A3 guard failure')
        ping(board, continuity, label + '_postcheck', True)
        return object()
    b = SimpleNamespace(_ping=ping, _capture=capture,
        _hold=lambda board, continuity, label: capture(board, continuity, label, {'kind': 'hold'}),
        _waveform_checks=lambda *a: None, log=SimpleNamespace(add=lambda *a: None))
    return b, calls


def test_ten_second_wait_and_exact_no_ARM_QA_sequence(monkeypatch):
    m = module(); b, calls = fake_bench(); now = [0.]
    b.sleep = lambda seconds: now.__setitem__(0, now[0] + seconds)
    monkeypatch.setattr(m.time, 'monotonic', lambda: now[0])
    assert m.check(b, None, '1' * 32) == '1' * 32
    assert now[0] == 10
    assert len(calls) == 37
    assert sum(c[0] == 'CAPTURE' for c in calls) == 17
    assert sum(c == ('CAPTURE', 'hold') for c in calls) == 10
    assert sum(c[0] == 'PING' for c in calls) == 20


def test_QA_failure_prevents_next_stimulus(monkeypatch):
    m = module(); b, calls = fake_bench(fail_at=4); now = [0.]
    b.sleep = lambda seconds: now.__setitem__(0, now[0] + seconds)
    monkeypatch.setattr(m.time, 'monotonic', lambda: now[0])
    with pytest.raises(ValueError, match='A3 guard failure'):
        m.check(b, None, '1' * 32)
    assert sum(c[0] == 'CAPTURE' for c in calls) == 4
    assert calls[-1][0] == 'CAPTURE'
