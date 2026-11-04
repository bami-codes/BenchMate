"""Additive stdlib-only artifact audit; never changes the frozen v4 runtime."""
import argparse
import json
from pathlib import Path

from .channel_timing_followup_v4 import verify as registered_verify
from .reading_verify import chain, check_file, require
from .reading_rules import digest


def verify(path):
    root=Path(path);answer=registered_verify(root)
    events=chain(root/'events.jsonl')
    registration=next(e['payload'] for e in events if e['kind']=='frame_timing_followup_registered')
    require(digest(json.loads((root/'protocol.json').read_text()))==registration['protocol_sha256'],'measurement_protocol_hash')
    design=json.loads((root/'reviewed-design.json').read_text())
    require(digest(design)==registration['reviewed_design_sha256'],'reviewed_design_hash')
    preflights=[e for e in events if e['kind']=='frame_timing_preflight_bound']
    require(len(preflights)==1,'one_preflight')
    pre=chain(check_file(root,preflights[0]['payload']))
    pong=pre[-1]['payload']
    require(pre[-1]['kind']=='run_completed' and pong.get('commands')==['PING']
            and pong.get('armed') is False and pong.get('stimuli')==0
            and pong['boot_id']!=registration['previous_boot_id'],'fresh_unarmed_preflight')
    bindings=[e for e in events if e['kind']=='channel_timing_model_bound']
    require(len(bindings)==1,'one_timing_binding')
    first_forecast=next(e for e in events if e['kind']=='training_forecasts_frozen')
    require(preflights[0]['sequence']<bindings[0]['sequence']<first_forecast['sequence'],'preflight_model_forecast_order')
    if events[-1]['kind']=='run_completed':
        require(json.loads((root/'result.json').read_text())==events[-1]['payload'],'result_artifact_matches_chain')
        frozen=json.loads((root/'predictions-frozen.json').read_text())
        require(frozen['policy']==bindings[0]['payload']['policy'],'frozen_policy_matches_bound_timing_model')
        require(frozen['policy']['version']==bindings[0]['payload']['version']
                and frozen['policy']['allowance_mV']==9.
                and frozen['policy']['fitted_timing_parameters']==[],'fixed_9mV_timing_rule')
        require(frozen['reviewed_design_sha256']==registration['reviewed_design_sha256'],'forecast_design')
    answer['preflight_events_checked']=len(pre)
    answer['artifact_hashes_checked']=4
    return answer


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('record');a=p.parse_args()
    from .verify import format_result
    try:r=verify(a.record)
    except (ValueError,OSError,KeyError,TypeError,StopIteration) as exc:
        print('FAIL '+str(exc)+' scope=internal_integrity+recorded_order creation_time=unproven');return 1
    print(format_result(r)+' prior_events_checked='+str(r['prior_events_checked'])
          +' preflight_events_checked='+str(r['preflight_events_checked'])
          +' artifact_hashes_checked='+str(r['artifact_hashes_checked']))
    return 0


if __name__=='__main__':raise SystemExit(main())
