from pathlib import Path
import json,hashlib,sys,shutil
ROOT=Path('/Users/bami/Documents/metaai');sys.path.insert(0,str(ROOT/'src'))
from benchmate.records import Recorder,read_events
from benchmate.physical_rc import STEP,SINE,SCOPE,REGIONS
source=ROOT/'examples/hardware-b1-b6-gate/2026-10-30/b1_bypass/condition/condition.json'
old=json.loads(source.read_text())
paths=['src/benchmate/physical_rc.py','src/benchmate/physical_bench.py','src/benchmate/measured_input.py',
       'src/benchmate/instrument.py','src/benchmate/agent.py','src/benchmate/providers.py','scripts/physical_spark_rc.py']
p={k:old[k] for k in ['configuration','voltage_conversion','guard_limits']}
p.update(scope=SCOPE,USB_identity=[9025,105,'3612211F36323632E4B233334B572F52'],
    nominal_design={'R_ohm':10000.,'C_f':1e-6},intervention_load_ohm=9990.,
    first_measurement=STEP,reserved_verification=SINE,
    source_sha256={rel:hashlib.sha256((ROOT/rel).read_bytes()).hexdigest() for rel in paths},
    calibration_source=str(source.relative_to(ROOT)),calibration_source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
    power_policy='Known passive fixture only. Last supply estimate 4.89 V retained, not newly metered. Code 1371 is a command center, not proof of physical REF. Explicit USB-off hookup/reconnection confirmation required for a fresh boot and one ARM. Same-fixture continuation requires the same armed boot. No firmware update, retry, servo or automatic re-arm.',
    training={'capture':'first unloaded step only','free_parameters':['tau_s'],'tau_bounds_s':[.002,.08],
              'gain_fixed':1.,'baseline':'three separate HOLD blocks before the waveform','all_512_OUT_samples_used':True,
              'fixed_point_alternatives':['nominal R and C','R=tau/Cnom with C=Cnom','R=Rnom with C=tau/Rnom'],
              'model_refit_from_loaded_or_reserved_data':False},
    scoring={'whole_RMS_mV_max':9,'each_region_RMS_mV_max':9,'step_regions_ms':REGIONS,'sine_phase_bins':8,
             'A4_block_mean_span_mV_max':3,'stationary_path_mean_span_mV_max':3,'max_time_error_us':25,
             'step_DAC_code_error_max':0,'sine_DAC_code_error_max':1,
             'same_frozen_models_for_loaded_step_and_reserved_sine':True,
             'guard_reference_reset_only_after_confirmed_new_boot':True,
             'waveforms_conditioned_on_measured_IN':True,'scored_OUT_never_used_for_reserved_prediction':True},
    budget={'initial_training_captures':1,'diagnostic_captures_max':2,'reserved_captures_max':1,
            'stationary_HOLD_blocks_per_scored_capture':4,'frames_per_capture':512,'max_API_requests':8,
            'usual_useful_path_scored_captures':3,'usual_useful_path_total_frames':7680,
            'operator_response_timeout_seconds':1800,'timeout_never_approval':True},
    tests={'command':'pytest -q -p no:cacheprovider tests/test_physical_bench.py tests/test_physical_rc.py tests/test_measured_input.py tests/test_instrument.py tests/test_instrument_transport.py tests/test_agent.py tests/test_providers.py','passed':113,'physical_hardware_IO':False,'API_calls':0},
    exclusions=['specimen identity and assembly truth from model input','previous specimen observations from model input',
                'arbitrary model-provided commands or voltages','automatic mounting','physical repair in this first adapter run',
                'absolute-voltage or calibrated-confidence claims','full-family or blinded benchmark claims'])
log=Recorder(ROOT/'runs/hardware-spark-rc-protocol',mode='prospective_physical_agent_protocol_freeze')
(log.path/'protocol.json').write_text(json.dumps(p,indent=2)+'\n')
(log.path/'freeze-source.py').write_bytes(Path(__file__).read_bytes())
digest=hashlib.sha256((log.path/'protocol.json').read_bytes()).hexdigest()
log.add('physical_agent_protocol_frozen',{'sha256':digest,'no_new_hardware_IO':True,'API_calls':0,'source_sha256':p['source_sha256']})
log.add('run_completed',{'protocol_sha256':digest,'implementation_tests_passed':113,'physical_execution_pending':True})
target=ROOT/'examples/hardware-spark-rc/2026-10-30/protocol-freeze'/log.path.name
target.parent.mkdir(parents=True,exist_ok=True);shutil.copytree(log.path,target)
for path in log.path.iterdir():assert path.read_bytes()==(target/path.name).read_bytes()
(ROOT/'runs/hardware-spark-rc-protocol-path.txt').write_text(str(target/'protocol.json')+'\n')
print(json.dumps({'protocol':str(target/'protocol.json'),'sha256':digest,'physical_execution_pending':True}))
