"""One bounded photo-binding follow-up; native SAM and OpenCV geometry stay distinct."""
import argparse
import hashlib
import json
import math
from pathlib import Path

from .reading_candidates_v3 import KINDS, PROMPT, parse
from .reading_photo_stage_v4 import validate_ports
from .records import Recorder, decode_events

ROOT = Path(__file__).resolve().parents[2]
SOURCES = (
    'src/benchmate/reading_photo_request_v5.py',
    'tests/test_reading_photo_request_v5.py',
    'docs/2026-11-04-photo-fallback-input-fix.md',
    'src/benchmate/reading_candidates_v3.py',
    'src/benchmate/reading_photo_stage_v4.py',
    'src/benchmate/reading_transport.py',
)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path, value):
    Path(path).write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n')


def geometry(body, full_size, input_size):
    """Never pretend an OpenCV fallback has a native SAM object or coordinates."""
    native = body.get('native_object')
    if native is not None:
        box = native['bounds_half_open']
        origin = 'native_SAM_input_coordinates'
    else:
        if body['localizer'] != 'OpenCV fallback':
            raise ValueError('Unknown candidate geometry provenance.')
        source = body['source_box']
        box = [math.floor(source[0] * input_size[0] / full_size[0]),
               math.floor(source[1] * input_size[1] / full_size[1]),
               math.ceil(source[2] * input_size[0] / full_size[0]),
               math.ceil(source[3] * input_size[1] / full_size[1])]
        origin = 'OpenCV_full_photo_box_scaled_to_input'
    if (len(box) != 4 or any(type(x) is not int for x in box)
            or not 0 <= box[0] < box[2] <= input_size[0]
            or not 0 <= box[1] < box[3] <= input_size[1]):
        raise ValueError('Invalid candidate geometry.')
    return {'id': body['id'], 'box_in_board_input_pixels': box,
            'localizer': body['localizer'], 'geometry_origin': origin,
            'lead_positions': None, 'lead_positions_status': 'Not independently extracted.'}


def request(parent):
    from PIL import Image
    from .agent import function_tool
    from .reading_transport import image_content
    parent = Path(parent).resolve()
    photo = parent / 'photo-faulted'
    decoded = photo / 'decoded'
    manifest_file = decoded / 'body-manifest.json'
    manifest = json.loads(manifest_file.read_text())
    selected = [c for c in manifest['components'] if c['read_selected']]
    ids = [c['id'] for c in selected]
    parse({'candidate_bodies': [], 'sam_body': None, 'mapping_status': 'unresolved',
           'reason': 'Input validation.'}, ids)
    state = json.loads((parent / 'state.json').read_text())
    schematic = parent / state['schematic_intake'] / 'input.png'
    board = photo / 'prepared/input.png'
    full = photo / 'prepared/clean-full.png'
    with Image.open(full) as im:
        full_size = im.size
    with Image.open(board) as im:
        input_size = im.size
    metadata = [geometry(c, full_size, input_size) for c in selected]
    tool = function_tool('propose_body_candidates',
        'Select plausible bodies and kinds; separately resolve or abstain on the schematic reference.', {
        'candidate_bodies': {'type': 'array', 'items': {'type': 'object', 'properties': {
            'sam_body': {'type': 'string', 'enum': ids},
            'kind': {'type': 'string', 'enum': KINDS}, 'reason': {'type': 'string'}},
            'required': ['sam_body', 'kind', 'reason'], 'additionalProperties': False}},
        'mapping_status': {'type': 'string', 'enum': ['unique', 'ambiguous', 'unresolved']},
        'sam_body': {'type': ['string', 'null'], 'enum': ids + [None]},
        'reason': {'type': 'string'}})
    text = PROMPT + '\nRequested component: ' + state['requested_component']
    text += '\nCandidate geometry: ' + json.dumps(metadata)
    images = [schematic, board]
    inventory_files = [manifest_file, full, schematic, board, parent / 'state.json']
    ports_file = parent / 'operator-photo-ports.json'
    if ports_file.exists():
        ports = validate_ports(json.loads(ports_file.read_text()))
        text += '\nOperator-confirmed connector ports only (not component references or values):\n' + json.dumps(ports)
        inventory_files.append(ports_file)
    content = [{'type': 'input_text', 'text': text},
               {'type': 'input_text', 'text': 'Intended schematic:'}, image_content(schematic.read_bytes()),
               {'type': 'input_text', 'text': 'Complete board photograph:'}, image_content(board.read_bytes())]
    for c in selected:
        view = c['views'][0]
        p = decoded / view['file']
        if sha(p) != view['sha256']:
            raise ValueError('Retained body crop changed.')
        images.append(p)
        content += [{'type': 'input_text', 'text': 'Body ' + c['id']}, image_content(p.read_bytes())]
    inventory = {str(p.relative_to(ROOT)): sha(p) for p in inventory_files + images[2:]}
    return content, tool, ids, inventory


def prepare(parent, output, public_plan):
    from .reading_timing_verify_v4 import verify_pair
    parent = Path(parent).resolve(); output = Path(output).resolve()
    result = verify_pair(parent)
    events = decode_events((parent / 'events.jsonl').read_bytes(), include_hash=True)
    if (not result['passed'] or events[-1]['kind'] != 'run_failed'
            or events[-1]['payload'] != {'stage': 'bind', 'error': 'KeyError', 'automatic_retry': False}):
        raise ValueError('This follow-up requires the preserved pre-provider binding failure.')
    if list((parent / 'photo-faulted/candidates-v3').glob('*/events.jsonl')):
        raise ValueError('Do not repeat an earlier candidate provider request.')
    content, tool, ids, inventory = request(parent)
    plan = {'schema': 'benchmate.photo_binding_followup.v5',
        'parent': str(parent.relative_to(ROOT)), 'parent_events_sha256': sha(parent / 'events.jsonl'),
        'parent_head_sha256': events[-1]['sha256'], 'parent_status': 'run_failed',
        'purpose': 'continue_photo_binding_after_pre_provider_input_error',
        'prior_failure_preserved_and_counted': True, 'new_terminal_diagnosis': False,
        'same_native_masks_reused': True, 'blind_test': False,
        'operator_numeric_values_supplied': False, 'surface_value_reading': False,
        'Spark_requests_max': 1, 'SAM_requests_max': 0, 'hardware_operations': 0,
        'candidate_ids_supplied': ids, 'inputs': inventory, 'tool': tool,
        'source_sha256': {n: sha(ROOT / n) for n in SOURCES},
        'request_content_sha256': hashlib.sha256(json.dumps(content, sort_keys=True).encode()).hexdigest(),
        'public_plan': str(Path(public_plan))}
    output.mkdir(parents=True, exist_ok=False)
    save(output / 'plan.json', plan)
    target = ROOT / public_plan; target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        raise ValueError('Public plan already exists.')
    target.write_bytes((output / 'plan.json').read_bytes())
    print(json.dumps({'plan': str(output.relative_to(ROOT)), 'candidates': ids,
                      'Spark_max': 1, 'SAM_max': 0, 'hardware': 0}))


def run(directory, execute):
    from .reading_transport import call
    from scripts import reading_experiment_timing_v4 as r
    directory = Path(directory).resolve(); plan = json.loads((directory / 'plan.json').read_text())
    if not execute:
        raise ValueError('Explicit execute required after the operator chooses to continue.')
    r.check_freeze()
    if (ROOT / plan['public_plan']).read_bytes() != (directory / 'plan.json').read_bytes():
        raise ValueError('Published/local plan differ.')
    commit = r.committed(ROOT / plan['public_plan'])
    parent = ROOT / plan['parent']
    if sha(parent / 'events.jsonl') != plan['parent_events_sha256']:
        raise ValueError('Preserved failed parent changed.')
    for n, h in plan['source_sha256'].items():
        if sha(ROOT / n) != h:
            raise ValueError('Prepared source changed: ' + n)
    content, tool, ids, inventory = request(parent)
    if (tool != plan['tool'] or ids != plan['candidate_ids_supplied'] or inventory != plan['inputs']
            or hashlib.sha256(json.dumps(content, sort_keys=True).encode()).hexdigest() != plan['request_content_sha256']):
        raise ValueError('Prepared request changed.')
    with (directory / 'started.json').open('x') as f:
        json.dump({'one_attempt': True, 'automatic_retry': False}, f)
    log = Recorder(directory / 'records', mode='photo_binding_followup_v5')
    log.add('photo_binding_followup_registered', {'plan_file': plan['public_plan'],
        'sha256': sha(directory / 'plan.json'), 'publication_commit': commit,
        'parent_events_sha256': plan['parent_events_sha256'],
        'parent_head_sha256': plan['parent_head_sha256'],
        'original_failed_pair_unchanged': True, 'hardware_operations': 0})
    try:
        child, result = call(content, tool=tool, output=log.path / 'spark', budget=r.BUDGET)
        r.linked(log, child, 'body_candidates_v5')
        receipt = parse(result['arguments'], ids)
        proposal = {'state': 'faulted', 'component': json.loads((parent / 'state.json').read_text())['requested_component'],
            'chosen_by': 'muse_spark', 'operator_confirmed': False, 'surface_values_read': False, **receipt}
        save(log.path / 'candidate-proposal.json', proposal)
        log.add('body_candidates_proposed', proposal)
        usage = result['usage']; cached = usage.get('input_tokens_details', {}).get('cached_tokens', 0)
        cost = ((usage['input_tokens'] - cached) * 1.25 + cached * .15 + usage['output_tokens'] * 4.25) / 1e6
        summary = {'Spark_requests': 1, 'SAM_requests': 0, 'hardware_operations': 0,
            'estimated_cost_USD': cost, 'rate_basis': 'retained cohort tariff; not invoice',
            'candidate_ids': [c['sam_body'] for c in receipt['candidate_bodies']],
            'mapping_status': receipt['mapping_status'], 'parent_failure_preserved': True}
        save(log.path / 'result.json', summary); log.add('run_completed', summary)
        print(json.dumps({'record': str(log.path.relative_to(ROOT)), **summary}))
    except BaseException:
        log.add('run_failed', {'automatic_retry': False, 'parent_failure_preserved': True})
        raise


def main():
    p = argparse.ArgumentParser(description=__doc__); sub = p.add_subparsers(dest='command', required=True)
    a = sub.add_parser('prepare'); a.add_argument('--parent', required=True); a.add_argument('--output', required=True); a.add_argument('--public-plan', required=True)
    a = sub.add_parser('run'); a.add_argument('directory'); a.add_argument('--execute', action='store_true')
    args = p.parse_args()
    if args.command == 'prepare':
        prepare(args.parent, args.output, args.public_plan)
    else:
        run(args.directory, args.execute)


if __name__ == '__main__':
    main()
