from pathlib import Path
import importlib.util,json,sys
import pytest
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('video_run_review',ROOT/'video/review_run.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
REPAIR=ROOT/'examples/overnight/2026-11-02/rehearsals/d01'
B5=ROOT/'examples/b5-unloaded-spark/2026-10-30/20261030T133514-4ea9a8848e'

def test_mock_repair_has_local_publication_not_a_physical_claim():
 r=mod.review(REPAIR)
 assert r['declared_source']=='mock' and not r['publication_remote']
 assert r['both_conditional_checks_pass'] and r['both_command_forecasts_pass']
 assert not r['editing_prerequisites_missing']
 assert '모의' in r['recorded_reason_original']

def test_original_b5_has_remote_publication_but_still_mock():
 r=mod.review(B5)
 assert r['declared_source']=='mock' and r['publication_remote']
 assert r['freeze_publication_before_observations']
 assert r['publication']['commit'].startswith('9cff3e8')
 assert not r['editing_prerequisites_missing']

@pytest.mark.parametrize('run',[REPAIR,B5])
def test_mock_cannot_replace_physical_scene(run):
 with pytest.raises(ValueError,match='Mock record'):mod.review(run,require_physical=True)

def test_corrupted_record_rejected(tmp_path):
 raw=(REPAIR/'events.jsonl').read_bytes().replace(b'meta_d01_repair_mock',b'meta_d01_repair_phys',1)
 p=tmp_path/'events.jsonl';p.write_bytes(raw)
 with pytest.raises(ValueError,match='integrity'):mod.review(p)

def test_changed_frozen_sidecar_rejected(tmp_path):
 (tmp_path/'events.jsonl').write_bytes((REPAIR/'events.jsonl').read_bytes())
 d=json.loads((REPAIR/'predictions-frozen.json').read_text());d['reason']='edited'
 (tmp_path/'predictions-frozen.json').write_text(json.dumps(d))
 with pytest.raises(ValueError,match='sidecar'):mod.review(tmp_path)

def test_truncated_run_is_not_complete(tmp_path):
 lines=(REPAIR/'events.jsonl').read_text().splitlines()
 (tmp_path/'events.jsonl').write_text('\n'.join(lines[:20])+'\n')
 r=mod.review(tmp_path)
 assert r['chain_valid'] and r['terminal_kind'] is None
 assert not r['both_conditional_checks_pass']
 assert r['editing_prerequisites_missing']

def rechain_copy(tmp_path,mutate):
 from benchmate.records import canonical
 import hashlib
 events=[json.loads(x) for x in (REPAIR/'events.jsonl').read_text().splitlines()]
 mutate(events);previous='0'*64;lines=[]
 for e in events:
  e.pop('sha256');e['previous_sha256']=previous
  previous=hashlib.sha256(canonical(e)).hexdigest();e['sha256']=previous;lines.append(json.dumps(e))
 (tmp_path/'events.jsonl').write_text('\n'.join(lines)+'\n')
 (tmp_path/'predictions-frozen.json').write_bytes((REPAIR/'predictions-frozen.json').read_bytes())
 return tmp_path

def test_a_valid_chain_cannot_link_checks_to_a_different_prediction(tmp_path):
 def mutate(events):
  e=next(e for e in events if e['kind']=='repair_prediction_comparison')
  e['payload']['prediction_sha256']='0'*64
 run=rechain_copy(tmp_path,mutate)
 with pytest.raises(ValueError,match='Check refers'):mod.review(run)

def test_conditional_pass_does_not_hide_command_forecast_failure(tmp_path):
 def mutate(events):
  e=next(e for e in events if e['kind']=='repair_prediction_comparison')
  e['payload']['command_forecast']['restored_nominal']['passed']=False
 run=rechain_copy(tmp_path,mutate);r=mod.review(run)
 assert r['both_conditional_checks_pass'] and not r['both_command_forecasts_pass']
 assert any('both results must remain visible' in n for n in r['presentation_notes'])
