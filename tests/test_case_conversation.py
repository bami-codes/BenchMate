"""The product conversation must remain a faithful, prefix-bounded replay."""
from copy import deepcopy
import json
import math
from pathlib import Path
import threading

import httpx
import pytest

from benchmate.case_review.evidence import RecordedConversation
from benchmate.case_review.service import CaseStore, Conflict
from benchmate.case_review.web import make_server
from benchmate.design_replay import D01_SHA

ROOT = Path(__file__).resolve().parents[1]

@pytest.fixture(scope='module')
def record():
    return RecordedConversation(ROOT)


def test_every_prefix_hides_future_sources_scores_and_answer(record):
    for cursor in range(140):
        result = record.snapshot(cursor)
        assert all(e['sequence'] <= cursor for e in result['evidence'])
        assert all(m['sequence'] <= cursor and max(m['refs']) <= cursor for m in result['messages'])
        assert all(p['sequence'] <= cursor and max(p['refs']) <= cursor for p in result['plots'])
        assert bool(result['answer']) == (cursor >= 137)
        assert bool(result['followups']) == (cursor >= 137)
        if cursor < 94:
            assert all(h['status'] == 'unresolved' and not h['scores'] for h in result['hypotheses'])
        if cursor < 93:
            assert not any(p['predictions'] for p in result['plots'])
    # Rewinding is a fresh reduction, not a mutable terminal report.
    record.snapshot(139)
    assert record.snapshot(0)['messages'] == []
    assert record.snapshot(49)['answer'] is None


def test_actor_menu_and_reserved_check_match_original(record):
    messages = {m['sequence']:m for m in record.snapshot(139)['messages']}
    choice = messages[52]
    assert choice['actor'] == 'Muse Spark' and choice['source'] == 'screen_translation'
    assert choice['original'] == json.loads(record.events[52]['payload']['arguments'])['reason']
    assert choice['choices'] == record.events[50]['payload']['result']['allowed_measurements']
    assert choice['choices'] == ['attach_output_load_step', 'repeat_unloaded_step']
    request = messages[54]
    assert request['actor'] == 'BenchMate'
    assert request['original'] == record.events[54]['payload']['instruction']
    assert not next(m for m in record.snapshot(54)['messages'] if m['sequence']==54)['operator_confirmed']
    assert next(m for m in record.snapshot(55)['messages'] if m['sequence']==54)['operator_confirmed']
    assert messages[97]['actor'] == 'BenchMate'
    assert json.loads(record.events[97]['payload']['arguments']) == {}
    assert 'asks' in messages[97]['title']
    assert record.snapshot(139)['answer']['repair_performed'] is False


def test_full_recorded_waveforms_use_channel_times_and_hold_origins(record):
    result = record.snapshot(139)
    for p,seq,comparison in zip(result['plots'],(47,93,132),(None,94,133),strict=True):
        raw=record.events[seq]['payload']
        assert len(p['observed_v']) == len(p['time_s']) == 512
        assert p['time_s'] == [t+d for t,d in zip(raw['data']['frame_time_s'],raw['data']['output_delay_s'],strict=True)]
        assert p['observed_v'] == [v-raw['baseline']['output_v'] for v in raw['data']['output_v']]
        assert p['baseline']['scored_OUT_samples_used'] == 0
        if comparison:
            for key,values in p['predictions'].items():
                score=record.events[comparison]['payload']['scores'][key]
                assert values == [v-raw['baseline']['output_v'] for v in score['prediction']['predicted_output_v']]
                rms=1000*math.sqrt(sum((a-b)**2 for a,b in zip(p['observed_v'],values,strict=True))/512)
                assert rms == pytest.approx(score['RMS_mV'],abs=1e-10)
                assert p['scores'][key]['regions'] == score['regions']
        else:
            assert not p['predictions']  # Never invent a historical nominal curve.
    assert not record.snapshot(93)['plots'][-1]['predictions']
    assert record.snapshot(94)['plots'][-1]['predictions']


def test_regional_failure_not_relabelled_by_overall_rms(record):
    s=record.snapshot(133)
    score=s['plots'][-1]['scores']['nominal_rc']
    assert score['RMS_mV'] < 9
    assert score['passed'] is False
    assert any(r['RMS_mV'] > 9 for r in score['regions'])
    assert next(h for h in s['hypotheses'] if h['id']=='nominal_rc')['status']=='rejected'
    assert next(h for h in s['hypotheses'] if h['id']=='c_changed')['status']=='supported'


@pytest.mark.parametrize('cursor',[-1,140,True,49.0,'49',None])
def test_invalid_positions_rejected(record,cursor):
    with pytest.raises(ValueError):record.snapshot(cursor)


def test_original_event_is_exact_copy_and_cannot_read_ahead(record):
    with pytest.raises(ValueError):record.event(94,93)
    e=record.event(52,52)
    assert e == record.events[52]
    e['payload']['name']='changed'
    assert record.event(52,52)['payload']['name']=='measure'


def test_unknown_design_confirmation_remains_blocked_and_recoverable(tmp_path):
    store=CaseStore(ROOT,tmp_path/'cases')
    first=store.create('Why slow?','recorded_walkthrough')['manifest']
    identity=first['case_id'];candidate=deepcopy(first['intended_design']['draft_candidate'])
    candidate['components'][0]['value_si']=None
    result=store.confirm_for_replay(identity,1,candidate)
    assert result['manifest']['revision']==2 and result['manifest']['experiment_link'] is None
    with pytest.raises(Conflict):store.conversation_snapshot(identity,139)
    resolved=store.confirm_for_replay(identity,2,first['intended_design']['draft_candidate'])
    assert resolved['manifest']['revision']==4
    assert resolved['manifest']['question']['sent_to_model'] is False
    assert 'generated action note' in resolved['manifest']['intended_design']['review_note']
    assert store.conversation_snapshot(identity,0)['record_sha256']==D01_SHA
    with pytest.raises(Conflict):store.confirm_for_replay(identity,4,candidate)


def test_http_conversation_gate_cursor_and_source(tmp_path):
    server=make_server(root=ROOT,output=tmp_path/'http',port=0)
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    try:
        with httpx.Client(base_url=f'http://127.0.0.1:{server.server_port}') as http:
            page=http.get('/')
            token=page.text.split('name="benchmate-session" content="')[1].split('"')[0]
            http.headers.update({'X-BenchMate-Session':token})
            assert '<iframe' not in page.text
            assert "font-src 'self'" in page.headers['content-security-policy']
            assert http.get('/Archivo-var.woff2').status_code==200
            m=http.post('/api/cases',json={'question':'Why slow?','scope':'recorded_walkthrough'}).json()['manifest']
            base=f"/api/cases/{m['case_id']}"
            assert http.get(base+'/timeline?cursor=139').status_code==409
            args={'revision':1,'candidate':m['intended_design']['draft_candidate']}
            assert http.post(base+'/confirm',json=args).status_code==200
            assert http.post(base+'/confirm',json=args).status_code==409
            assert http.get(base+'/timeline?cursor=49').json()['answer'] is None
            assert http.get(base+'/timeline?cursor=139').json()['answer']
            for query in ('','?cursor=-1','?cursor=140','?cursor=1.2','?cursor=1&cursor=2','?cursor=49&run=1'):
                assert http.get(base+'/timeline'+query).status_code==400
            assert http.get(base+'/event?cursor=93&sequence=94').status_code==400
            event=http.get(base+'/event?cursor=94&sequence=94').json()
            assert event['kind']=='physical_model_comparison' and event['sha256']
            assert http.get('/api/state').json()['paid_api_calls']==0
            assert not http.get('/api/state').json()['hardware_IO']
    finally:
        server.shutdown();server.server_close();thread.join()
