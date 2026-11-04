import json

from benchmate.records import Recorder
from benchmate.reading_wire_stage import verify


def registered(tmp_path):
    log = Recorder(tmp_path, mode='wire-stage-auditor-test')
    log.add('reading_pair_registered', {'cohort': 'reading-assisted-v1', 'run_id': log.path.name})
    return log


def test_preserved_failed_prefix_is_not_misreported_as_complete(tmp_path):
    log = registered(tmp_path)
    log.add('run_failed', {'stage': 'before_measurement'})
    result = verify(log.path)
    assert result['passed'] and result['run_status'] == 'run_failed'
    assert result['measurements'] == 0


def test_complete_claim_requires_forecast_observation_restoration_and_rerun(tmp_path):
    log = registered(tmp_path)
    log.add('run_completed', {'restored_verdict': 'consistent'})
    result = verify(log.path)
    assert not result['passed'] and result['error'] == 'incomplete_wire_pair'


def test_modified_event_is_rejected(tmp_path):
    log = registered(tmp_path)
    log.add('run_failed', {'stage': 'before_measurement'})
    rows = [json.loads(l) for l in log.file.read_text().splitlines()]
    rows[-1]['payload']['stage'] = 'edited'
    log.file.write_text('\n'.join(json.dumps(x) for x in rows) + '\n')
    assert not verify(log.path)['passed']
