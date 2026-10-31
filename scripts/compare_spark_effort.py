#!/usr/bin/env python3
"""Decision-only replay: five medium and five max requests, never hardware IO.

Freeze writes the exact two payloads and order. Execute requires the plan hash,
unchanged source files and an exclusive receipt; no retries or tool execution.
"""
import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1];sys.path.insert(0, str(ROOT/'src'))
import httpx
from benchmate.config import load_keys, redact
from benchmate.providers import PROVIDERS, ProviderError, reserve_budget
from benchmate.records import Recorder
from benchmate.viewer import load_record
from benchmate.physical_rc import TOOLS

SOURCE = 'examples/hardware-spark-rc/2026-10-30/20261029T174402-d3eaa8e612/execution'
SOURCE_SHA = '12ae389d77876283f62f520239ea4806a5dc77925c8bbe25708833922d29603f'
ORDER = ['medium','max','max','medium','medium','max','max','medium','medium','max']
PROMPT = '''This is a decision-only REPLAY of a recorded BenchMate experiment.
No hardware is connected to this conversation. Tool calls will be recorded,
not executed. Choose the next action at the supplied snapshot by returning
exactly one tool call and a concise Korean reason where the tool accepts one.
The experiment has already been inspected and its unloaded training step has
completed. The attached snapshot is its unchanged historical tool result.
Choose among the currently available actions, or abstain if the evidence is
insufficient to act. Do not assume any later measurement or assembly truth.

The declared alternatives are nominal RC, R changed with C nominal, and C
changed with R nominal. The common engineering allowance is 9 mV RMS for the
whole waveform AND each region, not a calibrated confidence interval.
Measurement tools represent fixed allowed experiments; physical rewiring
would require a human. Report neither a unique fault nor completed repair
from evidence that does not establish it. Verification and a verified final
report are only available after the required observations.
The task is to choose the next experiment, not to solve an unseen waveform.

Recorded tool result follows:
'''


def digest(raw):return hashlib.sha256(raw).hexdigest()
def encode(value):return (json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n').encode()


def freeze(destination):
    record = load_record(ROOT/SOURCE)
    if record['source_sha256'] != SOURCE_SHA:raise ValueError('D01 source changed')
    event = record['events'][50]
    if event['kind'] != 'tool_result' or event['payload']['name'] != 'measure':
        raise ValueError('Expected pre-load observation')
    snapshot = event['payload']['result']
    assert snapshot['allowed_measurements'] == ['attach_output_load_step','repeat_unloaded_step']
    tools = deepcopy(TOOLS)
    for tool in tools:
        tool['description'] = 'Replay choice only; will not execute. '+tool['description']
    common = {'model':'muse-spark-1.3','store':False,'max_output_tokens':8192,
              'tools':tools,'tool_choice':'auto','parallel_tool_calls':False,
              'input':[{'role':'user','content':PROMPT+json.dumps(snapshot,ensure_ascii=False,allow_nan=False)}]}
    destination = Path(destination);destination.mkdir(parents=True,exist_ok=False)
    payloads = {}
    for effort in ('medium','max'):
        raw = encode({**common,'reasoning':{'effort':effort}})
        name = effort+'-payload.json';(destination/name).write_bytes(raw)
        payloads[effort] = {'file':name,'sha256':digest(raw)}
    source_files = ['scripts/compare_spark_effort.py','src/benchmate/providers.py','src/benchmate/config.py',
                    'src/benchmate/records.py','src/benchmate/physical_rc.py']
    plan = {'schema':'benchmate.effort_decision_replay.v1','destination':PROVIDERS['meta']['url'],
            'requests_max':10,'order':ORDER,'payloads':payloads,'fresh_context_each_request':True,
            'standard_mapping':'medium is the API effort used by the existing standard D01 run',
            'hardware_IO':False,'execute_tool_calls':False,'automatic_retry':False,
            'source_record':SOURCE,'source_sha256':SOURCE_SHA,'observation_event':50,
            'observation_event_sha256':event['sha256'],
            'source_files':{name:digest((ROOT/name).read_bytes()) for name in source_files},
            'predeclared_review':{
                'primary':'Count exact measure/attach_output_load_step calls with nonempty reason, repeats, abstentions, inspection requests and invalid outputs.',
                'reason_review':'Report whether text connects loaded gain to R, distinguishes R/C alternatives, and avoids claiming an observed result. Manual descriptive review, not a blinded score.',
                'secondary':['elapsed_s','input_tokens','output_tokens','total_tokens'],
                'limitations':['Single easy snapshot with only two available experiments; five samples per setting.',
                    'Nominal alternatives are supplied; not autonomous hypothesis discovery or a full-agent accuracy comparison.',
                    'Neutral replay prompt differs from original directed-load prompt; original hidden reasoning is not reconstructed.',
                    'No claim that max is necessary or superior unless these results support a narrow statement.'],
                'on_failure':'Retain every attempt. Stop on HTTP/network failure; do not replace or retry it.'}}
    raw = encode(plan);(destination/'plan.json').write_bytes(raw)
    print(json.dumps({'plan':str(destination/'plan.json'),'sha256':digest(raw),'requests_max':10,'hardware_IO':False}))


def classify(body):
    calls = [x for x in body.get('output',[]) if x.get('type')=='function_call']
    if body.get('status') not in (None,'completed'):return 'incomplete'
    if len(calls)!=1:return 'invalid_call_count'
    call = calls[0]
    try:args=json.loads(call['arguments'])
    except (ValueError,KeyError,TypeError):return 'invalid_arguments'
    schema = next((x['parameters'] for x in TOOLS if x['name']==call.get('name')),None)
    if schema is None or not isinstance(args,dict) or set(args)!=set(schema['required']):return 'invalid_tool_or_fields'
    for key,value in args.items():
        spec=schema['properties'][key]
        if not isinstance(value,str) or len(value)>1600 or ('enum' in spec and value not in spec['enum']):return 'invalid_arguments'
    if call['name']=='measure':
        if not args['reason'].strip():return 'empty_reason'
        return args['action'] if args['action'] in ('attach_output_load_step','repeat_unloaded_step') else 'unavailable_action'
    if call['name']=='finish_report':return 'abstained' if args['verdict']=='abstained' and not args['candidate'] else 'premature_verdict'
    return 'inspect_again' if call['name']=='inspect_experiment' else 'unavailable_verification'


def execute(plan_path, approved, output):
    path=Path(plan_path);raw=path.read_bytes();plan=json.loads(raw)
    if digest(raw)!=approved or plan['order']!=ORDER or plan['requests_max']!=10:raise ValueError('Exact frozen plan required')
    if plan['destination']!=PROVIDERS['meta']['url']:raise ValueError('Unexpected destination')
    for name,sha in plan['source_files'].items():
        if digest((ROOT/name).read_bytes())!=sha:raise ValueError('Frozen source changed: '+name)
    payloads={}
    for effort,entry in plan['payloads'].items():
        raw=(path.parent/entry['file']).read_bytes()
        if digest(raw)!=entry['sha256']:raise ValueError('Frozen payload changed')
        payloads[effort]=json.loads(raw)
    keys=load_keys(ROOT/'.env');key=keys.get(PROVIDERS['meta']['key'])
    if not key:raise ProviderError('Local Meta key unavailable')
    with (path.parent/'execution-receipt.json').open('x') as f:json.dump({'plan_sha256':approved,'attempt_started':True},f)
    log=Recorder(output,mode='live_spark_effort_comparison_on_recorded_observation')
    (log.path/'plan.json').write_bytes(path.read_bytes())
    for entry in plan['payloads'].values():(log.path/entry['file']).write_bytes((path.parent/entry['file']).read_bytes())
    log.add('comparison_plan_frozen',plan);outcomes=[];requests=0
    print(json.dumps({'stage':'started','record':str(log.path)}),flush=True)
    try:
        with httpx.Client(timeout=90,follow_redirects=False) as client:
            for index,effort in enumerate(plan['order'],1):
                reserve_budget(ROOT/'.private/api-budget.json','meta',1.);requests+=1
                log.add('request_started',{'index':index,'effort':effort,'payload_sha256':plan['payloads'][effort]['sha256']})
                start=time.monotonic()
                try:
                    response=client.post(plan['destination'],json=payloads[effort],headers={'Authorization':'Bearer '+key})
                    if response.status_code>=400:raise ProviderError('Meta HTTP '+str(response.status_code))
                    body=response.json()
                    visible=[x for x in body.get('output',[]) if x.get('type') in ('message','function_call')]
                    item=redact({'index':index,'effort':effort,'response_id':body.get('id'),
                        'status':body.get('status'),'usage':body.get('usage'),'elapsed_s':time.monotonic()-start,
                        'visible_output_verbatim':visible,'classification':classify(body)},keys)
                    (log.path/f'reply-{index:02d}-{effort}.json').write_bytes(encode(item))
                    outcomes.append(item);log.add('decision_reply',item)
                    print(json.dumps({k:item[k] for k in ('index','effort','classification','elapsed_s')}),flush=True)
                except (httpx.HTTPError,ValueError,ProviderError,TypeError,KeyError) as exc:
                    item={'index':index,'effort':effort,'classification':'request_failed',
                          'elapsed_s':time.monotonic()-start,'error':str(exc) if isinstance(exc,ProviderError) else type(exc).__name__}
                    outcomes.append(item);log.add('request_failed',item);raise ProviderError(item['error']) from None
        result={'requests':requests,'outcomes':outcomes,'hardware_IO':False,'tool_calls_executed':0,'all_attempts_retained':True}
        (log.path/'result.json').write_bytes(encode(result));log.add('run_completed',result)
        print(json.dumps({'stage':'completed','record':str(log.path),'requests':requests}),flush=True)
    except (Exception,KeyboardInterrupt) as exc:
        result={'requests':requests,'outcomes':outcomes,'hardware_IO':False,'error':type(exc).__name__,'automatic_retry':False}
        (log.path/'result.json').write_bytes(encode(result));log.add('run_failed',result)
        print(json.dumps({'stage':'failed','record':str(log.path),'requests':requests,'error':type(exc).__name__}),flush=True)
        raise SystemExit(1)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='command',required=True)
    f=sub.add_parser('freeze');f.add_argument('--output',required=True)
    e=sub.add_parser('execute');e.add_argument('--plan',required=True);e.add_argument('--approved-plan-sha256',required=True)
    e.add_argument('--output',default=str(ROOT/'runs/effort-comparison'))
    args=p.parse_args()
    if args.command=='freeze':freeze(args.output)
    else:execute(args.plan,args.approved_plan_sha256,args.output)
