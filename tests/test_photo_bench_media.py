from PIL import Image, PngImagePlugin
import pytest

from benchmate.photo_bench.media import CropTransform, clean_derivative, import_photo, verify_local_master


def test_full_resolution_master_and_no_metadata(tmp_path):
    source = tmp_path / 'input.png'
    im = Image.new('RGB', (2100, 1800), 'navy')
    meta = PngImagePlugin.PngInfo()
    meta.add_text('GPS', 'private location must not survive')
    im.save(source, pnginfo=meta)
    before = source.read_bytes()
    record = import_photo(source, tmp_path / 'observation')
    assert source.read_bytes() == before
    assert record['master']['width'] == 2100
    assert record['overview']['width'] == 1600
    assert record['master']['metadata_present'] is False
    assert record['state_id'] is None and not record['same_state_verified']
    assert record['electrical_evidence'] == []
    assert verify_local_master(tmp_path / 'observation/master.png')['height'] == 1800


def test_exif_orientation_applied_once(tmp_path):
    image = Image.new('RGB', (6, 4), 'red')
    exif = Image.Exif()
    exif[274] = 6
    image.save(tmp_path / 'input.jpg', exif=exif)
    record = import_photo(tmp_path / 'input.jpg', tmp_path / 'out')
    assert (record['master']['width'], record['master']['height']) == (4, 6)
    with Image.open(tmp_path / 'out/master.png') as clean:
        assert not clean.info and not clean.getexif()


def test_crop_uses_full_master_pixels(tmp_path):
    source = tmp_path / 'master.png'
    image = Image.new('RGB', (2000, 1000), 'white')
    image.putpixel((1700, 500), (12, 34, 56))
    image.save(source)
    record = clean_derivative(source, tmp_path / 'crop.png', (1600, 400, 1800, 600))
    with Image.open(tmp_path / 'crop.png') as crop:
        assert crop.getpixel((100, 100)) == (12, 34, 56)
        assert crop.size == (200, 200)
    assert not record['upsampled']


def test_crop_transform_round_trip_and_corners():
    transform = CropTransform(201, 105, 2002, 1908, 1598, 1600)
    for point in [(0, 0), (1598, 1600), (42.2, 678.9)]:
        assert transform.from_master(*transform.to_master(*point)) == pytest.approx(point)
    assert transform.to_master(1598, 1600) == (2002, 1908)
    with pytest.raises(ValueError):
        transform.to_master(-0.1, 0)
    with pytest.raises(ValueError):
        CropTransform(0, 0, 10, 10, 20, 20)


def test_reject_metadata_and_trailing_bytes(tmp_path):
    source = tmp_path / 'tainted.png'
    info = PngImagePlugin.PngInfo()
    info.add_text('location', 'private')
    Image.new('RGB', (4, 4)).save(source, pnginfo=info)
    with pytest.raises(ValueError, match='metadata'):
        verify_local_master(source)
    Image.new('RGB', (4, 4)).save(source)
    source.write_bytes(source.read_bytes() + b'private metadata')
    with pytest.raises(ValueError):
        verify_local_master(source)


def test_reject_outside_crop_and_preserve_previous_output(tmp_path):
    source = tmp_path / 'master.png'
    Image.new('RGB', (20, 20)).save(source)
    with pytest.raises(ValueError, match='bounds'):
        clean_derivative(source, tmp_path / 'bad.png', (0, 0, 21, 20))
    target = tmp_path / 'existing.png'
    target.write_bytes(b'preserve this failed run')
    with pytest.raises(FileExistsError):
        clean_derivative(source, target)
    assert target.read_bytes() == b'preserve this failed run'


def test_views_do_not_become_same_state_group(tmp_path):
    for index in (1, 2):
        path = tmp_path / f'view{index}.png'
        Image.new('RGB', (4, 4), (index, 0, 0)).save(path)
        result = import_photo(path, tmp_path / f'record{index}')
        assert result['same_state_verified'] is False
        assert result['state_id'] is None
