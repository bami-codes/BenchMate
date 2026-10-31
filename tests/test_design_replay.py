"""A reviewed image must never silently become evidence for that same circuit."""
from copy import deepcopy
from pathlib import Path
import threading
import httpx

from benchmate.design_replay import D01_SHA, load_demo, matches_d01
from benchmate.known_design import confirm_design
from benchmate.known_design_web import make_server

ROOT = Path(__file__).resolve().parents[1]


def test_pinned_archive_and_nominal_match():
    demo = load_demo(ROOT)
    assert demo['provenance']['physical_record_sha256'] == D01_SHA
    original = demo['result']
    review = confirm_design(original, original['candidate'], reviewer_note='Software test review')
    assert matches_d01(review) and not review['measurement_verified']
    other = deepcopy(review)
    other['nominal_design']['C_f'] = 470e-9
    assert not matches_d01(other)
    assert not demo['provenance']['same_specimen_established']


def test_recorded_flow_requires_review_and_has_no_api(tmp_path):
    server = make_server(output=tmp_path/'ui', env_path=tmp_path/'.env',
                         budget_path=tmp_path/'budget', port=0, demo=load_demo(ROOT))
    thread = threading.Thread(target=server.serve_forever, daemon=True);thread.start()
    try:
        base = f'http://127.0.0.1:{server.server_port}'
        with httpx.Client(base_url=base) as client:
            html = client.get('/').text
            token = html.split('name="benchmate-session" content="')[1].split('"')[0]
            headers = {'X-BenchMate-Session': token, 'Origin': base}
            assert client.get('/replay/d01').status_code == 404
            item = client.post('/recorded-example', json={}, headers=headers).json()
            assert item['recorded'] and client.get('/state').json()['requests'] == 0
            args = {'id': item['id'], 'candidate': item['result']['candidate'], 'reviewer_note': ''}
            assert client.post('/confirm', json=args, headers=headers).status_code == 400
            assert client.get('/replay/d01').status_code == 404
            args['reviewer_note'] = 'Software test: nominal schematic reviewed'
            mismatch = deepcopy(args);mismatch['candidate']['components'][1]['value_si'] = 470e-9
            reviewed = client.post('/confirm', json=mismatch, headers=headers).json()
            assert not reviewed['historical_example']['available']
            assert client.get('/replay/d01').status_code == 404
            # A new review gets a new local file; the published vision output stays immutable.
            item = client.post('/recorded-example', json={}, headers=headers).json()
            args['id'] = item['id']
            reviewed = client.post('/confirm', json=args, headers=headers).json()
            assert reviewed['historical_example']['available']
            assert not reviewed['measurement_verified'] and not reviewed['historical_example']['new_measurement']
            response = client.get('/replay/d01')
            assert response.status_code == 200 and D01_SHA in response.text
            assert "frame-ancestors 'self'" in response.headers['content-security-policy']
            assert client.get('/state').json()['requests'] == 0
            assert not (tmp_path/'budget').exists()
    finally:
        server.shutdown();server.server_close();thread.join()
