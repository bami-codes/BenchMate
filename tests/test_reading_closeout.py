"""Actual retained evidence copied into tmp; no hardware/network/model calls."""
import json
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

from benchmate import reading_closeout as closeout
from benchmate.records import Recorder
from test_reading_verify import rechain

ROOT=Path(__file__).resolve().parents[1]
PREFIX=ROOT/'examples/reading-followup/2026-11-03/records/20261103T142003-2b176faa91'


@pytest.fixture
def record(tmp_path,monkeypatch):
    p=tmp_path/'SYNTHETIC_CLOSEOUT_TEST';shutil.copytree(PREFIX,p)
    # This test pins the retained pre-closeout prefix, even after production
    # closeout adds its two events to the public archive.
    lines=(p/'events.jsonl').read_text().splitlines()
    (p/'events.jsonl').write_text('\n'.join(lines[:241])+'\n')
    monkeypatch.setattr(closeout.prior,'check_publication',lambda *a:None)
    return p


def test_additive_closeout_preserves_previous_bytes_and_verifies_offline(record):
    before=(record/'events.jsonl').read_bytes()
    original=(record/'history/original/events.jsonl').read_bytes()
    closeout.close(record)
    assert (record/'events.jsonl').read_bytes().startswith(before)
    assert (record/'history/original/events.jsonl').read_bytes()==original
    r=closeout.verify(record)
    assert r['passed'] and r['run_status']=='run_completed'
    result=json.loads((record/'result.json').read_text())
    assert result['restored_photo_and_correspondence_recorded'] is False
    for module,args in [('benchmate',['verify']),('benchmate.reading_closeout',['verify'])]:
        out=subprocess.run([sys.executable,'-S','-m',module,*args,str(record)],cwd=ROOT,capture_output=True,text=True)
        assert out.returncode==0,out.stdout+out.stderr
        assert out.stdout.startswith('PASS ') and 'creation_time=unproven' in out.stdout


def test_rehashed_claim_of_new_restored_photo_is_rejected(record):
    closeout.close(record)
    def edit(events):events[-1]['payload']['restored_photo_and_correspondence_recorded']=True
    rechain(record/'events.jsonl',edit)
    events=closeout.chain(record/'events.jsonl')
    closeout.prior.save(record/'result.json',events[-1]['payload'])
    with pytest.raises(ValueError,match='rewritten closeout'):closeout.verify(record)


def test_cannot_silently_drop_photo_stage_already_recorded(record):
    events=closeout.prior.decode_events((record/'events.jsonl').read_bytes(),require_terminal=False,include_hash=True)
    log=Recorder.__new__(Recorder);log.path=record;log.file=record/'events.jsonl';log.sequence=len(events);log.previous=events[-1]['sha256']
    log.add('followup_photo_received',{'source':'synthetic test'})
    before=log.file.read_bytes()
    with pytest.raises(ValueError,match='already started'):closeout.close(record)
    assert log.file.read_bytes()==before
