"""Whole local control runner with a fake serial device and fake DMM reply."""
from pathlib import Path
import hashlib,importlib.util,json,math,sys
from types import SimpleNamespace
import numpy as np
import pytest
from benchmate.physical_bench import PhysicalBench
from benchmate.instrument import InstrumentConfig
from benchmate.records import read_events


@pytest.mark.parametrize('fault',[None,'drive_clips','bad_ref'])
def test_control_sequence_and_stop_before_later_waveform(tmp_path,monkeypatch,fault):
    root=Path(__file__).resolve().parents[1]
    spec=importlib.util.spec_from_file_location('range_runner',root/'scripts/b5_range_control.py')
    runner=importlib.util.module_from_spec(spec);spec.loader.exec_module(runner)
    old=json.loads((root/'examples/hardware-b1-b6-gate/2026-10-30/b1_bypass/condition/condition.json').read_text())
    p={k:old[k] for k in ['configuration','voltage_conversion','guard_limits']}
    p['guard_limits']['signal_envelope_v']=.95
    p.update(USB_identity=[9025,105,'fake_serial'],previous_boot_id='a'*32,calibration_supply_v=4.89,
             driver_v_per_code=old['actuator']['driver_v_per_code'])
    (tmp_path/'runs').mkdir();(tmp_path/'code.py').write_text('test source')
    p['source_sha256']={'code.py':hashlib.sha256((tmp_path/'code.py').read_bytes()).hexdigest()}
    protocol=tmp_path/'protocol.json';protocol.write_text(json.dumps(p))
    report=tmp_path/'report.json';report.write_text(json.dumps({'fixture':'resistor_only','USB_off_wiring_confirmed':True,
        'USB_connected':True,'verbatim':'FAKE operator confirmation','supply_v':4.89,'REF_v':1.637}))
    cfg=InstrumentConfig(**p['configuration']);commands=[]
    class Board:
        def __init__(self,*args,**kwargs):self.armed=False;self.code=0;self.uptime=0
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def reset_input_buffer(self):pass
        def write(self,command):
            w=command.decode().split();commands.append(w);self.uptime+=1
            packet={'protocol':'benchmate-instrument-v2','boot_id':'b'*32,'boot_id_ready':True,'uptime_ms':self.uptime}
            if w[0]=='PING':
                packet.update(type='pong',armed=self.armed,current_code=self.code,ref_code=self.code,dc_hold_supported=True,
                    adc_sample_state_channels=[0,1,2,21],adc_sample_states_readback=[255]*4,max_jump_code=cfg.max_jump)
            elif w[0]=='ARM':self.armed=True;self.code=int(w[2]);packet.update(type='armed')
            else:
                assert w[0]=='CAPTURE'
                kind=w[2];n=int(w[3]);period=int(w[4]);amp=int(w[5]);freq=int(w[6])
                packet.update(type='capture',source='hardware_uncalibrated',adc_bits=14,dac_bits=12,channels=['A1','A2','A3','A4'],
                    timestamp_semantics='analogRead_completion_us',timing_valid=True,overruns=0,adc_sample_states_readback_min=255,
                    adc_sample_state_channels=[0,1,2,21],adc_sample_states_readback_before=[255]*4,adc_sample_states_readback_after=[255]*4,
                    requested_samples=n,period_us=period,kind=kind,amplitude_or_hold_code=amp,frequency_millihz=freq,parked_ref_code=cfg.ref_code)
                if kind=='HOLD':codes=np.full(n,cfg.ref_code)
                elif kind=='STEP':codes=cfg.ref_code+np.where(np.arange(n)<n//10,-amp,amp)
                else:codes=cfg.ref_code+np.round(amp*np.sin(2*np.pi*freq/1000*np.arange(n)*period/1e6)).astype(int)
                delta=p['driver_v_per_code']*(codes-cfg.ref_code)
                if fault=='drive_clips':delta=np.minimum(delta,.3)
                rows=[]
                for i in range(n):
                    volts=[cfg.ref_v+.006+delta[i],cfg.ref_v+.007+delta[i],cfg.ref_v+.006+delta[i],cfg.ref_v+(.2 if fault=='bad_ref' else 0)]
                    counts=[]
                    for j,ch in enumerate(['A1','A2','A3','A4']):
                        if ch=='A4':counts.append(round(volts[j]*16383/cfg.vref_v))
                        else:
                            m=p['voltage_conversion']['channels'][ch];counts.append(round((volts[j]-m['offset_v'])/m['gain_v_per_count']))
                    rows.append([i*period,int(codes[i]),*counts,50,105,160,215])
                packet['rows']=rows
            self.response=(json.dumps(packet)+'\n').encode();return len(command)
        def read_until(self,*args,**kwargs):return self.response
    class Bench(PhysicalBench):
        def __init__(self,*args,**kwargs):
            super().__init__(*args,**kwargs,serial_factory=Board,ports=lambda:[SimpleNamespace(vid=9025,pid=105,serial_number='fake_serial',device='NOT_A_PORT')])
    def fake_sleep(_):
        pointer=tmp_path/'runs/hardware-b5-range-control-current-path.txt'
        if pointer.exists():
            path=Path(pointer.read_text().strip());request=path/'bias-request.json'
            if request.exists():
                q=json.loads(request.read_text());reply=path/q['response_file']
                if not reply.exists():reply.write_text(json.dumps({'request_id':q['request_id'],'verbatim':'FAKE independent DMM +0.006/+0.007',
                                        'input_minus_REF_v':.006,'output_minus_REF_v':.007}))
    monkeypatch.setattr(runner,'ROOT',tmp_path);monkeypatch.setattr(runner,'PhysicalBench',Bench)
    monkeypatch.setattr(runner.time,'sleep',fake_sleep)
    monkeypatch.setattr(sys,'argv',['runner','--protocol',str(protocol),'--connection-report',str(report)])
    if fault:
        with pytest.raises(SystemExit):runner.main()
    else:runner.main()
    path=Path((tmp_path/'runs/hardware-b5-range-control-current-path.txt').read_text().strip())
    events=read_events(path);result=events[-1]['payload']
    assert result['API_calls']==0 and sum(c[0]=='ARM' for c in commands)==1
    waves=[c[2] for c in commands if c[0]=='CAPTURE' and c[2]!='HOLD']
    if fault is None:
        assert result['passed'] and result['instrument']['retained_frames']==5120
        assert waves==['SINE','STEP','SINE']
        anchor=next(i for i,e in enumerate(events) if e['kind']=='differential_anchor_frozen')
        first=next(i for i,e in enumerate(events) if e['kind']=='control_waveform_requested')
        assert anchor<first
    elif fault=='drive_clips':
        assert waves==['SINE','STEP'] and not result['passed']
    else:assert waves==[] and not result['passed']
