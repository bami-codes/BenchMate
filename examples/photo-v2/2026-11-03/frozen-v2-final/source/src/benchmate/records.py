"""Append-only event records with a hash chain; exact playback makes no API call."""
import hashlib
import json
from pathlib import Path
from datetime import datetime, timezone
import uuid


def canonical(value):
    return json.dumps(value,sort_keys=True,separators=(",",":"),allow_nan=False).encode()


class Recorder:
    def __init__(self, root="runs", *, mode):
        self.path=Path(root)/(datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")+"-"+uuid.uuid4().hex[:10])
        self.path.mkdir(parents=True,exist_ok=False)
        self.file=self.path/"events.jsonl"
        self.previous="0"*64
        self.sequence=0
        self.add("run_started",{"mode":mode,"schema_version":1})

    def add(self, kind, payload):
        event={"sequence":self.sequence,"timestamp":datetime.now(timezone.utc).isoformat(),
               "kind":kind,"payload":payload,"previous_sha256":self.previous}
        digest=hashlib.sha256(canonical(event)).hexdigest()
        with self.file.open("a",encoding="utf-8") as f:
            f.write(json.dumps({**event,"sha256":digest},allow_nan=False)+"\n")
            f.flush()
        self.previous=digest
        self.sequence+=1


def decode_events(raw, *, require_terminal=True, include_hash=False):
    events=[]; previous="0"*64
    for line in raw.decode('utf-8').splitlines():
        event=json.loads(line)
        digest=event.pop("sha256")
        if event["sequence"] != len(events) or event["previous_sha256"] != previous or hashlib.sha256(canonical(event)).hexdigest()!=digest:
            raise ValueError("Run integrity check failed")
        events.append({**event,'sha256':digest} if include_hash else event);previous=digest
    if require_terminal and (not events or events[-1]["kind"] not in ("run_completed","run_failed")):
        raise ValueError("Run is incomplete; no terminal event")
    return events


def read_events(path):
    path=Path(path)
    if path.is_dir(): path=path/"events.jsonl"
    return decode_events(path.read_bytes())
