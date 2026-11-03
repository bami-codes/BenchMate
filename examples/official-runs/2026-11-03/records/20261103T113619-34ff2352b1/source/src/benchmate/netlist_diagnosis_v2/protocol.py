"""Preserve all 66 v1 runtime files before adding active-profile sources."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

from ..netlist_diagnosis.design import digest
from .session import POLICY, PROMPT, TOOLS, checked

ROOT = Path(__file__).resolve().parents[3]


def source_hashes():
    baseline = json.loads((ROOT/'examples/netlist-diagnosis/2026-11-02/summary.json').read_text())['source_sha256']
    for name, expected in baseline.items():
        if hashlib.sha256((ROOT/name).read_bytes()).hexdigest() != expected:
            raise ValueError('Frozen v1 source changed: ' + name)
    paths = set(baseline) | {'scripts/netlist_diagnosis_v2.py'}
    paths |= {str(p.relative_to(ROOT)) for p in Path(__file__).parent.glob('*.py')}
    return {name: hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in sorted(paths)}


def prepare(design):
    design = checked(design)
    return {'version': POLICY['version'], 'source_sha256': source_hashes(),
            'reviewed_design_sha256': digest(design), 'reviewed_design': design,
            'policy': deepcopy(POLICY), 'prompt': PROMPT, 'tools': deepcopy(TOOLS),
            'execution_authorized': False, 'physical_LED_qualified': False,
            'api_plan': {'model': 'muse-spark-1.3', 'requests_max': 8, 'max_output_tokens': 4096,
                         'max_payload_bytes': 64000, 'automatic_retry': False, 'image_requests': 0},
            'calibration_required_before_LED_hardware': [
                'Actual supply and REF anchors, not packaging or default model voltages.',
                '47k/10k measurement divider ratio and loading, with absolute DC retained.',
                'GND and REF remain distinct; the BJT emitter uses GND.',
                'Existing nominal-REF HOLD guard cannot be used for a biased active output.',
                'No raw collector connection to the LM358 measurement input.'],
            'paid_requests': 0, 'hardware_commands': 0}
