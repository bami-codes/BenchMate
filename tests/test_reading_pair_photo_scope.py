"""Pre-intake photo scope cannot be invented after outcomes or relabel old pixels."""
import json
import subprocess
import sys
from pathlib import Path

import pytest

from benchmate.reading_pair_audit import verify_pair,PHOTO_RULE
from benchmate.reading_rules import digest
from test_reading_verify import pair,artifact,rechain


@pytest.fixture
def waived_pair(pair):
    f=artifact(pair,'workflow.md',b'SYNTHETIC before-intake scope test only')
    def edit(events):
        events.insert(2,{'kind':'case_workflow_scope_frozen','payload':{**f,
            'frozen_before_schematic_intake':True,'frozen_before_hardware_measurements':True,
            'original_runtime_sources_changed':False,'optional_restored_photo':PHOTO_RULE}})
        photo=next(e['payload'] for e in events if e['kind']=='board_photo_received' and e['payload']['state']=='faulted')
        binding=next(e['payload'] for e in events if e['kind']=='body_binding' and e['payload']['state']=='faulted')
        events[:]=[e for e in events if not (e['kind'] in ('board_photo_received','bodies_decoded','body_binding_proposed','body_binding') and e['payload']['state']=='restored')]
        events.insert(-1,{'kind':'restored_photo_not_repeated','payload':{
            'reason':'unchanged_mini_board_external_restoration','operator_mini_configuration_unchanged':True,
            'new_restored_photo':False,'image_relabelled_as_restored':False,'new_SAM_requests':0,'new_binding_requests':0,
            'original_fault_photo_sha256':photo['sha256'],'reference_binding_sha256':digest(binding)}})
        events[-1]['payload'].update(both_state_photos_recorded=False,restored_photo_not_repeated=True)
        # Supply timestamp/hash fields to synthetic inserted items before rechain.
        for e in events:e.setdefault('timestamp','2026-11-03T00:00:00+00:00')
    rechain(pair/'events.jsonl',edit)
    return pair


def test_prospective_scope_preserves_full_diagnostic_and_reading_audit(waived_pair):
    r=verify_pair(waived_pair);assert r['passed'],r
    assert r['forecasts']==9 and r['measurements']==11
    result=subprocess.run([sys.executable,'-S','-m','benchmate.reading_pair_closeout','verify',str(waived_pair)],
        cwd=Path(__file__).resolve().parents[1],capture_output=True,text=True)
    assert result.returncode==0,result.stdout+result.stderr


@pytest.mark.parametrize('attack',['late_scope','fake_new_photo','wrong_reference'])
def test_valid_rehash_does_not_hide_photo_scope_violations(waived_pair,attack):
    def edit(events):
        if attack=='late_scope':
            item=events.pop(next(i for i,e in enumerate(events) if e['kind']=='case_workflow_scope_frozen'))
            events.insert(-2,item)
        elif attack=='fake_new_photo':events[-1]['payload']['both_state_photos_recorded']=True
        else:next(e for e in events if e['kind']=='restored_photo_not_repeated')['payload']['original_fault_photo_sha256']='f'*64
    rechain(waived_pair/'events.jsonl',edit)
    assert not verify_pair(waived_pair)['passed']
