"""Photo contract has no surface-value inference; wrong crop blocks the request."""
import hashlib
import io
import json

from PIL import Image
import pytest

from benchmate.reading_photo import prepare, binding_request


def png(color='white'):
    out = io.BytesIO(); Image.new('RGB', (100, 100), color).save(out, format='PNG'); return out.getvalue()


def test_localization_plan_excludes_value_reader_but_allows_schematic_binding(tmp_path):
    source = tmp_path/'source.png'; source.write_bytes(png())
    plan = prepare(source, tmp_path/'prepared', {}, 'a'*64)
    assert plan['Spark_reads_max'] == 0 and plan['Spark_binding_requests_max'] == 1
    assert plan['concepts'] == ['electronic component']
    assert 'intended schematic' in plan['allowed_for_binding']
    assert 'intended design' not in plan['excluded_from_model']


def test_binding_has_no_numeric_value_schema_and_supplies_unknown_leads(tmp_path, monkeypatch):
    source = tmp_path/'source.png'; source.write_bytes(png())
    prepare(source, tmp_path/'prepared', {}, 'a'*64)
    decoded = tmp_path/'decoded'; decoded.mkdir()
    crop = png('red'); (decoded/'body.png').write_bytes(crop)
    manifest = {'prepared': str(tmp_path/'prepared'), 'original_full_size': [100, 100], 'components': [
        {'id': 'sam-0', 'read_selected': True, 'source_box': [20, 20, 70, 70], 'localizer': 'SAM-derived body mask',
         'views': [{'file': 'body.png', 'sha256': hashlib.sha256(crop).hexdigest()}]}]}
    (decoded/'body-manifest.json').write_text(json.dumps(manifest))
    requests = []
    def fake(content, **kw):
        requests.append((content, kw))
        return tmp_path/'model-fixture', {'arguments': {'sam_body': 'sam-0', 'reason': 'One axial body in the visible series path.'}}
    monkeypatch.setattr('benchmate.reading_photo.call', fake)
    _, result = binding_request(decoded, source, 'R1', tmp_path/'budget', tmp_path/'out')
    assert result['operator_confirmed'] is False and result['chosen_by'] == 'muse_spark'
    tool = requests[0][1]['tool']
    assert set(tool['parameters']['properties']) == {'sam_body', 'reason'}
    assert '"lead_positions": null' in requests[0][0][0]['text']
    (decoded/'body.png').write_bytes(png('blue'))
    with pytest.raises(ValueError, match='crop changed'):
        binding_request(decoded, source, 'R1', tmp_path/'budget', tmp_path/'out')
    assert len(requests) == 1
