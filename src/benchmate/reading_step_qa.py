"""One explicitly selected fresh-boot step QA, unchanged wiring/guards, no API.

Reuses the original A3GuardMixin and PhysicalBench capture/firmware checks.
Order: three HOLD, one reserved-size step, one return HOLD; no retry/reset/refit.
All imports of serial/numpy are delayed so verification is stdlib-only.
"""
import argparse
import json
from pathlib import Path
import subprocess
import time

from .records import Recorder, canonical, decode_events
from .reading_rules import digest
from .reading_recovery import original_sources, check_publication, save, sha
from .reading_restored_v2 import verify as verify_failed
from .reading_verify import chain

ROOT = Path(__file__).resolve().parents[2]
NOTE = 'docs/2026-11-04-case02-step-QA.md'
FAILED = Path('examples/reading-restored-v2/2026-11-04/records/20261103T175520-a925a3910d')
STEP = {'kind': 'step', 'samples': 512, 'period_us': 500, 'amplitude_v': .35}
WAIT = 10.
CONFIRMATION = ('With USB off I retained the restored unloaded case02 specimen and all '
                'instrument/GND/REF wiring unchanged, removed probes, and reconnected '
                'the same USB port for the selected single fresh-boot step QA.')


def command_templates(protocol):
    # Local preparation only, not called by the stdlib verifier.
    from .instrument import InstrumentConfig, capture_command
    cfg = InstrumentConfig(**protocol['configuration'])
    boot = '1'*32
    arm = cfg.arm_command(boot).decode().strip().replace(boot, '{boot}')
    hold = capture_command(cfg, boot_id=boot, kind='hold', hold_v=cfg.ref_v,
                           samples=512, period_us=2000).decode().strip().replace(boot, '{boot}')
    step = capture_command(cfg, boot_id=boot, **STEP).decode().strip().replace(boot, '{boot}')
    return ['PING', 'PING', arm, 'PING'] + [s for c in (hold,hold,hold,step,hold) for s in (c,'PING')] + ['PING']


def make_plan(output):
    failed = verify_failed(ROOT/FAILED)
    if not failed['passed'] or failed['run_status'] != 'run_failed':
        raise ValueError('Verified terminal failed continuation required.')
    protocol = json.loads((ROOT/FAILED/'prepared/protocol.json').read_text())
    events = chain(ROOT/FAILED/'events.jsonl')
    commands = [e for e in events if e['kind']=='child_record_bound' and e['payload']['kind']=='terminal_diagnosis_failed']
    child = ROOT/FAILED/commands[-1]['payload']['file']
    native = chain(child)
    previous = next(e['payload']['boot_id'] for e in reversed(native)
                    if isinstance(e['payload'],dict) and e['payload'].get('type')=='pong')
    sources = dict(original_sources())
    sources.update(json.loads((ROOT/FAILED/'registration.json').read_text())['source_sha256'])
    for n in ('src/benchmate/reading_step_qa.py', 'src/benchmate/reading_recovery.py',
              'tests/test_reading_step_qa.py', NOTE):
        sources[n] = sha(ROOT/n)
    out = Path(output).resolve()
    out.mkdir(parents=True,exist_ok=False)
    plan = {'schema':'benchmate.fresh_boot_step_QA.v1', 'failed_record':str(FAILED),
        'failed_head_sha256':failed['head_sha256'], 'previous_boot_id':previous,
        'selected_by':'operator', 'operator_selection':'배선 변경 없이 새 부팅에서 같은 QA 1회',
        'wiring_change':False, 'protocol':protocol, 'protocol_sha256':digest(protocol),
        'source_sha256':sources, 'startup_wait_s':WAIT, 'ARM_max':1,
        'blocks_max':5, 'frames_max':2560, 'serial_commands_max':15,
        'block_order':['HOLD','HOLD','HOLD','STEP','HOLD'], 'step':STEP,
        'command_templates':command_templates(protocol), 'electrical_guards_unchanged':True,
        'A3_span_limit_mV':3., 'guard_history_reset_between_blocks':False,
        'firmware_upload':False, 'automatic_retry':False, 'SPARK_requests':0,
        'SAM_requests':0, 'estimated_USD':0., 'operator_confirmation':CONFIRMATION,
        'public_plan':str((out/'plan.json').relative_to(ROOT)),
        'scope':'Single new-boot unchanged-wiring reproducibility QA, not diagnosis, not full sine-then-step replay or proof of root-cause repair.'}
    save(out/'plan.json',plan)
    for n in sources:
        dst=out/'source'/n
        dst.parent.mkdir(parents=True,exist_ok=True)
        dst.write_bytes((ROOT/n).read_bytes())
    return plan


def validate_plan(plan):
    if (plan['schema']!='benchmate.fresh_boot_step_QA.v1' or plan['failed_record']!=str(FAILED)
            or plan['wiring_change'] is not False or plan['step']!=STEP
            or plan['block_order']!=['HOLD','HOLD','HOLD','STEP','HOLD']
            or (plan['ARM_max'],plan['blocks_max'],plan['frames_max'],plan['serial_commands_max'])!=(1,5,2560,15)
            or plan['startup_wait_s']!=WAIT or plan['A3_span_limit_mV']!=3.
            or plan['guard_history_reset_between_blocks'] is not False
            or plan['automatic_retry'] is not False or plan['operator_confirmation']!=CONFIRMATION
            or digest(plan['protocol'])!=plan['protocol_sha256']):
        raise ValueError('Frozen QA plan changed.')
    original_sources()
    for n,h in plan['source_sha256'].items():
        if sha(ROOT/n)!=h:
            raise ValueError('Frozen QA source changed: '+n)
    failed=verify_failed(ROOT/FAILED)
    if not failed['passed'] or failed['head_sha256']!=plan['failed_head_sha256'] or failed['run_status']!='run_failed':
        raise ValueError('Original failed continuation changed.')
    if json.loads((ROOT/FAILED/'prepared/protocol.json').read_text())!=plan['protocol']:
        raise ValueError('QA measurement protocol differs from failed attempt.')


def check(bench, board, previous_boot, *, monotonic=time.monotonic):
    from .instrument import BootContinuity, validate_boot_id
    c=BootContinuity()
    bench._ping(board,c,'QA_unarmed_PING',False)
    if c.boot_id==validate_boot_id(previous_boot):
        raise ValueError('Fresh unarmed boot required; no ARM.')
    bench.log.add('QA_USB_wait_started',{'boot_id':c.boot_id,'minimum_s':WAIT})
    start=monotonic()
    bench.sleep(WAIT)
    bench._ping(board,c,'QA_after_wait_PING',False)
    elapsed=monotonic()-start
    if elapsed<WAIT:
        raise ValueError('Ten-second wait not reached; no ARM.')
    bench.log.add('QA_USB_wait_completed',{'boot_id':c.boot_id,'minimum_s':WAIT,'elapsed_s':elapsed})
    packet=bench._request(board,c,bench.config.arm_command(c.boot_id),'QA_ARM',15)
    if packet.get('type')!='armed':
        raise ValueError('ARM not acknowledged; no capture.')
    bench._ping(board,c,'QA_armed_PING',True)
    bench.boot_id=c.boot_id
    for i in range(3):
        bench._hold(board,c,'QA_origin_'+str(i+1))
    bench.log.add('QA_step_requested',{'settings':STEP,'guard_history_preserved':True})
    rows=bench._capture(board,c,'QA_step',dict(STEP))
    bench._waveform_checks(rows,STEP)
    bench._hold(board,c,'QA_return_REF')
    bench._ping(board,c,'QA_final_PING',True)
    return c.boot_id


def run(plan_file, report_file, output, execute):
    if execute is not True:
        raise ValueError('Explicit selected --execute required.')
    plan=json.loads(Path(plan_file).read_text())
    validate_plan(plan)
    check_publication(plan_file)
    report=json.loads(Path(report_file).read_text())
    if report!={'verbatim':CONFIRMATION,'USB_off_wiring_confirmed':True,'USB_connected':True,
                'fixture':'unloaded','wiring_unchanged':True,'single_step_QA_selected':True}:
        raise ValueError('Actual unchanged-wiring USB reconnection confirmation required.')
    # One-shot marker survives even a preflight failure. No loop around run/check.
    with (Path(plan_file).parent/'execution-started.json').open('x') as f:
        json.dump({'automatic_retry':False,'attempts_max':1},f)
    import numpy as np
    import serial
    from .a3_ref_guard import A3GuardMixin, VERSION
    from .physical_bench import PhysicalBench
    class Bench(A3GuardMixin,PhysicalBench):
        pass
    log=Recorder(output,mode='single_fresh_boot_step_QA_no_API_not_diagnosis')
    save(log.path/'plan.json',plan)
    save(log.path/'operator-report.json',report)
    log.add('reference_step_QA_plan',plan)
    commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    log.add('QA_plan_publication',{'commit':commit,'remote':True,'plan_sha256':digest(plan),'before_serial':True})
    log.add('QA_operator_confirmation',report)
    bench=Bench(plan['protocol'],log,lambda *_:None,initial_report=report,
                previous_boot_id=plan['previous_boot_id'])
    passed=False
    try:
        ports=[p for p in bench.ports() if (p.vid,p.pid,p.serial_number)==tuple(plan['protocol']['USB_identity'])]
        if len(ports)!=1:
            raise ValueError('Expected Minima absent or ambiguous; no serial opened.')
        with serial.Serial(ports[0].device,115200,timeout=5,write_timeout=2) as board:
            bench.sleep(2)
            board.reset_input_buffer()
            check(bench,board,plan['previous_boot_id'])
        passed=True
        error=None
    except (Exception,KeyboardInterrupt) as exc:
        bench.stopped=True
        error=str(exc) if isinstance(exc,(ValueError,RuntimeError)) else type(exc).__name__
    events=decode_events(log.file.read_bytes(),require_terminal=False)
    packets=[e for e in events if isinstance(e['payload'],dict) and e['payload'].get('type') in ('capture','pong','armed','error')]
    last=packets[-1]['payload'] if packets else {}
    last_capture=max((e['sequence'] for e in events if e['kind']=='serial_command' and e['payload']['request'].startswith('CAPTURE ')),default=-1)
    park=(bool(packets) and packets[-1]['sequence']>last_capture and last.get('type')=='pong'
          and last.get('armed') is True and last.get('current_code')==last.get('ref_code')==bench.config.ref_code)
    means=np.asarray([r['means'] for r in bench.reference_means])
    spans=(np.ptp(means,axis=0)*1000).tolist() if len(means) else None
    result={'passed':passed,'error':error,'blocks_attempted':bench.capture_attempts,'frames':bench.frames,
        'boot_id':bench.boot_id,'guard_version':VERSION,'raw_mean_spans_mV':spans,
        'output_at_REF_confirmed':bool(park),'SPARK_requests':0,'SAM_requests':0,
        'estimated_USD':0.,'wiring_changed':False,'automatic_retry':False,'scope':plan['scope']}
    save(log.path/'result.json',result)
    log.add('run_completed' if passed else 'run_failed',result)
    print(json.dumps({'record':str(log.path),**result}),flush=True)
    return passed


def verify(path):
    out={'passed':False,'events':0,'error':None}
    try:
        root=Path(path)
        e=chain(root/'events.jsonl')
        plan=json.loads((root/'plan.json').read_text())
        if e[1]['kind']!='reference_step_QA_plan' or e[1]['payload']!=plan:
            raise ValueError('QA plan/file mismatch.')
        public=(ROOT/plan['public_plan']).resolve()
        if not public.is_relative_to(ROOT) or digest(json.loads(public.read_text()))!=digest(plan):
            raise ValueError('Published QA plan mismatch.')
        for name,h in plan['source_sha256'].items():
            file=(public.parent/'source'/name).resolve()
            if not file.is_relative_to((public.parent/'source').resolve()) or sha(file)!=h:
                raise ValueError('Frozen QA source snapshot mismatch.')
        failed=verify_failed(ROOT/plan['failed_record'])
        if not failed['passed'] or failed['run_status']!='run_failed' or failed['head_sha256']!=plan['failed_head_sha256']:
            raise ValueError('Failed predecessor changed.')
        publication=next(x for x in e if x['kind']=='QA_plan_publication')
        confirmation=next(x for x in e if x['kind']=='QA_operator_confirmation')
        report=json.loads((root/'operator-report.json').read_text())
        if confirmation['payload']!=report or report!={'verbatim':CONFIRMATION,'USB_off_wiring_confirmed':True,
                'USB_connected':True,'fixture':'unloaded','wiring_unchanged':True,'single_step_QA_selected':True}:
            raise ValueError('Actual operator reconnection report changed.')
        serial=[x for x in e if x['kind']=='serial_command']
        if (publication['payload']['plan_sha256']!=digest(plan) or publication['payload']['remote'] is not True
                or (serial and max(publication['sequence'],confirmation['sequence'])>=serial[0]['sequence'])):
            raise ValueError('Serial before matching plan publication.')
        pongs=[x['payload'] for x in e if isinstance(x['payload'],dict) and x['payload'].get('type')=='pong']
        boot=pongs[0]['boot_id'] if pongs else plan['previous_boot_id']
        actual=[x['payload']['request'] for x in serial]
        expected=[s.format(boot=boot) for s in plan['command_templates']]
        if actual!=expected[:len(actual)] or len(actual)>15:
            raise ValueError('Extra, reordered or unexpected serial command.')
        arms=[x for x in serial if x['payload']['request'].startswith('ARM ')]
        if arms:
            waited=next(x for x in e if x['kind']=='QA_USB_wait_completed')
            if (boot==plan['previous_boot_id'] or waited['sequence']>=arms[0]['sequence']
                    or waited['payload']['elapsed_s']<10. or pongs[0]['armed'] is not False):
                raise ValueError('ARM before fresh unarmed boot/ten-second wait.')
        guards=[x for x in e if x['kind']=='physical_electrical_guard']
        waves=[x for x in e if x['kind']=='physical_waveform_check']
        bad=[x for x in guards+waves if not all(x['payload']['checks'].values())]
        if len(bad)>1 or (bad and any(x['sequence']>bad[0]['sequence'] for x in serial)):
            raise ValueError('Command after first failed guard.')
        if any(x['payload'].get('guard_version')!='primary-REF-A3-v1' for x in guards):
            raise ValueError('Unexpected guard version.')
        result=json.loads((root/'result.json').read_text())
        if e[-1]['payload']!=result or result['SPARK_requests']!=0 or result['SAM_requests']!=0 or result['wiring_changed'] is not False or result['automatic_retry'] is not False:
            raise ValueError('QA result/usage mismatch.')
        captures=[x for x in serial if x['payload']['request'].startswith('CAPTURE ')]
        if result['blocks_attempted']!=len(captures) or not 0<=result['frames']<=512*len(captures):
            raise ValueError('QA frame/capture bounds mismatch.')
        packets=[x for x in e if isinstance(x['payload'],dict) and x['payload'].get('type') in ('capture','pong','armed','error')]
        last=packets[-1]['payload'] if packets else {}
        cap_seq=captures[-1]['sequence'] if captures else -1
        cfg=plan['protocol']['configuration']
        ref_code=round(4095*cfg['ref_v']/cfg['vref_v'])
        park=(bool(packets) and packets[-1]['sequence']>cap_seq and last.get('type')=='pong'
              and last.get('armed') is True and last.get('current_code')==last.get('ref_code')==ref_code)
        if result['output_at_REF_confirmed']!=park:
            raise ValueError('REF park not confirmed by a current post-capture PING.')
        if result['passed']:
            if (e[-1]['kind']!='run_completed' or len(actual)!=15 or len(guards)!=5 or bad
                    or result['frames']!=2560 or result['blocks_attempted']!=5 or len(waves)!=1
                    or not all(waves[0]['payload']['checks'].values())):
                raise ValueError('Incomplete passing five-block QA.')
        elif e[-1]['kind']!='run_failed':
            raise ValueError('Failure relabelled as completion.')
        out.update(passed=True,events=len(e),run_status=e[-1]['kind'],head_sha256=e[-1]['sha256'],
                   QA_passed=result['passed'],scope='internal_integrity+recorded_order',creation_time='unproven')
    except (ValueError,KeyError,TypeError,OSError,StopIteration,IndexError) as exc:
        out['error']=str(exc)
    return out


def main():
    p=argparse.ArgumentParser(description=__doc__)
    sub=p.add_subparsers(dest='command',required=True)
    a=sub.add_parser('plan');a.add_argument('--output',required=True)
    a=sub.add_parser('run')
    for name in ('plan','operator-report','output'):a.add_argument('--'+name,required=True)
    a.add_argument('--execute',action='store_true')
    a=sub.add_parser('verify');a.add_argument('record')
    args=p.parse_args()
    if args.command=='plan':
        v=make_plan(args.output)
        print(json.dumps({'plan':v['public_plan'],'blocks_max':5,'ARM_max':1,'API_calls':0,'estimated_USD':0.}))
        return 0
    if args.command=='run':
        return 0 if run(args.plan,args.operator_report,args.output,args.execute) else 1
    v=verify(args.record)
    print(('PASS' if v['passed'] else 'FAIL')+' '+json.dumps(v,separators=(',',':')))
    return 0 if v['passed'] else 1


if __name__=='__main__':
    raise SystemExit(main())
