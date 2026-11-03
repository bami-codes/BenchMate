#!/usr/bin/env python3
"""Fixed RAW conversion for photographed evidence; no API, metadata or local paths."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import struct
import sys

import numpy as np
import rawpy
from PIL import Image, ImageFilter, __version__ as pillow_version

VERSION = 'benchmate.raw_photo_conversion.v1'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def clean_png(image):
    clean = Image.frombytes('RGB', image.size, image.convert('RGB').tobytes())
    stream = io.BytesIO(); clean.save(stream, format='PNG')
    raw = stream.getvalue(); offset = 8; chunks = []
    while offset < len(raw):
        size = struct.unpack('>I', raw[offset:offset + 4])[0]
        chunks.append(raw[offset + 4:offset + 8].decode('ascii'))
        offset += 12 + size
    if set(chunks) != {'IHDR', 'IDAT', 'IEND'} or offset != len(raw):
        raise ValueError('Unexpected PNG metadata or trailing bytes.')
    return raw, {'sha256': sha(raw), 'width': clean.width, 'height': clean.height,
                 'bytes': len(raw), 'chunks': sorted(set(chunks)), 'metadata_present': False}


def convert(source, output):
    if rawpy.__version__ != '0.27.1' or pillow_version != '12.3.0':
        raise ValueError('Pinned rawpy 0.27.1 and Pillow 12.3.0 required.')
    out = Path(output)
    if out.exists():
        raise ValueError('Conversion exists; never overwrite an evidence derivative.')
    source_raw = Path(source).read_bytes()
    with rawpy.imread(io.BytesIO(source_raw)) as raw:
        camera_wb = list(raw.camera_whitebalance)
        if not all(np.isfinite(x) and x > 0 for x in camera_wb[:3]):
            raise ValueError('Camera white balance unavailable; no auto-WB fallback.')
        settings = dict(use_camera_wb=True, use_auto_wb=False, no_auto_bright=True,
                        bright=1., adjust_maximum_thr=0., output_color=rawpy.ColorSpace.sRGB,
                        output_bps=8, gamma=(2.222, 4.5), half_size=False,
                        median_filter_passes=0, noise_thr=None)
        info = {'raw_sizes': raw.sizes._asdict(), 'raw_type': str(raw.raw_type),
                'camera_whitebalance': camera_wb, 'color_description': raw.color_desc.decode()}
        rgb = raw.postprocess(**settings)
    base = Image.fromarray(rgb)
    sharpen = dict(radius=.8, percent=50, threshold=3)
    final = base.filter(ImageFilter.UnsharpMask(**sharpen))
    images = {}
    out.mkdir(parents=True, exist_ok=False)
    for name, image in [('render-unsharpened.png', base), ('render.png', final)]:
        data, record = clean_png(image)
        (out / name).write_bytes(data); images[name] = record
    manifest = {'schema': VERSION, 'source_sha256': sha(source_raw),
                'source_original_is_private': True, 'source_metadata_copied': False,
                'source_file_name_recorded': False, 'source_GPS_or_EXIF_recorded': False,
                'orientation': 'RAW stored orientation, applied by LibRaw',
                'postprocess': {**settings, 'output_color': 'rawpy.ColorSpace.sRGB'},
                'transfer_curve': 'Fixed gamma power 2.222, slope 4.5; no adaptive tone curve',
                'sharpening': {'method': 'Pillow.UnsharpMask', **sharpen},
                'white_balance_scope': 'As-shot camera coefficients, not a color calibration',
                'automatic_brightness_or_WB': False, 'manual_local_adjustments': False,
                'libraries': {'rawpy': rawpy.__version__, 'LibRaw': list(rawpy.libraw_version),
                              'Pillow': pillow_version, 'numpy': np.__version__,
                              'Python': sys.version.split()[0]},
                'converter_sha256': sha(Path(__file__).read_bytes()), 'raw_info': info,
                'images': images, 'hardware_IO': False, 'API_calls': 0}
    (out / 'conversion.json').write_text(json.dumps(manifest, indent=2, allow_nan=False) + '\n')
    print(json.dumps({'converted': str(out), 'width': final.width, 'height': final.height,
                      'metadata_removed': True, 'API_calls': 0}))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--image', required=True); p.add_argument('--output', required=True)
    a = p.parse_args(); convert(a.image, a.output)
