"""No hardware/model: exact one-ARM sequence, short-wait and stop-on-error gates."""
from types import SimpleNamespace
import json
import pytest

from benchmate.reading_step_qa import check, STEP


class Bench:
    def __init__(self, *, boot='2'*32, fail=None):
        self.boot=boot;self.calls=[];self.fail=fail
        self.log=SimpleNamespace(add=lambda *_:None)
        self.config=SimpleNamespace(arm_command=lambda b:('ARM '+b).encode())
        self.sleep=lambda seconds:self.calls.append(('sleep',seconds))
    def _ping(self,board,c,label,armed):
        c.boot_id=self.boot;self.calls.append(('PING',armed))
    def _request(self,*_):
        self.calls.append(('ARM',));return {'type':'armed'}
    def _hold(self,*_):
        self.calls.append(('HOLD',))
        if self.fail=='hold' and self.calls.count(('HOLD',))==2:
            raise ValueError('test guard failure')
    def _capture(self,board,c,label,settings):
        assert settings==STEP
        self.calls.append(('STEP',))
        if self.fail=='step':raise ValueError('test guard failure')
        return 'raw'
    def _waveform_checks(self,rows,settings):
        self.calls.append(('timing',))
        if self.fail=='timing':raise ValueError('test timing failure')


def clock(elapsed=10.01):
    ticks=iter([100.,100.+elapsed]);return lambda:next(ticks)


def test_exactly_three_holds_step_return_hold_and_one_arm_after_wait():
    b=Bench()
    assert check(b,None,'1'*32,monotonic=clock())=='2'*32
    assert [c[0] for c in b.calls if c[0] in ('HOLD','STEP')]==['HOLD','HOLD','HOLD','STEP','HOLD']
    assert b.calls.count(('ARM',))==1
    assert b.calls.index(('sleep',10.))<b.calls.index(('ARM',))
    assert b.calls[-1]==('PING',True)


@pytest.mark.parametrize('stage,last', [('hold','HOLD'),('step','STEP'),('timing','timing')])
def test_no_next_capture_or_ping_after_first_failure(stage,last):
    b=Bench(fail=stage)
    with pytest.raises(ValueError):check(b,None,'1'*32,monotonic=clock())
    assert b.calls[-1][0]==last and b.calls.count(('ARM',))==1
    if stage!='hold':assert b.calls.count(('HOLD',))==3


def test_stale_boot_or_short_wait_cannot_arm():
    b=Bench(boot='1'*32)
    with pytest.raises(ValueError,match='Fresh unarmed'):check(b,None,'1'*32,monotonic=clock())
    assert b.calls==[('PING',False)]
    b=Bench()
    with pytest.raises(ValueError,match='Ten-second'):check(b,None,'1'*32,monotonic=clock(9.9))
    assert ('ARM',) not in b.calls


def test_qa_command_matches_the_failed_native_reserved_step():
    from benchmate.reading_step_qa import ROOT, FAILED, command_templates
    protocol=json.loads((ROOT/FAILED/'prepared/protocol.json').read_text())
    events=[json.loads(x) for x in next((ROOT/FAILED/'diagnosis-restored').glob('*/events.jsonl')).read_text().splitlines()]
    native=next(e['payload']['request'] for e in reversed(events)
                if e['kind']=='serial_command' and e['payload']['request'].startswith('CAPTURE '))
    old_boot=native.split()[1]
    templates=command_templates(protocol)
    assert len(templates)==15
    assert templates[10]==native.replace(old_boot,'{boot}')
    assert sum(c.startswith('ARM ') for c in templates)==1
    assert [c.split()[2] for c in templates if c.startswith('CAPTURE ')]==['HOLD','HOLD','HOLD','STEP','HOLD']


def test_consumed_plan_cannot_retry_before_any_hardware_import(tmp_path,monkeypatch):
    from benchmate import reading_step_qa as m
    plan=tmp_path/'plan.json';plan.write_text('{}')
    report=tmp_path/'report.json'
    report.write_text(json.dumps({'verbatim':m.CONFIRMATION,'USB_off_wiring_confirmed':True,
        'USB_connected':True,'fixture':'unloaded','wiring_unchanged':True,'single_step_QA_selected':True}))
    (tmp_path/'execution-started.json').write_text('{}')
    monkeypatch.setattr(m,'validate_plan',lambda _:None)
    monkeypatch.setattr(m,'check_publication',lambda _:None)
    with pytest.raises(FileExistsError):m.run(plan,report,tmp_path/'no_run',True)
    assert not (tmp_path/'no_run').exists()
