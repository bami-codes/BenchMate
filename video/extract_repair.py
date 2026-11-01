"""Repair scene data. Default: mock rehearsal placeholder; pass a real run dir to use physical data."""
import os
V=os.path.dirname(os.path.abspath(__file__)); ROOT=os.environ.get('BENCHMATE_ROOT',os.path.dirname(V))
import json, sys
from datetime import datetime, timezone, timedelta
run=sys.argv[1] if len(sys.argv)>1 else ROOT+"/examples/d01-repair-rehearsal/2026-11-01/final_success/20261101T003829-400778438d"
sys.path.insert(0,ROOT+'/src')
from benchmate.records import read_events
ev=read_events(run)
KST=timezone(timedelta(hours=9))
fmt=lambda ts:datetime.fromisoformat(ts).astimezone(KST).strftime('%b %d %H:%M:%S KST')
obs=[e for e in ev if e['kind'] in('physical_observation','mock_rc_observation') and e['payload'].get('phase')=='repair_step'][0]
cmp=[e for e in ev if e['kind']=='repair_prediction_comparison']
frozen=next(e for e in ev if e['kind']=='repair_prediction_frozen')
pub=next(e for e in ev if e['kind']=='repair_prediction_publication')
conf=next(e for e in ev if e['kind']=='repair_operator_confirmation')
p=obs['payload'];d=p['data'];b=p['baseline']
t=[a+c for a,c in zip(d['frame_time_s'],d['output_delay_s'])]
rel=lambda arr:[v-b['output_v'] for v in arr]
s0=cmp[0]['payload']['conditional']
observed=rel(d['output_v']);lo=min(observed+rel(s0['unchanged']['prediction']['predicted_output_v']));hi=max(observed)
src=next(e['payload'] for e in ev if e['kind']=='repair_run_protocol')['source']
tm=frozen['payload']['transfer_models']
fc=frozen['payload']['forecasts'][0]
per=obs['payload']['settings']['period_us']*1e-6
ft=[i*per+fc['restored_nominal']['nominal_output_delay_s'] for i in range(len(fc['restored_nominal']['predicted_output_relative_origin_v']))]
out={'source':src,'ft':ft,'f_restored':fc['restored_nominal']['predicted_output_relative_origin_v'],'f_unchanged':fc['unchanged']['predicted_output_relative_origin_v'],
 'pass':{'restored':[c['payload']['conditional']['restored_nominal']['passed'] for c in cmp],'unchanged':[c['payload']['conditional']['unchanged']['passed'] for c in cmp],'forecast':[c['payload']['command_forecast']['restored_nominal']['passed'] for c in cmp]},
 'forecast_rms':[c['payload']['command_forecast']['restored_nominal']['RMS_mV'] for c in cmp],'t':t,'observed':observed,'restored_curve':rel(s0['restored_nominal']['prediction']['predicted_output_v']),
 'unchanged_curve':rel(s0['unchanged']['prediction']['predicted_output_v']),
 'scores':{'restored':[c['payload']['conditional']['restored_nominal']['RMS_mV'] for c in cmp],'unchanged':[c['payload']['conditional']['unchanged']['RMS_mV'] for c in cmp]},
 'restored':tm['restored'] if 'restored' in tm else tm[list(tm)[0]],'unchanged':tm['unchanged'],
 'sha':frozen['payload']['sha256'],'commit':pub['payload'].get('commit','(local mock)'),
 'commit_time':fmt(pub['timestamp']),'repair_time':fmt(conf['timestamp']),
 'reason_en':'(placeholder: Spark’s recorded repair reason will appear here)' if src=='mock' else '',
 'yr':[round(lo-0.02,2),round(hi+0.02,2)],'ticksY':[round(v*0.05,2) for v in range(int((lo-0.02)//0.05)+1,int((hi+0.02)//0.05)+1)]}
print(list(tm.keys()), out['scores'], out['yr'])
json.dump(out,open(V+'/data/repair.json','w'))
