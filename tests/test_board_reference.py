"""Pixel-only local registration, no implicit experimental state or publication."""
import io,json
from pathlib import Path
import threading
import httpx
from PIL import Image
import pytest
from benchmate.photo_bench.board_reference import register_board
from benchmate.photo_bench.evidence import PhotoCatalog,CATALOG
from benchmate.case_review.web import make_server

ROOT=Path(__file__).resolve().parents[1]


def minimal(tmp_path):
    p=tmp_path/CATALOG;p.parent.mkdir(parents=True)
    p.write_text(json.dumps({'schema':'benchmate.photo_evidence_catalog.v1','photos':[],'selection_note':'software fixture'}))
    source=tmp_path/'qa-source.jpg'
    image=Image.new('RGB',(80,100),'blue');exif=Image.Exif();exif[270]='PRIVATE_METADATA_SENTINEL';exif[315]='PRIVATE_AUTHOR_SENTINEL'
    image.save(source,exif=exif)
    return source


def test_registration_strips_metadata_and_preserves_original(tmp_path):
    source=minimal(tmp_path);original=source.read_bytes()
    result=register_board(tmp_path,source,'QA before repair','Operator description only')
    c=PhotoCatalog(tmp_path);p=c.describe(result['photo_id'])
    assert c.default_reference()==result['photo_id'] and source.read_bytes()==original
    assert not p['same_state_verified'] and p['capture_state_id'] is None and not p['can_authorize_repair']
    assert p['role']=='operator_supplied_reference' and p['capture_note']=='Operator description only'
    for raw in (c.image(result['photo_id'],'master'),c.jpeg(result['photo_id'])):
        assert b'PRIVATE_METADATA_SENTINEL' not in raw and b'PRIVATE_AUTHOR_SENTINEL' not in raw
        with Image.open(io.BytesIO(raw)) as im:
            assert not im.getexif() and 'exif' not in im.info and 'icc_profile' not in im.info
    with pytest.raises(FileExistsError):register_board(tmp_path,source,'Again')


def test_new_capture_preserves_old_and_is_discovered_without_restart(tmp_path):
    source=minimal(tmp_path);c=PhotoCatalog(tmp_path)
    assert c.default_reference() is None
    first=register_board(tmp_path,source,'First')
    other=tmp_path/'second.png';Image.new('RGB',(80,100),'red').save(other)
    second=register_board(tmp_path,other,'Second')
    listing=c.list()
    assert len(listing['photos'])==2 and listing['default_reference_id']==second['photo_id']
    assert c.image(first['photo_id']) and listing['same_state_groups']==[]


def test_registration_cannot_point_at_an_arbitrary_local_file(tmp_path):
    source=minimal(tmp_path);r=register_board(tmp_path,source,'QA')
    path=tmp_path/'.private/photo-bench/board-captures'/r['photo_id']/'catalog-entry.json'
    p=json.loads(path.read_text());p['master']['path']='secret.png';path.write_text(json.dumps(p))
    with pytest.raises(ValueError,match='arbitrary'):PhotoCatalog(tmp_path).list()


def test_board_jpeg_route_uses_explicit_registered_photo_and_origin_guard(tmp_path):
    server=make_server(root=ROOT,output=tmp_path/'cases',port=0)
    t=threading.Thread(target=server.serve_forever,daemon=True);t.start()
    try:
        with httpx.Client(base_url=f'http://127.0.0.1:{server.server_port}',trust_env=False) as c:
            response=c.get('/board.jpg?photo=img_8885')
            assert response.status_code==200 and response.headers['Content-Type']=='image/jpeg'
            with Image.open(io.BytesIO(response.content)) as im:assert im.size==(1200,1600) and not im.getexif()
            assert c.get('/board.jpg?photo=../pictures/secret').status_code==404
            assert c.get('/board.jpg?photo=img_8885',headers={'Origin':'https://evil.example'}).status_code==403
            assert c.get('/board.jpg?photo=img_8885&photo=img_8887').status_code==400
    finally:server.shutdown();server.server_close();t.join(timeout=3)
