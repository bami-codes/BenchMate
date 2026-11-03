#!/usr/bin/env python3
"""One bounded operator-requested photo follow-up; no instrument or case truth."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import sys

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from benchmate.image_archive import verify_clean_png
from benchmate.records import read_events

SOURCES = ('scripts/photo_cv_followup.py', 'src/benchmate/known_design.py',
           'src/benchmate/image_archive.py', 'src/benchmate/records.py',
           'src/benchmate/providers.py', 'src/benchmate/config.py')


def sha(raw): return hashlib.sha256(raw).hexdigest()


def save(file, data):
    file.write_text(json.dumps(data, indent=2, allow_nan=False) + '\n')


def prepare(photo, output, deadline):
    import cv2
    import numpy as np
    if cv2.__version__ != '4.12.0':
        raise ValueError('Pinned OpenCV 4.12.0 required.')
    photo, out = Path(photo), Path(output)
    if out.exists(): raise ValueError('No overwrite or automatic repeat.')
    source = photo / 'conversion/render.png'
    raw = source.read_bytes(); image = cv2.imdecode(np.frombuffer(raw, np.uint8), cv2.IMREAD_COLOR)
    h, w = image.shape[:2]
    # Observer-selected whole-board ROI, not a component-value or diagnosis input.
    roi_fraction = [.14, .30, .89, .72]
    l,t,r,b = [round(a * z) for a,z in zip(roi_fraction, [w,h,w,h])]
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    roi = hsv[t:b,l:r]
    threshold = float(np.percentile(roi[:,:,2], 60))
    white = np.zeros((h,w), np.uint8)
    white[t:b,l:r] = ((roi[:,:,1] < 60) & (roi[:,:,2] >= threshold)).astype(np.uint8)*255
    if np.count_nonzero(white) < 2000: raise ValueError('Insufficient board reference; no fallback.')
    means = image[white != 0].mean(axis=0)
    gains = means.mean()/means
    balanced = np.clip(image.astype(np.float32)*gains,0,255).astype(np.uint8)
    bhsv = cv2.cvtColor(balanced, cv2.COLOR_BGR2HSV)
    blue = cv2.inRange(bhsv, np.array([90,70,30]),np.array([135,255,255]))
    outside = np.zeros((h,w), np.uint8);outside[t:b,l:r]=255
    blue = cv2.bitwise_and(blue,outside)
    blue = cv2.morphologyEx(blue,cv2.MORPH_CLOSE,np.ones((7,7),np.uint8))
    blue = cv2.morphologyEx(blue,cv2.MORPH_OPEN,np.ones((3,3),np.uint8))
    contours,_ = cv2.findContours(blue,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
    candidates=[]
    for c in contours:
        x,y,cw,ch=cv2.boundingRect(c);area=float(cv2.contourArea(c));aspect=cw/ch;fill=area/(cw*ch)
        accepted = area >= 2000 and .6 <= aspect <= 1.8 and fill >= .45
        candidates.append({'box':[x,y,x+cw,y+ch],'area':area,'aspect':aspect,'fill':fill,'eligible':accepted})
    eligible=[x for x in candidates if x['eligible']]
    if not eligible: raise ValueError('No compact blue component; no manual replacement.')
    selected=max(eligible,key=lambda c:c['area'])
    objects=json.loads((photo/'decoded/crop-manifest.json').read_text())['objects']
    sam=next(o for o in objects if o['concept']=='resistor')
    with Image.open(photo/'prepared/input.png') as small: sw,sh=small.size
    x1,y1,x2,y2=sam['bounds_half_open']
    boxes=[[math.floor(x1*w/sw),math.floor(y1*h/sh),math.ceil(x2*w/sw),math.ceil(y2*h/sh)]]
    x1,y1,x2,y2=selected['box'];dx=.05*(x2-x1);dy=.05*(y2-y1)
    boxes.append([max(0,math.floor(x1-dx)),max(0,math.floor(y1-dy)),min(w,math.ceil(x2+dx)),min(h,math.ceil(y2+dy))])
    out.mkdir(parents=True,exist_ok=False)
    cv2.imwrite(str(out/'board-reference-mask.png'),white)
    cv2.imwrite(str(out/'blue-mask.png'),blue)
    crops=[]
    for i,(x1,y1,x2,y2) in enumerate(boxes):
        crop=balanced[y1:y2,x1:x2]
        lab=cv2.cvtColor(crop,cv2.COLOR_BGR2LAB)
        lab[:,:,0]=cv2.createCLAHE(clipLimit=2.,tileGridSize=(8,8)).apply(lab[:,:,0])
        enhanced=cv2.cvtColor(lab,cv2.COLOR_LAB2BGR)
        up=cv2.resize(enhanced,None,fx=3,fy=3,interpolation=cv2.INTER_CUBIC)
        if max(up.shape[:2])>1600: raise ValueError('Three-times crop exceeds model bound; no silent rescale.')
        file=out/('crop-'+str(i+1)+'.png')
        rgb=cv2.cvtColor(up,cv2.COLOR_BGR2RGB)
        Image.frombytes('RGB',(rgb.shape[1],rgb.shape[0]),rgb.tobytes()).save(file)
        verify_clean_png(file.read_bytes())
        crops.append({'file':file.name,'sha256':sha(file.read_bytes()),'source_box_half_open':[x1,y1,x2,y2],
                      'source':'previous SAM resistor mask' if i==0 else 'OpenCV largest compact blue component',
                      'size':[up.shape[1],up.shape[0]],'synthetic_upscale':3,'new_spatial_detail_claimed':False})
    plan={'schema':'benchmate.photo_cv_followup.v1','deadline_utc':deadline,'source_sha256':sha(raw),
          'source':str(source),'sources':{n:sha((ROOT/n).read_bytes()) for n in SOURCES},
          'libraries':{'OpenCV':cv2.__version__,'numpy':np.__version__},'board_roi_fraction':roi_fraction,
          'board_white_reference':{'saturation_lt':60,'value_percentile_min':60,'value_threshold':threshold,
                                   'pixels':int(np.count_nonzero(white)),'BGR_means':means.tolist(),'BGR_gains':gains.tolist()},
          'blue_HSV_bounds':[[90,70,30],[135,255,255]],'blue_candidates':candidates,'selected_blue':selected,
          'blue_rule':{'area_min':2000,'aspect_min_max':[.6,1.8],'fill_min':.45,'selection':'largest eligible contour'},
          'CLAHE':{'channel':'Lab L only','clipLimit':2.,'tileGridSize':[8,8]},
          'upscale':{'factor':3,'interpolation':'INTER_CUBIC','no_new_information':True},'crops':crops,
          'Spark_requests_exactly':2,'automatic_retry':False,'stop_after_these_readings':True,
          'not_provided_to_models':['this plan','SAM concept','OpenCV selection label','component hints','design','diagnosis','truth','case mapping'],
          'hardware_IO':False,'previous_photo_attempt_retained':True}
    save(out/'plan.json',plan)
    print(json.dumps({'prepared':str(out),'crops':crops,'API_calls':0}),flush=True)


def read(directory):
    from benchmate.known_design import extract
    d=Path(directory);p=json.loads((d/'plan.json').read_text())
    if datetime.now(timezone.utc)>=datetime.fromisoformat(p['deadline_utc']): raise ValueError('Time box ended; no call.')
    for n,h in p['sources'].items():
        if sha((ROOT/n).read_bytes())!=h:raise ValueError('Source changed before call.')
    if len(p['crops'])!=2:raise ValueError('Exactly two crops required.')
    for c in p['crops']:
        if sha((d/c['file']).read_bytes())!=c['sha256']:raise ValueError('Crop changed.')
    with (d/'read-started.json').open('x') as f:json.dump({'one_attempt_only':True},f)
    results=[]
    for c in p['crops']:
        if datetime.now(timezone.utc)>=datetime.fromisoformat(p['deadline_utc']):break
        raw=(d/c['file']).read_bytes()
        run,result=extract(raw,verify_clean_png(raw),'assembly_photo',output=d/'vision',
                           env_path=ROOT/'.env',budget_path=ROOT/'.private/photo-parts-budget.json')
        results.append({'crop':c['file'],'run':str(run.relative_to(d)),**result})
        save(d/'results.json',{'results':results,'automatic_retry':False,'photo_stage_finished':len(results)==2,
                               'deadline_reached':datetime.now(timezone.utc)>=datetime.fromisoformat(p['deadline_utc'])})
        read_events(run)
        print(json.dumps({'crop':c['file'],'status':result['status']}),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='command',required=True)
    a=sub.add_parser('prepare');a.add_argument('--photo',required=True);a.add_argument('--output',required=True);a.add_argument('--deadline-utc',required=True)
    a=sub.add_parser('read');a.add_argument('--prepared',required=True);a.add_argument('--execute',action='store_true')
    a=p.parse_args()
    if a.command=='prepare':prepare(a.photo,a.output,a.deadline_utc)
    elif a.execute:read(a.prepared)
    else:raise SystemExit('Explicit --execute required.')
