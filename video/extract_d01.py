"""Extract real D01 run traces for video graphics. Curves come from the record or the repo's own engine function."""
import os
V=os.path.dirname(os.path.abspath(__file__)); ROOT=os.environ.get('BENCHMATE_ROOT',os.path.dirname(V))
import json, sys
sys.path.insert(0,ROOT+'/src')
from benchmate.physical_rc import conditional_curve
R=(sys.argv[1].rstrip("/")+"/events.jsonl") if len(sys.argv)>1 else ROOT+"/examples/hardware-spark-rc/2026-10-30/20261029T174402-d3eaa8e612/execution/events.jsonl"
from benchmate.records import read_events
ev=read_events(R)
obs={e['payload']['phase']:e['payload'] for e in ev if e['kind']=='physical_observation'}
def trace(o,extra={}):
    d=o['data'];b=o['baseline']
    t=[ft+od for ft,od in zip(d['frame_time_s'],d['output_delay_s'])]
    out={'t':t,'observed':[v-b['output_v'] for v in d['output_v']],'drive':[v-b['input_v'] for v in d['input_v']]}
    for k,curve in extra.items(): out[k]=[v-b['output_v'] for v in curve]
    return out
train=next(e['payload'] for e in ev if e['kind']=='unloaded_training_completed')
u=obs['unloaded_step']
fit=conditional_curve(u,{'gain':1.,'tau_s':train['tau_s']})['predicted_output_v']
nom=conditional_curve(u,{'gain':1.,'tau_s':0.01})['predicted_output_v']
cmp=next(e['payload'] for e in ev if e['kind']=='physical_model_comparison')['scores']
ver=next(e['payload'] for e in ev if e['kind']=='physical_verification')['scores']
models=next(e['payload'] for e in ev if e['kind']=='loaded_point_models_frozen')['models']
out={
 'tau_ms':train['tau_s']*1000,'training_RMS_mV':train['training_RMS_mV'],
 'unloaded':trace(u,{'fit':fit,'nominal':nom}),
 'loaded':trace(obs['attach_output_load_step'],{k:cmp[k]['prediction']['predicted_output_v'] for k in cmp}),
 'reserved':trace(obs['reserved_sine'],{k:ver[k]['prediction']['predicted_output_v'] for k in ver}),
 'loaded_scores':{k:{'rms':v['RMS_mV'],'worst':max(r['RMS_mV'] for r in v['regions']),'passed':v['passed']} for k,v in cmp.items()},
 'reserved_scores':{k:{'rms':v['RMS_mV'],'worst':max(r['RMS_mV'] for r in v['regions']),'passed':v['passed']} for k,v in ver.items()},
 'models':models,
 'reason_load_ko':next(e['payload']['reason'] for e in ev if e['kind']=='physical_measurement_selected' and e['payload']['phase']=='attach_output_load_step'),
 'start':ev[0]['timestamp'],'end':ev[-1]['timestamp'],
 'request_time':next(e['timestamp'] for e in ev if e['kind']=='operator_action_requested'),
 'frames_total':(next((e['payload'] for e in ev if e['kind']=='run_completed'),{}).get('instrument') or {}).get('retained_frames'),
 'decisions':sum(1 for e in ev if e['kind']=='tool_call'),'source':R,
 'wiring':sum(1 for e in ev if e['kind']=='operator_action_requested' and e['payload'].get('fixture')=='output_load'),
 'reason_load_seq':next(e['sequence'] for e in ev if e['kind']=='physical_measurement_selected' and e['payload']['phase']=='attach_output_load_step'),
}
import os.path
tp=os.path.join(os.path.dirname(R),'translations.json')
tr={str(x['event_sequence']):x['english'] for x in json.load(open(tp))['entries']} if os.path.exists(tp) else {}
KNOWN='An unloaded step identifies only R × C. Repeating it adds no information. A known output load changes the divider gain, separating resistance change from capacitance change.'
out['reason_load_en']=tr.get(str(out['reason_load_seq'])) or (KNOWN if out['reason_load_ko'].startswith('무부하 스텝은 tau=R*C만 식별하여') else None)
json.dump(out,open(V+'/data/d01.json','w'))
print({k:v for k,v in out.items() if not isinstance(v,(dict,list))})
print(out['loaded_scores']);print(out['reserved_scores']);print(models)
