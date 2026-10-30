#!/usr/bin/env python3
"""Plot only recorded B5 forecasts and comparisons. No fit, provider or device."""
import argparse,hashlib,json,sys
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from benchmate.records import read_events

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('run');p.add_argument('--output',required=True);a=p.parse_args()
    root=Path(a.run);events=read_events(root)
    publication=next(e for e in events if e['kind']=='b5_prediction_publication')
    frozen=next(e['payload'] for e in events if e['kind']=='b5_predictions_frozen')
    observations=[e for e in events if e['kind']=='b5_observation' and e['payload']['purpose']=='verification']
    checks=[e['payload'] for e in events if e['kind']=='b5_reserved_check']
    assert len(observations)==len(checks)==len(frozen['command_forecasts'])==2
    assert all(o['payload']['source']=='mock' and o['sequence']>publication['sequence'] for o in observations)
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False,'svg.fonttype':'none'})
    fig,axes=plt.subplots(2,2,figsize=(13,8.2),gridspec_kw={'height_ratios':[3,1]})
    fig.patch.set_facecolor('#fafbf8');fig.subplots_adjust(top=.76,bottom=.16,hspace=.17,wspace=.23)
    fig.suptitle('Spark on a mock bench\nA generated structure predicts two unused inputs',fontsize=19,weight='bold')
    for i,(event,check,forecast) in enumerate(zip(observations,checks,frozen['command_forecasts'])):
        o=event['payload'];d=o['input_template']['data'];t=np.array(d['frame_time_s'])+d['output_delay_s']
        y=np.array(o['output_relative_origin_v']);pre=np.array(forecast['predicted_output_relative_origin_v']);conditional=np.array(check['conditional_prediction'])
        assert o['settings']==check['settings']==forecast['settings'] and len(t)==len(y)==len(pre)==len(conditional)
        ax=axes[0,i];residual=axes[1,i]
        ax.plot(t,y,color='#c75435',lw=1.6,label='Observed mock OUT')
        ax.plot(t,pre,color='#25689e',lw=1.6,ls='--',label='Forecast saved before observation')
        ax.plot(t,conditional,color='#26765b',lw=1.3,ls=':',label='Comparison using measured mock IN')
        s=o['settings'];title='±0.35 V step' if s['kind']=='step' else '±0.65 V, 5 Hz sine'
        ax.set_title(title,pad=12,fontsize=14,weight='bold');ax.set_ylabel('Output relative to fixed ADC origin (V)')
        ax.grid(alpha=.17)
        a1=check['command_forecast'];b=check['conditional']
        ax.set_title(title+f"\nWhole RMS: forecast {a1['RMS_mV']:.2f} mV · conditional {b['RMS_mV']:.2f} mV",pad=10,fontsize=12,weight='normal')
        residual.plot(t,(y-pre)*1000,color='#25689e',lw=.8)
        residual.plot(t,(y-conditional)*1000,color='#26765b',lw=.8)
        residual.axhline(0,color='#8b9491',lw=.7);residual.set_ylabel('Residual (mV)');residual.set_xlabel('Time (s)');residual.grid(alpha=.15)
    fig.legend(*axes[0,0].get_legend_handles_labels(),loc='upper center',bbox_to_anchor=(.5,.885),ncols=3,fontsize=10,frameon=False)
    fig.supxlabel('Both whole-waveform and every regional check passed.\nMock evidence only · unloaded · no parameter/topology uniqueness or physical validation\nForecast publication: '+publication['payload']['commit'][:7]+' · no reserved-output refitting',fontsize=10)
    target=Path(a.output);target.parent.mkdir(parents=True,exist_ok=True)
    fig.savefig(target,dpi=160,facecolor=fig.get_facecolor());plt.close(fig)
    provenance={'source_sha256':hashlib.sha256((root/'events.jsonl').read_bytes()).hexdigest(),
                'prediction_publication':publication['payload']['commit'],'curves':'Exact recorded arrays; no fitting or simulation during plotting.',
                'output_sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'source':'mock'}
    target.with_suffix('.provenance.json').write_text(json.dumps(provenance,indent=2)+'\n')
    print(json.dumps({'output':str(target),**provenance}))
if __name__=='__main__':main()
