"""New protocol manifests; never rewrite a historical protocol or source file."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

from .design import checked, digest
from .menu import POLICY
from .session import PROMPT, TOOLS

ROOT = Path(__file__).resolve().parents[3]


def source_hashes():
    preserved = json.loads((ROOT/'docs/2026-11-02-frozen-sources.json').read_text())['source_sha256']
    for name, expected in preserved.items():
        if hashlib.sha256((ROOT/name).read_bytes()).hexdigest() != expected:
            raise ValueError('Preserved source changed: ' + name)
    paths = set(preserved) | {'scripts/netlist_diagnosis.py'}
    paths |= {str(p.relative_to(ROOT)) for p in Path(__file__).parent.glob('*.py')}
    return {name: hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in sorted(paths)}


def prepare(design, *, calibration=None):
    design = checked(design)
    base = calibration or json.loads((ROOT/'examples/d01-repair-protocol/2026-11-01-repair-first/protocol.json').read_text())
    p = {k: deepcopy(base[k]) for k in ('configuration', 'voltage_conversion', 'guard_limits', 'USB_identity', 'calibration_provenance')}
    p.update(version=POLICY['version'], diagnosis_policy=deepcopy(POLICY),
             reviewed_design_sha256=digest(design), source_sha256=source_hashes(),
             calibration_is_new=False, execution_authorized=False,
             reference_method='Separate three-block pre-stimulus HOLD origins at commanded REF; scored OUT excluded.',
             reference_scope='Provisional REF-relative/incremental coordinates; not absolute voltage calibration.',
             api_plan={'model': 'muse-spark-1.3', 'effort': 'medium', 'requests_max': 8,
                       'max_output_tokens': 4096, 'max_payload_bytes': 64000, 'prompt': PROMPT, 'tools': TOOLS,
                       'automatic_retry': False, 'image_requests': 0,
                       'transmitted': 'Reviewed netlist, chosen actions, sparse measured IN/OUT, fit summaries, prospective check summaries.',
                       'excluded': ['operator assembly truth', 'photos', 'case/portal names', 'raw ADC blocks', 'local paths', 'API keys']})
    return p


def validate(protocol, design):
    if (protocol.get('version') != POLICY['version'] or protocol.get('diagnosis_policy') != POLICY
            or protocol.get('reviewed_design_sha256') != digest(checked(design))
            or protocol.get('source_sha256') != source_hashes()):
        raise ValueError('Frozen diagnosis policy, reviewed design or source manifest mismatch.')
