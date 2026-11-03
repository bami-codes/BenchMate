#!/usr/bin/env python3
"""Offline raw-record comparison; no serial/provider access or parameter fitting."""
import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
SOURCES=[
 ('Before GND lead replacement', 'examples/ref-bridge-QA/2026-11-03/20261103T023403-580a10e8e8/events.jsonl', 'bridge_QA_large_step_raw_capture'),
 ('After GND lead replacement', 'examples/original-guard-QA/2026-11-03/session01-ground-single/stages/20261103T035023-cf3444baee/events.jsonl', 'original_guard_unloaded_step_large_raw_capture')]


def main():
    out=ROOT/'examples/original-guard-QA/2026-11-03/analysis';out.mkdir(exist_ok=True)
    fig,axes=plt.subplots(3,1,figsize=(10,8),sharex=True)
    metrics=[];colors=['#b75b2d','#087b6a']
    for (name,path,kind),color in zip(SOURCES,colors):
        raw=(ROOT/path).read_bytes();events=[json.loads(x) for x in raw.splitlines()]
        p=next(e['payload'] for e in events if e['kind']==kind)
        a=np.asarray(p['rows']);v=a[:,2:6]*4.9/16383;edge=a[len(a)//10,0]
        delta=(v[-100:].mean(0)-v[5:46].mean(0))*1000
        metrics.append({'name':name,'path':path,'sha256':hashlib.sha256(raw).hexdigest(),
            'boot_id':p['boot_id'],'negative_to_positive_plateau_delta_mV':delta.tolist(),
            'pre_frames':[5,46],'late_frames':100,'statistics_use_raw_samples':True})
        t=(a[:,0]+a[:,6]-edge)/1000
        axes[0].plot(t,v[:,0]-v[5:46,0].mean(),label=name,color=color,lw=1.4)
        for ax,column in zip(axes[1:],[2,3]):
            time=(a[:,0]+a[:,column+6]-edge)/1000
            y=(v[:,column]-v[5:46,column].mean())*1000
            ax.plot(time[5:-5],np.convolve(y,np.ones(11)/11,mode='valid'),color=color,lw=1.5,label=name)
    axes[0].set_ylabel('IN change (V)')
    axes[1].set_ylabel('A3 REF change (mV)')
    axes[2].set_ylabel('A4 REF change (mV)')
    axes[2].set_xlabel('Time from commanded step (ms)')
    axes[0].legend(loc='lower right',fontsize=9)
    for ax in axes:
        ax.axvline(0,color='#777777',ls=':',lw=.8);ax.grid(alpha=.2);ax.set_xlim(-25,230)
    fig.suptitle('REF ADC readout before and after GND return lead replacement',fontsize=13)
    fig.text(.1,.015,'REF lines: 11-frame display average. All statistics use unfiltered raw samples.\n'
             'Different boots; nominal voltage conversion; no k correction or independent absolute calibration.',fontsize=9)
    fig.tight_layout(rect=(0,.065,1,.96));fig.savefig(out/'ground-return-comparison.png',dpi=160)
    (out/'ground-return-comparison.json').write_text(json.dumps(metrics,indent=2)+'\n')
    print(json.dumps({'figure':str(out/'ground-return-comparison.png'),'metrics':metrics}))


if __name__=='__main__':main()
