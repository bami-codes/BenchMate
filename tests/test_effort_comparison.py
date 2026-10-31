import importlib.util
import json
from pathlib import Path
import pytest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('effort_comparison',ROOT/'scripts/compare_spark_effort.py')
comparison=importlib.util.module_from_spec(spec);spec.loader.exec_module(comparison)


def test_two_payloads_only_differ_in_effort_and_exclude_future_data(tmp_path):
    target=tmp_path/'plan';comparison.freeze(target)
    standard=json.loads((target/'medium-payload.json').read_text())
    maximum=json.loads((target/'max-payload.json').read_text())
    assert standard.pop('reasoning')=={'effort':'medium'}
    assert maximum.pop('reasoning')=={'effort':'max'}
    assert standard==maximum
    prompt=standard['input'][0]['content']
    snapshot=json.loads(prompt.split('Recorded tool result follows:\n')[1])
    assert snapshot['training']['tau_s']==0.021383658508343437
    assert snapshot['supported_candidates']==[] and not snapshot['verified']
    assert len(snapshot['observations'])==1 and snapshot['observations'][0]['phase']=='unloaded_step'
    assert 'I8' not in prompt and '2.998376' not in prompt
    assert comparison.ORDER.count('medium')==comparison.ORDER.count('max')==5


@pytest.mark.parametrize('name,args,expected',[
    ('measure',{'action':'attach_output_load_step','reason':'Gain distinguishes R from C.'},'attach_output_load_step'),
    ('measure',{'action':'unloaded_step','reason':'Repeat'},'unavailable_action'),
    ('measure',{'action':'attach_output_load_step','reason':''},'empty_reason'),
    ('finish_report',{'verdict':'verified','candidate':'c_changed','current_explanation':'x','unresolved':'x','next_observation':'x'},'premature_verdict'),
    ('inspect_experiment',{},'inspect_again'),
])
def test_decision_classification_never_dispatches(name,args,expected):
    assert comparison.classify({'status':'completed','output':[{'type':'function_call','name':name,'arguments':json.dumps(args)}]})==expected
