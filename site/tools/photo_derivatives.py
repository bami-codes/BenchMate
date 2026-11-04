"""One recipe for every board photo on the site (cases 01, 02, 03, 04, 05; faulted and restored states).

Inputs are the metadata-free derivatives already in the repository: the 1200×1600 SAM input of each photo stage
(`prepared/input.png`) and, for case 04, the metadata-free RAW render (no SAM stage). Originals (DNG) are never read.

For each photo this writes, into assets/photos/:
  caseNN-<state>-crop.jpg          the photo, cropped to the mini board (one framing rule for every case), pixels untouched
  caseNN-<state>-outline.png       transparent layer: the boundary of each native SAM 3.1 mask that a RECORD ties to a part
                                   or a candidate (Spark's body call, operator-confirmed, or the engine's assignment test).
                                   Nothing is outlined that no record names.
  caseNN-<state>-documentary.jpg   the same crop with every native mask outlined, for the "documentary" toggle only
and merges the paths, crop box and provenance (source sha256, mask files, method) into tools/photos-caseNN.json.

Framing rule: every photo was taken on the same fixed rig (phone vertical on a stand, mini board centred), so one window
of the 1200×1600 frame, FRAME = [120, 380, 1080, 1100]
BRIGHTEN = 1.15  # one uniform brightness lift for every board crop (the bench photos are dark); no colour or local edits (960×720, 4:3), is used for every case and state. Outline rule: a 3 px band just outside the mask, label-tape yellow, with a 1 px
dark edge on both sides so it reads on the pale board. Masks are the native rasters (exact size, no resize).

  python3 tools/photo_derivatives.py            # write derivatives and photos-caseNN.json
  python3 tools/photo_derivatives.py --apply    # also point the existing run files (01, 02, 04) at the new derivatives
"""
import argparse, hashlib, json, pathlib
import numpy as np
from PIL import Image, ImageEnhance

SITE = pathlib.Path(__file__).resolve().parents[1]
REPO = SITE.parent
OUT = SITE / 'assets' / 'photos'
YELLOW = (255, 221, 0)
EDGE = (27, 31, 36)
BAND, EDGE_W = 3, 1
FRAME = [120, 380, 1080, 1100]
BRIGHTEN = 1.15  # one uniform brightness lift for every board crop (the bench photos are dark); no colour or local edits

RC = 'examples/reading-cohort/2026-11-03/records'
C03 = f'{RC}/20261104T051005-fac3d07c86'
PHOTOS = {
    '01': {'faulted': {'input': f'{RC}/20261103T125924-bf8f64512b/photo-faulted/prepared/input.png',
                       'native': f'{RC}/20261103T125924-bf8f64512b/photo-faulted/decoded/native-SAM',
                       'tied': [{'object_id': '1', 'part': 'R1', 'why': 'body_binding: Spark named sam-1 as R1, operator-confirmed (photo-faulted/body-binding.json)'}]}},
    '02': {'faulted': {'input': f'{RC}/20261103T165506-b6ad3e8cf7/photo-faulted/prepared/input.png',
                       'native': f'{RC}/20261103T165506-b6ad3e8cf7/photo-faulted/decoded/native-SAM',
                       'tied': [{'object_id': '2', 'part': 'sam-2', 'why': 'group reading: one of the two capacitor bodies read out of circuit; which is C1 followed from the frozen bands (reading-groups/2026-11-04/records/20261103T174217-008035637b)'},
                                {'object_id': '3', 'part': 'sam-3', 'why': 'group reading: the other capacitor body read out of circuit'}],
                       'documentary_displayed': 'all'},
           'restored': {'input': 'examples/reading-restored-v2/2026-11-04/records/20261103T182550-4ea22cc3a0/photo-restored/prepared/input.png',
                        'native': 'examples/reading-restored-v2/2026-11-04/records/20261103T182550-4ea22cc3a0/photo-restored/native-SAM',
                        'tied': [], 'documentary_displayed': ['0', '1', '2', '3', '4', '6', '7'],
                        'documentary_rule': 'examples/SAM-display/2026-11-04/case02-v2/manifest.json (containment rule; 7 of 8 shown)'}},
    '03': {'faulted': {'input': f'{C03}/photo-faulted/prepared/input.png',
                       'native': f'{C03}/history/reading/history/original/photo-faulted/decoded/native-SAM',
                       'tied': [{'object_id': '1', 'part': 'R1', 'why': 'body_binding: Spark named sam-1 as R1 (photo-v5 follow-up), operator-confirmed (history/reading/body-binding.json)'}]},
           'restored': {'input': f'{C03}/photo-restored/prepared/input.png',
                        'native': f'{C03}/photo-restored/decoded/native-SAM',
                        'tied': [], 'documentary_displayed': 'all',
                        'documentary_rule': f'{C03}/documentary-display/manifest.json (3 of 3 shown)'}},
    '04': {'faulted': {'render': f'{RC}/20261103T150223-18d6f08ac9/documentary-photo/conversion/render.png', 'tied': [],
                       'note': 'documentary photo of the faulted board; no SAM stage in this record'}},
    '05': {'faulted': {'input': f'{RC}/20261104T021333-c80ef3617e/photo-faulted/prepared/input.png',
                       'native': f'{RC}/20261104T021333-c80ef3617e/photo-faulted/decoded/native-SAM',
                       'tied': [{'object_id': '1', 'part': 'W1', 'why': 'body_candidates_proposed: Spark named sam-1 as W1, operator-confirmed (wire-path-confirmation.json)'}]}},
}


def sha(p):
    return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()


def board_box(img):
    """One window for every photo: the rig was fixed, so the mini board sits in the same place in each 1200×1600 frame."""
    assert img.size == (1200, 1600), img.size
    return list(FRAME)


def dilate(m, r):
    out = m.copy()
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            if dx * dx + dy * dy > r * r or (dx == 0 and dy == 0):
                continue
            s = np.zeros_like(m)
            ys, yd = (slice(dy, None), slice(None, -dy)) if dy > 0 else (slice(None, dy or None), slice(-dy, None)) if dy < 0 else (slice(None), slice(None))
            xs, xd = (slice(dx, None), slice(None, -dx)) if dx > 0 else (slice(None, dx or None), slice(-dx, None)) if dx < 0 else (slice(None), slice(None))
            s[ys, xs] = m[yd, xd]
            out |= s
    return out


def outline_layer(size, masks):
    """RGBA layer with the outline band of each mask: yellow band of BAND px just outside the mask, EDGE_W px dark on both sides."""
    w, h = size
    rgba = np.zeros((h, w, 4), dtype=np.uint8)
    for m in masks:
        inner = dilate(m, EDGE_W)
        band = dilate(m, EDGE_W + BAND)
        outer = dilate(m, 2 * EDGE_W + BAND)
        edge = (outer & ~band) | (inner & ~m)
        yellow = band & ~inner
        rgba[yellow] = (*YELLOW, 255)
        rgba[edge] = (*EDGE, 255)
    return Image.fromarray(rgba, 'RGBA')


def load_native(native, object_id):
    man = json.load(open(REPO / native / 'crop-manifest.json'))
    o = next(x for x in man['objects'] if str(x['object_id']) == str(object_id))
    im = Image.open(REPO / native / o['source_mask_file']).convert('L')
    m = np.asarray(im) > 127
    return m, o, man


def write_jpeg(img, path):
    img = ImageEnhance.Brightness(img.convert('RGB')).enhance(BRIGHTEN)
    img.save(path, 'JPEG', quality=92, optimize=True, progressive=True)  # no EXIF, no ICC, no metadata


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--apply', action='store_true', help='also point data/runs/*.json (cases 01, 02, 04) at the new derivatives')
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    for case, states in PHOTOS.items():
        pj = SITE / 'tools' / f'photos-case{case}.json'
        prov = json.load(open(pj)) if pj.exists() else {}
        prov['width'], prov['height'] = 1200, 1600
        prov['method'] = ('tools/photo_derivatives.py: one framing rule (the same 960×720 window of the 1200×1600 frame, FRAME) and one outline rule '
                          f'({BAND} px band just outside each native SAM 3.1 mask, label-tape yellow {YELLOW}, {EDGE_W} px dark edge) for every case; '
                          f'outlines only for masks a record ties to a part or a candidate; one uniform brightness lift ×{BRIGHTEN} on every crop, no colour or local edits; JPEG q92 without metadata')
        for state, cfg in states.items():
            if cfg.get('input'):
                src = REPO / cfg['input']; img = Image.open(src).convert('RGB'); src_sha = sha(src)
                src_note = f"{cfg['input']} (1200×1600 metadata-free SAM input, sha256 {src_sha[:12]}…)"
            else:
                src = REPO / cfg['render']; full = Image.open(src).convert('RGB'); src_sha = sha(src)
                img = full.resize((1200, 1600), Image.LANCZOS)
                src_note = f"{cfg['render']} (metadata-free RAW render 3024×4032, resized to 1200×1600 for the same framing, sha256 {src_sha[:12]}…)"
            box = board_box(img)
            crop = img.crop(box)
            base = f'case{case}-{state}'
            write_jpeg(crop, OUT / f'{base}-crop.jpg')
            prov[f'{state}_crop'] = f'assets/photos/{base}-crop.jpg'
            prov[f'{state}_crop_box'] = box
            prov[f'{state}_sha256'] = src_sha
            prov[f'{state}_source'] = src_note
            tied = cfg.get('tied') or []
            masks, tied_out = [], []
            for t in tied:
                m, o, man = load_native(cfg['native'], t['object_id'])
                masks.append(m)
                tied_out.append({**t, 'bounds_half_open': o['bounds_half_open'], 'mask_file': o['source_mask_file'], 'mask_sha256': sha(REPO / cfg['native'] / o['source_mask_file']), 'confidence': o.get('confidence')})
            if masks:
                layer = outline_layer(img.size, masks).crop(box)
                layer.save(OUT / f'{base}-outline.png', optimize=True)
                prov[f'{state}_outline'] = f'assets/photos/{base}-outline.png'
            else:
                prov.pop(f'{state}_outline', None)
            prov[f'{state}_outlined'] = tied_out
            disp = cfg.get('documentary_displayed')
            if disp:
                man = json.load(open(REPO / cfg['native'] / 'crop-manifest.json'))
                ids = [str(o['object_id']) for o in man['objects']] if disp == 'all' else disp
                all_masks = [load_native(cfg['native'], i)[0] for i in ids]
                doc = Image.alpha_composite(img.convert('RGBA'), outline_layer(img.size, all_masks)).crop(box)
                write_jpeg(doc, OUT / f'{base}-documentary.jpg')
                prov[f'{state}_documentary'] = f'assets/photos/{base}-documentary.jpg'
                prov[f'{state}_documentary_masks'] = {'displayed': ids, 'of': len(man['objects']), 'rule': cfg.get('documentary_rule') or 'every native mask'}
            for old in ('crop_r1', 'faulted_sam', 'restored_sam', 'faulted_pair', 'spark_candidates', 'restored_board'):
                prov.pop(old, None)
            print(case, state, 'box', box, 'outlined', [t['part'] for t in tied], 'documentary', bool(disp))
        pj.write_text(json.dumps(prov, ensure_ascii=False, indent=1) + '\n')
    if a.apply:
        apply_to_runs()


def apply_to_runs():
    """Point the already extracted runs (01, 02, 04) at the new derivatives. Only photo paths and the crop box change;
    no number, event or verdict is touched."""
    runs = SITE / 'data' / 'runs'
    P = {c: json.load(open(SITE / 'tools' / f'photos-case{c}.json')) for c in ('01', '02', '04')}

    def patch(run_id, fn):
        p = runs / f'{run_id}.json'; r = json.loads(p.read_text()); fn(r); p.write_text(json.dumps(r, ensure_ascii=False, separators=(',', ':'))); print('patched', run_id)

    def c01(r):
        ph = P['01']; po = r['photo']
        po.update({'crop': ph['faulted_crop'], 'crop_r1': None, 'crop_box': ph['faulted_crop_box'], 'image': {**po['image'], 'file': ph['faulted_crop']}, 'provenance': None})
        for s in po.get('sam', []):
            for m in s.get('masks', []):
                m['overlay_file'] = ph['faulted_outline']
        po['note'] = 'Photo untouched apart from the outline: the boundary of the native SAM 3.1 mask Spark named as R1.'
        b = r['reading']['binding']; b['photo'] = ph['faulted_crop']; b['overlay_file'] = ph['faulted_outline']; b['crop_box'] = ph['faulted_crop_box']
        for e in r['timeline']:
            if e['kind'] == 'body_binding':
                e['photo'] = ph['faulted_crop']; e['overlay_file'] = ph['faulted_outline']; e['crop_box'] = ph['faulted_crop_box']
    patch('20261103T125924-bf8f64512b', c01)

    def c02(r):
        ph = P['02']; po = r['photo']
        po.update({'crop': ph['faulted_crop'], 'crop_box': ph['faulted_crop_box'], 'image': {**po['image'], 'file': ph['faulted_crop']}})
        po['sam'][0]['masks'] = [{**m, 'overlay_file': ph['faulted_outline'] if str(m.get('object_id')) == '2' else None} for m in po['sam'][0]['masks']]
        po['note'] = 'Photo untouched apart from the two outlines: the boundaries of the native SAM 3.1 masks of the two capacitor bodies that were read out of circuit (sam-2 and sam-3). No model paired them with C1 or C2; the frozen bands did.'
        po['display_rule_image'] = {**po.get('display_rule_image', {}), 'file': ph['faulted_documentary'], 'displayed': ph['faulted_documentary_masks']['of'],
                                    'note': f"Documentary: the same photo with every native SAM 3.1 mask outlined ({ph['faulted_documentary_masks']['of']} of {ph['faulted_documentary_masks']['of']}). Not an identification."}
        for e in r['timeline']:
            if e['kind'] == 'body_group':
                e['photo'] = ph['faulted_crop']; e['overlay_file'] = ph['faulted_outline']; e['crop_box'] = ph['faulted_crop_box']
    patch('20261103T165506-b6ad3e8cf7', c02)

    def c02r(r):
        ph = P['02']; po = r['photo']
        po.update({'crop': ph['restored_crop'], 'crop_box': ph['restored_crop_box'], 'image': {**po['image'], 'file': ph['restored_crop']}})
        d = ph['restored_documentary_masks']
        po['display_rule_image'] = {**po.get('display_rule_image', {}), 'file': ph['restored_documentary'], 'displayed': len(d['displayed']),
                                    'note': f"Documentary: the same photo with the native SAM 3.1 masks outlined under the display-only rule chosen after the results ({len(d['displayed'])} of {d['of']} shown). Not an identification (docs/2026-11-04-case02-SAM-display-revision.md)."}
    patch('20261103T182550-4ea22cc3a0', c02r)

    def c04(r):
        ph = P['04']; po = r['photo']
        po.update({'crop': ph['faulted_crop'], 'crop_box': ph['faulted_crop_box'], 'image': {**po['image'], 'file': ph['faulted_crop'], 'width': 1200, 'height': 1600}})
    patch('20261103T150223-18d6f08ac9', c04)


if __name__ == '__main__':
    main()
