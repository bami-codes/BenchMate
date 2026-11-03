#!/usr/bin/env python3
"""Generic SAM → body masks → five independent surface views → code decoder."""
import argparse
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from benchmate.photo_v2 import pipeline


def main():
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='command',required=True)
    a=sub.add_parser('freeze');a.add_argument('--output',required=True)
    a=sub.add_parser('prepare');a.add_argument('--image',required=True);a.add_argument('--output',required=True);a.add_argument('--policy',required=True);a.add_argument('--evaluation',choices=['nonblind','prospective'],default='nonblind');a.add_argument('--capture-after-freeze',action='store_true')
    a=sub.add_parser('segment');a.add_argument('--prepared',required=True);a.add_argument('--execute',action='store_true')
    a=sub.add_parser('decode');a.add_argument('--prepared',required=True);a.add_argument('--output',required=True)
    a=sub.add_parser('read');a.add_argument('--decoded',required=True);a.add_argument('--execute',action='store_true')
    a=p.parse_args()
    if a.command=='freeze':r=pipeline.freeze(a.output);print(json.dumps({'frozen':a.output,'sources':len(r['source_sha256']),'API_calls':0}))
    elif a.command=='prepare':r=pipeline.prepare(a.image,a.output,a.policy,a.evaluation,a.capture_after_freeze);print(json.dumps({'prepared':a.output,'evaluation':r['evaluation'],'API_calls':0}))
    elif a.command=='decode':r=pipeline.decode(a.prepared,a.output);print(json.dumps({'decoded':a.output,'bodies':len(r['components']),'Spark_requests_planned':r['Spark_requests_planned'],'API_calls':0}))
    elif not a.execute:raise SystemExit('Explicit --execute required after call-count disclosure')
    elif a.command=='segment':print(json.dumps(pipeline.segment(a.prepared)))
    else:print(json.dumps({'bodies_read':len(pipeline.read(a.decoded))}))


if __name__=='__main__':main()
