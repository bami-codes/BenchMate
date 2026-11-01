import importlib.util
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('extract_benchmark',ROOT/'video/extract_benchmark.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

def test_task_b_results_do_not_turn_unrun_task_a_into_zero(tmp_path):
 import sys
 sys.path.insert(0,str(ROOT/'scripts'));import benchmark_linear as bl
 b=next(s for s in bl.load_specimens(bl.load_protocol(),False) if s['task']=='B')
 row={'task':'B','specimen':b['id'],'replicate':0,'outcome':'correct','protocol_sha256':bl.sha256(bl.PROTOCOL),'simulated_mountings':1}
 d=tmp_path/'spark_hidden';d.mkdir();(d/'results.jsonl').write_text(json.dumps(row)+'\n')
 result=m.extract(tmp_path)
 a=next(r for r in result['tasks']['A']['rows'] if r['arm']=='spark_hidden')
 assert a['status']=='not run' and 'correct' not in a
 b=next(r for r in result['tasks']['B']['rows'] if r['arm']=='spark_hidden')
 assert b['status']=='incomplete' and b['correct']==1 and b['of']==16

def test_first_failure_is_not_replaced_by_later_success(tmp_path):
 import benchmark_linear as bl
 b=next(s for s in bl.load_specimens(bl.load_protocol(),False) if s['task']=='B')
 row={'task':'B','specimen':b['id'],'replicate':0,'outcome':'incomplete','protocol_sha256':bl.sha256(bl.PROTOCOL),'simulated_mountings':None}
 d=tmp_path/'spark_hidden';d.mkdir();(d/'results.jsonl').write_text(json.dumps(row)+'\n'+json.dumps({**row,'outcome':'correct'})+'\n')
 out=next(r for r in m.extract(tmp_path)['tasks']['B']['rows'] if r['arm']=='spark_hidden')
 assert out['correct']==0
