"""No paid calls: decoding ambiguity, full-view votes, isolation and mask integrity."""
from copy import deepcopy
import json
from pathlib import Path

import httpx
import pytest

from benchmate.photo_v2.decode import resistor,capacitor,aggregate,compare_resistance_path
from benchmate.photo_v2.vision import validate,request,read_five
from benchmate.image_archive import verify_clean_png
from benchmate.records import read_events


def surface(colors=None,text=None,kind='R',axis='horizontal'):
    return {'kind':kind,'kind_confidence':.6,'appearance':'Observed package',
      'markings':[{'text':text,'alternatives':[],'confidence':.6}] if text else [],
      'band_axis':axis,'bands':[{'color':c,'alternatives':[],'confidence':.6} for c in colors or []],
      'uncertainties':[]}


def view(s,flipped=False):return {'status':'completed','surface':s,'flipped':flipped}


@pytest.mark.parametrize('colors,value',[
 (['yellow','violet','red','gold'],4700),
 (['yellow','violet','black','brown','brown'],4700),
 (['yellow','violet','black','brown','brown','red'],4700)])
def test_four_five_six_band_both_directions(colors,value):
    assert any(x['value_si']==value for x in resistor(colors))
    assert any(x['value_si']==value for x in resistor(colors[::-1]))


def test_non_preferred_value_is_not_replaced_by_standard_value():
    assert any(x['value_si']==5020 for x in resistor(['green','black','red','brown','brown']))


def test_ambiguous_first_band_alternatives_not_discarded():
    s=surface(['yellow','violet','black','brown','brown']);s['bands'][0]['alternatives']=['green']
    a=aggregate([view(s) for _ in range(5)])
    assert a['value_si']==4700 and a['vote_count']==5
    assert {x['value_si'] for x in a['candidates']} >= {4700,5700}
    assert a['agreement_is_not_accuracy'] and not a['measurement_verified']


def test_tied_votes_keep_both_candidates_even_with_one_display_value():
    a=surface(['yellow','violet','black','brown','brown']);b=surface(['green','violet','black','brown','brown'])
    out=aggregate([view(a),view(a),view(b),view(b),view(surface(kind='unknown'))])
    assert out['ties'] and out['vote_count']==2 and len(out['tied_candidates'])>=2
    assert {c['value_si'] for c in out['tied_candidates']} >= {4700,5700}


def test_mirror_index_is_normalized_for_band_tallies():
    colors=['yellow','violet','black','brown','brown']
    out=aggregate([view(surface(colors)),view(surface(colors[::-1]),True)])
    assert out['value_si']==4700
    assert out['band_votes'][0]['votes']=={'yellow':2}


def test_no_invented_band_majority_sequence_becomes_the_representative():
    sequences=[['yellow','violet','black','brown','brown'],['yellow','blue','brown','brown','brown'],
               ['green','violet','brown','brown','brown']]
    out=aggregate([view(surface(x)) for x in sequences])
    majority_value=4710 # yellow/violet/brown/brown/brown, observed by none
    assert out['value_si']!=majority_value
    assert all(x['value_si']!=majority_value for x in out['candidates'])


def test_unreadable_does_not_force_a_number():
    out=aggregate([view(surface(kind='unknown')) for _ in range(5)])
    assert out['value_si'] is None and out['vote_count']==0


@pytest.mark.parametrize('text,value',[('105J100',1e-6),('104K',1e-7),('474',470e-9),('1uF',1e-6),('479',4.7e-12)])
def test_cap_codes_are_calculated_from_observed_text(text,value):
    rows=capacitor(text,'C');assert len(rows)==1 and rows[0]['value_si']==pytest.approx(value)


def test_uncertain_type_does_not_destroy_marking_but_voltage_is_not_verified():
    c=capacitor('105J100','unknown')[0]
    assert c['conditional_component_kind'] and c['tolerance_fraction']==.05
    assert c['voltage_v_candidate']==100 and not c['voltage_verified']
    assert capacitor('BC547B','Q')==[] and capacitor('547','Q')==[]
    assert capacitor('105100','C')==[]


def test_effective_series_path_does_not_verify_individual_photo_resistor():
    a=aggregate([view(surface(['yellow','violet','black','brown','brown']))])
    out=compare_resistance_path(a,25158,component_binding_confirmed=True)
    assert not out['measurement_verified'] and out['conditional_remaining_series_ohm']==[20458]


def test_surface_schema_has_no_value_field_and_does_not_require_ports():
    s=surface(text='105J100',kind='unknown');assert validate(s)==s
    with pytest.raises(ValueError):validate({**s,'value_si':1e-6})


def test_native_request_is_hint_free_and_keeps_literal_uncertainty(tmp_path,monkeypatch):
    from PIL import Image
    import io
    monkeypatch.delenv('MODEL_API_KEY',raising=False)
    env=tmp_path/'.env';env.write_text('MODEL_API_KEY=fake-photo-v2-test-secret\n')
    image=Image.new('RGB',(40,20),'white');buffer=io.BytesIO();image.save(buffer,format='PNG');raw=buffer.getvalue()
    s=surface(text='105J100',kind='unknown');bodies=[]
    def handler(req):
        p=json.loads(req.content);bodies.append(p)
        assert len(p['input'])==1 and len(p['input'][0]['content'])==2
        assert 'value_si' not in json.dumps(p['tools']) and 'IN/OUT' not in p['input'][0]['content'][0]['text']
        return httpx.Response(200,json={'status':'completed','usage':{},'output':[{'type':'function_call','name':'report_surface','arguments':json.dumps(s)}]})
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        run,result=request(raw,output=tmp_path/'runs',env_path=env,budget_path=tmp_path/'budget.json',client=client)
    assert len(bodies)==1 and result['surface']==s
    assert read_events(run)[-1]['kind']=='run_completed'
    assert 'fake-photo-v2-test-secret' not in (run/'events.jsonl').read_text()


def test_exactly_five_independent_requests_and_view_pairing(tmp_path):
    import hashlib
    component={'id':'p','views':[]};calls=[]
    for name in ['baseline','clahe','board_wb','upscale','mirror']:
        data=name.encode();(tmp_path/(name+'.png')).write_bytes(data)
        component['views'].append({'name':name,'file':name+'.png','sha256':hashlib.sha256(data).hexdigest(),'flipped':name=='mirror'})
    def requester(raw,*,output,**kw):
        calls.append(raw);output.mkdir(parents=True);return output,{'status':'completed','surface':surface(kind='unknown')}
    result=read_five(component,tmp_path,env_path='not-read',budget_path='not-read',requester=requester)
    assert len(calls)==5 and len(result)==5
    assert [x['view_name'] for x in result]==[x['name'] for x in component['views']]


def test_parallel_reader_rejects_changed_image_before_that_request(tmp_path):
    c={'id':'p','views':[{'name':'x'+str(i),'file':'missing','sha256':'0'*64,'flipped':False} for i in range(5)]}
    def denied(*a,**k):pytest.fail('Changed image sent')
    with pytest.raises(FileNotFoundError):read_five(c,tmp_path,env_path='',budget_path='',requester=denied)


def test_invalid_last_view_prevents_every_request(tmp_path):
    import hashlib
    (tmp_path/'ok').write_bytes(b'ok')
    c={'id':'p','views':[{'name':str(i),'file':'ok','sha256':hashlib.sha256(b'ok').hexdigest(),'flipped':False} for i in range(5)]}
    c['views'][-1]['sha256']='0'*64
    def denied(*a,**k):pytest.fail('A request began before all inputs checked')
    with pytest.raises(ValueError,match='Frozen view changed'):read_five(c,tmp_path,env_path='',budget_path='',requester=denied)


def test_development_photo_cannot_be_called_prospective(tmp_path,monkeypatch):
    from benchmate.photo_v2 import pipeline
    import hashlib
    file=tmp_path/'photo.png';file.write_bytes(b'known-development-image')
    monkeypatch.setattr(pipeline,'check_policy',lambda p:{'source_development_images':[hashlib.sha256(file.read_bytes()).hexdigest()]})
    with pytest.raises(ValueError,match='new image'):
        pipeline.prepare(file,tmp_path/'never-created','unused','prospective',True)
    assert not (tmp_path/'never-created').exists()
