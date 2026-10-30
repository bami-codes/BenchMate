#!/usr/bin/env python3
"""Freeze the prospective physical B5 protocol without touching hardware."""
import argparse,hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from benchmate.b5_session import PROTOCOL

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',required=True);args=p.parse_args()
    original=ROOT/'examples/hardware-b5-preparation/2026-10-30/plan-freeze/20261030T033824-73cfdedc30/plan.json'
    old=json.loads(original.read_text())
    frozen={k:old[k] for k in ('configuration','voltage_conversion','guard_limits','USB_identity')}
    frozen['configuration']={**frozen['configuration'],'vref_v':4.90,'ref_v':1.646}
    for mapping in frozen['voltage_conversion']['channels'].values():mapping['gain_v_per_count']*=4.90/4.89
    frozen['previous_boot_id']='406b47f3f601918ca2f759d02015462b'
    frozen['b5_protocol']=PROTOCOL
    frozen['source_sha256']={str(path.relative_to(ROOT)):hashlib.sha256(path.read_bytes()).hexdigest()
                            for path in sorted((ROOT/'src/benchmate').glob('*.py'))}
    frozen['source_sha256']['scripts/b5_unloaded.py']=hashlib.sha256((ROOT/'scripts/b5_unloaded.py').read_bytes()).hexdigest()
    frozen['calibration_provenance']={'source':str(original.relative_to(ROOT)),
        'sha256':hashlib.sha256(original.read_bytes()).hexdigest(),
        'voltage_estimates':'Last reported 4.90V supply / 1.646V REF on October 30, not new measurements.',
        'ADC_gain_policy':'Old provisional gains scaled once by 4.90/4.89; no waveform-derived gain fit.',
        'A4_policy':'Loose electrical plausibility and same-boot block-change guard, never an absolute voltage anchor.'}
    target=Path(args.output);target.parent.mkdir(parents=True,exist_ok=True)
    with target.open('x') as file:json.dump(frozen,file,ensure_ascii=False,indent=2);file.write('\n')
    print(json.dumps({'path':str(target),'sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'hardware_IO':False}))
if __name__=='__main__':main()
