"""Build a read-only public replay from hash-checked, already public records."""
from pathlib import Path
import argparse, hashlib, json, shutil, sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from benchmate.viewer import load_record,render_viewer
from benchmate.design_replay import D01,D01_SHA
from benchmate.records import read_events

B5='examples/b5-unloaded-spark/2026-10-30/20261030T133514-4ea9a8848e'
REPAIR='examples/overnight/2026-11-02/rehearsals/d01'

def write_json(path,data):
    path.write_text(json.dumps(data,ensure_ascii=False,allow_nan=False)+'\n')

def build(out):
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    if out.resolve()==ROOT.resolve():raise ValueError('Use a dedicated output directory')
    manifest={'source':'retained records','hardware_calls':0,'api_calls':0,'records':{}}
    for slug,rel,origin in [('d01',D01,'physical'),('repair',REPAIR,'mock')]:
        record=load_record(ROOT/rel)
        if slug=='d01' and record['source_sha256']!=D01_SHA:raise ValueError('D01 evidence changed')
        if slug=='repair' and not any(e['kind']=='provider_configuration' and e['payload'].get('model')=='muse-spark-1.3' for e in record['events']):
            raise ValueError('Repair replay must contain the actual Spark rehearsal')
        (out/(slug+'.html')).write_text(render_viewer(record))
        manifest['records'][slug]={'path':rel,'source':origin,'events_sha256':record['source_sha256']}
    events=read_events(ROOT/B5/'events.jsonl')
    def obs(e):
        p=e['payload'];d=p['input_template']['data']
        return {'settings':p['settings'],'t':[a+b for a,b in zip(d['frame_time_s'],d['output_delay_s'])],
                'input_t':[a+b for a,b in zip(d['frame_time_s'],d['input_delay_s'])],
                'input':d['input_relative_origin_v'],'output':p['output_relative_origin_v']}
    checks=[e['payload'] for e in events if e['kind']=='b5_reserved_check']
    fit=next(e['payload'] for e in events if e['kind']=='b5_proposal_fit')
    proposal=next(e['payload'] for e in events if e['kind']=='b5_netlist_proposed')
    publication=next(e for e in events if e['kind']=='b5_prediction_publication')
    samples=[]
    for kind,predictions in [('training',fit['initial_generated_predictions']),('verification',[c['conditional_prediction'] for c in checks])]:
        for i,e in enumerate(e for e in events if e['kind']=='b5_observation' and e['payload']['purpose']==kind):
            row={**obs(e),'phase':kind,'prediction':predictions[i]}
            if kind=='verification':
                row['scores']={k:{'whole_mV':checks[i][k]['RMS_mV'],'worst_region_mV':max(r['RMS_mV'] for r in checks[i][k]['regions']),'passed':checks[i][k]['passed']} for k in ('conditional','command_forecast')}
            samples.append(row)
    source_sha=hashlib.sha256((ROOT/B5/'events.jsonl').read_bytes()).hexdigest()
    write_json(out/'b5-data.json',{'source':'mock','proposal':proposal,'publication':publication['payload'],
        'publication_time':publication['timestamp'],'source_sha256':source_sha,'samples':samples})
    manifest['records']['b5']={'path':B5,'source':'mock','events_sha256':source_sha}
    for name in ('index.html','b5.html','site.css','b5.js'):
        shutil.copyfile(ROOT/'web'/name,out/name)
    shutil.copyfile(ROOT/'docs/assets/benchmark-evaluation.png',out/'benchmark.png')
    shutil.copyfile(ROOT/'docs/assets/d01-story.png',out/'d01-story.png')
    (out/'fonts').mkdir(exist_ok=True)
    for name in ('IBMPlexSans-Regular.woff2','IBMPlexSans-SemiBold.woff2','OFL.txt'):
        shutil.copyfile(ROOT/'src/benchmate/assets'/name,out/'fonts'/name)
    write_json(out/'manifest.json',manifest)
    (out/'.nojekyll').write_text('')
    print(json.dumps({'output':str(out),'files':len(list(out.rglob('*'))),'records':manifest['records']},indent=2))

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',required=True);build(parser.parse_args().output)
