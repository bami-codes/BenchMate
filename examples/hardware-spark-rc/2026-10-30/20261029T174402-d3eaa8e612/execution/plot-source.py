from pathlib import Path
import sys,json
import numpy as np
ROOT=Path('/Users/bami/Documents/metaai');sys.path.insert(0,str(ROOT/'src'))
from benchmate.records import read_events
from benchmate.physical_rc import conditional_curve
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
run=Path((ROOT/'runs/hardware-spark-rc-current-path.txt').read_text().strip());events=read_events(run)
assert events[-1]['kind']=='run_completed'
training=next(e['payload'] for e in events if e['kind']=='unloaded_training_completed')
obs=[e['payload'] for e in events if e['kind']=='physical_observation']
comparisons={e['payload'].get('phase','reserved_sine'):e['payload']['scores'] for e in events if e['kind'] in ('physical_model_comparison','physical_verification')}
colors={'nominal_rc':'#8595a2','r_changed':'#b96731','c_changed':'#10796d'}
labels={'nominal_rc':'Nominal RC','r_changed':'R changed','c_changed':'C changed'}
fig,axes=plt.subplots(1,len(obs),figsize=(5*len(obs),4.5),layout='constrained',squeeze=False)
for ax,o in zip(axes[0],obs):
    d=o['data'];t=(np.asarray(d['frame_time_s'])+np.asarray(d['output_delay_s']))*1000
    origin=o['baseline']['output_v'];y=(np.asarray(d['output_v'])-origin)*1000;phase=o['phase']
    ax.plot(t,y,color='#17242d',lw=1.3,label='Measured OUT')
    if phase=='unloaded_step':
        curve=conditional_curve(o,{'gain':1.,'tau_s':training['tau_s']})['predicted_output_v']
        ax.plot(t,(np.asarray(curve)-origin)*1000,color='#10796d',lw=1.4,ls='--',label='Training fit (tau only)')
        title=f"Unloaded training\nτ = {training['tau_s']*1000:.2f} ms · RMS {training['training_RMS_mV']:.2f} mV"
    else:
        scores=comparisons[phase]
        for name,score in scores.items():
            curve=score['prediction']['predicted_output_v']
            verdict='PASS' if score['passed'] else 'FAIL'
            ax.plot(t,(np.asarray(curve)-origin)*1000,color=colors[name],lw=1.3,ls='--',label=f"{labels[name]}: {score['RMS_mV']:.2f} mV · {verdict}")
        title='Loaded step · ±0.20 V command' if phase=='attach_output_load_step' else 'Reserved sine · ±0.15 V, 5 Hz'
    ax.set_title(title,fontsize=11);ax.set_xlabel('Time (ms)');ax.set_ylabel('OUT − separate HOLD origin (mV)')
    ax.legend(fontsize=8,loc='best');ax.spines[['top','right']].set_visible(False)
fig.suptitle('Spark-selected new physical observations · fixed later models conditioned on measured IN',fontsize=13)
fig.supxlabel('PASS requires whole-waveform AND every-region RMS ≤ 9 mV. Nominal sine fails a region (11.65 mV).',fontsize=10)
path=run/'physical-spark-comparison.png';fig.savefig(path,dpi=170);plt.close(fig)
metadata={'training_curve_display':'Recomputed from recorded training tau and IN for display only; explicitly a fitted training curve.',
          'loaded_and_reserved_curves':'Exact prediction arrays stored in original execution events; no plot-time refit.',
          'voltage_display':'Subtract the separately recorded HOLD output origin from observed and predicted OUT.'}
(run/'plot-provenance.json').write_text(json.dumps(metadata,indent=2)+'\n')
(run/'plot-source.py').write_bytes(Path(__file__).read_bytes())
print(json.dumps({'plot':str(path),'observations':len(obs)}))
