"""Prepare an editing evidence packet without changing a run, making calls or driving a board."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from benchmate.records import canonical,decode_events


def score_summary(score):
    if not score:return None
    return {k:score[k] for k in ('passed','RMS_mV','max_abs_mV','regions') if k in score}


def review(path,*,require_physical=False):
    path=Path(path)
    if path.is_dir():path=path/'events.jsonl'
    raw=path.read_bytes();events=decode_events(raw,require_terminal=False,include_hash=True)
    if not events:raise ValueError('Empty event record')
    kinds={e['kind'] for e in events}
    repair='repair_run_protocol' in kinds
    if not repair and not any(k.startswith('b5_') for k in kinds):raise ValueError('Expected D01 repair or B5 run')
    prefix='repair' if repair else 'b5'
    frozen_kind='repair_prediction_frozen' if repair else 'b5_predictions_frozen'
    def all_of(kind):return [e for e in events if e['kind']==kind]
    def last_of(kind):return next((e for e in reversed(events) if e['kind']==kind),None)
    terminal=events[-1] if events[-1]['kind'] in ('run_completed','run_failed') else None
    sources={e['payload']['source'] for e in events if e['payload'].get('source') in ('mock','physical')}
    if len(sources)!=1:raise ValueError('Missing or mixed source labels')
    source=next(iter(sources))
    if require_physical and source!='physical':raise ValueError('Mock record cannot replace a physical scene')
    frozen=last_of(frozen_kind);pub=last_of(prefix+'_prediction_publication')
    observations=[e for e in events if (e['kind'] in ('physical_observation','mock_rc_observation') and e['payload'].get('phase') in ('repair_step','repair_reserved_sine'))] if repair else [e for e in all_of('b5_observation') if e['payload'].get('purpose')=='verification']
    checks=all_of('repair_prediction_comparison' if repair else 'b5_reserved_check')
    faults=[];notes=[];sidecar_ok=False
    if frozen:
        p=frozen['payload'];body={k:v for k,v in p.items() if k!='sha256'}
        if hashlib.sha256(canonical(body)).hexdigest()!=p.get('sha256'):raise ValueError('Frozen-model digest mismatch')
        sidecar=path.parent/'predictions-frozen.json'
        if sidecar.exists():
            stored=json.loads(sidecar.read_text())
            if hashlib.sha256(canonical(stored)).hexdigest()!=p['sha256']:raise ValueError('Frozen-model sidecar mismatch')
            sidecar_ok=True
        else:faults.append('Frozen-model sidecar missing')
    else:faults.append('No frozen repair/discovery model')
    ordered=False;remote=False
    if pub and frozen:
        remote=pub['payload'].get('remote') is True
        if pub['payload'].get('sha256')!=frozen['payload']['sha256']:raise ValueError('Publication refers to a different frozen model')
        ordered=bool(observations) and frozen['sequence']<pub['sequence']<min(e['sequence'] for e in observations)
        if pub['payload'].get('published') is not True:faults.append('Publication not acknowledged')
        if not ordered:faults.append('Freeze/publication/observation order is not established')
        if source=='physical' and not remote:faults.append('Physical forecast was not remotely published')
        if not remote:notes.append('Local freeze only; do not show a GitHub publication claim')
    else:faults.append('No matching publication event')
    confirmation=last_of('repair_operator_confirmation') if repair else None
    if repair:
        if not confirmation:faults.append('No repair confirmation')
        elif not (pub and observations and pub['sequence']<confirmation['sequence']<min(e['sequence'] for e in observations)):
            faults.append('Publication/repair-confirmation/observation order is not established')
        elif confirmation['payload'].get('prediction_sha256')!=frozen['payload']['sha256']:
            raise ValueError('Repair confirmation refers to another prediction')
    if len(observations)!=2 or len(checks)!=2:faults.append('Expected two post-freeze observations and two checks')
    rows=[]
    for e in checks:
        p=e['payload'];cond=p.get('conditional',{});cmd=p.get('command_forecast',{})
        link=p.get('prediction_sha256' if repair else 'frozen_sha256')
        if not frozen or link!=frozen['payload']['sha256']:raise ValueError('Check refers to a different frozen model')
        if repair and p.get('scored_OUT_refitted') is not False:raise ValueError('Validation-output non-refitting is not established')
        if repair:cond=cond.get('restored_nominal',{});cmd=cmd.get('restored_nominal',{})
        row={'sequence':e['sequence'],'timestamp':e['timestamp'],'settings':p.get('settings'),'conditional':score_summary(cond),'command_forecast':score_summary(cmd)}
        if repair:row['unchanged_conditional']=score_summary(p.get('conditional',{}).get('unchanged',{}))
        else:row['linear_alternatives']=[{'family':x.get('family'),**score_summary(x)} for x in p.get('linear_alternatives',[])]
        rows.append(row)
    conditional_ok=len(rows)==2 and all(x['conditional'] and x['conditional'].get('passed') is True for x in rows)
    command_ok=len(rows)==2 and all(x['command_forecast'] and x['command_forecast'].get('passed') is True for x in rows)
    if conditional_ok and not command_ok:notes.append('Conditional checks pass but command forecasts do not both pass; both results must remain visible')
    if not terminal:faults.append('Run has no terminal event; this is an integrity-checked prefix')
    elif terminal['kind']=='run_failed':notes.append('Failed first attempt; retain it and do not present it as a successful run')
    reason=(frozen['payload'].get('reason') if frozen else None) if repair else ((last_of('b5_netlist_proposed') or {}).get('payload',{}).get('rationale'))
    if not reason:faults.append('Recorded Spark reason unavailable')
    if source=='mock':notes.append('Simulated bench; cannot establish physical repair or physical B5')
    notes.append('Conditional curves are available after measured IN; this packet does not attest physical authenticity or calibration')
    return {'record_sha256':hashlib.sha256(raw).hexdigest(),'event_count':len(events),'chain_valid':True,'terminal_kind':terminal['kind'] if terminal else None,
      'kind':'D01 repair' if repair else 'B5','declared_source':source,'recorded_reason_original':reason,
      'frozen_sha256':frozen['payload']['sha256'] if frozen else None,'frozen_sidecar_verified':sidecar_ok,
      'publication_remote':remote,'freeze_publication_before_observations':ordered,
      'publication':pub['payload'] if pub else None,'publication_timestamp':pub['timestamp'] if pub else None,
      'operator_confirmation_timestamp':confirmation['timestamp'] if confirmation else None,
      'observations':[{'sequence':e['sequence'],'timestamp':e['timestamp'],'settings':e['payload'].get('settings')} for e in observations],
      'checks':rows,'both_conditional_checks_pass':conditional_ok,'both_command_forecasts_pass':command_ok,
      'terminal_report':terminal['payload'] if terminal else None,'editing_prerequisites_missing':faults,'presentation_notes':notes}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('run');p.add_argument('--output',required=True);p.add_argument('--require-physical',action='store_true');a=p.parse_args()
    result=review(a.run,require_physical=a.require_physical);out=Path(a.output)
    # Evidence records and existing editorial data are never overwritten.
    out.parent.mkdir(parents=True,exist_ok=True)
    with out.open('x') as f:json.dump(result,f,ensure_ascii=False,indent=2);f.write('\n')
    print(json.dumps({'review_written':str(out),'source':result['declared_source'],'missing':result['editing_prerequisites_missing']}))

if __name__=='__main__':main()
