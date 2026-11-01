#!/usr/bin/env python3
"""One assembly-photo Spark read and two SAM concepts. No hardware or retries.

Freeze exact payload hashes before execute. Render is a separate, offline step
using Meta's pinned parser; it never repairs, selects or requests a better mask.
"""
import argparse
import base64
from dataclasses import asdict
import hashlib
import io
import json
from pathlib import Path
import sys
import time

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
import httpx
from PIL import Image,ImageDraw
from benchmate.config import load_keys,redact
from benchmate.known_design import extract,payload_for,request_plan,sanitize_image
from benchmate.providers import PROVIDERS,ProviderError,reserve_budget
from benchmate.records import Recorder,canonical,read_events

CONCEPTS=('capacitor','resistor')
ENDPOINT='https://api.meta.ai/v1/responses'
SOURCES=('scripts/photo_model_probe.py','src/benchmate/known_design.py',
         'src/benchmate/providers.py','src/benchmate/records.py','src/benchmate/config.py')

def sha(raw):return hashlib.sha256(raw).hexdigest()
def save(path,value):path.write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n')

def sam_payload(image,concept):
    if concept not in CONCEPTS:raise ValueError('Only the two planned concepts')
    return {'model':'sam-3.1','store':False,'stream':False,
        'metadata':{'mask_encoding':'one_bit','include_confidence':'true'},
        'input':[{'type':'message','role':'user','content':[
            {'type':'input_text','text':concept},
            {'type':'input_image','image_url':'data:image/png;base64,'+base64.b64encode(image).decode()}]}]}

def freeze(manifest_path,output):
    path=Path(manifest_path);manifest=json.loads(path.read_text())
    if len(manifest['images'])!=1:raise ValueError('Exactly one photo')
    entry=manifest['images'][0]
    if entry['source_kind']!='assembly_photo':raise ValueError('Actual assembly photo required')
    file=(path.parent/entry['file']).resolve()
    if file.parent!=path.parent.resolve():raise ValueError('Image must be beside manifest')
    image=file.read_bytes();clean,_=sanitize_image(image)
    if sha(image)!=entry['info']['sha256'] or image!=clean:raise ValueError('Expected clean canonical PNG')
    out=Path(output);out.mkdir(parents=True,exist_ok=False);(out/'input.png').write_bytes(image)
    plan={'schema':'benchmate.photo_model_probe.v1','destination':ENDPOINT,'requests_max':3,
        'order':['spark_vision','sam_capacitor','sam_resistor'],'hardware_IO':False,'automatic_retry':False,
        'image':entry['info'],'manifest_sha256':sha(path.read_bytes()),
        'source_files':{name:sha((ROOT/name).read_bytes()) for name in SOURCES},
        'vision':{**request_plan(entry['info'],'assembly_photo'),'payload_sha256':sha(canonical(payload_for(image,'assembly_photo')))},
        'sam':{concept:{'payload_without_image':sam_payload(b'',concept),
            'payload_sha256':sha(canonical(sam_payload(image,concept)))} for concept in CONCEPTS},
        'parser':'meta-sam-parser==0.1.0; offline only',
        'review_before_calls':{
            'photo':'One visible resistor and one blue box capacitor on foreground mini breadboard; other bench hardware visible in background.',
            'vision':'Review all reported values, ambiguity and whether unlabelled/occluded ports remain unresolved. Physical photo must not become nominal design or diagnosis.',
            'sam':'Review every returned mask, including misses and false positives. Body localization may work while thin leads remain incomplete; do not claim electrical connection or fault identification.',
            'scope':'One selected development image, no pixel ground-truth masks; qualitative feasibility only.',
            'exclusions':['original phone files','GPS/EXIF','other five photos','file names/paths','assembly instructions','nominal answer key','prior circuit results','ADC data']}}
    save(out/'plan.json',plan)
    print(json.dumps({'plan':str(out/'plan.json'),'sha256':sha((out/'plan.json').read_bytes()),'requests_max':3,'hardware_IO':False}))

def sam_attempt(image,concept,*,output):
    log=Recorder(output,mode='live_sam_single_photo_concept');payload=sam_payload(image,concept)
    log.add('sam_request_frozen',{'concept':concept,'payload_sha256':sha(canonical(payload)),
        'image_sha256':sha(image),'endpoint':ENDPOINT,'model':'sam-3.1','requests_max':1,'hardware_IO':False})
    keys={};requests=0;start=None
    try:
        keys=load_keys(ROOT/'.env');key=keys.get('MODEL_API_KEY')
        if not key:raise ProviderError('Local Meta key unavailable')
        reserve_budget(ROOT/'.private/api-budget.json','meta',1.);requests=1;start=time.monotonic()
        log.add('sam_request_sent',{'request_number':1})
        with httpx.Client(timeout=90,follow_redirects=False) as client:
            response=client.post(ENDPOINT,json=payload,headers={'Authorization':'Bearer '+key})
        elapsed=time.monotonic()-start
        if response.status_code>=400:
            # Keep the response error, excluding credentials; no request headers are logged.
            (log.path/'http-error.txt').write_text(redact(response.text[:16000],keys))
            raise ProviderError('Meta HTTP '+str(response.status_code))
        body=response.json()
        visible=[x for x in body.get('output',[]) if x.get('type') in ('message','function_call')]
        record=redact({'response_id':body.get('id'),'status':body.get('status'),'usage':body.get('usage'),
            'elapsed_s':elapsed,'visible_output':visible},keys)
        save(log.path/'response-visible.json',record);log.add('sam_reply',record)
        text=''.join(c.get('text','') for x in visible if x.get('type')=='message'
                     for c in x.get('content',[]) if c.get('type')=='output_text')
        (log.path/'output-text.txt').write_text(redact(text,keys))
        if body.get('status')!='completed' or any(x.get('type')=='function_call' for x in visible):
            raise ProviderError('Incomplete or unexpected response retained')
        result={'status':'completed','concept':concept,'requests':1,'elapsed_s':elapsed,
                'empty_output':not text.strip(),'hardware_IO':False,'visual_quality':'not_yet_reviewed'}
        save(log.path/'result.json',result);log.add('run_completed',result)
    except (Exception,KeyboardInterrupt) as exc:
        result={'status':'failed','concept':concept,'requests':requests,'error':str(exc) if isinstance(exc,ProviderError) else type(exc).__name__,
            'elapsed_s':None if start is None else time.monotonic()-start,'hardware_IO':False,'automatic_retry':False}
        save(log.path/'result.json',result);log.add('run_failed',result)
    return log.path,result

def execute(path,approved,output):
    path=Path(path);plan=json.loads(path.read_text());image=(path.parent/'input.png').read_bytes()
    if sha(path.read_bytes())!=approved or plan['requests_max']!=3 or plan['order']!=['spark_vision','sam_capacitor','sam_resistor']:
        raise ValueError('Exact reviewed three-call plan required')
    if plan['destination']!=ENDPOINT or sha(image)!=plan['image']['sha256']:raise ValueError('Destination/image mismatch')
    if sanitize_image(image)[0]!=image:raise ValueError('Canonical metadata-free image required')
    for name,digest in plan['source_files'].items():
        if sha((ROOT/name).read_bytes())!=digest:raise ValueError('Source changed: '+name)
    if sha(canonical(payload_for(image,'assembly_photo')))!=plan['vision']['payload_sha256']:raise ValueError('Vision payload mismatch')
    for concept in CONCEPTS:
        if sha(canonical(sam_payload(image,concept)))!=plan['sam'][concept]['payload_sha256']:raise ValueError('SAM payload mismatch')
    with (path.parent/'execution-receipt.json').open('x') as f:json.dump({'plan_sha256':approved,'attempt_started':True},f)
    log=Recorder(output,mode='real_photo_vision_and_sam_probe');save(log.path/'plan.json',plan)
    (log.path/'input.png').write_bytes(image);log.add('photo_probe_frozen',plan);outcomes=[]
    print(json.dumps({'stage':'started','run':str(log.path)}),flush=True)
    try:
        run,result=extract(image,plan['image'],'assembly_photo',output=log.path/'vision',
            env_path=ROOT/'.env',budget_path=ROOT/'.private/api-budget.json')
        outcomes.append({'task':'spark_vision','run':str(run.relative_to(log.path)),**result})
        log.add('photo_read_finished',outcomes[-1]);print(json.dumps({'task':'spark_vision','status':result['status']}),flush=True)
        for concept in CONCEPTS:
            run,result=sam_attempt(image,concept,output=log.path/'sam')
            outcomes.append({'task':'sam_'+concept,'run':str(run.relative_to(log.path)),**result})
            log.add('segmentation_finished',outcomes[-1]);print(json.dumps({'task':'sam_'+concept,**result}),flush=True)
        result={'requests':sum(x['requests'] for x in outcomes),'outcomes':outcomes,'all_attempts_retained':True,'hardware_IO':False}
        save(log.path/'result.json',result);log.add('run_completed',result)
        print(json.dumps({'stage':'completed','run':str(log.path),'requests':result['requests']}),flush=True)
    except (Exception,KeyboardInterrupt) as exc:
        log.add('run_failed',{'error':type(exc).__name__,'outcomes':outcomes,'hardware_IO':False});raise

def render(run,output):
    # SAM output is data. Do not execute any returned text or discard extra matches.
    from importlib.metadata import version
    from meta_sam_parser import image_segmentation_format,CompletedOutcome,decode_mask_to_raster
    if version('meta-sam-parser')!='0.1.0':raise ValueError('Use pinned parser 0.1.0')
    run=Path(run);read_events(run);image=Image.open(run/'input.png').convert('RGB')
    result=json.loads((run/'result.json').read_text());out=Path(output);out.mkdir(parents=True,exist_ok=False)
    reports=[]
    for attempt in result['outcomes']:
        if not attempt['task'].startswith('sam_') or attempt['status']!='completed':continue
        concept=attempt['concept'];raw=(run/attempt['run']/'output-text.txt').read_text()
        parser=image_segmentation_format().create_parser();parser.push(raw);parsed=parser.finish(CompletedOutcome()).result
        report={'concept':concept,'parser_version':version('meta-sam-parser'),'diagnostics':[asdict(x) for x in parsed.diagnostics],
                'records':[asdict(x) for x in parsed.records],'masks':[],'source_output_sha256':sha(raw.encode())}
        masks=[x for x in parsed.records if x.kind=='mask'];combined=image.convert('RGBA');colors=[(40,196,126),(242,146,56),(87,137,255)]
        if len(masks)>64:raise ValueError('Unexpected number of masks; raw output retained')
        for index,record in enumerate(masks):
            b=record.bounds;coords=[b.left,b.top,b.right,b.bottom]
            if not all(x==int(x) for x in coords) or not (0<=b.left<b.right<=image.width and 0<=b.top<b.bottom<=image.height):
                raise ValueError('Mask coordinates outside source image')
            if record.mask.width*record.mask.height>image.width*image.height:raise ValueError('Mask too large')
            raster=decode_mask_to_raster(record.mask)
            if len(raster)!=record.mask.width*record.mask.height or not set(raster)<=set((0,1)):raise ValueError('Invalid binary raster')
            mask=Image.frombytes('L',(record.mask.width,record.mask.height),bytes(x*255 for x in raster))
            source_mask=Image.new('L',image.size,0)
            size=(int(b.right-b.left),int(b.bottom-b.top))
            source_mask.paste(mask.resize(size,Image.Resampling.NEAREST),(int(b.left),int(b.top)))
            safe_id=int(record.object_id);name=f'{concept}-object-{safe_id}'
            source_mask.save(out/(name+'-mask.png'))
            color=colors[index%len(colors)];layer=Image.new('RGBA',image.size,(*color,0));layer.putalpha(source_mask.point(lambda v:round(v*.42)))
            overlay=Image.alpha_composite(image.convert('RGBA'),layer);overlay.convert('RGB').save(out/(name+'-overlay.png'))
            combined=Image.alpha_composite(combined,layer)
            report['masks'].append({'object_id':record.object_id,'bounds_half_open':coords,'confidence':record.confidence,
                'raster_size':[record.mask.width,record.mask.height],'source_mask_file':name+'-mask.png','overlay_file':name+'-overlay.png',
                'resize_to_box':list(mask.size)!=list(size),'foreground_pixels':sum(source_mask.histogram()[1:])})
        combined.convert('RGB').save(out/(concept+'-all-masks.png'))
        report['match_count']=len(masks);save(out/(concept+'-decoded.json'),report)
        reports.append({'concept':concept,'match_count':len(masks),'diagnostics':len(parsed.diagnostics)})
    save(out/'render-summary.json',{'source_run_sha256':sha((run/'events.jsonl').read_bytes()),'results':reports,
        'all_masks_rendered':True,'manual_mask_edits':False,'renderer_source_sha256':sha(Path(__file__).read_bytes()),'new_API_calls':0,'hardware_IO':False})
    print(json.dumps({'render':str(out),'results':reports}))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='command',required=True)
    f=sub.add_parser('freeze');f.add_argument('--manifest',required=True);f.add_argument('--output',required=True)
    e=sub.add_parser('execute');e.add_argument('--plan',required=True);e.add_argument('--approved-plan-sha256',required=True)
    e.add_argument('--output',default=str(ROOT/'runs/photo-model-probe'))
    r=sub.add_parser('render');r.add_argument('--run',required=True);r.add_argument('--output',required=True)
    args=p.parse_args()
    if args.command=='freeze':freeze(args.manifest,args.output)
    elif args.command=='execute':execute(args.plan,args.approved_plan_sha256,args.output)
    else:render(args.run,args.output)
