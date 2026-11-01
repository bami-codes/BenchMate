"""Pinned, read-only examples for the design-to-evidence walkthrough.

The schematic was read on October 31. D01 was measured separately on October
30. A shared nominal design is not identity of specimens or a new experiment.
"""
import hashlib
import json
import math
from pathlib import Path
from .known_design import sanitize_image
from .viewer import load_record, render_viewer

D01 = 'examples/hardware-spark-rc/2026-10-30/20261029T174402-d3eaa8e612/execution'
VISION = 'examples/vision-spark/2026-10-31/20261031T060049-13a656638d/attempts/20261031T060050-8f3ccccdc9'
D01_SHA = '12ae389d77876283f62f520239ea4806a5dc77925c8bbe25708833922d29603f'
VISION_SHA = 'f50d93c66cc7fb797a6e983d8cd8e6283381f81f22dde8307d9ee0550a5e4909'
RESULT_SHA = '8809a3479d13249961f0f3cb4bedff98a6bf80835241519636057fef0d17d31e'
IMAGE_SHA = '02e3c887f773fccaf9b2a356e597f88cfce2b75e442ffb5b97595777acfadda0'


def matches_d01(reviewed):
    model = reviewed.get('nominal_design', {})
    return (reviewed.get('schema') == 'benchmate.reviewed_nominal_rc.v1'
            and math.isclose(model.get('R_ohm', 0), 10000., rel_tol=1e-12)
            and math.isclose(model.get('C_f', 0), 1e-6, rel_tol=1e-12))


def load_demo(root):
    root = Path(root)
    physical = load_record(root / D01)
    visual = load_record(root / VISION)
    raw = (root / VISION / 'result.json').read_bytes()
    original = (root / VISION / 'input.png').read_bytes()
    if (physical['source_sha256'] != D01_SHA or visual['source_sha256'] != VISION_SHA
            or hashlib.sha256(raw).hexdigest() != RESULT_SHA
            or hashlib.sha256(original).hexdigest() != IMAGE_SHA):
        raise ValueError('Recorded demo evidence changed')
    image, info = sanitize_image(original)
    if image != original:
        raise ValueError('Recorded demo image is not metadata-free')
    return {'image': image, 'info': info, 'result': json.loads(raw),
            'viewer': render_viewer(physical).encode(),
            'provenance': {'vision_record_sha256': VISION_SHA,
                           'physical_record_sha256': D01_SHA,
                           'vision_date_kst': '2026-10-31', 'physical_date_kst': '2026-10-30',
                           'same_specimen_established': False, 'new_measurement': False,
                           'synthetic_schematic': True}}
