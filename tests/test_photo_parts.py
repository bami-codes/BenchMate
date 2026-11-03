"""Offline image preparation/crop coordinates; never invoke a paid provider."""
import importlib.util
import io
from pathlib import Path

from PIL import Image, PngImagePlugin
import pytest

from benchmate.image_archive import verify_clean_png

ROOT = Path(__file__).resolve().parents[1]


def module():
    spec = importlib.util.spec_from_file_location('photo_parts_test', ROOT / 'scripts/photo_parts.py')
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    return m


def test_metadata_removed_full_pixels_preserved_and_no_truth_filename(tmp_path):
    m = module()
    image = Image.new('RGB', (1800, 1000), (110, 120, 130))
    metadata = PngImagePlugin.PngInfo(); metadata.add_text('answer', 'private_value_do_not_send')
    source = tmp_path / 'secret-case-name.png'; image.save(source, pnginfo=metadata)
    out = tmp_path / 'prepared'; plan = m.prepare(source, out)
    info = verify_clean_png((out / 'input.png').read_bytes())
    assert info['width'] == 1600
    with Image.open(out / 'clean-full.png') as full:
        assert full.size == (1800, 1000) and full.info == {}
        assert full.getpixel((100, 100)) == (110, 120, 130)
    assert 'secret-case-name' not in str(plan) and 'private_value_do_not_send' not in str(plan)
    assert m.checked(out)[1] == plan


def test_pixel_crop_uses_source_scale_and_fixed_padding():
    m = module()
    assert m.crop_box([10, 20, 30, 40], (100, 100), (1000, 2000), .15) == [70, 340, 330, 860]
    assert m.crop_box([0, 0, 100, 100], (100, 100), (1000, 2000), .15) == [0, 0, 1000, 2000]


def test_out_of_image_mask_is_not_silently_repaired():
    m = module()
    with pytest.raises(ValueError, match='outside exact input'):
        m.crop_box([-1, 0, 10, 10], (100, 100), (100, 100), .15)


def test_execute_flags_checked_before_any_file_or_provider_access():
    m = module()
    with pytest.raises(ValueError, match='Explicit --execute'):
        m.segment('does-not-exist', False)
    with pytest.raises(ValueError, match='explicit --execute'):
        m.read_parts('does-not-exist', False)


def test_clean_crop_png_has_only_supported_metadata_free_content():
    m = module(); image = Image.new('RGB', (50, 20), 'white')
    info = verify_clean_png(m.png(image))
    assert (info['width'], info['height']) == (50, 20)
