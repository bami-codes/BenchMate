"""Load explicitly allowed local settings without executing a shell."""
import os
from pathlib import Path


KEY_NAMES=("MODEL_API_KEY","BASETEN_API_KEY")


def load_keys(path=".env"):
    values={}
    p=Path(path)
    if p.exists():
        for line in p.read_text().splitlines():
            line=line.strip()
            if not line or line.startswith("#") or "=" not in line: continue
            key,value=line.split("=",1)
            key=key.strip()
            if key in KEY_NAMES:
                value=value.strip()
                if len(value)>=2 and value[0]==value[-1] and value[0] in "\"'": value=value[1:-1]
                values[key]=value
    return {key:os.environ.get(key) or values.get(key,"") for key in KEY_NAMES}


def redact(value, keys):
    if isinstance(value,str):
        for secret in keys.values():
            if secret: value=value.replace(secret,"[REDACTED]")
        return value
    if isinstance(value,list): return [redact(x,keys) for x in value]
    if isinstance(value,dict): return {k:redact(v,keys) for k,v in value.items()}
    return value

