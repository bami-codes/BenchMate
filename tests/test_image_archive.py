import hashlib,io,struct,zlib
import pytest
from PIL import Image,PngImagePlugin
from benchmate.image_archive import verify_clean_png


def png(level=6,**kwargs):
    out=io.BytesIO();Image.new('RGB',(40,30),'#4783aa').save(out,format='PNG',compress_level=level,**kwargs);return out.getvalue()


def test_compression_is_not_metadata_or_archive_identity():
    a,b=png(0),png(9)
    assert a!=b
    for raw in (a,b):
        info=verify_clean_png(raw)
        assert info['sha256']==hashlib.sha256(raw).hexdigest()
        assert info['archive_bytes_preserved'] and info['metadata_checked']
        assert (info['width'],info['height'])==(40,30)


@pytest.mark.parametrize('kind',[b'tEXt',b'eXIf',b'iCCP',b'acTL'])
def test_all_ancillary_metadata_and_animation_chunks_rejected(kind):
    raw=png();data=b'not retained'
    chunk=struct.pack('>I',len(data))+kind+data+struct.pack('>I',zlib.crc32(kind+data)&0xffffffff)
    with pytest.raises(ValueError):verify_clean_png(raw[:33]+chunk+raw[33:])


@pytest.mark.parametrize('case',['crc','trailing','truncated','rgba','oversize'])
def test_corrupt_or_out_of_scope_archives_fail(case):
    raw=png()
    if case=='crc':raw=raw[:30]+bytes([raw[30]^1])+raw[31:]
    elif case=='trailing':raw+=b'GPS data'
    elif case=='truncated':raw=raw[:-1]
    else:
        out=io.BytesIO();Image.new('RGBA' if case=='rgba' else 'RGB',(1601,1) if case=='oversize' else (40,30)).save(out,format='PNG');raw=out.getvalue()
    with pytest.raises(ValueError):verify_clean_png(raw)
