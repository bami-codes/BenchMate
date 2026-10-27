from benchmate.records import Recorder
from benchmate.viewer import export_viewer
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
