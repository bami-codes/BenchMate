import os
V=os.path.dirname(os.path.abspath(__file__)); ROOT=os.environ.get('BENCHMATE_ROOT',os.path.dirname(V))
import json
R=ROOT+"/examples/b5-unloaded-spark/2026-10-30/20261030T133514-4ea9a8848e/events.jsonl"
import sys
sys.path.insert(0,ROOT+'/src')
from benchmate.records import read_events
ev=read_events(R)
def ob(e):
    p=e['payload'];d=p['input_template']['data']
    return {'settings':p['settings'],'t':[a+b for a,b in zip(d['frame_time_s'],d['output_delay_s'])],'in':d['input_relative_origin_v'],'out':p['output_relative_origin_v']}
train=[ob(e) for e in ev if e['kind']=='b5_observation' and e['payload']['purpose']=='training']
ver=[ob(e) for e in ev if e['kind']=='b5_observation' and e['payload']['purpose']=='verification']
checks=[e['payload'] for e in ev if e['kind']=='b5_reserved_check']
ia=next(e['payload'] for e in ev if e['kind']=='b5_initial_assessment')
pf=next(e['payload'] for e in ev if e['kind']=='b5_proposal_fit')
prop=next(e for e in ev if e['kind']=='b5_netlist_proposed')
pub=next(e for e in ev if e['kind']=='b5_prediction_publication')
out={'train':train,'ver':ver,
 'ver_pred':[c['conditional_prediction'] for c in checks],
 'ver_scores':[{'cond':c['conditional']['RMS_mV'],'cond_worst':max(r['RMS_mV'] for r in c['conditional']['regions']),'cmd':c['command_forecast']['RMS_mV'],
    'linear':sorted([(a['family'],a['RMS_mV']) for a in c['linear_alternatives']],key=lambda x:x[1])} for c in checks],
 'linear_train':[{'family':c['model']['family'],'worst_check_rms':max(k['RMS_mV'] for k in c['checks'])} for c in ia['candidates']],
 'proposal':prop['payload'],'proposal_time':prop['timestamp'],
 'fit_rms':[k['RMS_mV'] for k in pf['checks']],'train_pred':pf['initial_generated_predictions'],
 'publication':pub['payload'],'publication_time':pub['timestamp'],
 'reserved_time':next(e['timestamp'] for e in ev if e['kind']=='b5_observation' and e['payload']['purpose']=='verification'),
}
json.dump(out,open(V+'/data/b5.json','w'))
print(out['linear_train']);print(out['ver_scores']);print(out['fit_rms']);print(out['publication_time'],out['reserved_time'])
import numpy as np
for o in train: print(o['settings'], round(max(o['out']),3), round(min(o['out']),3), round(max(o['in']),3))
