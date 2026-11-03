"""Failed primary slots remain fixed while separately counted attempts proceed."""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]


def module():
    spec = importlib.util.spec_from_file_location('followup_test', ROOT / 'scripts/official_passive_followup.py')
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def index():
    policy = json.loads((ROOT / 'docs/2026-11-03-official-run-policy.json').read_text())
    value = {'slots': deepcopy(policy['ordered_slots'])}
    value['slots'][0].update(status='failed', run_id='immutable-original', error='guard failure')
    return value


def test_followup_does_not_replace_or_modify_failed_primary():
    m = module(); value = index(); before = deepcopy(value['slots'])
    follow = m.select_slot(value, '01-F02')
    assert value['slots'] == before
    assert follow in value['followups'] and follow not in value['slots']
    assert follow['selected_for_case_demo'] is False and follow['required'] is False
    assert follow['followup_of'] == '01-F01' and follow['attempt_ordinal'] == 2


def test_cannot_reregister_original_or_skip_followup_number():
    m = module(); value = index()
    with pytest.raises(ValueError, match='never replace'):
        m.select_slot(value, '01-F01')
    with pytest.raises(ValueError, match='contiguous'):
        m.select_slot(value, '01-F03')


def test_no_concurrent_followup():
    m = module(); value = index()
    follow = m.select_slot(value, '01-F02')
    follow.update(run_id='new-attempt', status='running')
    with pytest.raises(ValueError, match='no concurrent'):
        m.select_slot(value, '01-F03')


def test_restored_slot_requires_completed_separate_verification():
    m = module(); value = index()
    with pytest.raises(ValueError, match='unresolved'):
        m.select_slot(value, '01-R01')
    follow = m.select_slot(value, '01-F02')
    follow.update(status='completed', verification_completed=False)
    with pytest.raises(ValueError, match='unresolved'):
        m.select_slot(value, '01-R01')
    follow['verification_completed'] = True
    restored = m.select_slot(value, '01-R01')
    assert restored['slot_id'] == '01-R01'
    assert value['slots'][0]['status'] == 'failed'


def test_followup_cannot_skip_other_required_case_slots():
    m = module(); value = index()
    with pytest.raises(ValueError, match='unresolved'):
        m.select_slot(value, '04-F01')


def test_actual_original_model_prompt_bench_and_protocol_are_reused():
    m = module()
    from benchmate.official_passive import Session, Bench, PROMPT, prepare
    assert m.base.Session is Session and m.base.Bench is Bench and m.base.PROMPT == PROMPT
    p = m.base.load_prepared(ROOT / 'examples/official-prepared/2026-11-03/design-01')[1]
    design = json.loads((ROOT / 'examples/reviewed-designs/2026-11-03-pilot/design-01.json').read_text())
    assert p == prepare(design)
    sources = m.full_sources(p)
    assert len(sources) == 82 and all(sources[k] == v for k, v in p['official_source_sha256'].items())


def test_ten_second_wait_once_per_new_unarmed_boot(monkeypatch):
    m = module(); calls = []; now = [100.]
    monkeypatch.setattr(m.base.Bench, '_ping', lambda *a: calls.append(('PING', a[-1])))
    monkeypatch.setattr(m.time, 'monotonic', lambda: now[0])
    b = m.SettledBench.__new__(m.SettledBench)
    b.startup_waited_boot = None
    b.log = SimpleNamespace(add=lambda kind, payload: calls.append((kind, payload)))
    def sleep(seconds):
        calls.append(('WAIT', seconds)); now[0] += seconds
    b.sleep = sleep
    continuity = SimpleNamespace(boot_id='2' * 32)
    b._ping(None, continuity, 'initial', False)
    assert ('WAIT', 10.) in calls
    assert calls[-1][0] == 'usb_startup_wait_completed'
    before = len(calls)
    b._ping(None, continuity, 'still_unarmed', False)
    assert len(calls) == before + 1
    b._ping(None, continuity, 'armed', True)
    assert sum(c[0] == 'WAIT' for c in calls) == 1
    continuity.boot_id = '3' * 32
    b._ping(None, continuity, 'new_boot', False)
    assert sum(c[0] == 'WAIT' for c in calls) == 2


def test_early_sleep_return_stops_before_ARM(monkeypatch):
    m = module()
    monkeypatch.setattr(m.base.Bench, '_ping', lambda *a: None)
    monkeypatch.setattr(m.time, 'monotonic', lambda: 100.)
    b = m.SettledBench.__new__(m.SettledBench)
    b.startup_waited_boot = None
    b.log = SimpleNamespace(add=lambda *a: None)
    b.sleep = lambda s: None
    with pytest.raises(ValueError, match='wait not reached'):
        b._ping(None, SimpleNamespace(boot_id='2' * 32), 'initial', False)
    assert b.startup_waited_boot is None
