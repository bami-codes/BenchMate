"""Isolated fake-device checks. Test records remain in /private/tmp only."""
from pathlib import Path
import importlib.util,sys,tempfile,json,shutil,types
REAL=Path('/Users/bami/Documents/metaai')
sys.path.insert(0,str(REAL/'src'))
spec=importlib.util.spec_from_file_location('repair_capture','/private/tmp/benchmate-capture-conditional-repair-after-reset.py')
mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
prediction=Path((REAL/'runs/d01-repair-voltage-path.txt').read_text().strip())
p=json.loads(prediction.read_text());cfg=mod.InstrumentConfig(**p['configuration'])
conditional=Path((REAL/'runs/d01-repair-conditional-plan-path.txt').read_text().strip())

def run_case(fault):
    root=Path(tempfile.mkdtemp(prefix='benchmate-repair-fake-',dir='/private/tmp'))
    (root/'runs').mkdir();(root/'runs/d01-repair-conditional-plan-path.txt').write_text(str(conditional))
    for rel in [p['model_plan'],'src/benchmate/instrument.py','src/benchmate/measured_input.py']:
        target=root/rel;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(REAL/rel,target)
    commands=[]
    class Board:
        def __init__(self,*args,**kwargs):self.armed=False;self.code=0;self.uptime=0;self.response=b''
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def reset_input_buffer(self):pass
        def write(self,command):
            words=command.decode().split();commands.append(words);self.uptime+=1
            packet={'protocol':'benchmate-instrument-v2','boot_id':'dddddddddddddddddddddddddddddddd','boot_id_ready':True,'uptime_ms':self.uptime}
            if words[0]=='PING':
                packet.update(type='pong',armed=self.armed,current_code=self.code,ref_code=self.code,
                    dc_hold_supported=True,adc_sample_state_channels=[0,1,2,21],adc_sample_states_readback=[255]*4,max_jump_code=cfg.max_jump)
            elif words[0]=='ARM':
                self.armed=True;self.code=int(words[2]);packet.update(type='armed')
            elif words[0]=='CAPTURE':
                kind=words[2];n=int(words[3]);period=int(words[4]);amp=int(words[5]);freq=int(words[6])
                packet.update(type='capture',source='hardware_uncalibrated',adc_bits=14,dac_bits=12,
                    channels=['A1','A2','A3','A4'],timestamp_semantics='analogRead_completion_us',timing_valid=True,
                    overruns=0,adc_sample_states_readback_min=255,adc_sample_state_channels=[0,1,2,21],
                    adc_sample_states_readback_before=[255]*4,adc_sample_states_readback_after=[255]*4,
                    requested_samples=n,period_us=period,kind=kind,amplitude_or_hold_code=amp,
                    frequency_millihz=freq,parked_ref_code=cfg.ref_code)
                if fault=='changed_boot':packet['boot_id']='c'*32
                waveform=next((w for w in p['waveforms'] if w['settings']['kind']==kind.lower()),None)
                rows=[]
                for i in range(n):
                    code=waveform['expected_DAC_codes'][i] if waveform else cfg.ref_code
                    which='no_repair_counterfactual' if fault=='unrepaired_truth' else 'repair_to_declared_nominal_C'
                    center=p['actuator']['driver_v_per_code']*cfg.ref_code+p['actuator']['driver_offset_v']
                    g=p['waveforms'][0]['predictions']['repair_to_declared_nominal_C']['gain']
                    out=(waveform['predictions'][which]['predicted_A2_v'][i] if waveform else cfg.ref_v+g*(center-cfg.ref_v))+.012
                    drive=p['actuator']['driver_v_per_code']*code+p['actuator']['driver_offset_v']
                    volts=[drive,out,drive,cfg.ref_v+(.20 if fault=='bad_ref' else 0)]
                    counts=[]
                    for j,ch in enumerate(['A1','A2','A3','A4']):
                        if ch=='A4':counts.append(round(volts[j]*16383/cfg.vref_v))
                        else:
                            a=p['voltage_conversion']['channels'][ch]
                            counts.append(round((volts[j]-a['offset_v'])/a['gain_v_per_count']))
                    rows.append([i*period,code,*counts,50,105,160,215])
                packet['rows']=rows
            else:raise AssertionError('Unexpected command')
            self.response=(json.dumps(packet)+'\n').encode();return len(command)
        def read_until(self,*args,**kwargs):return self.response
    mod.ROOT=root;mod.serial.Serial=Board
    mod.list_ports.comports=lambda:[types.SimpleNamespace(vid=9025,pid=105,serial_number='3612211F36323632E4B233334B572F52',device='FAKE_NOT_A_DEVICE')]
    mod.time.sleep=lambda seconds:None
    try:mod.main();success=True
    except SystemExit:success=False
    if fault in [None,'unrepaired_truth']:
        assert success
        result_path=Path((root/'runs/d01-repair-conditional-capture-path.txt').read_text().strip())/'result.json'
        result=json.loads(result_path.read_text())
        assert result['incremental_repair_check_passed'] is (fault is None) and result['capture_attempts']==7
        if fault=='unrepaired_truth':assert result['scores']['step']['models']['no_repair_counterfactual']['passed']
        assert sum(c[0]=='ARM' for c in commands)==1 and all(c[0]!='DC' for c in commands)
        assert [c[2] for c in commands if c[0]=='CAPTURE']==['HOLD','HOLD','HOLD','STEP','HOLD','SINE','HOLD']
    else:
        assert not success
        assert [c[2] for c in commands if c[0]=='CAPTURE']==['HOLD']
    return {'case':fault or 'two_frozen_checks','passed':True,'real_hardware_IO':False}

print('ISOLATED FAKE-DEVICE TESTS; no real serial port opened')
results=[run_case(fault) for fault in [None,'unrepaired_truth','changed_boot','bad_ref']]
print(json.dumps({'tests':results}))
