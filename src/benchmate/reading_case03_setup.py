"""Prospective case03 scope; physical numerical/candidate stages are additive."""
import argparse
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[2]


def declare(record):
    sys.path.insert(0,str(ROOT))
    from scripts import reading_experiment as r
    from .channel_timing_followup_v4 import qualification
    log=r.open_pair(record,['awaiting_schematic_intake']);q=qualification()
    if log.control['case_id']!='03' or any(e['kind']=='case03_workflow_scope_frozen' for e in r.decode_events(log.file.read_bytes(),require_terminal=False)):
        raise ValueError('Declare03 exactly once before its fresh schematic intake.')
    names=['src/benchmate/reading_case03_setup.py','docs/2026-11-04-reading-case03-start.md',
           'src/benchmate/channel_timing_v4.py','src/benchmate/channel_timing_session_v4.py','src/benchmate/reading_candidates_v3.py']
    value={'schema':'benchmate.case03_workflow_scope.v4','source_sha256':{n:r.sha(ROOT/n) for n in names},
        'timing_qualification':'examples/channel-timing/2026-11-04/candidate02/manifest.json',
        'timing_qualification_sha256':r.sha(ROOT/'examples/channel-timing/2026-11-04/candidate02/manifest.json'),
        'before_schematic_intake':True,'before_physical_stimulus':True,
        'numerical_and_reading_profiles':'Same qualified v4 backend; staged adapter published before hardware.',
        'photo_binding':'v3 candidate set/kind and nullable reference; no surface values; ambiguous bodies are not operator truth labels.',
        'restored_consistent_binding':'Prospectively omit Spark reference/value request; restored SAM is visual only.',
        'later_stage_extensions':'Version, qualify and publish before the corresponding paid/physical/observation stage.',
        'calls_planned_max':{'Spark':19,'SAM':2},'automatic_retry':False}
    r.save(log.path/'case03-workflow-scope.json',value)
    public=r.PUBLIC/'case03-scopes'/log.path.name/'scope.json';r.save(ROOT/public,value)
    log.add('case03_workflow_scope_frozen',{'file':'case03-workflow-scope.json','sha256':r.sha(log.path/'case03-workflow-scope.json'),
        'public_manifest':str(public),'before_schematic_intake':True,'before_physical_stimulus':True})
    print(json.dumps({'record':str(log.path),'public_scope':str(public),'Spark_requests':0,'hardware_commands':0}))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('record');declare(p.parse_args().record)
