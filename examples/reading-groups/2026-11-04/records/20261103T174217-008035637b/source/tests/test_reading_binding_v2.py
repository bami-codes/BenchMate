"""A null-format repair cannot become a physical identity or trigger a retry."""
from copy import deepcopy
import hashlib
import io
import json
import pytest

from benchmate.reading_binding_v2 import parse_binding
from benchmate.reading_unordered import compare_unordered


@pytest.mark.parametrize('body,normalization', [(None, None), ('null', 'exact_string_null_to_JSON_null_abstention'),
                                              ('sam-2', None)])
def test_only_exact_null_is_normalized_with_raw_reply_retained(body, normalization):
    raw = {'sam_body': body, 'reason': 'Parallel bodies share the same nodes.'}
    saved = deepcopy(raw)
    result = parse_binding(raw, ['sam-2', 'sam-3'])
    assert raw == saved == result['raw_arguments']
    assert result['normalization'] == normalization
    assert result['sam_body'] == (None if body in (None, 'null') else body)
    assert result['operator_confirmed'] is False


@pytest.mark.parametrize('body', ['NULL', ' null ', '', 'sam-4', ['sam-2'], {}, 0, False])
def test_invalid_candidates_are_not_guessed(body):
    with pytest.raises(ValueError):
        parse_binding({'sam_body': body, 'reason': 'Ambiguous.'}, ['sam-2', 'sam-3'])


def test_binding_adapter_preserves_request_and_never_repeats_for_string_null(tmp_path, monkeypatch):
    from PIL import Image
    from benchmate import reading_photo, reading_transport, reading_binding_v2
    raw = io.BytesIO()
    Image.new('RGB', (100, 100), 'white').save(raw, format='PNG')
    source = tmp_path/'source.png'
    source.write_bytes(raw.getvalue())
    reading_photo.prepare(source, tmp_path/'prepared', {}, 'a'*64)
    d = tmp_path/'decoded'
    d.mkdir()
    (d/'crop.png').write_bytes(raw.getvalue())
    (d/'body-manifest.json').write_text(json.dumps({
        'prepared': str(tmp_path/'prepared'), 'original_full_size': [100, 100],
        'components': [{'id': 'sam-2', 'read_selected': True, 'source_box': [20, 20, 70, 70],
                        'localizer': 'SAM-derived body mask',
                        'views': [{'file': 'crop.png', 'sha256': hashlib.sha256(raw.getvalue()).hexdigest()}]}]}))
    requests = []
    def fake(content, **kw):
        requests.append((content, kw))
        return tmp_path/'retained-request', {'arguments': {'sam_body': 'null', 'reason': 'Ambiguous parallel bodies.'}}
    monkeypatch.setattr(reading_photo, 'call', fake)
    monkeypatch.setattr(reading_transport, 'call', fake)
    with pytest.raises(ValueError):
        reading_photo.binding_request(d, source, 'C1', tmp_path/'budget', tmp_path/'out')
    _, proposal, receipt = reading_binding_v2.binding_request(d, source, 'C1', tmp_path/'budget', tmp_path/'out')
    assert len(requests) == 2  # One explicit call per version, no live provider.
    assert requests[0] == requests[1]
    assert proposal['sam_body'] is None and proposal['localizer'] is None
    assert receipt['raw_arguments']['sam_body'] == 'null'
    assert receipt['correspondence'] == 'unresolved'
    (d/'crop.png').write_bytes(b'changed')
    with pytest.raises(ValueError, match='crop changed'):
        reading_binding_v2.binding_request(d, source, 'C1', tmp_path/'budget', tmp_path/'out')
    assert len(requests) == 2


def examples():
    return [{'id': 'changed:C1', 'role': 'active', 'intervals': {'C1': [.42, .56], 'C2': [.095, .105]}},
            {'id': 'nominal', 'role': 'reference', 'intervals': {'C1': [.95, 1.05], 'C2': [.095, .105]}}]


def test_unordered_match_is_invariant_to_physical_order():
    for values, body in [({'sam-2': .47, 'sam-3': .1}, 'sam-2'), ({'sam-2': .1, 'sam-3': .47}, 'sam-3')]:
        result = compare_unordered(values, examples())
        assert result['fits'] == ['changed:C1'] and not result['reference_fits']
        assert result['conditional_unique_binding']['C1'] == body
        assert result['nearest_value_assignment'] is False and result['refitted'] is False


def test_nearest_value_cannot_force_a_match_or_resurrect_nominal():
    result = compare_unordered({'sam-2': 1., 'sam-3': .1}, examples())
    assert result['fits'] == [] and result['reference_fits'] == ['nominal']
    assert result['outcome'] == 'all_explanations_rejected'
    assert result['conditional_unique_binding'] is None
    assert compare_unordered({'sam-2': .2, 'sam-3': .3}, examples())['fits'] == []


def test_multiple_permutations_keep_identity_unresolved_even_with_one_family():
    rows = [{'id': 'overlap', 'role': 'active', 'intervals': {'C1': [.09, .2], 'C2': [.09, .2]}}]
    result = compare_unordered({'sam-2': .1, 'sam-3': .11}, rows)
    assert len(result['matches'][0]['assignments']) == 2
    assert result['fits'] == ['overlap']
    assert result['body_identity_status'] == 'unresolved'
    assert result['conditional_unique_binding'] is None


def test_multiple_families_and_nonfinite_values_do_not_force_identity():
    rows = examples()
    rows[1]['role'] = 'active'
    rows[1]['intervals']['C1'] = [.4, .6]
    result = compare_unordered({'sam-2': .47, 'sam-3': .1}, rows)
    assert result['outcome'] == 'indistinguishable' and result['conditional_unique_binding'] is None
    for value in (float('nan'), float('inf'), -.1, True):
        with pytest.raises(ValueError):
            compare_unordered({'sam-2': value, 'sam-3': .1}, examples())
