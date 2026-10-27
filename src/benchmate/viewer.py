"""One evidence UI for complete offline exports and verified live log prefixes."""
import base64
import hashlib
from importlib.resources import files
import json
from pathlib import Path
from .records import decode_events


def load_record(run, *, live=False):
    path=Path(run)
    if path.is_dir():path=path/'events.jsonl'
    raw=path.read_bytes()
    if live and raw and not raw.endswith(b'\n'):
        # Recorder can be between writes, including within a UTF-8 codepoint.
        raw=raw[:raw.rfind(b'\n')+1]
    events=decode_events(raw,require_terminal=not live,include_hash=True)
    return {'events':events,'source_sha256':hashlib.sha256(raw).hexdigest(),
            'run_id':path.parent.name,'transport':'live_log' if live else 'replay',
            'integrity':'verified_prefix' if live else 'verified_complete'}


def render_viewer(record):
    payload=json.dumps(record,ensure_ascii=False,allow_nan=False)
    payload=payload.replace('&','\\u0026').replace('<','\\u003c').replace('>','\\u003e').replace('\u2028','\\u2028').replace('\u2029','\\u2029')
    resources=files('benchmate')
    css=resources.joinpath('viewer.css').read_text()
    for marker,name in [('/*FONT_REGULAR*/','IBMPlexSans-Regular.woff2'),('/*FONT_SEMIBOLD*/','IBMPlexSans-SemiBold.woff2')]:
        css=css.replace(marker,base64.b64encode(resources.joinpath('assets',name).read_bytes()).decode())
    return (resources.joinpath('viewer.html').read_text()
            .replace('/*CONNECT_POLICY*/',"'self'" if record.get('transport')=='live_log' else "'none'")
            .replace('/*VIEWER_CSS*/',css)
            .replace('/*VIEWER_JS*/',resources.joinpath('viewer.js').read_text())
            .replace('/*FONT_LICENSE*/',json.dumps(resources.joinpath('assets','OFL.txt').read_text()).replace('<','\\u003c'))
            .replace('/*RECORD_DATA*/',payload))


def export_viewer(run,output=None):
    path=Path(run)
    if path.is_dir():path=path/'events.jsonl'
    record=load_record(path)
    target=Path(output) if output else path.parent/'report.html'
    if target.resolve()==path.resolve():raise ValueError('Report cannot overwrite the source record')
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(render_viewer(record),encoding='utf-8')
    return target
