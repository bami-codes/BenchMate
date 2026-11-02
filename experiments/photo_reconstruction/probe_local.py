"""Bounded local compatibility probes. Synthetic pixels only, no API or bench."""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import resource
import subprocess
import sys
import time


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for part in iter(lambda: f.read(1024 * 1024), b''):
            h.update(part)
    return h.hexdigest()


def environment():
    import cv2
    import numpy as np
    import torch
    result = {'schema': 'benchmate.photo_environment.v1', 'python': platform.python_version(),
              'os': platform.system(), 'os_version': platform.mac_ver()[0], 'architecture': platform.machine(),
              'packages': {name: importlib.metadata.version(name) for name in
                           ['torch', 'torchvision', 'numpy', 'Pillow', 'opencv-python-headless', 'einops', 'safetensors']},
              'mps_built': torch.backends.mps.is_built(), 'mps_available': torch.backends.mps.is_available(),
              'cuda_available': torch.cuda.is_available(), 'devices': {},
              'external_requests': 0, 'hardware_commands': 0}
    for device in ['cpu'] + (['mps'] if torch.backends.mps.is_available() else []):
        try:
            a = torch.arange(16, dtype=torch.float32).reshape(4, 4)
            expected = a @ a.T
            actual = (a.to(device) @ a.to(device).T).cpu()
            result['devices'][device] = {'matrix_multiply_passed': bool(torch.allclose(actual, expected))}
        except Exception as exc:
            result['devices'][device] = {'error_type': type(exc).__name__, 'error': str(exc)}
    image = np.zeros((64, 64), dtype=np.uint8)
    image[16:48, 16:48] = 255
    result['opencv_corner_detection_passed'] = cv2.goodFeaturesToTrack(image, 4, .01, 5).shape == (4, 1, 2)
    return result


def cotracker(source: Path, checkpoint: Path, device: str):
    import numpy as np
    import torch
    sys.path.insert(0, str(source.resolve()))
    from cotracker.predictor import CoTrackerPredictor

    torch.set_num_threads(4)
    torch.manual_seed(2718)
    record = {'schema': 'benchmate.model_compatibility.v1', 'model': 'CoTracker3 scaled offline',
              'device_requested': device, 'cpu_fallback_enabled': os.environ.get('PYTORCH_ENABLE_MPS_FALLBACK') == '1',
              'source_commit': subprocess.check_output(['git', '-C', str(source), 'rev-parse', 'HEAD'], text=True).strip(),
              'checkpoint_sha256': digest(checkpoint), 'torch_version': torch.__version__,
              'input': 'seeded synthetic translated texture; not captured video',
              'frames': 8, 'input_height': 192, 'input_width': 256, 'queries': 4,
              'use': 'compatibility only, not wire or circuit reconstruction evaluation',
              'external_requests': 0, 'hardware_commands': 0}
    start = time.monotonic()
    try:
        if device == 'mps' and not torch.backends.mps.is_available():
            raise RuntimeError('MPS unavailable')
        predictor = CoTrackerPredictor(checkpoint=None).eval()
        state = torch.load(checkpoint, map_location='cpu', weights_only=True)
        predictor.model.load_state_dict(state.get('model', state))
        predictor.to(device)
        record['model_resolution'] = list(predictor.interp_shape)
        texture = np.random.default_rng(2718).integers(0, 256, (192, 256, 3), dtype=np.uint8)
        frames = np.stack([np.roll(texture, shift=(i, 2 * i), axis=(0, 1)) for i in range(8)])
        video = torch.from_numpy(frames).permute(0, 3, 1, 2)[None].float().to(device)
        queries = torch.tensor([[[0, 70, 60], [0, 140, 60], [0, 70, 120], [0, 140, 120]]], dtype=torch.float32).to(device)
        record['load_seconds'] = round(time.monotonic() - start, 3)
        inference_start = time.monotonic()
        with torch.inference_mode():
            tracks, visibility = predictor(video, queries=queries)
        if device == 'mps':
            torch.mps.synchronize()
            record['mps_driver_allocated_bytes'] = torch.mps.driver_allocated_memory()
        tracks, visibility = tracks.cpu(), visibility.cpu()
        record.update({'status': 'passed' if bool(torch.isfinite(tracks).all()) and list(tracks.shape) == [1, 8, 4, 2] else 'invalid_output',
                       'inference_seconds': round(time.monotonic() - inference_start, 3),
                       'tracks_shape': list(tracks.shape), 'visibility_shape': list(visibility.shape),
                       'tracks': tracks.tolist(), 'visibility': visibility.tolist()})
    except Exception as exc:
        record.update({'status': 'failed', 'error_type': type(exc).__name__, 'error': str(exc)[:8000]})
    record['total_seconds'] = round(time.monotonic() - start, 3)
    record['process_peak_rss_bytes'] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * (1 if platform.system() == 'Darwin' else 1024)
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('probe', choices=['environment', 'cotracker'])
    parser.add_argument('--source', type=Path)
    parser.add_argument('--checkpoint', type=Path)
    parser.add_argument('--device', choices=['cpu', 'mps'], default='cpu')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError('Do not overwrite first probe results')
    if args.probe == 'environment':
        result = environment()
    else:
        if not args.source or not args.checkpoint:
            parser.error('CoTracker needs an existing source checkout and checkpoint')
        result = cotracker(args.source, args.checkpoint, args.device)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({key: value for key, value in result.items() if key not in ('tracks', 'visibility')}), flush=True)
    if result.get('status') not in (None, 'passed'):
        raise SystemExit(1)


if __name__ == '__main__':
    main()
