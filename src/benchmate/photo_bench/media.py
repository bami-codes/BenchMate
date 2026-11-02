"""Pixel-only local masters and explicit crop coordinates. No network or USB."""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import io
import json
from pathlib import Path
import struct
import subprocess
import tempfile
import warnings
import zlib

from PIL import Image, ImageOps

MAX_INPUT_BYTES = 64_000_000
MAX_PIXELS = 24_000_000
MAX_MASTER_BYTES = 80_000_000
SUPPORTED = {'.heic', '.heif', '.jpg', '.jpeg', '.png'}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as handle:
        for block in iter(lambda: handle.read(1 << 20), b''):
            digest.update(block)
    return digest.hexdigest()


def verify_local_master(path: Path) -> dict:
    """Unlike API archives, local masters may exceed 1600px; reject all metadata."""
    if not 0 < path.stat().st_size <= MAX_MASTER_BYTES:
        raise ValueError('Master byte limit exceeded')
    raw = path.read_bytes()
    if not raw.startswith(b'\x89PNG\r\n\x1a\n'):
        raise ValueError('Expected PNG')
    pos, kinds, dimensions = 8, [], None
    while pos < len(raw):
        if pos + 12 > len(raw):
            raise ValueError('Truncated PNG')
        length = struct.unpack('>I', raw[pos:pos + 4])[0]
        kind = raw[pos + 4:pos + 8]
        end = pos + 12 + length
        if end > len(raw) or kind not in (b'IHDR', b'IDAT', b'IEND'):
            raise ValueError('Unsupported PNG chunk or metadata')
        payload = raw[pos + 8:pos + 8 + length]
        if zlib.crc32(kind + payload) & 0xffffffff != struct.unpack('>I', raw[end - 4:end])[0]:
            raise ValueError('PNG CRC mismatch')
        if kind == b'IHDR':
            if kinds or length != 13:
                raise ValueError('Invalid PNG header')
            w, h, depth, color, compression, filtering, interlace = struct.unpack('>IIBBBBB', payload)
            if not 0 < w * h <= MAX_PIXELS or min(w, h) < 1:
                raise ValueError('Master pixel limit exceeded')
            if (depth, color, compression, filtering, interlace) != (8, 2, 0, 0, 0):
                raise ValueError('Expected non-interlaced RGB pixels')
            dimensions = (w, h)
        elif not kinds or kinds[0] != b'IHDR':
            raise ValueError('Missing PNG header')
        elif kind == b'IEND':
            if length or b'IDAT' not in kinds or end != len(raw):
                raise ValueError('Invalid PNG ending')
        elif b'IEND' in kinds:
            raise ValueError('Data after PNG ending')
        kinds.append(kind)
        pos = end
    if not kinds or kinds[-1] != b'IEND':
        raise ValueError('Missing PNG ending')
    with Image.open(io.BytesIO(raw)) as im:
        im.load()
        if im.size != dimensions or im.mode != 'RGB' or im.info or im.getexif() or getattr(im, 'n_frames', 1) != 1:
            raise ValueError('Expected a single metadata-free RGB image')
    return {'width': dimensions[0], 'height': dimensions[1], 'bytes': len(raw),
            'sha256': hashlib.sha256(raw).hexdigest(), 'metadata_checked': True,
            'metadata_present': False}


def _read_pixels(path: Path) -> Image.Image:
    with warnings.catch_warnings():
        warnings.simplefilter('error', Image.DecompressionBombWarning)
        with Image.open(path) as image:
            if image.width * image.height > MAX_PIXELS or getattr(image, 'n_frames', 1) != 1:
                raise ValueError('Expected one bounded still image')
            upright = ImageOps.exif_transpose(image)
            rgb = upright.convert('RGB')
            # Image.copy/convert alone may retain EXIF, ICC or text dictionaries.
            clean = Image.new('RGB', rgb.size)
            clean.paste(rgb)
            return clean


def decode_pixels(source: Path) -> tuple[Image.Image, str]:
    """Use native macOS HEIC decoding; temporary files never become API inputs."""
    if source.suffix.lower() not in SUPPORTED or not 0 < source.stat().st_size <= MAX_INPUT_BYTES:
        raise ValueError('Unsupported type or input byte limit exceeded')
    if source.suffix.lower() not in {'.heic', '.heif'}:
        return _read_pixels(source), 'Pillow + EXIF orientation + pixel-only RGB'
    with tempfile.TemporaryDirectory(prefix='benchmate-heic-') as temporary:
        decoded = Path(temporary) / 'decoded.png'
        try:
            subprocess.run(['/usr/bin/sips', '-s', 'format', 'png', str(source.resolve()), '--out', str(decoded)],
                           check=True, capture_output=True, timeout=60)
        except (OSError, subprocess.SubprocessError) as exc:
            raise ValueError('Native HEIC decoding failed') from exc
        return _read_pixels(decoded), 'macOS sips + EXIF orientation + pixel-only RGB'


@dataclass(frozen=True)
class CropTransform:
    """Continuous pixel-edge coordinates. Rectangle right/bottom are exclusive.

    Origin is the top-left edge of the oriented master, not raw HEIC sensor axes.
    Pixel centres are (column+0.5,row+0.5). No SAM inclusive-box conversion here.
    """
    left: int
    top: int
    right: int
    bottom: int
    output_width: int
    output_height: int

    def __post_init__(self):
        if not all(type(v) is int for v in asdict(self).values()):
            raise ValueError('Crop bounds and dimensions must be integers')
        if not (0 <= self.left < self.right and 0 <= self.top < self.bottom
                and self.output_width > 0 and self.output_height > 0):
            raise ValueError('Invalid crop rectangle')
        if self.output_width > self.right - self.left or self.output_height > self.bottom - self.top:
            raise ValueError('Upsampling is not permitted')

    def to_master(self, x: float, y: float) -> tuple[float, float]:
        if not (0 <= x <= self.output_width and 0 <= y <= self.output_height):
            raise ValueError('Point outside crop')
        return (self.left + x * (self.right - self.left) / self.output_width,
                self.top + y * (self.bottom - self.top) / self.output_height)

    def from_master(self, x: float, y: float) -> tuple[float, float]:
        if not (self.left <= x <= self.right and self.top <= y <= self.bottom):
            raise ValueError('Point outside source rectangle')
        return ((x - self.left) * self.output_width / (self.right - self.left),
                (y - self.top) * self.output_height / (self.bottom - self.top))


def clean_derivative(master: Path, output: Path, bounds: tuple[int, int, int, int] | None = None,
                     max_edge: int = 1600) -> dict:
    """Always crop the full-resolution oriented master, never a preview."""
    if not 1 <= max_edge <= 1600:
        raise ValueError('Transmission derivatives must be within 1600 pixels')
    if output.exists():
        raise FileExistsError('Preserve existing derivatives')
    source = verify_local_master(master)
    w, h = source['width'], source['height']
    left, top, right, bottom = bounds or (0, 0, w, h)
    if not (0 <= left < right <= w and 0 <= top < bottom <= h):
        raise ValueError('Crop exceeds master bounds')
    scale = min(1.0, max_edge / max(right - left, bottom - top))
    ow, oh = max(1, round((right - left) * scale)), max(1, round((bottom - top) * scale))
    transform = CropTransform(left, top, right, bottom, ow, oh)
    with Image.open(master) as image:
        pixels = image.crop((left, top, right, bottom)).resize((ow, oh), Image.Resampling.LANCZOS)
        clean = Image.new('RGB', pixels.size)
        clean.paste(pixels)
        output.parent.mkdir(parents=True, exist_ok=True)
        clean.save(output, format='PNG')
    from benchmate.image_archive import verify_clean_png
    result = verify_clean_png(output.read_bytes())
    result.update({'master_sha256': source['sha256'], 'transform': asdict(transform),
                   'coordinate_system': 'oriented-master pixel edges; crop right/bottom exclusive',
                   'upsampled': False})
    return result


def import_photo(source: Path, destination: Path) -> dict:
    """One independent observation. Never group changing circuits by file order."""
    if destination.exists():
        raise FileExistsError('Preserve existing photo observations')
    source_digest = sha256(source)
    pixels, decoder = decode_pixels(source)
    destination.mkdir(parents=True)
    master = destination / 'master.png'
    pixels.save(master, format='PNG')
    record = {'schema': 'benchmate.photo_observation.v1', 'id': 'photo-' + source_digest[:16],
              'source_name': source.name, 'source_sha256': source_digest, 'decoder': decoder,
              'master': {'file': 'master.png', **verify_local_master(master)},
              'overview': {'file': 'overview.png', **clean_derivative(master, destination / 'overview.png')},
              'state_id': None, 'same_state_verified': False, 'use': 'development',
              'network_requests': 0, 'hardware_commands': 0,
              'visual_observations': [], 'electrical_evidence': [],
              'coordinate_system': 'oriented-master pixel edges; raw orientation not interchangeable'}
    if sha256(source) != source_digest:
        raise ValueError('Source changed during import')
    (destination / 'record.json').write_text(json.dumps(record, ensure_ascii=False, indent=2) + '\n')
    return record
