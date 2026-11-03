"""Versioned generic localization, body-only crops and five fixed views."""
import hashlib
import importlib.util
import io
import json
import math
from pathlib import Path
import contextlib

from PIL import Image

from ..records import canonical

ROOT=Path(__file__).resolve().parents[3]
SOURCES=('src/benchmate/photo_v2/__init__.py','src/benchmate/photo_v2/decode.py',
 'src/benchmate/photo_v2/vision.py','src/benchmate/photo_v2/pipeline.py','scripts/photo_v2.py',
 'scripts/photo_parts.py','scripts/photo_model_probe.py','src/benchmate/known_design.py',
 'src/benchmate/image_archive.py','src/benchmate/providers.py','src/benchmate/config.py','src/benchmate/records.py',
 'docs/2026-11-03-photo-v2-protocol.md')
CONCEPT='electronic component'
VIEWS=('baseline','clahe','board_wb','upscale','mirror')


def sha(raw):return hashlib.sha256(raw).hexdigest()
def save(path,value):Path(path).write_text(json.dumps(value,indent=2,allow_nan=False)+'\n')


def helper(file):
    spec=importlib.util.spec_from_file_location('preserved_'+Path(file).stem,ROOT/file)
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m


def freeze(output):
    from .vision import PROMPT,TOOL
    out=Path(output);out.mkdir(parents=True,exist_ok=False)
    hashes={n:sha((ROOT/n).read_bytes()) for n in SOURCES}
    dev=[]
    for path in ('examples/official-photos/2026-11-03/01-faulted/conversion/render.png',
                 'examples/official-photos/2026-11-03/01-faulted/conversion/render-unsharpened.png',
                 'examples/official-photos/2026-11-03/01-faulted/prepared/input.png'):
        if (ROOT/path).exists():dev.append(sha((ROOT/path).read_bytes()))
    policy={'schema':'benchmate.photo_v2_policy.v1','source_sha256':hashes,'SAM_concept':CONCEPT,
      'SAM_requests_per_photo':1,'views':list(VIEWS),'Spark_requests_per_body':5,'max_workers':5,'body_read_limit':8,
      'source_development_images':dev,'automatic_retry':False,'body_refinement':'opening then largest contour convex hull',
      'body_open_radius_fraction':.08,'body_min_area':80,'body_max_area_fraction':.25,'neutral_background_RGB':[255,255,255],
      'fallback':{'method':'HSV blue contours','H_min_max':[90,135],'S_min':70,'V_min':30,'area_min':2000,'aspect_min_max':[.4,5.],'fill_min':.45,'duplicate_bbox_IoU':.65,'contained_fraction':.85},
      'white_reference':{'S_lt':60,'V_percentile_min':60,'min_pixels':2000,'target':'channel common mean'},
      'CLAHE':{'channel':'Lab L','clipLimit':2.,'tileGridSize':[8,8]},'upscale':3,'max_edge':1600,
      'literal_prompt':PROMPT,'literal_tool':TOOL,'vote_rules':{'whole_view_support_required':True,'band_tallies_retained':True,'E_series_filter':False,'ties_retained':True,'agreement_is_not_accuracy':True},
      'measurement_scope':'Independent observations; effective path does not uniquely verify visible part.',
      'first_prospective_test':'New photograph captured after policy publication, operator attestation required; not proof of double blinding or capture time.'}
    save(out/'policy.json',policy)
    for n in hashes:
        f=out/'source'/n;f.parent.mkdir(parents=True,exist_ok=True);f.write_bytes((ROOT/n).read_bytes())
    return policy


def check_policy(file):
    p=json.loads(Path(file).read_text())
    for n,h in p['source_sha256'].items():
        if sha((ROOT/n).read_bytes())!=h:raise ValueError('Frozen photo-v2 source changed: '+n)
    return p


def prepare(image,output,policy_file,evaluation,capture_after_freeze=False):
    p=check_policy(policy_file);source=Path(image).read_bytes()
    if evaluation=='prospective' and (not capture_after_freeze or sha(source) in p['source_development_images']):
        raise ValueError('A new image and capture-after-freeze operator attestation are required; development image is nonblind.')
    out=Path(output);parts=helper('scripts/photo_parts.py')
    with contextlib.redirect_stdout(io.StringIO()):plan=parts.prepare(image,out)
    if evaluation=='prospective' and plan['input']['sha256'] in p['source_development_images']:
        raise ValueError('Known development pixels cannot be a prospective test.')
    plan.update(schema='benchmate.photo_parts.v2',concepts=[CONCEPT],SAM_requests_max=1,
                Spark_reads_max=40,views_per_body=5,evaluation=evaluation,
                capture_after_freeze_operator_attested=capture_after_freeze,
                policy_sha256=sha(Path(policy_file).read_bytes()),policy=p,sources=p['source_sha256'])
    save(out/'plan.json',plan);return plan


def segment(prepared):
    d,p=helper('scripts/photo_parts.py').checked(prepared)
    with (d/'sam-started.json').open('x') as f:json.dump({'one_attempt':True},f)
    probe=helper('scripts/photo_model_probe.py')
    run,result=probe.sam_attempt((d/'input.png').read_bytes(),CONCEPT,allowed_concepts=(CONCEPT,),output=d/'sam')
    save(d/'sam-outcomes.json',[{'concept':CONCEPT,'run':str(run.relative_to(d)),**result}])
    return result


def _iou(a,b):
    inter=max(0,min(a[2],b[2])-max(a[0],b[0]))*max(0,min(a[3],b[3])-max(a[1],b[1]))
    return inter/max(1,(a[2]-a[0])*(a[3]-a[1])+(b[2]-b[0])*(b[3]-b[1])-inter)


def _contained(a,b):
    inter=max(0,min(a[2],b[2])-max(a[0],b[0]))*max(0,min(a[3],b[3])-max(a[1],b[1]))
    return inter/max(1,(a[2]-a[0])*(a[3]-a[1]))


def _png(rgb):
    image=Image.frombytes('RGB',(rgb.shape[1],rgb.shape[0]),rgb.tobytes());b=io.BytesIO();image.save(b,format='PNG');return b.getvalue()


def body_and_views(rgb,mask,wb_gains,out,prefix):
    """Keep actual body pixels, neutralize outside; never inpaint marks or holes."""
    import cv2
    import numpy as np
    ys,xs=np.where(mask!=0)
    if len(xs)<80:return None
    x1,x2=int(xs.min()),int(xs.max())+1;y1,y2=int(ys.min()),int(ys.max())+1
    roi=rgb[y1:y2,x1:x2];m=mask[y1:y2,x1:x2]!=0
    balanced=np.clip(roi.astype(np.float32)*wb_gains,0,255).astype(np.uint8)
    lab=cv2.cvtColor(roi,cv2.COLOR_RGB2LAB);lab[:,:,0]=cv2.createCLAHE(clipLimit=2.,tileGridSize=(8,8)).apply(lab[:,:,0])
    enhanced=cv2.cvtColor(lab,cv2.COLOR_LAB2RGB)
    arrays={'baseline':roi,'clahe':enhanced,'board_wb':balanced,'upscale':roi,'mirror':roi}
    views=[]
    for name in VIEWS:
        a=arrays[name].copy();a[~m]=255
        if name=='upscale':a=cv2.resize(a,None,fx=3,fy=3,interpolation=cv2.INTER_CUBIC)
        if name=='mirror':a=a[:,::-1].copy()
        image=Image.frombytes('RGB',(a.shape[1],a.shape[0]),a.tobytes());image.thumbnail((1600,1600),Image.Resampling.LANCZOS)
        raw=_png(np.asarray(image));file=prefix+'-'+name+'.png';(out/file).write_bytes(raw)
        views.append({'name':name,'file':file,'sha256':sha(raw),'flipped':name=='mirror','size':list(image.size)})
    cv2.imwrite(str(out/(prefix+'-body-mask.png')),mask)
    return {'id':prefix,'source_box':[x1,y1,x2,y2],'views':views,'mask_file':prefix+'-body-mask.png'}


def decode(prepared,output):
    import cv2
    import numpy as np
    if cv2.__version__!='4.12.0':raise ValueError('Pinned OpenCV 4.12.0 required')
    parts=helper('scripts/photo_parts.py');d,plan=parts.checked(prepared)
    out=Path(output);parts.decode(d,out/'native-SAM')
    native=json.loads((out/'native-SAM/crop-manifest.json').read_text())
    rgb=np.asarray(Image.open(d/'clean-full.png').convert('RGB'));h,w=rgb.shape[:2]
    small=np.asarray(Image.open(d/'input.png').convert('RGB'));sh,sw=small.shape[:2]
    hsv=cv2.cvtColor(rgb,cv2.COLOR_RGB2HSV);white=(hsv[:,:,1]<60)&(hsv[:,:,2]>=np.percentile(hsv[:,:,2],60))
    means=rgb[white].mean(axis=0) if np.count_nonzero(white)>=2000 else np.ones(3)
    gains=means.mean()/np.maximum(means,1.)
    cv2.imwrite(str(out/'white-reference-mask.png'),white.astype(np.uint8)*255)
    components=[];notes=[]
    for i,o in enumerate(native['objects']):
        if not o['source_mask_file']:
            notes.append({'source':'SAM','object':o['photo_component_id'],'skipped':'Native raster/bounds mismatch; no stretching'});continue
        original=np.asarray(Image.open(out/'native-SAM'/o['source_mask_file']).convert('L'))
        ys,xs=np.where(original!=0)
        if len(xs)<80 or len(xs)>.25*sw*sh:notes.append({'source':'SAM','object':o['photo_component_id'],'skipped':'Outside body area bounds: 80px to 25% of full photo'});continue
        radius=max(1,round(min(xs.max()-xs.min()+1,ys.max()-ys.min()+1)*.08))
        opened=cv2.morphologyEx(original,cv2.MORPH_OPEN,cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(2*radius+1,2*radius+1)))
        contours,_=cv2.findContours(opened,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
        if not contours:notes.append({'source':'SAM','object':o['photo_component_id'],'skipped':'No body survives opening'});continue
        selected=max(contours,key=cv2.contourArea);body=np.zeros_like(original);cv2.drawContours(body,[cv2.convexHull(selected)],-1,255,-1)
        full=cv2.resize(body,(w,h),interpolation=cv2.INTER_NEAREST)
        c=body_and_views(rgb,full,gains,out,'sam-'+str(i))
        if c:components.append({**c,'localizer':'SAM-derived body mask','native_object':o,'mask_derived_not_native':True,'native_mask_unchanged':True,'mask_coordinate_upsampling':'nearest-neighbor to full source'})
    blue=cv2.inRange(hsv,np.array([90,70,30]),np.array([135,255,255]))
    blue=cv2.morphologyEx(blue,cv2.MORPH_CLOSE,np.ones((7,7),np.uint8));blue=cv2.morphologyEx(blue,cv2.MORPH_OPEN,np.ones((3,3),np.uint8))
    cv2.imwrite(str(out/'OpenCV-blue-mask.png'),blue)
    contours,_=cv2.findContours(blue,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
    contours=sorted(contours,key=lambda c:(cv2.boundingRect(c)[1],cv2.boundingRect(c)[0]))
    for i,contour in enumerate(contours):
        x,y,cw,ch=cv2.boundingRect(contour);area=float(cv2.contourArea(contour));box=[x,y,x+cw,y+ch]
        eligible=area>=2000 and .4<=cw/ch<=5 and area/(cw*ch)>=.45
        note={'source':'OpenCV','contour':i,'box':box,'area':area,'eligible':eligible}
        if not eligible:notes.append(note);continue
        duplicate=next((c['id'] for c in components if _iou(box,c['source_box'])>=.65 or _contained(box,c['source_box'])>=.85),None)
        if duplicate:notes.append({**note,'duplicate_of':duplicate,'not_read_twice':True});continue
        mask=np.zeros((h,w),np.uint8);cv2.drawContours(mask,[cv2.convexHull(contour)],-1,255,-1)
        c=body_and_views(rgb,mask,gains,out,'cv-'+str(i))
        if c:components.append({**c,'localizer':'OpenCV fallback','mask_derived_not_native':True})
        notes.append(note)
    for i,c in enumerate(components):c['read_selected']=i<8
    manifest={'schema':'benchmate.body_views.v2','prepared':str(d.resolve()),'policy_sha256':plan['policy_sha256'],
              'input_sha256':plan['input']['sha256'],'evaluation':plan['evaluation'],'components':components,'notes':notes,
              'white_reference_RGB_gains':gains.tolist(),'original_full_size':[w,h],
              'Spark_requests_planned':min(8,len(components))*5,'all_candidates_retained':True,'hardware_IO':False,
              'libraries':{'OpenCV':cv2.__version__,'numpy':np.__version__,'Pillow':Image.__version__}}
    save(out/'body-manifest.json',manifest);return manifest


def read(decoded):
    from .decode import aggregate
    from .vision import read_five
    d=Path(decoded);m=json.loads((d/'body-manifest.json').read_text())
    _,plan=helper('scripts/photo_parts.py').checked(m['prepared'])
    if plan['policy_sha256']!=m['policy_sha256']:raise ValueError('Body policy changed')
    for c in m['components']:
        for v in c['views']:
            if sha((d/v['file']).read_bytes())!=v['sha256']:raise ValueError('Body view changed')
    with (d/'read-started.json').open('x') as f:json.dump({'one_attempt_only':True,'requests_max':m['Spark_requests_planned']},f)
    results=[]
    for c in m['components']:
        if not c['read_selected']:continue
        views=read_five(c,d,env_path=ROOT/'.env',budget_path=ROOT/'.private/photo-parts-budget.json')
        result={'component_id':c['id'],'localizer':c['localizer'],'raw_views':views,'decoded':aggregate(views),
                'evaluation':m['evaluation'],'schematic_ref':None,'component_binding_confirmed':False}
        results.append(result);save(d/'results.json',{'schema':'benchmate.photo_v2_results.v1','components':results,'expected_bodies':min(8,len(m['components'])),'completed':len(results)==min(8,len(m['components'])),'model_received_design_or_measurement':False})
    if not results:save(d/'results.json',{'schema':'benchmate.photo_v2_results.v1','components':[],'completed':True,'reason':'No eligible bodies','model_received_design_or_measurement':False})
    return results
