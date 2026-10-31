#!/usr/bin/env python3
"""Audit a completed three-schematic vision batch without making API calls.

Values/connections use the pre-existing fixture answer key. Bounding-box review
is a separate post-hoc diagnostic, not a preregistered accuracy metric.
"""
import argparse
import hashlib
import io
import json
import math
from pathlib import Path
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from PIL import Image
from benchmate.known_design import payload_for,candidate_netlist,nominal_rc
from benchmate.records import read_events,canonical


def sha(raw):return hashlib.sha256(raw).hexdigest()


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--run',required=True)
    p.add_argument('--inputs',required=True);p.add_argument('--source-commit',required=True)
    p.add_argument('--output',required=True);args=p.parse_args()
    run=Path(args.run);inputs=Path(args.inputs)
    manifest_path=inputs/'prepared/manifest.json';manifest=json.loads(manifest_path.read_text())
    truth_path=inputs/'truth.json';truth=json.loads(truth_path.read_text())
    events=read_events(run);result=json.loads((run/'result.json').read_text())
    assert events[-1]['kind']=='run_completed' and events[-1]['payload']==result
    frozen=next(e['payload'] for e in events if e['kind']=='vision_batch_frozen')
    assert frozen['manifest_sha256']==sha(manifest_path.read_bytes())
    assert result['requests']==3 and len(result['outcomes'])==len(manifest['images'])==len(truth['cases'])==3
    for path in [manifest_path,truth_path]:
        relative=str(path.resolve().relative_to(ROOT))
        assert path.read_bytes()==subprocess.check_output(['git','show',args.source_commit+':'+relative],cwd=ROOT)
    for relative,digest in frozen['source_sha256'].items():
        saved=subprocess.check_output(['git','show',args.source_commit+':'+relative],cwd=ROOT)
        assert sha(saved)==digest==sha((ROOT/relative).read_bytes())
    rows=[];responses=[];elapsed=0.;tokens={'input_tokens':0,'output_tokens':0,'total_tokens':0}
    for outcome,entry,expected_case in zip(result['outcomes'],manifest['images'],truth['cases']):
        assert outcome['id']==entry['id'] and outcome['requests']==1
        attempt=run/'attempts'/outcome['run'];trace=read_events(attempt)
        assert trace[-1]['kind']=='run_completed'
        data=json.loads((attempt/'result.json').read_text());assert data==trace[-1]['payload']
        reply=json.loads((attempt/'response-visible.json').read_text())
        assert reply==next(e['payload'] for e in trace if e['kind']=='vision_reply')
        assert reply['status']=='completed' and len([e for e in trace if e['kind']=='vision_request_sent'])==1
        plan=json.loads((attempt/'plan.json').read_text())
        assert plan==next(e['payload'] for e in trace if e['kind']=='vision_request_frozen')
        image=(attempt/'input.png').read_bytes();assert sha(image)==entry['info']['sha256']==plan['image']['sha256']
        with Image.open(io.BytesIO(image)) as im:assert not im.info and not im.getexif();size=im.size
        request=payload_for(image,entry['source_kind'])
        assert sha(canonical(request))==next(e['payload']['sha256'] for e in trace if e['kind']=='vision_payload_committed')
        calls=[x for x in reply['visible_output'] if x['type']=='function_call'];assert len(calls)==1 and calls[0]['name']=='report_design'
        raw=(attempt/'arguments.txt').read_text();assert raw==calls[0]['arguments']
        candidate=json.loads(raw);assert candidate==data['candidate']
        assert data['netlist']==candidate_netlist(candidate)
        assert data['nominal_rc_candidate']==nominal_rc(candidate,entry['source_kind'])
        assert not data['operator_confirmed'] and not data['measurement_verified'] and not data['hardware_IO']
        by_kind={x['kind']:x for x in candidate['components']};expected=expected_case['expected']
        component_set=len(candidate['components'])==2 and set(by_kind)=={'R','C'}
        values=component_set and all((by_kind[k]['value_si'] is None if expected[field] is None else
            by_kind[k]['value_si'] is not None and math.isclose(by_kind[k]['value_si'],expected[field],rel_tol=1e-12,abs_tol=0))
            for k,field in [('R','R_ohm'),('C','C_f')])
        connections=component_set and all(set((by_kind[x['kind']]['a'],by_kind[x['kind']]['b']))==set(x['nodes']) for x in expected['connections'])
        missing_ok=(expected['C_f'] is not None or (by_kind['C']['value_si'] is None and candidate['status']=='incomplete' and bool(candidate['ambiguities'])))
        handoff=(data['nominal_rc_candidate'] is not None)==expected['nominal_design_allowed_after_review']
        boxes=[]
        # Symbol-body construction coordinates, from make_vision_fixtures.py.
        bodies={'R':[300,205,490,255],'C':[590,345,710,367]}
        for item in candidate['components']:
            bbox=[v*size[i%2] for i,v in enumerate(item['bbox'])];body=bodies[item['kind']]
            contains=bbox[0]<=body[0] and bbox[1]<=body[1] and bbox[2]>=body[2] and bbox[3]>=body[3]
            boxes.append({'name':item['name'],'predicted_pixels':bbox,'drawing_symbol_body_pixels':body,'contains_full_symbol_body':contains})
        rows.append({'id':entry['id'],'input':expected_case['file'],'attempt':outcome['run'],
            'expected':expected,'observed_values':{k:by_kind[k]['value_si'] for k in by_kind},
            'reported_status':candidate['status'],'component_set_matches':component_set,'values_match':values,
            'connections_match':connections,'unknown_preserved':missing_ok,'handoff_gate_matches':handoff,
            'declared_fixture_checks_pass':all([component_set,values,connections,missing_ok,handoff]),
            'posthoc_bbox_diagnostic':boxes,'response_id':reply['response_id'],'api_elapsed_s':reply['elapsed_s']})
        responses.append(reply['response_id']);elapsed+=reply['elapsed_s']
        for key in tokens:tokens[key]+=reply['usage'][key]
    assert len(set(responses))==3
    audit={'scope':'Three synthetic schematic development checks. Not real-photo accuracy, hardware evidence or a general vision benchmark.',
        'source_commit':args.source_commit,'manifest_sha256':sha(manifest_path.read_bytes()),'truth_sha256':sha(truth_path.read_bytes()),
        'batch_events_sha256':sha((run/'events.jsonl').read_bytes()),'hash_chains_verified':4,'source_files_verified':len(frozen['source_sha256']),
        'payload_hashes_verified':3,'metadata_free_images_verified':3,'all_visible_arguments_retained':True,
        'fresh_context_requests':3,'automatic_retry':False,'hardware_IO':False,'API_elapsed_s':elapsed,'token_usage':tokens,
        'preexisting_answer_key_checks':rows,'declared_checks_passed':sum(x['declared_fixture_checks_pass'] for x in rows),
        'bbox_scope':'Post-hoc symbol-body containment diagnostic, not a preregistered scoring rule. Box semantics were not tightly defined; do not use these coordinates as precise repair/SAM targeting.',
        'external_attestation':False}
    Path(args.output).write_text(json.dumps(audit,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'requests':3,'checks_passed':audit['declared_checks_passed'],'API_elapsed_s':elapsed,'token_usage':tokens,
        'bbox_full_symbol_containment':[x['contains_full_symbol_body'] for row in rows for x in row['posthoc_bbox_diagnostic']]}))


if __name__=='__main__':main()
