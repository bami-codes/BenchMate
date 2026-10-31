#!/usr/bin/env python3
"""Prepare images, review payloads, or execute a bounded fresh-context vision batch."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from benchmate.known_design import extract, request_plan, sanitize_image, sha
from benchmate.records import Recorder


def read_manifest(path):
    path=Path(path).resolve();raw=path.read_bytes();manifest=json.loads(raw)
    if manifest.get('schema')!='benchmate.vision_manifest.v1' or not 1<=len(manifest['images'])<=10:
        raise ValueError('Expected one to ten prepared images')
    if len({entry['id'] for entry in manifest['images']})!=len(manifest['images']):raise ValueError('Duplicate manifest identifiers')
    checked=[]
    for entry in manifest['images']:
        target=(path.parent/entry['file']).resolve()
        if target.parent!=path.parent:raise ValueError('Image must be beside its manifest')
        image=target.read_bytes()
        if sha(image)!=entry['info']['sha256']:raise ValueError('Prepared image hash mismatch')
        normalized,info=sanitize_image(image)
        if normalized!=image or not entry['info']['metadata_removed']:raise ValueError('Prepared image is not a clean canonical PNG')
        plan=request_plan(entry['info'],entry['source_kind'])
        checked.append((entry,image,plan))
    return manifest,sha(raw),checked


def main():
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='command',required=True)
    prepare=sub.add_parser('prepare');prepare.add_argument('--image',action='append',required=True)
    prepare.add_argument('--kind',choices=['intended_schematic','assembly_photo'],required=True)
    prepare.add_argument('--output',required=True)
    batch=sub.add_parser('batch');batch.add_argument('--manifest',required=True)
    batch.add_argument('--execute',action='store_true');batch.add_argument('--approved-manifest-sha256')
    batch.add_argument('--output',default=str(ROOT/'runs/vision'))
    serve=sub.add_parser('serve');serve.add_argument('--execute',action='store_true')
    serve.add_argument('--demo',action='store_true',help='Load the recorded schematic reading and separate D01 replay; no paid calls')
    serve.add_argument('--port',type=int,default=8766);serve.add_argument('--max-requests',type=int,default=10)
    serve.add_argument('--output',default=str(ROOT/'runs/vision-ui'))
    args=p.parse_args()
    if args.command=='prepare':
        if not 1<=len(args.image)<=10:raise ValueError('Prepare one to ten images')
        destination=Path(args.output);destination.mkdir(parents=True,exist_ok=False);entries=[]
        for index,path in enumerate(args.image,1):
            image,info=sanitize_image(Path(path).read_bytes());name=f'image-{index:02d}.png'
            (destination/name).write_bytes(image)
            entries.append({'id':f'image-{index:02d}','file':name,'source_kind':args.kind,'info':info})
        manifest={'schema':'benchmate.vision_manifest.v1','images':entries,'max_paid_requests':len(entries),
            'automatic_retry':False,'hardware_IO':False,'all_outputs_retained':True}
        target=destination/'manifest.json';target.write_text(json.dumps(manifest,indent=2)+'\n')
        print(json.dumps({'manifest':str(target),'sha256':sha(target.read_bytes()),'requests':len(entries)}))
    elif args.command=='batch':
        manifest,digest,checked=read_manifest(args.manifest)
        if not args.execute:
            print(json.dumps({'manifest_sha256':digest,'max_paid_requests':len(checked),'requests':[x[2] for x in checked]},indent=2));return
        if args.approved_manifest_sha256!=digest:raise ValueError('Exact reviewed manifest hash required')
        receipt=Path(args.manifest).parent/'execution-receipt.json'
        with receipt.open('x') as file:json.dump({'manifest_sha256':digest,'attempt_started':True},file)
        log=Recorder(args.output,mode='spark_vision_bounded_batch')
        sources={name:sha((ROOT/name).read_bytes()) for name in ['scripts/known_design.py','src/benchmate/known_design.py','src/benchmate/providers.py','src/benchmate/records.py']}
        log.add('vision_batch_frozen',{'manifest_sha256':digest,'max_paid_requests':len(checked),'source_sha256':sources,'all_outputs_retained':True})
        outcomes=[]
        try:
            for entry,image,plan in checked:
                run,result=extract(image,entry['info'],entry['source_kind'],output=log.path/'attempts',
                    env_path=ROOT/'.env',budget_path=ROOT/'.private/api-budget.json')
                outcome={'id':entry['id'],'run':run.name,'status':result['status'],'requests':result['requests']}
                outcomes.append(outcome);log.add('image_attempt_recorded',outcome)
                print(json.dumps(outcome),flush=True)
            result={'outcomes':outcomes,'all_attempts_retained':True,'requests':sum(x['requests'] for x in outcomes),'hardware_IO':False}
            (log.path/'result.json').write_text(json.dumps(result,indent=2)+'\n');log.add('run_completed',result)
            print(json.dumps({'run':str(log.path),**result}),flush=True)
        except (Exception,KeyboardInterrupt) as exc:
            log.add('run_failed',{'error':type(exc).__name__,'outcomes':outcomes});raise
    else:
        if not 1024<=args.port<=65535:raise ValueError('Choose port 1024..65535')
        from benchmate.known_design_web import make_server
        from benchmate.design_replay import load_demo
        server=make_server(output=args.output,env_path=ROOT/'.env',budget_path=ROOT/'.private/api-budget.json',
            port=args.port,enable_api=args.execute,max_requests=args.max_requests,
            demo=load_demo(ROOT) if args.demo else None)
        print(json.dumps({'url':f'http://127.0.0.1:{server.server_port}','paid_API_enabled':args.execute,
            'record':str(server.intake_log.path),'hardware_IO':False}),flush=True)
        try:server.serve_forever()
        except KeyboardInterrupt:pass
        finally:server.intake_log.add('run_completed',{'server_stopped':True,'hardware_IO':False});server.server_close()


if __name__=='__main__':main()
