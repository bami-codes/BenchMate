"""QA orchestration cannot retry a failed guard or substitute a waveform."""
import importlib.util
from pathlib import Path

import pytest

path = Path(__file__).resolve().parents[1]/'experiments/check_passive_reference.py'
spec = importlib.util.spec_from_file_location('reference_qa_under_test', path)
qa = importlib.util.module_from_spec(spec); spec.loader.exec_module(qa)


class Bench:
    def __init__(self, *, boot='2'*32, fail=None):
        self.boot, self.fail, self.actions = boot, fail, []
        self.config = self
    def arm_command(self, boot): return b'ARM fixed-test-envelope\n'
    def _ping(self, board, continuity, label, armed):
        self.actions.append(('PING', armed)); continuity.boot_id = self.boot
    def _request(self, board, continuity, command, label, timeout):
        self.actions.append(('ARM',)); return {'type': 'armed'}
    def _hold(self, board, continuity, label):
        self.actions.append(('HOLD',))
        if len([a for a in self.actions if a[0]=='HOLD']) == self.fail:
            raise ValueError('Electrical/reference guard failed')


def test_exact_ten_holds_and_one_arm_without_any_diagnostic_waveform():
    b = Bench(); assert qa.check_reference(b, object(), '1'*32) == '2'*32
    assert [a[0] for a in b.actions].count('ARM') == 1
    assert [a[0] for a in b.actions].count('HOLD') == 10
    assert set(a[0] for a in b.actions) == {'PING', 'ARM', 'HOLD'}


def test_guard_failure_stops_without_retry_or_final_success_ping():
    b = Bench(fail=2)
    with pytest.raises(ValueError, match='guard failed'): qa.check_reference(b, object(), '1'*32)
    assert b.actions[-1] == ('HOLD',)
    assert [a[0] for a in b.actions].count('HOLD') == 2
    assert [a[0] for a in b.actions].count('ARM') == 1


def test_unchanged_boot_stops_before_arm():
    b = Bench(boot='1'*32)
    with pytest.raises(ValueError, match='New boot'): qa.check_reference(b, object(), '1'*32)
    assert b.actions == [('PING', False)]
