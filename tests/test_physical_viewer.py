"""Recorded physical RC presentation: no future leakage or reconstructed fits."""
import json
from pathlib import Path
import shutil
import subprocess
import pytest
from benchmate.records import read_events
from benchmate.viewer import export_viewer,load_record

ROOT=Path(__file__).resolve().parents[1]
RUN=ROOT/'examples/hardware-spark-rc/2026-10-30/20261029T174402-d3eaa8e612/execution'


def evaluate(events,cursor,expression='view',selection=None):
    if not shutil.which('node'):pytest.skip('node is required for reducer checks')
    script="""const fs=require('fs'),vm=require('vm');
const input=JSON.parse(fs.readFileSync(0,'utf8'));
const source=fs.readFileSync(input.source,'utf8');
const value=vm.runInNewContext(source+';const view=physicalRCView(events,cursor,selection);JSON.stringify('+input.expression+')',
  {events:input.events,cursor:input.cursor,selection:input.selection});
process.stdout.write(value);"""
    result=subprocess.run(['node','-e',script],input=json.dumps({'source':str(ROOT/'src/benchmate/viewer_physical.js'),
        'events':events,'cursor':cursor,'selection':selection,'expression':expression}),text=True,capture_output=True,check=True,timeout=15)
    return json.loads(result.stdout)


@pytest.fixture
def events():return read_events(RUN)


def index(events,kind,phase=None):
    return next(i for i,e in enumerate(events) if e['kind']==kind and (phase is None or e['payload'].get('phase')==phase))


def test_initial_view_does_not_claim_future_physical_evidence(events):
    view=evaluate(events,0)
    assert view['origin']=='unknown' and view['series']==[] and view['report'] is None
    assert view['verification'] is None and 'verified' not in view['status'].lower()


def test_training_trace_never_gains_a_reconstructed_curve(events):
    point=index(events,'unloaded_training_completed')
    view=evaluate(events,point)
    assert view['origin']=='hardware' and len(view['observations'])==1
    assert [s['key'] for s in view['series']]==['observed','drive']
    reading=evaluate(events,point,'physicalRCReading(view)')
    assert 'indistinguishable' in reading['explanation']


def test_reserved_plan_and_observation_do_not_leak_later_comparison(events):
    point=index(events,'physical_acquisition_plan_frozen','reserved_sine')
    view=evaluate(events,point)
    assert view['focus']['phase']=='reserved_sine' and view['series']==[]
    assert view['verification'] is None and view['report'] is None
    point=index(events,'physical_observation','reserved_sine')
    view=evaluate(events,point)
    assert {s['key'] for s in view['series']}=={'observed','drive'}
    assert view['scores'] is None


def test_exact_recorded_predictions_and_region_failure_survive_display_transform(events):
    view=evaluate(events,len(events)-1)
    assert view['report']['payload']['candidate']=='c_changed'
    assert view['verification']['payload']['passed']
    p=events[index(events,'physical_observation','reserved_sine')]['payload']
    scores=events[index(events,'physical_verification')]['payload']['scores']
    curves={s['key']:s['y'] for s in view['series']}
    expected=[v-p['baseline']['output_v'] for v in scores['c_changed']['prediction']['predicted_output_v']]
    assert curves['predicted']==expected
    for a,b,raw,pred in zip(curves['observed'],curves['predicted'],p['data']['output_v'],scores['c_changed']['prediction']['predicted_output_v']):
        assert a-b==pytest.approx(raw-pred,abs=1e-14)
    assert view['scores']['nominal_rc']['RMS_mV']<9 and not view['scores']['nominal_rc']['passed']
    assert max(r['RMS_mV'] for r in view['scores']['nominal_rc']['regions'])>9
    loaded=index(events,'physical_measurement_selected','attach_output_load_step')
    selected=evaluate(events,len(events)-1,selection=loaded)
    assert selected['focus']['phase']=='attach_output_load_step'
    assert selected['scores']['c_changed']['RMS_mV']==pytest.approx(2.9983767729458504)


def test_failed_prefix_remains_failed(events):
    point=index(events,'physical_acquisition_plan_frozen','reserved_sine')
    prefix=events[:point+1]+[{'kind':'run_failed','sequence':point+1,'payload':{'error':'constructed failure'}}]
    view=evaluate(prefix,len(prefix)-1)
    assert view['status']=='Session failed' and view['verification'] is None
    assert view['series']==[]


def test_physical_export_is_read_only_and_offline(tmp_path):
    before=(RUN/'events.jsonl').read_bytes();path=export_viewer(RUN,tmp_path/'physical.html')
    html=path.read_text()
    assert 'function physicalRCView' in html and 'Spark at the workbench' in html
    assert "connect-src 'none'" in html
    assert (RUN/'events.jsonl').read_bytes()==before
    assert load_record(RUN)['events'][-1]['payload']['instrument']['retained_frames']==7680
