"""Whole VGGT-Omega operator compatibility, explicitly separating trained weights."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import resource
import subprocess
import sys
import time


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--device', choices=['cpu', 'mps'], required=True)
    parser.add_argument('--resolution', type=int, default=416)
    parser.add_argument('--frames', type=int, default=2)
    parser.add_argument('--checkpoint', type=Path)
    parser.add_argument('--image', type=Path, help='One metadata-free local master; no multi-state photo fusion')
    parser.add_argument('--prediction-dir', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.image:
        args.frames = 1
    if args.prediction_dir and args.prediction_dir.exists():
        raise FileExistsError('Keep earlier prediction arrays')
    if args.output.exists():
        raise FileExistsError('Keep the first result')
    if not (args.resolution in (128, 256, 416, 512) and 1 <= args.frames <= 6):
        raise ValueError('Bounded compatibility inputs only')
    import torch
    sys.path.insert(0, str(args.source.resolve()))
    from vggt_omega.models import VGGTOmega
    from vggt_omega.utils.pose_enc import encoding_to_camera
    torch.set_num_threads(4)
    torch.manual_seed(20261102)
    record = {'schema': 'benchmate.vggt_compatibility.v1', 'device': args.device,
              'source_commit': subprocess.check_output(['git', '-C', str(args.source), 'rev-parse', 'HEAD'], text=True).strip(),
              'torch': torch.__version__, 'dtype': 'float32', 'autocast': False,
              'cpu_fallback_enabled': os.environ.get('PYTORCH_ENABLE_MPS_FALLBACK') == '1',
              'weights': 'official checkpoint' if args.checkpoint else 'random initialization; NOT pretrained',
              'input': 'one local cleaned photo' if args.image else 'seeded synthetic RGB, NOT user photographs', 'frames': args.frames,
              'resolution': args.resolution, 'architecture_reduced': False,
              'claims': 'operator/device compatibility only; no geometric accuracy claim',
              'external_requests': 0, 'hardware_commands': 0, 'user_photos_uploaded': 0,
              'adapter_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    start = time.monotonic()
    try:
        print(json.dumps({'phase': 'constructing full architecture', 'device': args.device}), flush=True)
        model = VGGTOmega(autocast=False).eval()
        record['parameter_count'] = sum(p.numel() for p in model.parameters())
        if args.checkpoint:
            digest = hashlib.sha256()
            with args.checkpoint.open('rb') as file:
                for part in iter(lambda: file.read(1 << 20), b''):
                    digest.update(part)
            record['checkpoint_sha256'] = digest.hexdigest()
            state = torch.load(args.checkpoint, map_location='cpu', weights_only=True, mmap=True)
            model.load_state_dict(state, strict=True)
            record['state_dict_loaded_strictly'] = True
            record['checkpoint_bytes'] = args.checkpoint.stat().st_size
            del state
        model.to(args.device)
        if args.image:
            from benchmate.photo_bench.media import verify_local_master
            from vggt_omega.utils.load_fn import load_and_preprocess_images
            record['local_image'] = verify_local_master(args.image)
            images = load_and_preprocess_images([str(args.image)], image_resolution=args.resolution, mode='max_size').to(args.device)
        else:
            images = torch.rand(args.frames, 3, args.resolution, args.resolution).to(args.device)
        record['preprocessed_shape'] = list(images.shape)
        record['initialization_seconds'] = round(time.monotonic() - start, 3)
        print(json.dumps({'phase': 'forward', 'parameter_count': record['parameter_count']}), flush=True)
        forward_start = time.monotonic()
        with torch.inference_mode():
            output = model(images)
            extrinsics, intrinsics = encoding_to_camera(output['pose_enc'], output['images'].shape[-2:])
        if args.device == 'mps':
            torch.mps.synchronize()
            record['mps_driver_allocated_bytes_after_forward'] = torch.mps.driver_allocated_memory()
        record['forward_seconds'] = round(time.monotonic() - forward_start, 3)
        record['outputs'] = {k: {'shape': list(v.shape), 'device': str(v.device), 'finite': bool(torch.isfinite(v).all().cpu())}
                             for k, v in output.items()}
        record['camera_decode_finite'] = bool(torch.isfinite(extrinsics).all().cpu()) and bool(torch.isfinite(intrinsics).all().cpu())
        record['status'] = 'passed' if all(v['finite'] for v in record['outputs'].values()) and record['camera_decode_finite'] else 'nonfinite_output'
        if args.prediction_dir:
            import numpy as np
            args.prediction_dir.mkdir(parents=True, exist_ok=False)
            arrays = {key: output[key].detach().cpu().numpy() for key in ['pose_enc', 'depth', 'depth_conf']}
            arrays.update(extrinsics=extrinsics.detach().cpu().numpy(), intrinsics=intrinsics.detach().cpu().numpy())
            np.savez_compressed(args.prediction_dir / 'predictions.npz', **arrays)
            record['prediction_arrays_saved_locally'] = True
    except Exception as exc:
        record.update({'status': 'failed', 'error_type': type(exc).__name__, 'error': str(exc)[:8000]})
    record['total_seconds'] = round(time.monotonic() - start, 3)
    record['peak_rss_bytes'] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * (1 if platform.system() == 'Darwin' else 1024)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(record, indent=2) + '\n')
    print(json.dumps(record), flush=True)
    raise SystemExit(0 if record['status'] == 'passed' else 1)


if __name__ == '__main__':
    main()
