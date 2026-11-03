"""Follow-up provenance checks; synthetic records never control hardware or APIs."""
import json
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

from benchmate import reading_followup as followup
from benchmate.records import Recorder
from test_reading_verify import artifact, rechain

ROOT = Path(__file__).resolve().parents[1]
QA = ROOT/'examples/reading-recovery/2026-11-03/records/20261103T140847-47f2534f1a'
NATIVE = ROOT/'examples/official-runs/2026-11-03/records/20261103T113619-34ff2352b1'


def test_original_terminal_cannot_be_reopened(tmp_path):
    log = Recorder(tmp_path, mode='SYNTHETIC_TEST_ONLY')
    log.add('run_failed', {'preserved': True})
    before = log.file.read_bytes()
    with pytest.raises(ValueError, match='Terminal follow-up'):
        followup.open_record(log.path, ['awaiting_restored_setup'])
    assert log.file.read_bytes() == before


def test_QA_failure_remains_disqualifying_even_after_valid_rehash(tmp_path):
    target = tmp_path/'QA'; shutil.copytree(QA, target)
    followup.qa_checked(target)
    def edit(events):
        guard = next(e for e in events if e['kind']=='physical_electrical_guard')
        guard['payload']['checks'][next(iter(guard['payload']['checks']))] = False
    rechain(target/'events.jsonl', edit)
    with pytest.raises(ValueError, match='passing three-HOLD'):
        followup.qa_checked(target)


@pytest.fixture
def record(tmp_path, monkeypatch):
    log = Recorder(tmp_path, mode='SYNTHETIC_FOLLOWUP_TEST_ONLY')
    child = Recorder(log.path/'history/original', mode='SYNTHETIC_FAILED_PARENT')
    child.add('run_failed', {'source':'synthetic'})
    qa = log.path/'history/QA'; shutil.copytree(QA, qa)
    qe,qr,qp = followup.qa_checked(qa)
    # Original reading-pair audit has independent full tests. Here use a small
    # synthetic parent to isolate added follow-up ordering/accounting checks.
    old_head = qp['failed_pair_head_sha256']
    monkeypatch.setattr(followup, 'verify_original', lambda *a, **k: {
        'passed':True,'run_status':'run_failed','head_sha256':old_head,
        'events':2,'forecasts':0,'measurements':0,'order_checks':0,'prediction_files':0})
    reg = {'original_primary_status':'failed','original_selection_unchanged':True,
        'counted':True,'selected_first_attempt':False,'original_head_sha256':old_head,
        'QA_head_sha256':qe[-1]['sha256'],'QA_boot_id':qr['boot_id'],
        'requested_photo_component':'R1'}
    followup.save(log.path/'registration.json', reg)
    log.add('restored_followup_registered', reg)
    followup.bind(log, child.file, 'original_failed_pair')
    followup.bind(log, qa/'events.jsonl', 'recovery_QA')
    # Retained diagnostic forecasts/acquisitions go through the real base audit.
    for e in followup.chain(NATIVE/'events.jsonl')[1:-1]:
        log.add(e['kind'], e['payload'])
    shutil.copyfile(NATIVE/'predictions-frozen.json', log.path/'predictions-frozen.json')
    report = {'agent_report':{'verdict':'consistent'}}
    a = artifact(log.path, 'diagnostic-result.json', json.dumps(report).encode())
    log.add('restored_followup_diagnosis_completed', {**report,'artifact':a})
    log.add('followup_photo_received', {'artifacts':[artifact(log.path,'photo.png')]})
    log.add('followup_bodies_decoded', {'bodies':['sam-0','sam-1'],'artifacts':[]})
    p = {'sam_body':'sam-0','reason':'Geometry only.','component':'R1','chosen_by':'muse_spark'}
    binding = Recorder(log.path/'binding', mode='SYNTHETIC_BINDING')
    binding.add('run_completed', {'arguments':{k:p[k] for k in ('sam_body','reason')}})
    followup.bind(log, binding.file, 'body_binding')
    log.add('body_binding_proposed', p)
    log.add('body_binding', {**p,'operator_confirmed':True})
    log.add('run_completed', {'original_pair_status':'failed','restored_verdict':'consistent',
        'operator_restored_and_rerun_consistent':True,
        'display_caption':'No mismatch in the tests Spark chose'})
    return log.path


def test_followup_checks_native_forecasts_and_history(record):
    result = followup.verify(record)
    assert result['passed'] and result['forecasts'] > 0 and result['measurements'] > 0


@pytest.mark.parametrize('attack', ['fake_Spark','early_photo','rewrite_failure','rewrite_verdict'])
def test_rehash_does_not_hide_false_provenance_or_summary(record, attack):
    def edit(events):
        if attack=='fake_Spark':
            next(e for e in events if e['kind']=='body_binding')['payload']['sam_body']='sam-1'
        elif attack=='early_photo':
            photo = events.pop(next(i for i,e in enumerate(events) if e['kind']=='followup_photo_received'))
            events.insert(next(i for i,e in enumerate(events) if e['kind']=='restored_followup_diagnosis_completed'), photo)
        elif attack=='rewrite_failure':
            events[-1]['payload']['original_pair_status']='completed'
        else:
            events[-1]['payload']['restored_verdict']='changed'
    rechain(record/'events.jsonl', edit)
    with pytest.raises(ValueError):
        followup.verify(record)


def test_cli_imports_without_site_packages_keys_or_network():
    result = subprocess.run([sys.executable,'-S','-m','benchmate.reading_followup','--help'],
        cwd=ROOT,capture_output=True,text=True)
    assert result.returncode==0, result.stderr
