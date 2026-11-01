"""Repair-run Story/Evidence presentation: mock labels, frozen prediction first, no reconstructed curves."""
import json
from pathlib import Path
import shutil
import subprocess
import pytest
from benchmate.records import read_events
from benchmate.viewer import load_record

ROOT=Path(__file__).resolve().parents[1]
RUN=ROOT/'examples/d01-repair-rehearsal/2026-11-01/final_success/20261101T003829-400778438d'


def evaluate(events,cursor,expression='view',selection=None,translations=None):
    if not shutil.which('node'):pytest.skip('node is required for reducer checks')
    script="""const fs=require('fs'),vm=require('vm');
const input=JSON.parse(fs.readFileSync(0,'utf8'));
const source=fs.readFileSync(input.source,'utf8');
const value=vm.runInNewContext(source+';const view=physicalRCView(events,cursor,selection);JSON.stringify('+input.expression+')',
  {events:input.events,cursor:input.cursor,selection:input.selection,translations:input.translations});
process.stdout.write(value);"""
    result=subprocess.run(['node','-e',script],input=json.dumps({'source':str(ROOT/'src/benchmate/viewer_physical.js'),
        'events':events,'cursor':cursor,'selection':selection,'expression':expression,'translations':translations or {}}),
        text=True,capture_output=True,check=True,timeout=15)
    return json.loads(result.stdout)


@pytest.fixture
def events():return read_events(RUN)


def index(events,kind):return next(i for i,e in enumerate(events) if e['kind']==kind)


def test_mock_repair_is_labelled_as_rehearsal_and_completes(events):
    view=evaluate(events,len(events)-1)
    assert view['repair'] and view['scripted'] and view['origin']=='mock'
    assert view['status']=='Repair verified within declared RC alternatives'
    story=evaluate(events,len(events)-1,'physicalProductStory(view)')
    assert story['complete'] and 'Spark' not in story['title'] and 'Not a physical repair' in story['limits']
    assert story['lock']['sha256']==events[index(events,'repair_prediction_frozen')]['payload']['sha256'] and not story['lock']['remote']
    assert '0.49 mV step ✓' in story['metrics'] and '11.39 mV step ✗' in story['metrics'] and '4.20 mV 4 Hz sine ✓' in story['metrics']
    assert story['forecast'].startswith('Forecast published before the repair') and '0.56 mV ✓' in story['forecast']


def test_no_lock_or_repair_claim_before_the_prediction_is_frozen(events):
    before=index(events,'repair_prediction_frozen')-1
    story=evaluate(events,before,'physicalProductStory(view)')
    assert story['lock'] is None and not story['complete'] and story['title']=='Capacitance changed. Now repair it.'
    view=evaluate(events,before)
    assert view['repaired']==[] and 'repair' not in view['status'].lower()


def test_post_repair_curves_are_the_recorded_frozen_predictions(events):
    first=index(events,'repair_prediction_comparison')
    view=evaluate(events,first)
    assert view['focus']['phase']=='repair_step'
    keys=[s['key'] for s in view['series']]
    assert keys==['observed','drive','baseline','predicted']
    baseline=events[first-1]['payload']['baseline']['output_v']
    recorded=events[first]['payload']['conditional']['restored_nominal']['prediction']['predicted_output_v']
    assert view['series'][3]['y']==pytest.approx([v-baseline for v in recorded])
    acquired=evaluate(events,first-1)
    assert [s['key'] for s in acquired['series']]==['observed','drive']


def test_translation_sidecar_is_pinned_to_event_hash_and_original(tmp_path,events):
    run=tmp_path/'run';shutil.copytree(RUN,run)
    frozen=index(events,'repair_prediction_frozen');hashed=load_record(RUN)['events']
    entry={'event_sequence':frozen,'event_sha256':hashed[frozen]['sha256'],'field':'reason',
        'original':events[frozen]['payload']['reason'],'english':'Reading aid.'}
    (run/'translations.json').write_text(json.dumps({'entries':[entry]}))
    assert load_record(run)['translations']=={str(frozen):'Reading aid.'}
    story=evaluate(events,len(events)-1,'physicalProductStory(view,translations)',translations={str(frozen):'Reading aid.'})
    assert story['explanation']=='Reading aid.' and story['reasonTranslated'] and story['reasonOriginal']==entry['original']
    (run/'translations.json').write_text(json.dumps({'entries':[{**entry,'original':'changed'}]}))
    with pytest.raises(ValueError):load_record(run)


def test_real_spark_mock_is_not_mislabelled_as_scripted():
    recorded=read_events(ROOT/'examples/overnight/2026-11-02/rehearsals/d01')
    story=evaluate(recorded,len(recorded)-1,'physicalProductStory(view)')
    assert 'recorded Spark decisions' in story['limits']
    assert 'scripted decisions' not in story['limits']
    assert 'Not a physical repair' in story['limits']
