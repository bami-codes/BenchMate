from pathlib import Path
import hashlib,json,sys,shutil
ROOT=Path('/Users/bami/Documents/metaai');sys.path.insert(0,str(ROOT/'src'))
from benchmate.records import Recorder
from benchmate.range_control import CONTROL_WAVEFORMS
source=ROOT/'examples/hardware-b1-b6-gate/2026-10-30/b1_bypass/condition/condition.json'
old=json.loads(source.read_text())
paths=['src/benchmate/range_control.py','src/benchmate/physical_bench.py','src/benchmate/physical_rc.py',
       'src/benchmate/instrument.py','src/benchmate/measured_input.py','src/benchmate/records.py','scripts/b5_range_control.py']
p={k:old[k] for k in ['configuration','voltage_conversion','guard_limits']}
p['guard_limits']['signal_envelope_v']=.95
p.update(scope='Prospective resistor-only range and physical-bias control before B5 diode insertion; not a B5 discovery or full D2 acceptance.',
    previous_boot_id='4faed097aeda0ad9efdd84b22dd1ba4e',
    USB_identity=[9025,105,'3612211F36323632E4B233334B572F52'],
    calibration_supply_v=old['configuration']['vref_v'],driver_v_per_code=old['actuator']['driver_v_per_code'],
    calibration_source=str(source.relative_to(ROOT)),calibration_source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
    source_sha256={rel:hashlib.sha256((ROOT/rel).read_bytes()).hexdigest() for rel in paths},
    control_order=CONTROL_WAVEFORMS,
    anchors={'fresh_supply_and_REF_before_ARM':True,'DMM_IN_minus_REF_and_OUT_minus_REF_at_HOLD':True,
             'DMM_absolute_bias_limit_v':.03,'DMM_path_difference_limit_v':.01,'subsequent_HOLD_blocks':3,
             'gain_policy':'prior channel/driver gains times fresh reported supply divided by 4.89; no waveform fit',
             'offset_policy':'independent DMM physical biases minus subsequent HOLD means; never assumed zero'},
    fixed_scores={'OUT_minus_IN_whole_and_region_RMS_mV_max':9,'IN_minus_frozen_driver_whole_and_region_RMS_mV_max':9,
                  'A4_and_stationary_channel_mean_span_mV_max':3,'max_time_error_us':25,'sine_DAC_code_error_max':1,'step_DAC_code_error_max':0,
                  'input_5_95_span_ratio_bounds':[.85,1.05],'physical_bias_peak_margin_v':.06},
    startup='Known passive resistor-only fixture. Confirm USB-off changes and new boot. One explicit REF ARM; no automatic retry, servo, firmware upload or re-arm.',
    budget={'API_calls':0,'scored_waveforms':3,'stationary_HOLD_blocks':7,'expected_frames':5120,
            'max_operator_wait_seconds':1800,'while_waiting':'PING only every 2 seconds; same boot and REF park required'},
    failure='Preserve all data and stop before the next scored waveform; no new amplitude or threshold after viewing failure.',
    B5_revision={'large_amplitude_v':.8,'original_synthetic_large_amplitude_v':1.,'reason':'Headroom for first physical development conditions, declared before any diode data.',
                 'planned_training':'0.5 V step; 1 Hz 0.2/0.8 V sine unloaded; 0.8 V sine with separately measured nominal 4.7 kohm load.',
                 'reserved':'0.35 V step and 1 Hz 0.8 V sine with 9.99 kohm load; all B5 data still unobserved.'},
    validation={'tests_passed':13,'real_serial_IO':False,'API_calls':0,'tests':'Independent DC anchors, drive clipping, buffer clipping, regional failures, bias bounds; fake byte-protocol runner normal/bad-REF/clipped-drive stop.'},
    assembly_status='Operator removal/loose-diode reply pending; diode not requested for insertion.',
    cited_diode_polarity_source='https://www.vishay.com/docs/81857/1n4148.pdf')
log=Recorder(ROOT/'runs/hardware-b5-range-plan',mode='prospective_range_control_before_any_B5_data')
(log.path/'plan.json').write_text(json.dumps(p,indent=2)+'\n');digest=hashlib.sha256((log.path/'plan.json').read_bytes()).hexdigest()
(log.path/'freeze-source.py').write_bytes(Path(__file__).read_bytes())
(log.path/'assembly-and-scope.md').write_bytes((ROOT/'docs/b5-preparation.md').read_bytes())
log.add('B5_range_plan_frozen',{'plan_sha256':digest,'source_sha256':p['source_sha256'],'hardware_IO':False,'API_calls':0})
log.add('run_completed',{'plan_sha256':digest,'control_execution_pending':True,'B5_diode_data_observed':False})
target=ROOT/'examples/hardware-b5-preparation/2026-10-30/plan-freeze'/log.path.name
target.parent.mkdir(parents=True,exist_ok=True);shutil.copytree(log.path,target)
for path in log.path.iterdir():assert path.read_bytes()==(target/path.name).read_bytes()
(ROOT/'runs/b5-range-plan-path.txt').write_text(str(target/'plan.json')+'\n')
doc=ROOT/'docs/preregistration.md'
doc.write_text(doc.read_text()+'''
## First physical B5 preparation — 2026-10-30, before diode observations

The prior Spark-directed physical D01 run is complete. The next target remains
B5 structure proposal and independent checks; no B5 diode data or holdout has
been acquired for this revision. A resistor-only fixture control comes first.

The first physical development large-signal amplitude is explicitly **0.8 V**
instead of the synthetic example's 1.0 V, to retain operating headroom. Small
signal remains 0.2 V; sine frequency is 1 Hz, 512 frames at 4 ms. The planned
training step is 0.5 V. Reserve the 0.35 V step and 0.8 V sine with the existing
9.99 kohm load; a separately measured nominal 4.7 kohm load is training-only.
This does not claim a result at +/-1 V or completion of the original D2 freeze.

Nonlinear physical prediction must retain actual IN/OUT-minus-REF bias. Fresh
supply/REF and independent differential DMM readings at HOLD anchor channel
offsets before scored waveforms. Do not silently set both DC origins to zero,
fit scored OUT offsets, or identify the diode model from a one-point meter test.
Provisional gains may scale with newly reported supply; their slope is not
fit from scored data. Raw A4 remains a stability guard, with no automatic servo.

The local resistor-only control compares OUT with measured IN and independently
checks IN against the prior driver-volts-per-code map. The same predeclared
9 mV whole/region allowance and 3 mV stationary/A4 span apply; these remain
engineering limits, not confidence bounds. Failures stop later scored captures
and remain visible. The control makes zero API calls. It is not a B5 discovery,
full D2 acceptance, or the November 1 repeated-run/X1 development gate.
See [preparation and bias policy](b5-preparation.md).
''')
print(json.dumps({'plan':str(target/'plan.json'),'sha256':digest,'tests_passed':13,'hardware_IO':False,'API_calls':0}))
