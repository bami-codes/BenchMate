#!/usr/bin/env python3
"""Bounded unloaded B5 rehearsal/live runner. Defaults to mock + scripted.

The scripted provider is explicitly a software check, never Spark evidence.
--provider meta uses Spark max and at most eight paid requests. No retries.
Physical mode requires fresh explicit operator reports and remote prediction
publication; it never treats a mock confirmation as a physical action.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time
import uuid

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from benchmate.agent import drive_agent
from benchmate.b5_session import B5Session, PROMPT, PROTOCOL
from benchmate.b5_bench import MockB5Bench, PhysicalB5Bench
from benchmate.providers import MetaToolSession, ProviderError
from benchmate.records import Recorder, canonical
from benchmate.config import load_keys, redact


class ScriptedProvider:
    def __init__(self):
        self.i=0
        self.calls=[('inspect_bench',{}),('measure',{'action':'resistor_control','reason':'Scripted ADC path check'}),
                    ('prepare_specimen',{}),('measure',{'action':'amplitude_sweep','reason':'Scripted amplitude comparison'}),
                    ('propose_netlist',{'elements':[
                        dict(name='R1',kind='R',a='IN',b='OUT',value=10000.,model='none'),
                        dict(name='D1',kind='D',a='OUT',b='REF',value=0.,model='generic_diode')],
                        'rationale':'Scripted software-test proposal; not authored by Spark.'}),
                    ('verify_proposal',{}),('finish_report',{'verdict':'verified',
                        'explanation':'Scripted mock integration test completed. No physical or Spark evidence.',
                        'limits':'Unloaded behavioral check only; no unique parameters or topology.'})]
    def next_call(self):
        if self.i>=len(self.calls):raise RuntimeError('Scripted path stopped; do not fabricate a pass')
        name,args=self.calls[self.i];self.i+=1
        return {'call_id':str(self.i),'name':name,'arguments':json.dumps(args)}
    def submit_result(self,*args):pass
    def sanitize(self,value):return value
    def metadata(self):return {'provider':'scripted','http_requests':0,'Spark_authored':False}
    def close(self):pass


def publish(log, frozen, digest, remote):
    path=log.path/'predictions-frozen.json'
    path.write_bytes(canonical(frozen)+b'\n')
    if not remote:return {'sha256':digest,'published':True,'remote':False,'scope':'Local software rehearsal only'}
    def git(*args):
        return subprocess.check_output(['git',*args],cwd=ROOT,text=True,stderr=subprocess.STDOUT).strip()
    if git('diff','--cached','--name-only'):raise ValueError('Existing staged changes; prediction publication stopped')
    if git('remote','get-url','origin') not in ('https://github.com/bami-codes/BenchMate.git','https://github.com/bami-codes/BenchMate','git@github.com:bami-codes/BenchMate.git'):
        raise ValueError('Unexpected publication destination')
    raw=path.read_text();keys=load_keys(str(ROOT/'.env'))
    if redact(raw,keys)!=raw:raise ValueError('Secret scan rejected prediction file')
    if any(x in raw.lower() for x in ('bearer ','private key','model_api_key','baseten_api_key')):
        raise ValueError('Credential pattern in prediction file')
    relative=Path('examples/b5-unloaded-freezes')/log.path.name/'predictions.json'
    destination=ROOT/relative;destination.parent.mkdir(parents=True,exist_ok=False)
    destination.write_text(raw)
    git('add','--',str(relative))
    if git('diff','--cached','--name-only')!=str(relative):raise ValueError('Unexpected staged path')
    git('diff','--cached','--check')
    git('commit','-m','Freeze unloaded B5 predictions before reserved acquisition')
    commit=git('rev-parse','HEAD');git('push','origin','HEAD:main')
    if git('ls-remote','origin','refs/heads/main').split()[0]!=commit:raise ValueError('Remote commit not confirmed')
    return {'sha256':digest,'published':True,'remote':True,'commit':commit,'path':str(relative),
            'url':f'https://github.com/bami-codes/BenchMate/blob/{commit}/{relative}'}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--bench',choices=['mock','physical'],default='mock')
    p.add_argument('--provider',choices=['scripted','meta'],default='scripted')
    p.add_argument('--publish-freeze',action='store_true')
    p.add_argument('--protocol');p.add_argument('--initial-report')
    p.add_argument('--output',default=str(ROOT/'runs/b5-unloaded'))
    args=p.parse_args()
    if args.bench=='physical' and (not args.protocol or not args.initial_report or not args.publish_freeze or args.provider!='meta'):
        p.error('Physical mode needs protocol, explicit report, Meta provider and remote freeze publication')
    log=Recorder(args.output,mode=f'{args.provider}_unloaded_B5_{args.bench}')
    sources={str(path.relative_to(ROOT)):hashlib.sha256(path.read_bytes()).hexdigest() for path in sorted((ROOT/'src/benchmate').glob('*.py'))}
    sources['scripts/b5_unloaded.py']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    log.add('b5_source_manifest',{'sha256':sources,'protocol_sha256':hashlib.sha256(canonical(PROTOCOL)).hexdigest()})
    for rel in sources:
        path=log.path/'source'/rel;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes((ROOT/rel).read_bytes())
    print(json.dumps({'stage':'started','record':str(log.path),'bench':args.bench,'provider':args.provider}),flush=True)
    def confirm(fixture):
        request_id=uuid.uuid4().hex
        request={'request_id':request_id,'fixture':fixture,'USB_off_required':True,
                 'instruction':'USB를 뽑고 LED가 꺼진 뒤 1N4148의 띠 없는 쪽을 미니보드 D8(OUT), 띠 있는 쪽을 D13(REF)에 설치한다. C 두 개와 OUT 부하·IN 분기는 계속 없고, 저항·11/14번 우회 점퍼·나머지 배선을 유지한다. 무전원에서 D8↔큰 보드 E30, D13↔큰 보드 D50 통전을 확인한다. 프로브를 제거한 뒤 같은 USB 포트로 연결한다.',
                 'response_file':'operator-response-'+request_id+'.json'}
        log.add('operator_action_requested',request)
        (log.path/'operator-request.json').write_text(json.dumps(request,ensure_ascii=False,indent=2)+'\n')
        print(json.dumps({'stage':'awaiting_operator','request_file':str(log.path/'operator-request.json')}),flush=True)
        response=log.path/request['response_file'];deadline=time.monotonic()+1800
        while not response.exists():
            if time.monotonic()>deadline:raise ValueError('Operator timeout; no automatic approval')
            time.sleep(.5)
        report=json.loads(response.read_text())
        if report.get('request_id')!=request_id or report.get('cancelled') is True:raise ValueError('Unmatched/cancelled operator response')
        return report
    model=bench=None
    try:
        if args.bench=='mock':bench=MockB5Bench(log)
        else:
            protocol=json.loads(Path(args.protocol).read_text());report=json.loads(Path(args.initial_report).read_text())
            if protocol.get('b5_protocol')!=PROTOCOL:raise ValueError('Frozen unloaded protocol mismatch')
            for rel,digest in protocol['source_sha256'].items():
                if sources.get(rel)!=digest:raise ValueError('Source changed after protocol freeze')
            if set(protocol['source_sha256'])!=set(sources):raise ValueError('Incomplete source freeze')
            if report.get('fixture')!='resistor_only' or report.get('USB_off_wiring_confirmed') is not True or report.get('USB_connected') is not True:
                raise ValueError('Fresh resistor-control confirmation required before provider request')
            bench=PhysicalB5Bench(protocol,log,confirm,initial_report=report,previous_boot_id=protocol['previous_boot_id'])
        session=B5Session(bench,log,lambda f,d:publish(log,f,d,args.publish_freeze))
        model=ScriptedProvider() if args.provider=='scripted' else MetaToolSession(
            prompt=PROMPT,tools=session.tools,log=log,effort='max',max_requests=8,max_output_tokens=8192,max_payload_bytes=128000,
            env_path=str(ROOT/'.env'),budget_path=str(ROOT/'.private/api-budget.json'))
        result=model.sanitize({**drive_agent(session,model),**model.metadata()})
        (log.path/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');log.add('run_completed',result)
        print(json.dumps({'stage':'completed','record':str(log.path),**result},ensure_ascii=False),flush=True)
    except (Exception,KeyboardInterrupt) as exc:
        message=str(exc) if isinstance(exc,(ValueError,ProviderError)) else type(exc).__name__
        failure={'error':message,'source':args.bench,'automatic_retry':False}
        if bench is not None:failure['instrument']=bench.metadata()
        if model is not None:failure=model.sanitize({**failure,**model.metadata()})
        log.add('run_failed',failure);print(json.dumps({'stage':'failed','record':str(log.path),**failure}),flush=True)
        raise SystemExit(1)
    finally:
        if model:model.close()


if __name__=='__main__':main()
