from pathlib import Path
import sys,json,hashlib,shutil,os
ROOT=Path('/Users/bami/Documents/metaai');sys.path.insert(0,str(ROOT/'src'))
os.environ.setdefault('MPLCONFIGDIR','/private/tmp/benchmate-matplotlib')
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from benchmate.records import read_events,Recorder

source=Path((ROOT/'runs/d01-repair-conditional-capture-path.txt').read_text().strip())
events=read_events(source);result=json.loads((source/'result.json').read_text());p=json.loads((source/'prediction.json').read_text())
assert events[-1]['kind']=='run_completed' and result['incremental_repair_check_passed']
baseline=next(e for e in events if e['kind']=='pre_stimulus_origin_frozen')
first_wave=next(e for e in events if e['kind']=='serial_command' and ' STEP ' in e['payload']['request'])
assert baseline['sequence']<first_wave['sequence']
assert hashlib.sha256((source/'baseline.json').read_bytes()).hexdigest()==result['baseline']['sha256']
protocol=Path((ROOT/'runs/d01-repair-conditional-plan-path.txt').read_text().strip()).parent
protocol_events=read_events(protocol)
freeze=next(e for e in protocol_events if e['kind']=='conditional_protocol_frozen')
assert freeze['timestamp']<events[0]['timestamp']
assert hashlib.sha256((protocol/'protocol.json').read_bytes()).hexdigest()==result['prediction_sha256']
assert hashlib.sha256((ROOT/'src/benchmate/measured_input.py').read_bytes()).hexdigest()==p['predictor_sha256']

analysis=Recorder(ROOT/'runs/hardware-d01-conditional-analysis',mode='audit_and_plot_of_prospective_incremental_check')
(analysis.path/'controller-source.py').write_bytes(Path(__file__).read_bytes())
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False})
fig,axes=plt.subplots(2,2,figsize=(12.5,7),gridspec_kw={'height_ratios':[3,1.2]},layout='constrained')
colors={'repair_to_declared_nominal_C':'#1458b6','no_repair_counterfactual':'#858d99'}
for col,kind in enumerate(['step','sine']):
    raw=next(e['payload'] for e in events if e['kind']==kind+'_raw_capture');rows=np.asarray(raw['rows'])
    a=p['voltage_conversion']['channels']['A2'];observed=rows[:,3]*a['gain_v_per_count']+a['offset_v']
    t=(rows[:,0]+rows[:,7])*1e-6
    if kind=='step':t-=rows[raw['step_index'],0]*1e-6
    ax=axes[0,col];ar=axes[1,col]
    ax.plot(t*1000,(observed-result['baseline']['output_v'])*1000,color='#b85d17',lw=1,label='New observed OUT change')
    for name in colors:
        recorded=next(e['payload'] for e in events if e['kind']=='conditional_prediction_computed' and e['payload']['kind']==kind and e['payload']['model']==name)
        predicted=np.asarray(recorded['predicted_output_v']);residual=(observed-predicted)*1000
        assert abs(np.sqrt(np.mean(residual**2))-result['scores'][kind]['models'][name]['RMS_mV'])<1e-10
        assert recorded['scored_output_samples_used_for_prediction']==0
        label='Fixed repair model, measured IN' if name.startswith('repair') else 'Fixed no-repair model, measured IN'
        ax.plot(t*1000,(predicted-result['baseline']['output_v'])*1000,color=colors[name],ls='--',lw=1.2,label=label)
        ar.plot(t*1000,residual,color=colors[name],lw=.7)
    ax.set_title(('Step' if kind=='step' else '5 Hz sine')+' | incremental check passed',loc='left',fontweight='bold')
    ax.set_ylabel('Change from separate HOLD origin (mV)');ax.grid(alpha=.15);ax.legend(fontsize=8)
    if kind=='step':ax.set_xlim(-10,80)
    ar.axhline(0,color='#999',lw=.7);ar.grid(alpha=.15);ar.set_xlabel('Time (ms; all scored samples below)');ar.set_ylabel('Residual (mV)')
fig.suptitle('D01 repair | new measured-input conditional check\nSeparate HOLD origin fixed first; R/C unchanged; all samples scored. Absolute voltage accuracy remains unverified.',fontsize=12)
fig.savefig(analysis.path/'conditional-repair.png',dpi=170);plt.close(fig)
audit={'protocol_precedes_first_device_command':True,'baseline_precedes_both_scored_waveforms':True,
    'baseline_sha256':result['baseline']['sha256'],'predictor_source_matches_frozen_hash':True,
    'recorded_prediction_residuals_reproduce_scores':True,'validation_OUT_samples_used_by_predictor':0,
    'incremental_repair_check_passed':True,'absolute_voltage_verification_passed':False,
    'capture_frames':3584,'scored_frames':1024,'separate_origin_frames':1536,'return_guard_frames':1024,
    'previous_zero_capture_timeout_preserved':True,'unit_tests_passed':9,
    'fake_device_cases_passed':['repaired response with +12mV baseline offset','unrepaired response rejected','changed boot abort','bad REF abort'],
    'fake_device_checks_use_no_real_serial_port':True}
(analysis.path/'audit.json').write_text(json.dumps(audit,indent=2)+'\n');analysis.add('audit',audit)
analysis.add('run_completed',{'hardware_IO':False,'incremental_check_passed':True,'absolute_voltage_accuracy_claimed':False})

base=ROOT/'examples/hardware-d01-repair/2026-10-30'
sources={
    'conditional-protocol-initial':ROOT/'runs/hardware-d01-repair-conditional-protocol/20261029T154919-76b86ed75c',
    'conditional-transport-failure':ROOT/'runs/hardware-d01-repair-conditional-capture/20261029T154955-695b8dca47',
    'conditional-protocol-after-reset':protocol,
    'conditional-capture':source,
    'conditional-analysis':analysis.path,
}
manifest=[]
for label,src in sources.items():
    read_events(src);dst=base/label;assert not dst.exists();shutil.copytree(src,dst)
    for file in sorted(src.iterdir()):
        if file.is_file():
            assert file.read_bytes()==(dst/file.name).read_bytes()
            manifest.append({'source':str(file.relative_to(ROOT)),'copy':str((dst/file.name).relative_to(base)),'sha256':hashlib.sha256(file.read_bytes()).hexdigest()})
(base/'conditional-provenance.json').write_text(json.dumps(manifest,indent=2)+'\n')
shutil.copyfile('/private/tmp/check-conditional-after-reset.py',base/'conditional-analysis/fake-device-check-source.py')
readme=base/'README.md';text=readme.read_text()
text=text.replace('Status: the operator removed the added capacitor, and the first post-repair\nstep/sine captures completed. **Both frozen absolute-voltage checks failed**;\nthe separate fitted dynamics are close to the repair prediction.',
'''Status: **new input-conditioned incremental repair checks passed**. The first
absolute-voltage checks remain failed. The later protocol uses a separate
pre-stimulus HOLD origin and measured IN, with unchanged circuit parameters;
it does not establish absolute voltage accuracy.''')
text+='''

## Prospective measured-input incremental check

The user reported stationary **REF 1.635 V / DRIVE-REF -0.010 V** and proposed
using measured IN. Under the existing provisional mappings, the first attempt's
A1 differed from its predicted driver level by only +0.300/+0.289 mV on average
(step/sine), corresponding to about +0.15 mV at OUT. Input substitution alone
therefore cannot remove that attempt's +12–13 mV output residual.

The revised protocol fixes R, C, gain, thresholds, input handling and
initialization before new data. Three separate HOLD blocks then fix input/output
origins before either scored waveform. The predictor receives measured A1 and
channel timing; it never receives scored A2 values. A4 remains a stability guard.
This is an incremental, measured-input-conditioned check; the predicted curve
becomes available after IN is observed, not before acquisition. No scored OUT
offset, amplitude, phase or circuit parameter is fitted.

The first start received zero bytes for PING and stopped before any capture
or stimulus. That record remains in `conditional-transport-failure`. After
the operator reported RESET, a separately frozen continuation required a new
unarmed boot and one explicit REF ARM. USB/wiring were reported unchanged;
the prior supply estimate was retained, not newly metered. This exception is
limited to the known passive fixture and raw stationary guards.

| Fixed conditional model | Step RMS | 5 Hz sine RMS | Result |
|---|---:|---:|---|
| Repair to nominal C | **2.118 mV** | **2.045 mV** | Whole and all regional checks passed |
| No-repair counterfactual | 11.267 mV | 11.340 mV | Failed |

Worst repaired-model region RMS was 3.406 mV for the step and 3.138 mV for
the sine, below the unchanged 9 mV limits. All 3,584 frames were retained:
1,536 origin frames, 1,024 scored frames and 1,024 return-guard frames.
A4 block means spanned 1.114 mV. Boot `32edea4b481494f595ac2d2bf5cd3a17`
remained unchanged; output returned to code 1371. No additional DMM reading
or center-tracking loop was used for this check.

This supports the repaired **incremental response within the two declared
models**. Absolute-voltage accuracy, general REF tracking, B5 nonlinear
calibration, broad diagnosis and full D2 acceptance remain unestablished.
The first failed absolute checks are not relabeled as passed.

![New input-conditioned predictions and all residuals](conditional-analysis/conditional-repair.png)

[Protocol](conditional-protocol-after-reset/protocol.json),
[result](conditional-capture/result.json), [audit](conditional-analysis/audit.json),
and [source-copy hashes](conditional-provenance.json) preserve this separate attempt.
'''
readme.write_text(text)
doc=ROOT/'docs/measured-input.md'
assert not doc.exists()
doc.write_text('''# Measured-IN conditional incremental prediction

`benchmate.measured_input.predict_incremental_rc` accepts measured input and
channel timing, fixed gain/tau, and input/output origins from a **separate
pre-stimulus HOLD**. It accepts no scored output samples. The fixed RC rule is
`d(delta_OUT)/dt = (gain * delta_IN - delta_OUT) / tau`, with REF treated as
stationary under the existing A4 guard.

Each measured A1 sample reconstructs the held input level during its command
frame. The solver propagates the exact exponential through the measured frame
intervals and samples at the A2 read-completion delay. STEP initialization uses
the measured pre-step IN mean after firmware settling. SINE initialization is
the periodic state of the first complete measured IN cycle, assumed representative
of the prior warmup. Every scored sample is retained. ADC read completion is
still only a provisional proxy for the true sample aperture.

Freeze the model, input processing, initial-state rule, guards and acceptance
criteria before collection. Acquire independent stationary origins and freeze
them before the scored waveforms. Compute conditional curves from A1 only, then
compare with A2. Do not estimate an offset or parameters from scored OUT. This
is not an absolute waveform prediction made before observing IN, and is not
absolute voltage calibration.

The software reduces repeated manual center matching for this limited linear
response check. Relative channel gain, REF movement, clipping, timing and supply
limits still matter. It does not eliminate meter use for wiring changes,
component measurements, failed guards or absolute/nonlinear calibration. In
particular, a B5 diode's physical bias cannot be certified by canceling a DC
origin.

Nine numerical tests cover independent closed-form step/jitter, exact periodic
sample-and-hold sine including its first sample, a later input-level change and
invalid data/timing. Isolated fake-device runs accept repaired dynamics with a
separate 12 mV offset, reject unrepaired dynamics, and stop after a changed boot
or failed REF guard. The [new physical repair check](../examples/hardware-d01-repair/2026-10-30/README.md)
passed at 2.118/2.045 mV RMS, while the old absolute checks remain failed.

The ordinary Spark agent remains synthetic-only; this predictor does not by
itself enable unrestricted hardware diagnosis or general automatic A4 control.
''')
ref=ROOT/'docs/reference-tracking.md'
ref.write_text(ref.read_text()+'''

## Measured-input revision and bounded physical result

Stationary DMM REF / DRIVE-REF was 1.635 / -0.010 V. Comparing different
boots and codes does not prove a code-independent 6 mV actuator drift. Under
the retained provisional mappings, measured A1 and commanded driver predictions
in the failed attempt differed by only about 0.30 mV on average, insufficient
to explain its +12–13 mV OUT residual by input substitution alone.

The [measured-IN method](measured-input.md) therefore verifies incremental
response from a separate stationary origin. A new prospective step/sine check
passed at 2.118/2.045 mV RMS with the original repair model unchanged. This
does not correct or rescore the old absolute predictions. A4 servo control
remains disabled, and meter use is retained where absolute bias or a failed
guard requires it.
''')
main=ROOT/'README.md';text=main.read_text()
text=text.replace('calibrated hardware accuracy, physical repair and holdout generalization remain unestablished.',
    'calibrated absolute hardware accuracy, automated physical diagnosis and holdout generalization remain unestablished.')
text=text.replace('Verified repair prediction, A4 alignment and full D2 validation remain pending.',
    'A separately frozen measured-IN incremental check then passed at 2.12/2.04 mV RMS; its stationary origin was acquired before both scored waveforms. This verifies the limited response-change check, not absolute voltage. A4 alignment and full D2 validation remain pending.')
text=text.replace('Physical B5 discovery and D01 repair validation remain pending.',
    'Physical B5 discovery remains pending; the limited D01 incremental repair check is recorded separately above.')
main.write_text(text)
plan=ROOT/'docs/2026-10-30-plan.md'
plan.write_text(plan.read_text()+'''

## Updated checkpoint after measured-input validation

D01 incremental repair verification passed in a separately frozen new attempt
(step/sine 2.118/2.045 mV RMS). The first absolute predictions remain failed.
One zero-capture PING timeout and the operator's RESET are retained. The
predictor and guards have unit/fake-device checks; Spark hardware integration
is still pending. Latest completed boot is 32edea4b481494f595ac2d2bf5cd3a17,
parked code 1371. The next requested USB-off action is to remove the E30-A55
OUT-load lead, retaining the 9.99 kohm resistor and REF return, and measure a
separate 1 kohm shunt outside the circuit. B1/B6 acquisition has not started.
''')
print(json.dumps({'archived_files':len(manifest),'new_graph':str(analysis.path/'conditional-repair.png'),'incremental_check_passed':True,'absolute_voltage_verified':False,'hardware_IO':False}))
