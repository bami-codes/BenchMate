"""Boundary and handoff checks for the versioned R/C/D/Q image reader."""
from copy import deepcopy
import io
import json
import struct
import zlib

import pytest
from PIL import Image

from benchmate.image_archive import verify_clean_png
from benchmate.netlist_intake import payload_for, reviewed, validate_candidate, extract
from benchmate.known_design import sanitize_image
from benchmate.netlist_diagnosis.design import CONFIRMATION


def part(name, kind, nodes, value=None, marking=''):
    return dict(name=name, kind=kind, nodes=nodes, value_si=value,
                marking=marking, evidence='Visible symbol and labelled wire.', bbox=[.1, .1, .9, .9])


def reading(parts):
    return dict(status='unverified_visual_candidate', candidate=dict(status='needs_review',
        summary='Visible intended schematic.', components=parts, ambiguities=[]))


def active():
    return reading([part('R1', 'R', ['IN', 'BASE'], 4700.),
                    part('R2', 'R', ['VCC', 'ANODE'], 1000.),
                    part('D1', 'D', ['ANODE', 'COL'], marking='red LED'),
                    part('Q1', 'Q', ['COL', 'BASE', 'GND'], marking='BC547B')])


def confirm(value, **kwargs):
    return reviewed(value, source_sha256='a'*64, confirmation=CONFIRMATION,
                    note='Operator verified every visible terminal and value.', **kwargs)


def test_active_graph_and_explicit_alias_handoff():
    r = confirm(active())
    assert r['schema'] == 'benchmate.reviewed_active_netlist.v2'
    assert r['elements'][3]['nodes'] == ['COL', 'BASE', 'GND']
    assert 'R1=Rbase' in r['reviewer_note']
    assert r['harness']['physical_calibration_and_wiring_approved'] is False


@pytest.mark.parametrize('change', ['swap_CE', 'ground_REF', 'diode_reverse', 'wrong_value'])
def test_incorrect_active_reading_cannot_be_silently_replaced(change):
    r = active(); p = r['candidate']['components']
    if change == 'swap_CE': p[3]['nodes'] = ['GND', 'BASE', 'COL']
    if change == 'ground_REF': p[3]['nodes'][2] = 'REF'
    if change == 'diode_reverse': p[2]['nodes'].reverse()
    if change == 'wrong_value': p[0]['value_si'] = 470.
    with pytest.raises(ValueError): confirm(r)


def test_wire_is_operator_addition_and_original_candidate_is_preserved():
    r = reading([part('R1', 'R', ['OUT', 'REF'], 10000.), part('C1', 'C', ['OUT', 'REF'], 1e-6)])
    original = deepcopy(r)
    out = confirm(r, add_direct_wire=True)
    assert r == original
    assert out['elements'][-1]['kind'] == 'W'
    assert 'Operator added' in out['reviewer_note']


def test_q_needs_three_nodes_and_no_invented_beta():
    r = active()['candidate']; r['components'][3]['nodes'].pop()
    with pytest.raises(ValueError): validate_candidate(r)
    r = active()['candidate']; r['components'][3]['value_si'] = 300
    with pytest.raises(ValueError): validate_candidate(r)


def test_c2pa_chunk_removed_even_when_pillow_info_is_empty():
    b = io.BytesIO(); Image.new('RGB', (12, 12), 'white').save(b, format='PNG')
    png = b.getvalue(); data = b'local signature not for the model'; kind = b'caBX'
    chunk = struct.pack('>I', len(data))+kind+data+struct.pack('>I', zlib.crc32(kind+data)&0xffffffff)
    original = png[:33]+chunk+png[33:]
    assert Image.open(io.BytesIO(original)).info == {}
    with pytest.raises(ValueError): verify_clean_png(original)
    clean, info = sanitize_image(original)
    verify_clean_png(clean)
    payload = json.dumps(payload_for(clean))
    assert 'signature not for the model' not in payload
    assert 'design-cases.json' not in payload
    assert info['source_sha256'] != info['sha256']


def test_one_failed_http_attempt_is_retained_without_retry(tmp_path):
    class Reply:
        status_code = 503
    class Client:
        calls = 0
        def post(self, *args, **kwargs):
            self.calls += 1
            return Reply()
    env = tmp_path/'env'; env.write_text('MODEL_API_KEY=test-only\n')
    b = io.BytesIO(); Image.new('RGB', (12, 12), 'white').save(b, format='PNG')
    image, info = sanitize_image(b.getvalue()); client = Client()
    run, result = extract(image, info, output=tmp_path/'runs', env_path=env,
                          budget_path=tmp_path/'budget.json', client=client)
    assert client.calls == result['requests'] == 1
    assert result['status'] == 'failed'
    assert (run/'result.json').exists()
    assert 'test-only' not in (run/'events.jsonl').read_text()
