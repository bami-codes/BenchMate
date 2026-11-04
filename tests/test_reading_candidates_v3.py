from copy import deepcopy

import pytest

from benchmate.reading_candidates_v3 import parse


def ambiguous():
    return {'candidate_bodies': [
        {'sam_body': 'sam-a', 'kind': 'C', 'reason': 'Capacitor body.'},
        {'sam_body': 'sam-b', 'kind': 'C', 'reason': 'Another capacitor body.'}],
        'mapping_status': 'ambiguous', 'sam_body': None,
        'reason': 'Both share the same terminals.'}


def test_abstention_retains_both_candidate_ids_and_kinds():
    a = ambiguous()
    result = parse(a, ['sam-a', 'sam-b', 'sam-wire'])
    assert result['candidate_bodies'] == a['candidate_bodies']
    assert result['sam_body'] is None
    assert result['raw_arguments'] == a


def test_exact_string_null_has_an_explicit_normalization_receipt():
    a = ambiguous()
    a['sam_body'] = 'null'
    result = parse(a, ['sam-a', 'sam-b'])
    assert result['sam_body'] is None
    assert result['raw_arguments']['sam_body'] == 'null'
    assert result['normalization'] == 'exact_string_null_to_JSON_null_abstention'


@pytest.mark.parametrize('change', ['unknown_id', 'duplicate', 'value_field', 'unlisted_selected'])
def test_invalid_or_invented_candidates_are_rejected(change):
    a = deepcopy(ambiguous())
    if change == 'unknown_id':
        a['candidate_bodies'][0]['sam_body'] = 'invented'
    elif change == 'duplicate':
        a['candidate_bodies'][1]['sam_body'] = 'sam-a'
    elif change == 'value_field':
        a['candidate_bodies'][0]['value'] = 0.47e-6
    else:
        a.update(mapping_status='unique', sam_body='sam-wire')
    with pytest.raises(ValueError):
        parse(a, ['sam-a', 'sam-b', 'sam-wire'])


def test_no_visible_candidate_does_not_force_a_selection():
    a = {'candidate_bodies': [], 'mapping_status': 'unresolved', 'sam_body': None,
         'reason': 'No plausible body can be identified from these image regions.'}
    assert parse(a, ['sam-a'])['candidate_bodies'] == []
