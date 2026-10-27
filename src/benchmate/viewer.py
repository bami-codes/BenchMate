"""Export a self-contained, read-only execution report from a verified record."""
import hashlib
from importlib.resources import files
import json
from pathlib import Path
from .records import read_events


def export_viewer(run,output=None):
    path=Path(run)
    if path.is_dir():path=path/'events.jsonl'
    read_events(path)  # Reject corrupted or incomplete records before rendering.
    raw=path.read_bytes()
    events=[json.loads(line) for line in raw.decode().splitlines()]
    payload=json.dumps({'events':events,'source_sha256':hashlib.sha256(raw).hexdigest(),
                        'run_id':path.parent.name},ensure_ascii=False,allow_nan=False)
    # JSON is data inside a script element: escape HTML delimiters explicitly.
    payload=payload.replace('&','\\u0026').replace('<','\\u003c').replace('>','\\u003e').replace('\u2028','\\u2028').replace('\u2029','\\u2029')
    template=files('benchmate').joinpath('viewer.html').read_text()
    target=Path(output) if output else path.parent/'report.html'
    if target.resolve()==path.resolve():raise ValueError('Report cannot overwrite the source record')
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(template.replace('/*RECORD_DATA*/',payload),encoding='utf-8')
    return target
