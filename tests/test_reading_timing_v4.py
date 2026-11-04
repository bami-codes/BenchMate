from copy import deepcopy
import json
from pathlib import Path
import pytest

from benchmate import channel_timing_v4 as timing
from benchmate.reading_catalog_timing_v4 import build_catalog, profile
from benchmate.reading_rules import make_forecast, score_reading
from benchmate.netlist_diagnosis.menu import MENU
from scripts.timing_synthetic_v4 import analytic_capture, specimens, element
from scripts import reading_experiment_timing_v4 as runtime


DESIGN={'elements':[element('R1','R','IN','N1',10000.),element('R2','R','N1','OUT',10000.),element('C1','C','OUT','REF',1e-6)]}


@pytest.fixture(scope='module')
def catalog():
    captures=[]
    for name in ('unloaded_step_small','loaded_step_large'):
        c=analytic_capture(MENU[name],12200.,None,1e-6);c['purpose']='training';captures.append(c)
    result=timing.assess(DESIGN['elements'],captures)
    rows=[r for r in result['hypotheses'] if r['status']=='adequate']
    assert {r['id'] for r in rows}=={'changed:R1','changed:R2'}
    for row in rows:
        total=sum(e['value'] for e in row['model']['elements'] if e['kind']=='R')
        assert total==pytest.approx(12200.,rel=.05)
    frozen={'models':rows}
    verification={'survivors':[r['id'] for r in rows],'frozen_sha256':'f'*64}
    return build_catalog(DESIGN,frozen,verification,captures),captures,frozen,verification


def test_series_sum_ambiguity_and_common_backend(catalog):
    value,_,_,_=catalog
    assert value['timing_model_version']==timing.VERSION
    assert {e['id'] for e in value['explanations']}=={'changed:R1','changed:R2'}
    assert runtime.PhysicalSession.__module__=='benchmate.channel_timing_session_v4'


def test_profile_uses_new_timing_not_old_input_hold():
    _,r,rl,c,elements=specimens()[0]
    capture=analytic_capture(MENU['unloaded_step_large'],r,rl,c);capture['purpose']='training'
    row={'changed_component':'C1','model':{'elements':elements}}
    interval,rule=profile(row,'C1',[capture],.05)
    assert interval==[0.,None] and all(rule['passed'])


def test_reserved_outputs_cannot_enter_catalog(catalog):
    _,captures,frozen,verification=catalog
    bad=deepcopy(captures);bad[0]['purpose']='verification'
    with pytest.raises(ValueError,match='Only training'):build_catalog(DESIGN,frozen,verification,bad)


def test_three_free_numeric_outcomes_without_refitting(catalog):
    value,_,_,_=catalog
    rules=json.loads(Path('docs/2026-11-03-reading-rules.json').read_text())
    request={'component':'R1','quantity':'resistance','reason':'Synthetic choice to test frozen reading logic.','chosen_by':'muse_spark'}
    forecast=make_forecast(request,value,rules)
    results=[]
    for number in (2200.,10000.,6000.):
        observed={'component':'R1','quantity':'resistance','value':number,'unit':'ohm','source':'operator_dmm',
            'power_off_confirmed':True,'component_isolated_confirmed':True,'meter_range':20000.,'meter_resolution':10.,
            'photo':{'file':'synthetic-not-physical.png','sha256':'0'*64}}
        results.append(score_reading(forecast,observed))
    assert results[0]['fits']==['changed:R1']
    assert results[1]['fits']==['changed:R2']
    assert results[2]['outcome']=='all_explanations_rejected'
    assert all(r['refitted'] is False for r in results)
