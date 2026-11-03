"""Restored-only continuation after the separately scored unordered reading.

No frozen diagnostic source is changed. The existing reading_experiment.diagnose,
photo preparation, SAM and decoding functions are called directly. This adapter
only registers inherited evidence, uses the nullable binding parser and preserves
an unresolved parallel-body group in the final restored photo.
"""
import argparse
import json
from pathlib import Path
import shutil
import sys
from types import SimpleNamespace

from .records import Recorder, decode_events
from .reading_rules import digest
from .reading_verify import chain, check_file, verify_run as verify_parent
from .reading_group_experiment import verify as verify_group, sha, PARENT

ROOT = Path(__file__).resolve().parents[2]
NOTE = 'docs/2026-11-04-case02-restored-continuation.md'
EXTRA = ('src/benchmate/reading_restored_v2.py', 'src/benchmate/reading_binding_v2.py',
         'src/benchmate/reading_unordered.py', 'src/benchmate/reading_group_experiment.py',
         'tests/test_reading_restored_v2.py', NOTE)
GROUP = Path('examples/reading-groups/2026-11-04/records/20261103T174217-008035637b')
RESTORATION = ('USB off: install 1uF/105 at mini C8-C13; reinstall the same measured '
               '104 at E8-E13; retain R1 10k B3-B8, R2 20k D8-D13, large A35 to mini '
               'A3 and the instrument wiring. No output load, bypass or external diode. '
               'Remove probes and reconnect the same USB port.')
ACTIVE = False


def runtime():
    sys.path.insert(0, str(ROOT))
    from scripts import reading_experiment
    return reading_experiment


def eligible(parent, group, reading):
    if (not parent['passed'] or parent['run_status'] != 'run_failed'
            or not group['passed'] or group['run_status'] != 'run_completed'
            or reading['fits'] != ['changed:C1']
            or reading['conditional_unique_binding'] != {'C1': 'sam-2', 'C2': 'sam-3'}
            or reading['refitted'] is not False or reading['source'] != 'operator_dmm'):
        raise ValueError('Retained failed parent and completed unique unordered reading required.')


def group_confirmation(bodies, manifest):
    ids = [b['id'] for b in manifest['components']]
    if (len(bodies) != 2 or len(set(bodies)) != 2
            or any(b not in ids for b in bodies)):
        raise ValueError('Confirm two distinct existing capacitor body candidates; never invent masks.')
    return {'components': ['C1', 'C2'], 'sam_bodies': sorted(bodies),
            'correspondence': 'unresolved_parallel_group', 'individual_bindings': None,
            'chosen_by': 'operator', 'operator_confirmed': True,
            'confirmation_scope': 'These two bodies are the two capacitors, not which is C1.',
            'surface_values_used_for_scoring': False}


def prepare(report_file):
    r = runtime()
    frozen = r.check_freeze()
    old = ROOT/PARENT
    p = verify_parent(old)
    g = verify_group(ROOT/GROUP)
    reading = json.loads((ROOT/GROUP/'group-reading-score.json').read_text())
    eligible(p, g, reading)
    report = json.loads(Path(report_file).read_text())
    if report != {'instruction': RESTORATION, 'operator_verbatim': '완료',
                  'USB_off_wiring_confirmed': True, 'USB_reconnected': True,
                  'fixture': 'unloaded'}:
        raise ValueError('Actual confirmed restoration report required.')
    data = r.index()
    if any(a['case_id'] == '02' and a['status'] not in ('failed', 'completed') for a in data['attempts']):
        raise ValueError('Another case02 continuation is active.')
    log = Recorder(ROOT/'runs/reading-cohort', mode='unordered_reading_restored_continuation_v2')
    for name in ('reviewed-design.json', 'schematic.png'):
        shutil.copyfile(old/name, log.path/name)
    shutil.copytree(old/'prepared', log.path/'prepared')
    sources = {name: sha(ROOT/name) for name in EXTRA}
    for name in EXTRA:
        target = log.path/'additive-source'/name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT/name, target)
    prior = decode_events((old/'events.jsonl').read_bytes(), include_hash=True)
    boot = next(e['payload']['boot_id'] for e in prior if e['kind'] == 'diagnosis_finished' and e['payload']['state'] == 'faulted')
    registration = {'schema': 'benchmate.unordered_restored_continuation.v2', 'cohort': r.COHORT,
        'case_id': '02', 'run_id': log.path.name, 'attempt': 1+sum(a['case_id']=='02' for a in data['attempts']),
        'state': 'restored_only', 'official': True, 'counted': True, 'selected_first_attempt': False,
        'followup_of': old.name, 'original_pair': str(PARENT), 'original_status': 'run_failed',
        'original_head_sha256': p['head_sha256'], 'reading_group': str(GROUP),
        'reading_group_head_sha256': g['head_sha256'], 'original_selection_unchanged': True,
        'source_sha256': sources, 'original_freeze_sha256': digest(frozen), 'previous_boot_id': boot,
        'blind_test': False, 'inherited_data_sent_to_diagnostic_model': False,
        'diagnostic_Spark_max': 8, 'SAM_max': 1, 'binding_Spark_max': 1,
        'restored_photo_required': True, 'binding_version': 'nullable-v2',
        'restored_body_identity_may_remain_unresolved': True,
        'public_registration': str(r.PUBLIC/'registrations'/(log.path.name+'.json'))}
    r.save(log.path/'registration.json', registration)
    r.save(ROOT/registration['public_registration'], registration)
    r.save(log.path/'operator-restoration-report.json', report)
    log.add('restored_continuation_registered', registration)
    log.add('inherited_records_bound', {'original_head_sha256': p['head_sha256'], 'reading_group_head_sha256': g['head_sha256']})
    assembly = json.loads((ROOT/'runs/reading-cohort'/old.name/'faulted-assembly-local-only.json').read_text())
    sealed = next(e['payload']['sha256'] for e in prior if e['kind'] == 'specimen_assembly_sealed' and e['payload']['state'] == 'faulted')
    if digest(assembly) != sealed:
        raise ValueError('Original sealed assembly changed.')
    log.add('specimen_seal_opened', {'sealed_sha256': sealed, 'assembly': assembly,
            'after_group_reading_score': True, 'prior_release_note': 'docs/2026-11-04-case02-isolated-capacitance-result.md',
            'transmitted_to_model': False})
    log.add('operator_restoration_confirmed', report)
    log.add('continuation_artifacts_bound', {'artifacts': [{'file': str(f.relative_to(log.path)), 'sha256': sha(f)}
        for f in sorted(log.path.rglob('*')) if f.is_file() and f.name != 'events.jsonl']})
    r.state(log, 'awaiting_restored_preflight', case_id='02', requested_component='C1', last_boot=boot)
    data['attempts'].append({'run_id': log.path.name, 'case_id': '02', 'attempt': registration['attempt'],
        'status': 'registered', 'counted': True, 'selected_first_attempt': False,
        'execution_scope': 'restored_only_followup_after_unordered_reading', 'followup_of': old.name,
        'original_primary_status': 'failed'})
    r.save(ROOT/r.INDEX, data)
    print(json.dumps({'record': str(log.path), 'registration': registration['public_registration'], 'API_calls': 0, 'hardware_commands': 0}))


def open_record(path, phases):
    r = runtime()
    log = r.open_pair(path, phases)
    reg = json.loads((log.path/'registration.json').read_text())
    for name, h in reg['source_sha256'].items():
        if sha(ROOT/name) != h:
            raise ValueError('Frozen continuation source changed: '+name)
    return log, reg


def gate(log, reg, execute):
    global ACTIVE
    if execute is not True:
        raise ValueError('Explicit --execute required for a physical or paid stage.')
    runtime().committed(ROOT/reg['public_registration'])
    ACTIVE = True


def probe(args):
    r = runtime()
    log, reg = open_record(args.record, ['awaiting_restored_preflight'])
    gate(log, reg, args.execute)
    with (log.path/'PING-started.json').open('x') as f:
        json.dump({'commands_max': 1, 'stimuli': 0, 'automatic_retry': False}, f)
    # Same PING checks as the preserved passive_pilot probe, no ARM or capture.
    import time
    import serial
    from serial.tools import list_ports
    from .instrument import BootContinuity, receive_response
    protocol = json.loads((log.path/'prepared/protocol.json').read_text())
    child = Recorder(log.path/'preflight', mode='restored_continuation_PING_only')
    try:
        ports = [p for p in list_ports.comports() if (p.vid,p.pid,p.serial_number) == tuple(protocol['USB_identity'])]
        if len(ports) != 1:
            raise ValueError('Expected Minima absent or ambiguous; no port opened.')
        continuity = BootContinuity()
        with serial.Serial(ports[0].device, 115200, timeout=5, write_timeout=2) as board:
            time.sleep(2)
            board.reset_input_buffer()
            child.add('serial_command', {'request': 'PING', 'purpose': 'Read boot only; no ARM or stimulus'})
            if board.write(b'PING\n') != 5:
                raise ValueError('Incomplete PING write; no retry.')
            packet = receive_response(board, child, 'preflight_PING')
            continuity.check(packet)
        if (packet.get('type') != 'pong' or packet.get('armed') is not False
                or packet.get('current_code') != 0 or packet.get('ref_code') != 0
                or packet.get('dc_hold_supported') is not True
                or packet.get('adc_sample_state_channels') != [0,1,2,21]
                or packet.get('adc_sample_states_readback') != [255]*4
                or continuity.boot_id == reg['previous_boot_id']):
            raise ValueError('New unarmed v2 boot required; no ARM.')
        result = {'boot_id': continuity.boot_id, 'armed': False, 'commands': ['PING'], 'stimuli': 0}
        r.save(child.path/'result.json', result)
        child.add('run_completed', result)
        r.linked(log, child.path, 'preflight')
        r.state(log, 'awaiting_restored_setup', preflight_record=str(child.path.relative_to(log.path)))
        print(json.dumps({'record': str(log.path), 'preflight': str(child.path), **result}))
    except (Exception, KeyboardInterrupt) as exc:
        child.add('run_failed', {'error': str(exc), 'automatic_retry': False})
        r.linked(log, child.path, 'preflight_failed')
        raise


def run(args):
    r = runtime()
    log, reg = open_record(args.record, ['awaiting_restored_setup'])
    gate(log, reg, args.execute)
    # The preserved diagnose function builds the fresh model with only intended
    # design, own observations and unchanged tools. No inherited evidence enters.
    r.diagnose(SimpleNamespace(record=str(log.path), state='restored', execute=args.execute,
        initial_report=args.initial_report, assembly_record=args.assembly_record,
        previous_boot_id=reg['previous_boot_id'], preflight_run=str(log.path/log.control['preflight_record'])))


def photo_stage(args):
    r = runtime()
    phases = {'photo': ['awaiting_restored_photo'], 'segment': ['awaiting_restored_segmentation'],
              'decode': ['awaiting_restored_decode'], 'bind': ['awaiting_restored_binding']}
    log, reg = open_record(args.record, phases[args.command])
    if args.command in ('segment','bind'):
        gate(log, reg, args.execute)
    if args.command == 'photo':
        return r.photo_prepare(args)
    if args.command == 'segment':
        return r.segment(args)
    if args.command == 'decode':
        return r.decode(args)
    from .reading_binding_v2 import binding_request
    r.start_stage(log, 'restored-body-binding', args.execute)
    child, proposal, receipt = binding_request(log.path/'photo-restored/decoded', log.path/'schematic.png',
        'C1', r.BUDGET, log.path/'photo-restored/binding')
    r.linked(log, child, 'body_binding')
    log.add('body_binding_proposed', {'state': 'restored', **proposal})
    log.add('binding_parser_receipt', receipt)
    r.save(log.path/'photo-restored/binding-proposal.json', proposal)
    r.save(log.path/'photo-restored/binding-parser-receipt.json', receipt)
    r.state(log, 'awaiting_restored_group_confirmation')
    print(json.dumps({'proposal': proposal, 'receipt': receipt}))


def finish(args):
    r = runtime()
    log, _ = open_record(args.record, ['awaiting_restored_group_confirmation'])
    if args.operator_confirmed is not True:
        raise ValueError('Actual operator candidate-group confirmation required.')
    manifest = json.loads((log.path/'photo-restored/decoded/body-manifest.json').read_text())
    group = group_confirmation(args.bodies, manifest)
    r.save(log.path/'photo-restored/body-group.json', group)
    log.add('restored_body_group_confirmed', group)
    verdict = log.control['restored_verdict']
    result = {'case_id':'02', 'original_pair_status':'run_failed', 'original_selection_unchanged':True,
        'original_failure_counted':True, 'restored_followup_counted':True, 'blind_test':False,
        'reading_group_completed':True, 'restored_verdict':verdict,
        'operator_restored_and_rerun_consistent':verdict=='consistent',
        'display_caption':'No mismatch in the tests Spark chose' if verdict=='consistent' else None,
        'native_diagnostic_repair_claim_overwritten':False, 'new_restored_photo_recorded':True,
        'restored_body_identity':'unresolved_parallel_group'}
    r.save(log.path/'result.json', result)
    log.add('run_completed', result)
    r.update_index(log.path.name, status='completed', restored_verdict=verdict,
                   completion_method='preserved_fault_and_unordered_reading_plus_restored_followup')
    print(json.dumps({'record':str(log.path), **result}))


def verify(path):
    from . import verify as legacy
    out = {'passed':False, 'events':0, 'forecasts':0, 'measurements':0,
           'order_checks':0, 'prediction_files':0, 'error':None}
    try:
        root = Path(path)
        events = decode_events((root/'events.jsonl').read_bytes(), require_terminal=False, include_hash=True)
        reg = json.loads((root/'registration.json').read_text())
        if reg['original_pair'] != str(PARENT) or reg['reading_group'] != str(GROUP):
            raise ValueError('Unexpected inherited record.')
        parent, grouped = verify_parent(ROOT/PARENT), verify_group(ROOT/GROUP)
        reading = json.loads((ROOT/GROUP/'group-reading-score.json').read_text())
        eligible(parent, grouped, reading)
        if parent['head_sha256'] != reg['original_head_sha256'] or grouped['head_sha256'] != reg['reading_group_head_sha256']:
            raise ValueError('Inherited terminal head changed.')
        out.update(events=len(events)+parent['events']+grouped['events'], forecasts=parent['forecasts']+1,
                   measurements=parent['measurements']+2, order_checks=parent['order_checks']+2,
                   prediction_files=parent['prediction_files']+1)
        for name, h in reg['source_sha256'].items():
            check_file(root, {'file':'additive-source/'+name, 'sha256':h})
        registered = restored = preflight = diagnosis = photo = decoded = choice = receipt = confirmed = None
        terminal = False
        for e in events:
            if terminal:
                raise ValueError('Event after terminal.')
            k,p = e['kind'],e['payload']
            if k == 'restored_continuation_registered':
                if registered is not None or p != reg or p['original_status'] != 'run_failed' or p['original_selection_unchanged'] is not True:
                    raise ValueError('Registration or original accounting changed.')
                registered = p
            elif k == 'operator_restoration_confirmed':
                if not registered or restored or p['instruction'] != RESTORATION or p['operator_verbatim'] != '완료':
                    raise ValueError('Invalid restoration declaration.')
                restored = p
            elif k == 'continuation_artifacts_bound':
                for item in p['artifacts']:
                    check_file(root,item)
            elif k == 'specimen_seal_opened':
                original = chain(ROOT/PARENT/'events.jsonl')
                original_seal = next(x['payload']['sha256'] for x in original if x['kind']=='specimen_assembly_sealed' and x['payload']['state']=='faulted')
                if digest(p['assembly']) != p['sealed_sha256'] or p['sealed_sha256'] != original_seal or p['after_group_reading_score'] is not True:
                    raise ValueError('Released assembly differs from original commitment.')
            elif k == 'child_record_bound':
                file = check_file(root,p)
                child = chain(file,p['head_sha256'])
                if p['kind']=='preflight':
                    preflight = child[-1]['payload']
                    if not restored or preflight.get('armed') is not False or preflight.get('commands')!=['PING'] or preflight.get('stimuli')!=0 or preflight['boot_id']==reg['previous_boot_id']:
                        raise ValueError('Restored preflight is not a fresh unarmed PING.')
                    out['events'] += len(child)
                elif p['kind'].startswith('terminal_diagnosis'):
                    if not preflight:
                        raise ValueError('Diagnosis before preflight.')
                    audited = legacy.verify_run(file,expected_head=p['head_sha256'])
                    if not audited['passed']:
                        raise ValueError('Restored child audit: '+str(audited['error']))
                    for name in ('events','forecasts','measurements','order_checks','prediction_files'):
                        out[name] += audited[name]
                    if p['kind']=='terminal_diagnosis':
                        diagnosis = child[-1]['payload']['agent_report']
                else:
                    out['events'] += len(child)
                    if p['kind']=='body_binding':
                        choice = child[-1]['payload']['arguments']
            elif k == 'diagnosis_finished':
                if diagnosis is None or p['state']!='restored' or p['agent_report']!=diagnosis:
                    raise ValueError('Unbound restored diagnosis.')
            elif k == 'board_photo_received':
                if diagnosis is None or p['state']!='restored' or photo:
                    raise ValueError('Restored photo before diagnosis or duplicate.')
                for item in p['artifacts']:
                    check_file(root,item)
                photo = p
            elif k == 'bodies_decoded':
                if not photo or decoded:
                    raise ValueError('Decode before new restored photo or duplicate.')
                for item in p['artifacts']:
                    check_file(root,item)
                decoded = json.loads(check_file(root,{'file':p['manifest'],'sha256':p['sha256']}).read_text())
            elif k == 'binding_parser_receipt':
                from .reading_binding_v2 import parse_binding
                if not decoded or choice is None or parse_binding(choice,[b['id'] for b in decoded['components'] if b['read_selected']]) != p:
                    raise ValueError('Parser normalization not bound to original response.')
                receipt = p
            elif k == 'restored_body_group_confirmed':
                if not receipt or not decoded or group_confirmation(p['sam_bodies'],decoded)!=p:
                    raise ValueError('Unqualified or invented restored candidate group.')
                confirmed = p
            elif k in ('run_completed','run_failed'):
                terminal = True
                if k=='run_completed':
                    if not diagnosis or not photo or not confirmed or p['restored_verdict']!=diagnosis['verdict'] or p['original_pair_status']!='run_failed' or p['native_diagnostic_repair_claim_overwritten'] is not False:
                        raise ValueError('Incomplete restored case or rewritten native repair claim.')
                    if p['display_caption'] != ('No mismatch in the tests Spark chose' if diagnosis['verdict']=='consistent' else None):
                        raise ValueError('Wrong restored caption.')
        if registered is None or restored is None:
            raise ValueError('Missing registration/restoration.')
        out.update(passed=True,run_status=events[-1]['kind'],head_sha256=events[-1]['sha256'],
                   scope='internal_integrity+recorded_order',creation_time='unproven')
    except (ValueError,TypeError,KeyError,OSError,StopIteration) as exc:
        out['error']=str(exc)
    return out


def fail(args, exc):
    r = runtime()
    file = Path(args.record)/'events.jsonl'
    events = decode_events(file.read_bytes(), require_terminal=False, include_hash=True)
    if events[-1]['kind'] in ('run_completed','run_failed'):
        return
    log = Recorder.__new__(Recorder)
    log.path=file.parent;log.file=file;log.previous=events[-1]['sha256'];log.sequence=len(events)
    bound={e['payload']['file'] for e in events if e['kind']=='child_record_bound'}
    for child in log.path.rglob('events.jsonl'):
        if child==file or str(child.relative_to(log.path)) in bound:
            continue
        try:r.linked(log,child.parent,'failed_stage_retained')
        except ValueError:pass
    log.add('run_failed',{'stage':args.command,
        'error':str(exc) if isinstance(exc,(ValueError,RuntimeError)) else type(exc).__name__,
        'automatic_retry':False})
    r.update_index(log.path.name,status='failed',failed_stage=args.command)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    sub=p.add_subparsers(dest='command',required=True)
    a=sub.add_parser('prepare');a.add_argument('--restoration-report',required=True)
    for name in ('probe','run','photo','segment','decode','bind','confirm-group'):
        a=sub.add_parser(name);a.add_argument('--record',required=True)
        if name in ('probe','run','segment','bind'):a.add_argument('--execute',action='store_true')
        if name=='run':
            a.add_argument('--initial-report',required=True);a.add_argument('--assembly-record',required=True)
        if name=='photo':
            a.add_argument('--image',required=True);a.add_argument('--new-capture-confirmed',action='store_true')
        if name=='confirm-group':
            a.add_argument('--bodies',nargs=2,required=True);a.add_argument('--operator-confirmed',action='store_true')
    a=sub.add_parser('verify');a.add_argument('record')
    args=p.parse_args()
    if args.command=='verify':
        result=verify(args.record)
        print(('PASS' if result['passed'] else 'FAIL')+' '+json.dumps(result,separators=(',',':')))
        return 0 if result['passed'] else 1
    try:
        if args.command=='prepare':prepare(args.restoration_report)
        elif args.command=='probe':probe(args)
        elif args.command=='run':run(args)
        elif args.command=='confirm-group':finish(args)
        else:photo_stage(args)
    except (Exception,KeyboardInterrupt) as exc:
        if ACTIVE and hasattr(args,'record'):
            fail(args,exc)
        raise
    return 0


if __name__=='__main__':
    raise SystemExit(main())
