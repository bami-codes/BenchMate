import base64
from copy import deepcopy
import io
import json
from pathlib import Path
import threading

import httpx
from PIL import Image, PngImagePlugin
import pytest

from benchmate.known_design import (candidate_netlist,confirm_design,extract,nominal_rc,
    payload_for,sanitize_image,validate_candidate)
from benchmate.known_design_web import make_server
from benchmate.records import read_events


def image_bytes():
    output=io.BytesIO();Image.new('RGB',(80,60),'white').save(output,'PNG');return output.getvalue()


def candidate():
    return {'status':'needs_review','summary':'Software test fixture, not Spark output.',
        'components':[{'name':'R1','kind':'R','a':'IN','b':'OUT','value_si':10000.,'marking':'10k',
            'evidence':'Visible label','bbox':[.1,.1,.4,.3]},
            {'name':'C1','kind':'C','a':'OUT','b':'REF','value_si':1e-6,'marking':'1uF',
             'evidence':'Visible label','bbox':[.5,.3,.7,.6]}],'ambiguities':[]}


def test_metadata_is_removed_and_orientation_preserved():
    original=Image.new('RGB',(80,60),'white');exif=original.getexif();exif[274]=6;exif[270]='Private location description'
    metadata=PngImagePlugin.PngInfo();metadata.add_text('GPS','private coordinates')
    stream=io.BytesIO();original.save(stream,'PNG',exif=exif,pnginfo=metadata)
    clean,info=sanitize_image(stream.getvalue());decoded=Image.open(io.BytesIO(clean))
    assert decoded.size==(60,80) and not decoded.info and not decoded.getexif()
    assert b'Private location' not in clean and b'private coordinates' not in clean
    assert info['metadata_removed'] and info['source_sha256']!=info['sha256']


def test_unknown_value_survives_without_becoming_nominal():
    value=candidate();value['components'][1]['value_si']=None;value['status']='incomplete'
    assert validate_candidate(value)==value
    assert nominal_rc(value,'intended_schematic') is None
    assert 'unresolved connection or value' in candidate_netlist(value)


@pytest.mark.parametrize('bad',[float('nan'),float('inf'),True,-1,'10000'])
def test_bad_numeric_values_rejected(bad):
    value=candidate();value['components'][0]['value_si']=bad
    with pytest.raises(ValueError):validate_candidate(value)


def test_connections_and_source_kind_gate_nominal_design():
    value=candidate()
    assert nominal_rc(value,'intended_schematic')=={'R_ohm':10000.,'C_f':1e-6,'tau_s':.01}
    assert nominal_rc(value,'assembly_photo') is None
    value['components'][1]['a']='IN'
    assert nominal_rc(value,'intended_schematic') is None
    value=candidate();value['ambiguities']=['Connection hidden']
    assert nominal_rc(value,'intended_schematic') is None


def test_confirmation_keeps_edits_separate_and_rejects_assembly_truth():
    original={'status':'unverified_visual_candidate','source_kind':'intended_schematic','candidate':candidate()}
    edited=candidate();edited['components'][0]['value_si']=12000
    result=confirm_design(original,edited,reviewer_note='Read 12k on intended design.')
    assert result['operator_edited'] and result['nominal_design']['R_ohm']==12000
    assert original['candidate']['components'][0]['value_si']==10000
    assert not result['measurement_verified'] and not result['hardware_IO']
    with pytest.raises(ValueError):confirm_design({**original,'source_kind':'assembly_photo'},edited,reviewer_note='Checked')


def test_payload_contains_only_clean_image_and_reading_instructions():
    clean,info=sanitize_image(image_bytes());payload=payload_for(clean,'intended_schematic')
    assert payload['model']=='muse-spark-1.3' and payload['reasoning']['effort']=='max'
    assert len(payload['input'])==1 and len(payload['input'][0]['content'])==2
    parts=payload['input'][0]['content']
    assert base64.b64decode(parts[1]['image_url'].split(',')[1])==clean
    assert not any(word in json.dumps(payload) for word in ('D01','21.4','case-01','truth.json'))


@pytest.mark.parametrize('arguments,expected',[(json.dumps(candidate()),'unverified_visual_candidate'),('not json','failed')])
def test_provider_retains_raw_visible_output_and_never_retries(tmp_path,arguments,expected):
    seen=[]
    def respond(request):
        seen.append(request)
        return httpx.Response(200,json={'id':'test-only','status':'completed','usage':{},'output':[
            {'type':'reasoning','encrypted_content':'opaque-never-log'},
            {'type':'message','content':[{'type':'output_text','text':'Visible text retained exactly.'}]},
            {'type':'function_call','name':'report_design','call_id':'test','arguments':arguments}]})
    env=tmp_path/'.env';env.write_text('MODEL_API_KEY=test-fixture-key-not-real\n')
    clean,info=sanitize_image(image_bytes())
    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        path,result=extract(clean,info,'intended_schematic',output=tmp_path/'runs',env_path=env,budget_path=tmp_path/'budget.json',client=client)
    assert len(seen)==1 and result['status']==expected
    raw=(path/'events.jsonl').read_text()
    assert 'opaque-never-log' not in raw and 'test-fixture-key-not-real' not in raw
    assert 'Visible text retained exactly.' in raw
    assert (path/'arguments.txt').read_text()==arguments
    assert read_events(path)[-1]['kind']==('run_failed' if expected=='failed' else 'run_completed')


def test_server_preview_blocks_api_and_cross_origin(tmp_path):
    server=make_server(output=tmp_path/'ui',env_path=tmp_path/'.env',budget_path=tmp_path/'budget',port=0)
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    try:
        base=f'http://127.0.0.1:{server.server_port}'
        with httpx.Client(base_url=base) as client:
            html=client.get('/').text
            token=html.split('name="benchmate-session" content="')[1].split('"')[0]
            headers={'X-BenchMate-Session':token,'Origin':base}
            assert client.get('/state').json()['api_enabled'] is False
            payload={'image_base64':base64.b64encode(image_bytes()).decode(),'source_kind':'intended_schematic'}
            assert client.post('/prepare',json=payload,headers={'Origin':'https://unrelated.example'}).status_code==403
            image=client.post('/prepare',json=payload,headers=headers).json()
            response=client.post('/extract',json={'id':image['id']},headers=headers)
            assert response.status_code==400 and 'disabled' in response.json()['error']
            assert not (tmp_path/'budget').exists()
    finally:server.shutdown();server.server_close();thread.join()


def test_server_enforces_attempt_limit_and_one_attempt_per_image(tmp_path):
    calls=[]
    def fake_extract(*args,**kwargs):
        calls.append(args);path=tmp_path/f'fake-{len(calls)}';path.mkdir()
        return path,{'status':'failed','error':'TEST FIXTURE','requests':0,'hardware_IO':False}
    server=make_server(output=tmp_path/'ui',env_path=tmp_path/'.env',budget_path=tmp_path/'budget',port=0,
        enable_api=True,max_requests=1,extractor=fake_extract)
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    try:
        base=f'http://127.0.0.1:{server.server_port}'
        with httpx.Client(base_url=base) as client:
            token=client.get('/').text.split('name="benchmate-session" content="')[1].split('"')[0]
            headers={'X-BenchMate-Session':token,'Origin':base}
            payload={'image_base64':base64.b64encode(image_bytes()).decode(),'source_kind':'intended_schematic'}
            image=client.post('/prepare',json=payload,headers=headers).json()
            assert client.post('/extract',json={'id':image['id']},headers=headers).status_code==200
            assert client.post('/extract',json={'id':image['id']},headers=headers).status_code==400
            payload['source_kind']='assembly_photo';other=client.post('/prepare',json=payload,headers=headers).json()
            assert client.post('/extract',json={'id':other['id']},headers=headers).status_code==400
            assert len(calls)==1
    finally:server.shutdown();server.server_close();thread.join()
