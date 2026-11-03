"""Explicit pre-photo Spark-binding omission; one documentary SAM request only.

The pre-photo diagnostic record is archived byte-for-byte as a verified prefix.
Frozen numerical/photo sources stay unchanged. No restored component identity or
value is assigned. Offline verification imports no image/provider/serial module.
"""
import argparse
import contextlib
import io
import json
from pathlib import Path
import shutil

from . import reading_restored_v2 as prior
from .records import decode_events
from .reading_verify import chain, check_file

ROOT = prior.ROOT
NOTE = 'docs/2026-11-04-case02-restored-documentary-photo.md'
EXTRA = ('src/benchmate/reading_restored_sam_closeout.py',
         'tests/test_reading_restored_sam_closeout.py', NOTE)
CAPTION = 'No mismatch in the tests Spark chose'
ACTIVE = False


def sha(path):
    return prior.sha(path)


def pre_photo(events, photo_directory_exists=False):
    if photo_directory_exists or any(e['kind'] in ('documentary_scope_frozen','documentary_photo_received')
            or (e['kind']=='board_photo_received' and e['payload'].get('state')=='restored') for e in events):
        raise ValueError('Declare this amendment once, before restored photo intake/inspection.')
    diagnosis = next(e['payload'] for e in reversed(events) if e['kind']=='diagnosis_finished')
    if diagnosis['state']!='restored' or diagnosis['agent_report']['verdict']!='consistent' or diagnosis['agent_report']['components']:
        raise ValueError('A consistent restored diagnosis without a suspect is required.')


def declare(record):
    r=prior.runtime()
    log,_=prior.open_record(record,['awaiting_restored_photo'])
    events=decode_events(log.file.read_bytes(),require_terminal=False,include_hash=True)
    pre_photo(events,(log.path/'photo-restored').exists())
    audit=prior.verify(log.path)
    if not audit['passed']:
        raise ValueError('Pre-photo core audit failed.')
    # No photo path/bytes are accepted or accessed by declaration.
    temp=ROOT/'.private/documentary-core-snapshots'/log.path.name
    temp.parent.mkdir(parents=True,exist_ok=True)
    shutil.copytree(log.path,temp,ignore=shutil.ignore_patterns('*-local-only.json'))
    core=log.path/'documentary-core'
    shutil.move(str(temp),str(core))
    if not prior.verify(core)['passed'] or (core/'events.jsonl').read_bytes()!=log.file.read_bytes():
        raise ValueError('Core prefix snapshot differs from the existing record.')
    inventory=[{'file':str(f.relative_to(core)),'sha256':sha(f)} for f in sorted(core.rglob('*'))
               if f.is_file() and str(f.relative_to(core)) not in ('events.jsonl','state.json','verification.txt')]
    policy={'schema':'benchmate.restored_documentary_photo.v1','case_id':'02','restored_verdict':'consistent',
        'requested_by':'operator','after_diagnostic_result_known':True,'photo_already_uploaded':True,
        'before_photo_inspection':True,'before_photo_intake':True,'before_photo_capture':False,
        'reason':'No suspect after consistent rerun; previous Spark already abstained on parallel C1/C2 geometry. A further binding request is redundant.',
        'prior_binding_requirement_waived':True,'prior_binding_requirement_satisfied':False,
        'SAM_requests_max':1,'Spark_binding_requests_max':0,'Spark_value_requests_max':0,
        'SAM_scope':'Before/after documentary visualization only; never component identity, value, absence, or diagnosis evidence.',
        'restored_component_identification_used':False,'restored_body_group_confirmation_required':False,
        'core_record':'documentary-core','core_head_sha256':audit['head_sha256'],'core_inventory':inventory,
        'source_sha256':{n:sha(ROOT/n) for n in EXTRA},
        'public_policy':str(Path('examples/restored-documentary/2026-11-04/policies')/log.path.name/'scope.json')}
    out=log.path/'documentary-policy'
    r.save(out/'scope.json',policy)
    for n in EXTRA:
        target=out/'source'/n;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/n,target)
    public=ROOT/policy['public_policy']
    r.save(public,policy)
    shutil.copytree(out/'source',public.parent/'source')
    log.add('documentary_scope_frozen',{'file':'documentary-policy/scope.json','sha256':sha(out/'scope.json'),
        'core_prefix_head_sha256':audit['head_sha256'],'after_result_before_photo_inspection':True})
    r.state(log,'documentary_awaiting_photo')
    print(json.dumps({'record':str(log.path),'public_policy':policy['public_policy'],'Spark_max':0,'SAM_max':1,'image_bytes_read':0}))


def open_record(record,phases):
    r=prior.runtime()
    log,_=prior.open_record(record,phases)
    policy=json.loads((log.path/'documentary-policy/scope.json').read_text())
    for n,h in policy['source_sha256'].items():
        if sha(ROOT/n)!=h:
            raise ValueError('Frozen documentary source changed: '+n)
    return r,log,policy


def photo(args):
    r,log,policy=open_record(args.record,['documentary_awaiting_photo'])
    events=decode_events(log.file.read_bytes(),require_terminal=False)
    if not any(e['kind']=='documentary_scope_publication' for e in events):
        raise ValueError('Record remote policy publication before RAW conversion/intake.')
    from .photo_v2.pipeline import helper
    from .image_archive import verify_clean_png
    verify_clean_png(Path(args.image).read_bytes())
    out=log.path/'photo-restored/prepared'
    with contextlib.redirect_stdout(io.StringIO()):
        plan=helper('scripts/photo_parts.py').prepare(args.image,out)
    old=json.loads((ROOT/prior.PARENT/'photo-faulted/prepared/plan.json').read_text())
    if plan['input']['sha256']==old['input']['sha256']:
        raise ValueError('Fault photograph cannot be relabelled as a restored capture.')
    plan.update(schema='benchmate.restored_documentary_input.v1',concepts=['electronic component'],
        SAM_requests_max=1,Spark_reads_max=0,Spark_binding_requests_max=0,
        order='One generic SAM request, retain native masks and documentary overlays, no binding/value inference.',
        scope=policy['SAM_scope'],identification_evidence=False,surface_value_reading_enabled=False,
        policy_sha256=r.digest(policy),evaluation='known_case_documentary_not_blind')
    r.save(out/'plan.json',plan)
    conversion=json.loads(Path(args.conversion).read_text())
    if (conversion['source_metadata_copied'] is not False or conversion['source_GPS_or_EXIF_recorded'] is not False
            or conversion['images']['render.png']['sha256']!=sha(args.image)):
        raise ValueError('Fixed clean RAW conversion provenance required.')
    r.save(log.path/'photo-restored/raw-conversion.json',conversion)
    artifacts=[{'file':str(f.relative_to(log.path)),'sha256':sha(f)} for f in
               [out/'input.png',out/'clean-full.png',out/'plan.json',log.path/'photo-restored/raw-conversion.json']]
    log.add('documentary_photo_received',{'state':'restored','new_actual_state_operator_reported':True,
        'identification_evidence':False,'artifacts':artifacts})
    r.state(log,'documentary_awaiting_SAM')


def publish(record):
    r,log,policy=open_record(record,['documentary_awaiting_photo'])
    if any(e['kind']=='documentary_scope_publication' for e in decode_events(log.file.read_bytes(),require_terminal=False)):
        raise ValueError('Publication already recorded.')
    commit=r.committed(ROOT/policy['public_policy'])
    log.add('documentary_scope_publication',{'commit':commit,'remote':True,
        'policy_sha256':sha(log.path/'documentary-policy/scope.json'),'before_photo_intake':True})
    print(json.dumps({'record':str(log.path),'commit':commit,'image_bytes_read':0}))


def validate_SAM(events,input_sha):
    req=next(e['payload'] for e in events if e['kind']=='sam_request_frozen')
    result=events[-1]['payload']
    if (events[-1]['kind']!='run_completed' or result.get('model')!='sam-3.1' or result.get('requests')!=1
            or req['image_sha256']!=input_sha or req['concept']!='electronic component' or req['tool'] is not None
            or req['model']!='sam-3.1' or req['requests_max']!=1
            or any(e['kind']=='model_request_frozen' for e in events)):
        raise ValueError('Exactly one image-only generic SAM call required; Spark is omitted.')


def segment(args):
    global ACTIVE
    r,log,policy=open_record(args.record,['documentary_awaiting_SAM'])
    if args.execute is not True:
        raise ValueError('Explicit --execute required.')
    r.committed(ROOT/policy['public_policy'])
    r.start_stage(log,'documentary-SAM',args.execute)
    ACTIVE=True
    from .reading_photo import segment as sam
    p=log.path/'photo-restored/prepared'
    sam(p,r.BUDGET)
    outcome=json.loads((p/'sam-outcomes.json').read_text())[0]
    child=p/outcome['run']
    validate_SAM(chain(child/'events.jsonl'),json.loads((p/'plan.json').read_text())['input']['sha256'])
    r.linked(log,child,'restored_documentary_SAM')
    r.state(log,'documentary_awaiting_render')


def mask_overlay(prepared,native):
    from PIL import Image,ImageChops,ImageFilter
    manifest=json.loads((native/'crop-manifest.json').read_text())
    photo=Image.open(prepared/'input.png').convert('RGB')
    mask=Image.new('L',photo.size)
    drawn=0
    for o in manifest['objects']:
        if o['schematic_ref'] is not None or o['association_status']!='unassigned':
            raise ValueError('Documentary masks must have no component association.')
        if o['source_mask_file'] is None:
            continue
        m=Image.open(native/o['source_mask_file']).convert('L')
        if m.size!=photo.size:
            raise ValueError('Do not stretch a native mask.')
        mask=ImageChops.lighter(mask,m);drawn+=1
    edge=ImageChops.subtract(mask.filter(ImageFilter.MaxFilter(3)),mask.filter(ImageFilter.MinFilter(3)))
    return Image.composite(Image.new('RGB',photo.size,(30,190,120)),photo,edge),len(manifest['objects']),drawn


def render(args):
    global ACTIVE
    r,log,_=open_record(args.record,['documentary_awaiting_render'])
    ACTIVE=True
    from .photo_v2.pipeline import helper
    from PIL import Image,ImageDraw
    p=log.path/'photo-restored'
    with contextlib.redirect_stdout(io.StringIO()):
        helper('scripts/photo_parts.py').decode(p/'prepared',p/'native-SAM')
    after,count,drawn=mask_overlay(p/'prepared',p/'native-SAM')
    before_dir=ROOT/prior.PARENT/'photo-faulted'
    before,old_count,old_drawn=mask_overlay(before_dir/'prepared',before_dir/'decoded/native-SAM')
    out=p/'documentary';out.mkdir()
    after.save(out/'restored-SAM-overview.png',format='PNG')
    before.save(out/'faulted-SAM-overview.png',format='PNG')
    canvas=Image.new('RGB',(before.width+after.width+24,max(before.height,after.height)+70),'white')
    canvas.paste(before,(0,70));canvas.paste(after,(before.width+24,70))
    draw=ImageDraw.Draw(canvas)
    draw.text((12,6),'Faulted photograph - SAM regions',fill='black',font_size=24)
    draw.text((before.width+36,6),'Restored photograph - SAM regions',fill='black',font_size=24)
    draw.text((12,38),'Documentary visualization only. No component identity or value inferred.',fill='black',font_size=20)
    canvas.save(out/'before-after-SAM.png',format='PNG')
    manifest={'schema':'benchmate.documentary_SAM_comparison.v1','purpose':'visualization_only',
        'identification_evidence':False,'component_assignments':[],'values_read':[],
        'restored_mask_records':count,'restored_masks_drawn':drawn,
        'faulted_mask_records':old_count,'faulted_masks_drawn':old_drawn,
        'all_native_records_retained':True,'manual_mask_edits':False,'OpenCV_fallback_masks':0,
        'method':'All exact-size native masks, same three-pixel green boundary; images are not spatially registered.',
        'faulted_input':{'repo_file':str((before_dir/'prepared/input.png').relative_to(ROOT)),'sha256':sha(before_dir/'prepared/input.png')},
        'restored_input':{'file':'photo-restored/prepared/input.png','sha256':sha(p/'prepared/input.png')}}
    r.save(out/'manifest.json',manifest)
    log.add('documentary_masks_rendered',{'identification_evidence':False,'restored_mask_records':count,
        'artifacts':[{'file':str(f.relative_to(log.path)),'sha256':sha(f)} for d in (p/'native-SAM',out)
                     for f in sorted(d.rglob('*')) if f.is_file()]})
    r.state(log,'documentary_awaiting_close')
    print(json.dumps(manifest))


def result_value(mask_count):
    return {'schema':'benchmate.restored_documentary_closeout.v1','case_id':'02','source':'physical',
        'restored_verdict':'consistent','display_caption':CAPTION,'blind_test':False,
        'original_pair_status':'run_failed','original_failure_counted':True,'restored_followup_counted':True,
        'original_first_selection_unchanged':True,'operator_restored_and_rerun_consistent':True,
        'native_diagnostic_repair_claim_overwritten':False,'new_restored_photo_recorded':True,
        'restored_photo_documentary_only':True,'restored_binding_performed':False,
        'prior_restored_binding_requirement_waived':True,'prior_restored_binding_requirement_satisfied':False,
        'restored_component_identity_verified':False,'SAM_used_as_identification_evidence':False,
        'restored_mask_records':mask_count,'photo_Spark_requests':0,'photo_SAM_requests':1,
        'completed_under_explicit_photo_scope_amendment':True}


def close(args):
    r,log,policy=open_record(args.record,['documentary_awaiting_close'])
    r.committed(ROOT/policy['public_policy'])
    manifest=json.loads((log.path/'photo-restored/documentary/manifest.json').read_text())
    result=result_value(manifest['restored_mask_records'])
    log.add('restored_binding_omitted',{'reason':policy['reason'],'Spark_requests':0,
        'declared_before_photo_inspection':True,'omission_is_not_successful_binding':True})
    r.save(log.path/'result.json',result)
    log.add('run_completed',result)
    r.save(log.path/'state.json',{'phase':'completed_documentary_photo_binding_omitted','restored_verdict':'consistent'})
    r.update_index(log.path.name,status='completed',pending_stage=None,restored_verdict='consistent',
        completion_method='preserved_fault_reading_restored_rerun_plus_documentary_SAM_binding_omitted')
    print(json.dumps({'record':str(log.path),**result}))


def verify(record):
    out={'passed':False,'error':None}
    try:
        root=Path(record)
        core=root/'documentary-core'
        core_raw=(core/'events.jsonl').read_bytes()
        raw=(root/'events.jsonl').read_bytes()
        if not raw.startswith(core_raw):
            raise ValueError('Existing diagnostic prefix was rewritten.')
        base=prior.verify(core)
        if not base['passed']:
            raise ValueError('Archived core audit failed: '+str(base['error']))
        prefix=decode_events(core_raw,require_terminal=False,include_hash=True)
        pre_photo(prefix)
        events=decode_events(raw,require_terminal=False,include_hash=True)
        suffix=events[len(prefix):]
        if not suffix or suffix[0]['kind']!='documentary_scope_frozen':
            raise ValueError('No pre-photo scope declaration.')
        policy=json.loads(check_file(root,suffix[0]['payload']).read_text())
        if (policy['core_head_sha256']!=base['head_sha256'] or policy['SAM_requests_max']!=1
                or policy['Spark_binding_requests_max']!=0 or policy['Spark_value_requests_max']!=0
                or policy['before_photo_inspection'] is not True or policy['prior_binding_requirement_satisfied'] is not False
                or policy['restored_component_identification_used'] is not False):
            raise ValueError('Changed omission/visualization scope.')
        for item in policy['core_inventory']:
            check_file(core,item);check_file(root,item)
        for name,h in policy['source_sha256'].items():
            check_file(root,{'file':'documentary-policy/source/'+name,'sha256':h})
        publication=photo=sam=rendered=omitted=None
        added_events=0
        for e in suffix:
            k,p=e['kind'],e['payload']
            if k in ('run_completed','run_failed') and e is not events[-1]:
                raise ValueError('Event after terminal closeout.')
            if k in ('serial_command','diagnosis_started','training_forecasts_frozen'):
                raise ValueError('No new hardware/diagnostic stage is allowed in photo closeout.')
            if k in ('body_binding_proposed','body_binding','binding_parser_receipt','restored_body_group_confirmed'):
                raise ValueError('Restored correspondence cannot be silently reinstated.')
            if k=='documentary_scope_publication':
                if publication or photo or p['remote'] is not True or p['policy_sha256']!=sha(root/'documentary-policy/scope.json'):
                    raise ValueError('Late or invalid policy publication.')
                publication=p
            elif k=='documentary_photo_received':
                if not publication or photo or p['identification_evidence'] is not False:
                    raise ValueError('Photo before binding omission publication or wrong scope.')
                for item in p['artifacts']:check_file(root,item)
                photo=p
            elif k=='child_record_bound':
                if not photo or sam or p['kind'] not in ('restored_documentary_SAM','restored_documentary_SAM_failed'):
                    raise ValueError('Only one documentary SAM child is allowed.')
                file=check_file(root,p);child=chain(file,p['head_sha256'])
                inp=json.loads((root/'photo-restored/prepared/plan.json').read_text())
                if p['kind']=='restored_documentary_SAM':
                    validate_SAM(child,inp['input']['sha256'])
                else:
                    req=next(x['payload'] for x in child if x['kind']=='sam_request_frozen')
                    if (events[-1]['kind']!='run_failed' or child[-1]['kind']!='run_failed'
                            or req['model']!='sam-3.1' or req['image_sha256']!=inp['input']['sha256']
                            or req['concept']!='electronic component' or req['tool'] is not None):
                        raise ValueError('Unqualified failed SAM child.')
                sam=child;added_events+=len(child)
            elif k=='documentary_masks_rendered':
                if not sam or rendered or p['identification_evidence'] is not False:
                    raise ValueError('Unqualified mask visualization.')
                for item in p['artifacts']:check_file(root,item)
                comparison=json.loads((root/'photo-restored/documentary/manifest.json').read_text())
                if (comparison['purpose']!='visualization_only' or comparison['identification_evidence'] is not False
                        or comparison['component_assignments'] or comparison['values_read']
                        or comparison['manual_mask_edits'] is not False or comparison['OpenCV_fallback_masks']!=0):
                    raise ValueError('Documentary regions cannot become identification/value evidence.')
                rendered=p
            elif k=='restored_binding_omitted':
                if not rendered or omitted or p['Spark_requests']!=0 or p['omission_is_not_successful_binding'] is not True:
                    raise ValueError('False binding completion claim.')
                omitted=p
            elif k=='run_completed':
                if not omitted or p!=result_value(rendered['restored_mask_records']) or json.loads((root/'result.json').read_text())!=p:
                    raise ValueError('Incomplete or misleading documentary closeout.')
        out={**base,'passed':True,'events':base['events']+len(suffix)+added_events,
             'head_sha256':events[-1]['sha256'],'run_status':events[-1]['kind'],
             'restored_binding_performed':False,'restored_SAM_identification_evidence':False,'error':None}
    except (ValueError,TypeError,KeyError,OSError,StopIteration) as exc:
        out['error']=str(exc)
    return out


def fail(args,exc):
    r=prior.runtime()
    file=Path(args.record)/'events.jsonl'
    events=decode_events(file.read_bytes(),require_terminal=False,include_hash=True)
    if events[-1]['kind'] in ('run_completed','run_failed'):return
    from .records import Recorder
    log=Recorder.__new__(Recorder)
    log.path=file.parent;log.file=file;log.previous=events[-1]['sha256'];log.sequence=len(events)
    bound={e['payload']['file'] for e in events if e['kind']=='child_record_bound'}
    for child in (log.path/'photo-restored/prepared/sam').glob('*/events.jsonl'):
        if str(child.relative_to(log.path)) not in bound:
            try:r.linked(log,child.parent,'restored_documentary_SAM_failed')
            except ValueError:pass
    log.add('run_failed',{'stage':args.command,'error':str(exc) if isinstance(exc,(ValueError,RuntimeError)) else type(exc).__name__,
                          'automatic_retry':False,'restored_diagnostic_result_unchanged':True})
    r.update_index(log.path.name,status='failed',failed_stage=args.command)


def main():
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='command',required=True)
    for name in ('declare','publish','photo','segment','render','close','verify'):
        a=sub.add_parser(name);a.add_argument('record')
        if name=='photo':a.add_argument('--image',required=True);a.add_argument('--conversion',required=True)
        if name=='segment':a.add_argument('--execute',action='store_true')
    args=p.parse_args()
    if args.command=='verify':
        v=verify(args.record);print(('PASS' if v['passed'] else 'FAIL')+' '+json.dumps(v,separators=(',',':')))
        return 0 if v['passed'] else 1
    try:
        if args.command=='declare':declare(args.record)
        elif args.command=='publish':publish(args.record)
        else:{'photo':photo,'segment':segment,'render':render,'close':close}[args.command](args)
    except (Exception,KeyboardInterrupt) as exc:
        if ACTIVE:
            fail(args,exc)
        raise
    return 0


if __name__=='__main__':raise SystemExit(main())
