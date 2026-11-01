import importlib.util
import json
from pathlib import Path
import httpx
import pytest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('photo_probe',ROOT/'scripts/photo_model_probe.py')
probe=importlib.util.module_from_spec(spec);spec.loader.exec_module(probe)


def test_sam_payload_has_only_requested_concept_and_clean_image():
    image=(ROOT/'examples/photo-probe-input/2026-11-01/prepared/image-01.png').read_bytes()
    payload=probe.sam_payload(image,'capacitor')
    assert payload['model']=='sam-3.1' and payload['stream'] is False
    assert payload['metadata']['mask_encoding']=='one_bit'
    parts=payload['input'][0]['content']
    assert len(parts)==2 and parts[0]['text']=='capacitor'
    import base64
    assert base64.b64decode(parts[1]['image_url'].split(',')[1])==image
    without_image={**payload,'input':[{'role':'user','content':[parts[0]]}]}
    assert not any(s in json.dumps(without_image) for s in ['IMG_8885','10k','1uF','GPS','D01'])
    with pytest.raises(ValueError):probe.sam_payload(image,'capacitor,resistor')


def test_freeze_and_tamper_stop_before_any_call(tmp_path):
    out=tmp_path/'plan'
    probe.freeze(ROOT/'examples/photo-probe-input/2026-11-01/prepared/manifest.json',out)
    path=out/'plan.json';digest=probe.sha(path.read_bytes());plan=json.loads(path.read_text())
    assert plan['requests_max']==3 and list(plan['sam'])==['capacitor','resistor']
    assert plan['vision']['source_kind']=='assembly_photo'
    plan['requests_max']=4;path.write_text(json.dumps(plan))
    with pytest.raises(ValueError):probe.execute(path,digest,tmp_path/'runs')
    assert not (out/'execution-receipt.json').exists()


@pytest.mark.parametrize('status,body,expected',[
    (200,{'id':'test-only','status':'completed','output':[{'type':'message','content':[{'type':'output_text','text':''}]}]},'completed'),
    (403,{'error':{'message':'test fixture denied'}},'failed'),
    (200,{'id':'test-only','status':'incomplete','output':[]},'failed'),
])
def test_sam_keeps_empty_and_failure_without_retry(tmp_path,monkeypatch,status,body,expected):
    monkeypatch.setattr(probe,'ROOT',tmp_path)
    (tmp_path/'.env').write_text('MODEL_API_KEY=software-test-only\n')
    calls=[]
    def handler(request):calls.append(request);return httpx.Response(status,json=body)
    client=httpx.Client(transport=httpx.MockTransport(handler))
    monkeypatch.setattr(probe.httpx,'Client',lambda **kwargs:client)
    run,result=probe.sam_attempt(b'test-image','resistor',output=tmp_path/'out')
    assert len(calls)==1 and result['requests']==1 and result['status']==expected
    assert 'software-test-only' not in (run/'events.jsonl').read_text()
    assert probe.read_events(run)[-1]['kind']==('run_completed' if expected=='completed' else 'run_failed')
    if expected=='completed':assert result['empty_output'] is True
