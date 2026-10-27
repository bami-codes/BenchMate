from copy import deepcopy
import pytest
from benchmate.recommendations import validate_next, next_schema
from benchmate.menu import measurement_menu
from benchmate.physics import Acquisition
from benchmate.agent import ToolRejected
from test_agent import make_session, report


def choice(**changes):
    return {'kind':'menu_action','action':'sine_f0_a1.0_s0_l0','requirement':'',
            'reason':'Check the large-signal response again.',**changes}


@pytest.mark.parametrize('value',[
    'Run a 0.2 V sine centered at 1.2 V reference.',
    choice(action='sine_ref_1.2'),choice(ref_v=1.2),choice(settings={'ref_v':1.2}),
    choice(requirement='adjustable_reference'),choice(kind='unavailable'),
    choice(kind='unavailable',action='',requirement='invented_equipment'),
    choice(reason=''),choice(reason='x'*321),choice(action=[]),
])
def test_unchecked_or_custom_instructions_are_rejected(value):
    with pytest.raises(ValueError):validate_next(value,measurement_menu())


def test_menu_is_the_only_source_of_executable_settings():
    menu=measurement_menu();original=deepcopy(menu)
    value=choice(reason='Model commentary could mention 1.2 V REF, but cannot override the selected action.')
    result=validate_next(value,menu)
    assert result['settings']==menu[value['action']].to_dict()
    assert result['settings']['ref_v']==1.6 and '1.2' not in result['instruction']
    assert result['execution']=='not_scheduled' and not result['hardware_calibrated']
    assert menu==original
    assert set(next_schema(menu)['properties']['action']['enum'])=={'',*menu}
    with pytest.raises(ValueError,match='fixed fixture REF'):
        validate_next(choice(action='bad'),{'bad':Acquisition(ref_v=1.2)})


def test_missing_reference_capability_is_explicit_and_has_no_action_settings():
    result=validate_next(choice(kind='unavailable',action='',requirement='adjustable_reference'),measurement_menu())
    assert result['status']=='unavailable' and 'settings' not in result
    assert 'Unavailable with this fixture' in result['instruction']
    assert 'fixed near 1.6 V' in result['instruction']


def test_invalid_final_suggestion_can_be_corrected_without_acquiring(tmp_path):
    session,calls=make_session(tmp_path)
    session.dispatch('inspect_experiment',{})
    bad=report();bad['next_observation']='Move REF to 1.2 V.'
    with pytest.raises(ToolRejected,match='next_observation'):
        session.dispatch('finish_report',bad)
    assert session.report is None and len(calls)==1
    session.dispatch('finish_report',report())
    assert session.report['next_measurement']['status']=='menu_checked'
    assert len(calls)==1
