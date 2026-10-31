#!/usr/bin/env python3
"""Deterministic schematic fixtures, never photographs or Spark outputs."""
import argparse
import json
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',required=True);args=p.parse_args()
    folder=Path(args.output);folder.mkdir(parents=True,exist_ok=False)
    font_path=Path('/System/Library/Fonts/Supplemental/Arial.ttf')
    font=lambda n:ImageFont.truetype(str(font_path),n) if font_path.exists() else ImageFont.load_default(size=n)
    truth=[]
    for index,(r,c,rlabel,clabel) in enumerate([(10000,1e-6,'10 kΩ','1 µF'),(4700,470e-9,'4.7 kΩ','470 nF'),(22000,None,'22 kΩ','?')],1):
        image=Image.new('RGB',(1100,650),'white');d=ImageDraw.Draw(image)
        d.text((45,30),'RC low-pass — intended schematic',font=font(28),fill='black')
        d.line([(120,230),(300,230)],fill='black',width=5);d.rectangle((300,205,490,255),outline='black',width=4)
        d.line([(490,230),(900,230)],fill='black',width=5);d.ellipse((644,224,656,236),fill='black')
        d.line([(650,230),(650,345)],fill='black',width=5);d.line([(590,345),(710,345)],fill='black',width=5)
        d.line([(590,367),(710,367)],fill='black',width=5);d.line([(650,367),(650,500),(120,500)],fill='black',width=5)
        d.text((85,170),'IN',font=font(26),fill='black');d.text((875,170),'OUT',font=font(26),fill='black')
        d.text((85,520),'REF',font=font(26),fill='black');d.text((320,130),'R1  '+rlabel,font=font(28),fill='black')
        d.text((735,335),'C1  '+clabel,font=font(28),fill='black')
        name=f'case-{index:02d}.png';image.save(folder/name)
        truth.append({'file':name,'source':'synthetic_schematic','expected':{'R_ohm':r,'C_f':c,
            'connections':[{'kind':'R','nodes':['IN','OUT']},{'kind':'C','nodes':['OUT','REF']}],
            'nominal_design_allowed_after_review':c is not None},'case': 'missing_capacitance' if c is None else 'labelled_rc'})
    (folder/'truth.json').write_text(json.dumps({'scope':'Local answer key; never part of the provider payload. Three hand-authored schematic fixtures, not an accuracy benchmark.','cases':truth},indent=2)+'\n')
    print(str(folder))


if __name__=='__main__':main()
