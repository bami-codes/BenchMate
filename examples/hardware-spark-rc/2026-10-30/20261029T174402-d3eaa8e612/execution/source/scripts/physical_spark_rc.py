#!/usr/bin/env python3
"""One live Spark run with a bounded physical adapter and manual-wiring pause.

The operator prepares the initial known-passive fixture before invocation.
Subsequent requests appear in operator-request.json in the run directory.
The coordinating session relays the instruction and writes the exact reply
with the matching request_id. No timeout is interpreted as approval.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import time
import uuid

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from benchmate.agent import drive_agent
from benchmate.physical_rc import PhysicalRCSession,PROMPT
from benchmate.physical_bench import PhysicalBench
from benchmate.providers import MetaToolSession,ProviderError
from benchmate.records import Recorder


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--protocol',required=True)
    parser.add_argument('--initial-report',required=True)
    parser.add_argument('--previous-boot-id',required=True)
    args=parser.parse_args()
    protocol_path=Path(args.protocol);protocol=json.loads(protocol_path.read_text())
    allowed={'src/benchmate/physical_rc.py','src/benchmate/physical_bench.py','src/benchmate/measured_input.py',
             'src/benchmate/instrument.py','src/benchmate/agent.py','src/benchmate/providers.py','scripts/physical_spark_rc.py'}
    if set(protocol['source_sha256'])!=allowed:raise ValueError('Unexpected frozen source manifest')
    for rel,digest in protocol['source_sha256'].items():
        if hashlib.sha256((ROOT/rel).read_bytes()).hexdigest()!=digest:raise ValueError('Source changed after protocol freeze: '+rel)
    initial=json.loads(Path(args.initial_report).read_text())
    if initial.get('fixture')!='unloaded' or initial.get('USB_connected') is not True or initial.get('USB_off_wiring_confirmed') is not True:
        raise ValueError('Initial unloaded fixture must be confirmed before the live provider call')
    log=Recorder(ROOT/'runs/hardware-spark-rc',mode='live_spark_new_physical_RC_measurements')
    (log.path/'protocol.json').write_bytes(protocol_path.read_bytes())
    (log.path/'initial-operator-report.json').write_text(json.dumps(initial,ensure_ascii=False,indent=2)+'\n')
    for rel in allowed:
        destination=log.path/'source'/rel;destination.parent.mkdir(parents=True,exist_ok=True);destination.write_bytes((ROOT/rel).read_bytes())
    log.add('physical_run_protocol',{'protocol_sha256':hashlib.sha256(protocol_path.read_bytes()).hexdigest(),
            'source_sha256':protocol['source_sha256'],'specimen_truth_sent_to_model':False,'prior_specimen_results_sent_to_model':False,
            'new_measurements_only':True,'automatic_retry_or_rearm':False,'repair_performed':False})
    (ROOT/'runs/hardware-spark-rc-current-path.txt').write_text(str(log.path)+'\n')
    print(json.dumps({'stage':'started','record':str(log.path)}),flush=True)

    def confirm_wiring(fixture):
        if fixture!='output_load':raise ValueError('No further fixture change is allowed in this run')
        request_id=uuid.uuid4().hex
        request={'request_id':request_id,'fixture':fixture,'USB_off_required':True,
            'instruction':'USB를 뽑고 LED가 꺼지면 큰 보드 E30–A55 OUT 부하 점퍼 하나를 연결한다. A55–C35 IN 분기는 없어야 한다. B28–B35 우회 점퍼, D55–D60 9.99kΩ 저항, C23–A60 REF선, 14번 점퍼와 미니보드 DUT는 유지한다. USB를 같은 포트에 재연결한 뒤 완료를 보고한다.',
            'model_selected_action':'attach_output_load_step','response_file':'operator-response-'+request_id+'.json'}
        log.add('operator_action_requested',request)
        (log.path/'operator-request.json').write_text(json.dumps(request,ensure_ascii=False,indent=2)+'\n')
        print(json.dumps({'stage':'awaiting_operator','request_file':str(log.path/'operator-request.json')},ensure_ascii=False),flush=True)
        response_path=log.path/request['response_file'];deadline=time.monotonic()+1800
        while not response_path.exists():
            if time.monotonic()>deadline:raise ValueError('Operator confirmation timeout; no acquisition or automatic approval')
            time.sleep(.5)
        response=json.loads(response_path.read_text())
        if response.get('request_id')!=request_id or response.get('fixture')!=fixture:
            raise ValueError('Operator response does not match the pending request')
        if response.get('cancelled') is True:raise ValueError('Operator cancelled the intervention')
        return response

    model=None
    bench=PhysicalBench(protocol,log,confirm_wiring,initial_report=initial,previous_boot_id=args.previous_boot_id)
    try:
        session=PhysicalRCSession(bench.acquire,log)
        model=MetaToolSession(prompt=PROMPT,tools=session.tools,log=log,effort='medium',
              env_path=str(ROOT/'.env'),budget_path=str(ROOT/'.private/api-budget.json'),max_requests=8)
        result={**drive_agent(session,model),**model.metadata(),'instrument':bench.metadata()}
        result=model.sanitize(result)
        (log.path/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
        log.add('run_completed',result)
        print(json.dumps({'stage':'completed','record':str(log.path),'agent_report':result['agent_report'],
                         'reserved_check_passed':result['reserved_check_passed'],'instrument':result['instrument']},ensure_ascii=False),flush=True)
    except (Exception,KeyboardInterrupt) as exc:
        message=str(exc) if isinstance(exc,(ValueError,ProviderError)) else type(exc).__name__
        failure={'error':message,'source':'physical','instrument':bench.metadata(),'automatic_retry':False}
        if model is not None:failure=model.sanitize({**failure,**model.metadata()})
        log.add('run_failed',failure)
        print(json.dumps({'stage':'failed','record':str(log.path),**failure},ensure_ascii=False),flush=True)
        raise SystemExit(1)
    finally:
        if model is not None:model.close()


if __name__=='__main__':main()
