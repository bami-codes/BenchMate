from copy import deepcopy
import json
from pathlib import Path
from types import SimpleNamespace
import pytest

from benchmate import reading_photo_stage_v4 as stage
from benchmate.reading_timing_verify_v4 import verify_pair
from benchmate.records import Recorder


PORTS={'schema':'benchmate.operator_photo_ports.v1','operator_confirmed':True,'source':'operator_confirmed_wiring_table',
 'ports':{'IN':{'wire_color':'green','mini_contact':'A3'},'OUT':{'wire_color':'blue','mini_contact':'A13'},'REF':{'wire_color':'white','mini_contact':'A17'}},
 'component_values_or_reference_assignments_included':False}


def test_only_port_context_is_admitted():
    assert stage.validate_ports(PORTS)==PORTS['ports']
    for mutation in ('value','reference','instruction'):
        value=deepcopy(PORTS);value['ports']['IN'][mutation]='R1 2.2k'
        with pytest.raises(ValueError):stage.validate_ports(value)


@pytest.mark.parametrize('contact',['A35','A0','A18','F3','R1','2.2k'])
def test_invalid_or_non_port_contact_is_rejected(contact):
    value=deepcopy(PORTS);value['ports']['IN']['mini_contact']=contact
    with pytest.raises(ValueError):stage.validate_ports(value)


def test_ambiguous_bodies_cannot_get_an_operator_truth_label(tmp_path,monkeypatch):
    p=tmp_path/'photo-faulted';p.mkdir()
    (p/'candidate-proposal.json').write_text(json.dumps({'mapping_status':'ambiguous','sam_body':None}))
    report=tmp_path/'report.json';report.write_text(json.dumps({'accepted':True,'operator_verbatim':'Synthetic acceptance does not invent identity.'}))
    monkeypatch.setattr(stage,'opened',lambda *a:(None,SimpleNamespace(path=tmp_path),None))
    with pytest.raises(ValueError,match='ambiguous'):stage.confirm(tmp_path,report)


def test_restored_omission_cannot_be_chosen_after_photo_receipt(tmp_path,monkeypatch):
    (tmp_path/'photo-restored').mkdir()
    monkeypatch.setattr(stage,'opened',lambda *a:(None,SimpleNamespace(path=tmp_path,control={'restored_verdict':'consistent'}),None))
    with pytest.raises(ValueError,match='before photo'):stage.restored_scope(tmp_path)


def test_changed_board_cannot_reuse_fault_pixels(tmp_path,monkeypatch):
    (tmp_path/'restored-photo-scope.json').write_text(json.dumps({'component_identity_claimed':False}))
    for tag in ('faulted','restored'):
        p=tmp_path/('photo-'+tag)/'prepared';p.mkdir(parents=True);(p/'input.png').write_bytes(b'Synthetic identical pixels, not a real image.')
    helpers=SimpleNamespace(sha=lambda p:Path(p).read_bytes())
    monkeypatch.setattr(stage,'opened',lambda *a:(helpers,SimpleNamespace(path=tmp_path,control={'restored_verdict':'consistent'}),None))
    with pytest.raises(ValueError,match='new restored capture'):stage.finish(tmp_path)


def test_failed_mock_prefix_can_be_audited_without_a_false_completed_pair(tmp_path):
    log=Recorder(tmp_path,mode='synthetic_mock_prefix_not_hardware')
    log.add('reading_pair_registered',{'cohort':'reading-assisted-v1','run_id':log.path.name})
    log.add('run_failed',{'mock':True,'automatic_retry':False})
    r=verify_pair(log.path)
    assert r['passed'] and r['run_status']=='run_failed' and r['events']==3
