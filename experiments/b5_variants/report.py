"""Report all registered variant cases; zero/partial primary sets have no rate."""
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'experiments'))
from b5_variants.bench import IDS

def build(runs,classification):
    primary=set(classification['primary']);table=[]
    for arm in ('engine_only','oracle_library','spark'):
        path=Path(runs)/arm/'results.jsonl';rows={}
        if path.exists():
            for line in path.read_text().splitlines():
                row=json.loads(line);rows.setdefault((row['variant'],row['replicate']),row)
        variants=[]
        for variant in IDS:
            count=2 if arm=='spark' and not variant.startswith('G') else 1
            observed=[rows.get((variant,k)) for k in range(count)]
            variants.append({'variant':variant,'class':classification['variants'][variant]['class'],
                'primary':variant in primary,'outcomes':[r['outcome'] if r else 'not_run' for r in observed],
                'unneeded_diode_proposals':sum(r.get('unneeded_diode_proposals',0) for r in observed if r)})
        selected=[v for v in variants if v['primary']]
        outcomes=[o for v in selected for o in v['outcomes']]
        complete=bool(outcomes) and 'not_run' not in outcomes
        table.append({'arm':arm,'variants':variants,'independent_primary_circuits':len(primary),
            'primary_correct':sum(o=='correct' for o in outcomes),'primary_expected_runs':len(outcomes),
            'primary_rate':sum(o=='correct' for o in outcomes)/len(outcomes) if complete else None,
            'primary_status':'complete' if complete else 'empty_primary_set' if not primary else 'incomplete',
            'wrong_verifications':sum(r['outcome']=='wrong' for r in rows.values()),
            'audit_unresolved':sum('audit_status' in r for r in rows.values()),
            'http_requests':sum(r.get('http_requests',0) for r in rows.values())})
    return {'source':'mock','selection_conditioned':True,'unique_topology_claimed':False,'table':table}

if __name__=='__main__':
    c=json.loads(Path(sys.argv[1]).read_text());print(json.dumps(build(ROOT/'runs/b5-variants/evaluation-v1',c),indent=2))
