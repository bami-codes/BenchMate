from benchmate.records import Recorder
from benchmate.viewer import export_viewer
from benchmate.viewer import load_record,render_viewer
import pytest


def test_viewer_escapes_model_content_and_preserves_record(tmp_path):
    log=Recorder(tmp_path,mode='synthetic_test')
    log.add('run_completed',{'report':'</script><script>alert("secret")</script>'})
    original=log.file.read_bytes()
    report=export_viewer(log.path)
    html=report.read_text()
    assert '</script><script>alert' not in html
    assert '\\u003c/script\\u003e' in html
    assert 'connect-src' in html and '/*RECORD_DATA*/' not in html
    assert log.file.read_bytes()==original
    with pytest.raises(ValueError,match='overwrite'):export_viewer(log.path,log.file)


def test_viewer_refuses_incomplete_record(tmp_path):
    log=Recorder(tmp_path,mode='synthetic_test')
    with pytest.raises(ValueError,match='incomplete'):export_viewer(log.path)


def test_live_prefix_ignores_partial_write_but_never_accepts_corrupt_event(tmp_path):
    log=Recorder(tmp_path,mode='continuous_live_agent')
    prefix=load_record(log.path,live=True)
    assert prefix['transport']=='live_log' and len(prefix['events'])==1
    complete=log.file.read_bytes()
    log.file.write_bytes(complete+b'{"unfinished":"\xe2')
    assert load_record(log.path,live=True)==prefix
    log.file.write_bytes(complete.replace(b'run_started',b'run_changed'))
    with pytest.raises(ValueError,match='integrity'):load_record(log.path,live=True)


def test_replay_and_live_embed_the_same_renderer_and_separate_transport(tmp_path):
    log=Recorder(tmp_path,mode='synthetic_test');log.add('run_completed',{'source':'synthetic'})
    replay=render_viewer(load_record(log.path));live=render_viewer(load_record(log.path,live=True))
    for html in [replay,live]:
        assert 'lang="en"' in html and 'window.BenchMateUI=' in html
        assert 'Connections for this step' in html and 'Experiment trail' in html
        assert 'data:font/woff2;base64,' in html and '/*FONT_' not in html
        assert 'SIL OPEN FONT LICENSE' in html
    assert "connect-src 'none'" in replay and "connect-src 'self'" in live
    assert '"transport": "replay"' in replay and '"transport": "live_log"' in live


def test_live_log_rejects_other_origins_and_hosts():
    from benchmate.live_viewer import allowed_origin
    assert allowed_origin('127.0.0.1:8765',None,8765)
    assert allowed_origin('localhost:8765','http://localhost:8765',8765)
    assert not allowed_origin('attacker.example:8765',None,8765)
    assert not allowed_origin('127.0.0.1:8765','https://attacker.example',8765)


def test_comparison_sidecar_is_bound_to_the_unmodified_record(tmp_path):
    import json
    log=Recorder(tmp_path,mode='synthetic_test');log.add('run_completed',{})
    record=load_record(log.path)
    sidecar={'source_sha256':record['source_sha256'],'entries':[
        {'event_sequence':0,'event_sha256':record['events'][0]['sha256'],'comparison':{'conditions':[]}}]}
    file=log.path/'comparison.json';file.write_text(json.dumps(sidecar))
    assert load_record(log.path)['comparison']==sidecar
    sidecar['entries'][0]['event_sha256']='wrong';file.write_text(json.dumps(sidecar))
    with pytest.raises(ValueError,match='Comparison event'):load_record(log.path)
    sidecar['source_sha256']='wrong';file.write_text(json.dumps(sidecar))
    with pytest.raises(ValueError,match='Comparison source'):load_record(log.path)


def test_reconstructed_training_curves_do_not_use_verification(tmp_path):
    import copy
    import json
    import shutil
    from pathlib import Path
    from benchmate.comparison import reconstruct_comparisons
    from benchmate.records import read_events
    if shutil.which('ngspice') is None:pytest.skip('ngspice not installed')
    source=Path(__file__).parents[1]/'examples/discovery-mismatch-english/events.jsonl'
    original=source.read_bytes();events=read_events(source);comparisons=[];diagnostics=[]
    for changed in (False,True):
        log=Recorder(tmp_path,mode=events[0]['payload']['mode'])
        for e in events[1:]:
            payload=copy.deepcopy(e['payload'])
            if changed and e['kind']=='verification_acquisition':
                payload['data']['out_v']=[v+.4 for v in payload['data']['out_v']]
            log.add(e['kind'],payload)
        raw=log.file.read_bytes();sidecar=json.loads(reconstruct_comparisons(log.path).read_text())
        assert raw==log.file.read_bytes()
        assert all(max(e['training_event_sequences'])<e['event_sequence'] for e in sidecar['entries'])
        comparisons.append([e['comparison'] for e in sidecar['entries'] if e['kind']!='verification'])
        diagnostics.append([e['comparison'] for e in sidecar['entries'] if e['kind']=='verification'])
    assert comparisons[0]==comparisons[1]
    assert diagnostics[0]!=diagnostics[1]  # Only post-observation scoring can change.
    assert all(c['discrimination']=='proposal_only_passes' for c in diagnostics[0][0]['conditions'])
    assert all(not c['proposal']['adequacy']['passed'] for c in diagnostics[1][0]['conditions'])
    assert source.read_bytes()==original
