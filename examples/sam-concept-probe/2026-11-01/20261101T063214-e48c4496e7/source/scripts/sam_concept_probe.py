#!/usr/bin/env python3
"""Separate preregistered SAM prompt experiment, exactly three concepts.

No Spark call, hardware IO, prompt selection after seeing results or retries.
The original generic-capacitor miss remains unchanged evidence.
"""
import argparse
import json
from pathlib import Path
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'));sys.path.insert(0,str(ROOT/'src'))
import photo_model_probe as shared
from benchmate.records import Recorder,canonical

CONCEPTS=('blue capacitor','blue rectangular component','film capacitor')
IMAGE='examples/photo-probe-input/2026-11-01/prepared/image-01.png'
IMAGE_SHA='9c5482333974f097e1cdb4f7575f7f13eb6692b8db9b6d14d63296c2f6df9d34'
SOURCES=('scripts/sam_concept_probe.py',)+shared.SOURCES

def payload(image,concept):return shared.sam_payload(image,concept,allowed_concepts=CONCEPTS)

def freeze(output):
    image=(ROOT/IMAGE).read_bytes()
    if shared.sha(image)!=IMAGE_SHA or shared.sanitize_image(image)[0]!=image:raise ValueError('Exact previously cleaned image required')
    out=Path(output);out.mkdir(parents=True,exist_ok=False);(out/'input.png').write_bytes(image)
    plan={'schema':'benchmate.sam_prompt_specificity.v1','experiment':'new_prompt_specificity_experiment',
        'not_a_retry_of':'examples/photo-model-probe/2026-11-01/20261101T001812-2e9c1094fe',
        'original_generic_capacitor_result':'0 matches; unchanged and retained',
        'destination':shared.ENDPOINT,'model':'sam-3.1','concepts':list(CONCEPTS),'requests_max':3,
        'image_sha256':IMAGE_SHA,'source_files':{p:shared.sha((ROOT/p).read_bytes()) for p in SOURCES},
        'sam':{c:{'payload_without_image':payload(b'',c),'payload_sha256':shared.sha(canonical(payload(image,c)))} for c in CONCEPTS},
        'hardware_IO':False,'automatic_retry':False,'Spark_requests':0,
        'analysis_plan':'Run all three once in this order. Decode and show every mask/miss/false positive without manual edits or choosing a new prompt. One development image, no pixel ground truth. Do not infer extra-capacitor identity, wiring, diagnosis or reliability.',
        'scope':'Optional display feasibility only; SAM is not required for B5 or D01 repair.',
        'exclusions':['GPS/EXIF','original phone files','other photos','assembly truth','prior ADC/results','local paths','answer key']}
    shared.save(out/'plan.json',plan)
    print(json.dumps({'plan':str(out/'plan.json'),'sha256':shared.sha((out/'plan.json').read_bytes()),'requests_max':3,'hardware_IO':False}))

def execute(plan_path,digest,commit,output):
    path=Path(plan_path).resolve();plan=json.loads(path.read_text());image=(path.parent/'input.png').read_bytes()
    if (shared.sha(path.read_bytes())!=digest or plan['concepts']!=list(CONCEPTS) or plan['requests_max']!=3
        or plan['destination']!=shared.ENDPOINT or shared.sha(image)!=IMAGE_SHA or shared.sanitize_image(image)[0]!=image):
        raise ValueError('Reviewed frozen plan/image required')
    if set(plan['source_files'])!=set(SOURCES):raise ValueError('Incomplete source freeze')
    for p,h in plan['source_files'].items():
        if shared.sha((ROOT/p).read_bytes())!=h:raise ValueError('Source changed after freeze')
    for c in CONCEPTS:
        if shared.sha(canonical(payload(image,c)))!=plan['sam'][c]['payload_sha256']:raise ValueError('Payload changed')
    # Read-only proof of preregistration; no API request until the plan is remote.
    def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT,stderr=subprocess.PIPE)
    if len(commit)!=40 or any(c not in '0123456789abcdef' for c in commit):raise ValueError('Exact publication commit required')
    if git('remote','get-url','origin').decode().strip() not in ('https://github.com/bami-codes/BenchMate.git','https://github.com/bami-codes/BenchMate'):
        raise ValueError('Unexpected publication repository')
    if git('ls-remote','origin','refs/heads/main').decode().split()[0]!=commit:raise ValueError('Remote preregistration is not verified')
    if git('show',commit+':'+str(path.relative_to(ROOT)))!=path.read_bytes():raise ValueError('Plan differs from published bytes')
    with (path.parent/'execution-receipt.json').open('x') as f:json.dump({'plan_sha256':digest,'preregistered_commit':commit,'attempt_started':True},f)
    log=Recorder(output,mode='sam_prompt_specificity_new_experiment');shared.save(log.path/'plan.json',plan)
    (log.path/'input.png').write_bytes(image)
    for p in SOURCES:
        target=log.path/'source'/p;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes((ROOT/p).read_bytes())
    log.add('new_sam_experiment_preregistered',{'plan_sha256':digest,'commit':commit,**plan})
    outcomes=[];print(json.dumps({'stage':'started','record':str(log.path)}),flush=True)
    for concept in CONCEPTS:
        run,result=shared.sam_attempt(image,concept,output=log.path/'sam',allowed_concepts=CONCEPTS)
        outcomes.append({'task':'sam_'+concept,'run':str(run.relative_to(log.path)),**result})
        log.add('segmentation_finished',outcomes[-1]);print(json.dumps(outcomes[-1]),flush=True)
    result={'requests':sum(x['requests'] for x in outcomes),'outcomes':outcomes,'all_attempts_retained':True,'hardware_IO':False,
        'experiment':'new_prompt_specificity_experiment','automatic_retry':False}
    shared.save(log.path/'result.json',result);log.add('run_completed',result)
    print(json.dumps({'stage':'completed','record':str(log.path),'requests':result['requests']}),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='command',required=True)
    s=sub.add_parser('freeze');s.add_argument('--output',required=True)
    s=sub.add_parser('execute');s.add_argument('--plan',required=True);s.add_argument('--plan-sha256',required=True)
    s.add_argument('--preregistered-commit',required=True);s.add_argument('--output',default=str(ROOT/'runs/sam-concept-probe'))
    args=p.parse_args()
    if args.command=='freeze':freeze(args.output)
    else:execute(args.plan,args.plan_sha256,args.preregistered_commit,args.output)
