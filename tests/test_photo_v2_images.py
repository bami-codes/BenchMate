"""Pinned OpenCV environment: pixel masking and fixed-view transformation checks."""
from pathlib import Path
import sys
import hashlib

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import numpy as np
from PIL import Image
from benchmate.photo_v2.pipeline import body_and_views,_iou,_contained
from benchmate.image_archive import verify_clean_png


def test_body_pixel_identity_and_background_suppression(tmp_path):
    image=np.full((100,160,3),17,np.uint8)
    image[20:80,30:130]=[100,120,150]
    image[35:65,60:65]=[10,20,30]
    mask=np.zeros((100,160),np.uint8);mask[20:80,30:130]=255
    # Irregular corners inside the bounding rectangle must become white.
    mask[20:30,30:45]=0
    result=body_and_views(image,mask,np.array([1.1,1.,.9]),tmp_path,'object')
    assert len(result['views'])==5
    base=np.asarray(Image.open(tmp_path/'object-baseline.png'))
    roi=image[20:80,30:130];inside=mask[20:80,30:130]!=0
    assert np.array_equal(base[inside],roi[inside])
    assert np.all(base[~inside]==255)
    mirrored=np.asarray(Image.open(tmp_path/'object-mirror.png'))
    assert np.array_equal(mirrored,base[:,::-1])
    assert Image.open(tmp_path/'object-upscale.png').size==(300,180)
    for v in result['views']:
        raw=(tmp_path/v['file']).read_bytes()
        assert verify_clean_png(raw)['sha256']==v['sha256']


def test_contained_color_fragments_are_not_independent_body_reads():
    fragment=[20,20,30,60];body=[10,10,80,80]
    assert _iou(fragment,body)<.65 and _contained(fragment,body)==1
