"""Verify stripped RGB PNG archives without depending on encoder byte identity."""
import hashlib
import io
import struct
import zlib
from PIL import Image


def verify_clean_png(raw):
    """Accept only bounded 8-bit RGB PNGs containing IHDR, IDAT and IEND.

    Archive integrity remains the caller's pinned SHA-256. PNG compression is
    lossless but not canonical across encoder/library versions, so re-encoding
    is not a metadata check. No EXIF, text, profiles, extra frames or trailing
    bytes are accepted; all chunk CRCs and decoded pixels are checked.
    """
    if not isinstance(raw,bytes) or not 0<len(raw)<=12_000_000 or raw[:8]!=b'\x89PNG\r\n\x1a\n':
        raise ValueError('Expected a bounded metadata-free RGB PNG')
    offset=8;chunks=[];size=None;ended=False
    while offset<len(raw):
        if offset+12>len(raw):raise ValueError('Truncated PNG chunk')
        length=struct.unpack('>I',raw[offset:offset+4])[0]
        kind=raw[offset+4:offset+8];end=offset+12+length
        if end>len(raw) or kind not in (b'IHDR',b'IDAT',b'IEND'):
            raise ValueError('Metadata, unsupported or truncated PNG chunk')
        data=raw[offset+8:offset+8+length]
        expected=struct.unpack('>I',raw[offset+8+length:end])[0]
        if zlib.crc32(kind+data)&0xffffffff!=expected:raise ValueError('PNG CRC mismatch')
        if kind==b'IHDR':
            if chunks or length!=13:raise ValueError('Invalid PNG header')
            width,height,depth,color,compression,filtering,interlace=struct.unpack('>IIBBBBB',data)
            if not (0<width<=1600 and 0<height<=1600 and (depth,color,compression,filtering,interlace)==(8,2,0,0,0)):
                raise ValueError('Expected stripped 8-bit RGB image within 1600 pixels')
            size=(width,height)
        elif not chunks or chunks[0]!=b'IHDR':raise ValueError('Missing PNG header')
        elif kind==b'IEND':
            if length or b'IDAT' not in chunks or end!=len(raw):raise ValueError('Invalid PNG ending')
            ended=True
        chunks.append(kind);offset=end
    if not ended:raise ValueError('Missing PNG ending')
    with Image.open(io.BytesIO(raw)) as image:
        image.load()
        if image.format!='PNG' or image.mode!='RGB' or image.size!=size or image.info or image.getexif() or getattr(image,'n_frames',1)!=1:
            raise ValueError('Expected a single metadata-free RGB image')
    digest=hashlib.sha256(raw).hexdigest()
    return {'sha256':digest,'source_sha256':digest,'width':size[0],'height':size[1],
            'bytes':len(raw),'metadata_present':False,'metadata_checked':True,
            'pixels_reencoded':False,'resize_max_edge':1600,'archive_bytes_preserved':True}
