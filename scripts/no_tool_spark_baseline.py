#!/usr/bin/env python3
"""Five independent, unchanged no-tool prompts. Dry run unless --execute.

All visible replies and failures are retained. Asking for more measurements is
appropriate uncertainty, not a failure. This small qualitative comparison is
not an accuracy benchmark or a basis for selecting only favorable answers.
"""
import argparse,json,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
import httpx
from benchmate.config import load_keys,redact
from benchmate.providers import PROVIDERS,reserve_budget,ProviderError
from benchmate.records import Recorder

QUESTION='Designed RC low-pass 10 kΩ, 1 µF. Measured time constant 21.4 ms. What is wrong?'
PAYLOAD={'model':'muse-spark-1.3','reasoning':{'effort':'max'},'store':False,
         'max_output_tokens':8192,'input':[{'role':'user','content':QUESTION}]}
PLAN={'destination':PROVIDERS['meta']['url'],'requests':5,'payload_per_request':PAYLOAD,
      'fresh_context_each_request':True,'tools':[],'automatic_retry':False,
      'scope':'Qualitative five-response baseline; requests for additional measurements are appropriate, not failures.'}

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--execute',action='store_true')
    p.add_argument('--output',default=str(ROOT/'runs/no-tool-spark'));args=p.parse_args()
    if not args.execute:print(json.dumps(PLAN,ensure_ascii=False,indent=2));return
    keys=load_keys(str(ROOT/'.env'));key=keys.get(PROVIDERS['meta']['key'])
    if not key:raise ProviderError('Local Meta key unavailable')
    log=Recorder(args.output,mode='five_fresh_no_tool_spark_responses');log.add('baseline_plan_frozen',PLAN)
    print(json.dumps({'stage':'started','record':str(log.path)}),flush=True)
    replies=[];requests=0
    try:
        with httpx.Client(timeout=90,follow_redirects=False) as client:
            for index in range(5):
                reserve_budget(ROOT/'.private/api-budget.json','meta',1.);requests+=1;began=time.monotonic()
                response=client.post(PLAN['destination'],json=PAYLOAD,headers={'Authorization':'Bearer '+key})
                if response.status_code>=400:raise ProviderError(f'Meta HTTP {response.status_code}; no retry')
                body=response.json()
                text='\n'.join(c.get('text','') for item in body.get('output',[]) if item.get('type')=='message'
                              for c in item.get('content',[]) if c.get('type')=='output_text')
                record=redact({'index':index+1,'response_id':body.get('id'),'status':body.get('status'),
                               'usage':body.get('usage'),'elapsed_s':time.monotonic()-began,'visible_text_verbatim':text},keys)
                replies.append(record);log.add('no_tool_reply',record)
                if body.get('status') not in (None,'completed') or not text.strip() or any(i.get('type')=='function_call' for i in body.get('output',[])):
                    raise ProviderError('Incomplete or unexpected response; retained without retry')
        result={'requests':requests,'replies':replies,'all_five_retained':True,'selection_or_automatic_grading':False}
        (log.path/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');log.add('run_completed',result)
        print(json.dumps({'stage':'completed','record':str(log.path),'requests':requests}),flush=True)
    except (Exception,KeyboardInterrupt) as exc:
        failure={'error':str(exc) if isinstance(exc,ProviderError) else type(exc).__name__,'requests':requests,'replies_retained':len(replies),'automatic_retry':False}
        log.add('run_failed',redact(failure,keys));print(json.dumps({'record':str(log.path),**failure}),flush=True)
        raise SystemExit(1)
if __name__=='__main__':main()
