"""Fake serial only: exercise the actual byte protocol and stop conditions."""
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
import json
import numpy as np
import pytest
from benchmate.instrument import InstrumentConfig
from benchmate.physical_bench import PhysicalBench
from benchmate.physical_rc import STEP,SINE
from test_physical_rc import Log,observation


@pytest.fixture
def protocol():
    root=Path(__file__).resolve().parents[1]
    p=json.loads((root/'examples/hardware-b1-b6-gate/2026-10-30/b1_bypass/condition/condition.json').read_text())
    return {k:deepcopy(p[k]) for k in ['configuration','voltage_conversion','guard_limits']}|{'USB_identity':[9025,105,'3612211F36323632E4B233334B572F52']}


class FakeBoard:
    def __init__(self,protocol,fault=None):
        self.p=protocol;self.cfg=InstrumentConfig(**protocol['configuration']);self.fault=fault
        self.commands=[];self.opens=0;self.armed=False;self.code=0;self.boot='b'*32;self.uptime=0;self.loaded=False
    def factory(self,*args,**kwargs):self.opens+=1;return self
    def __enter__(self):return self
    def __exit__(self,*args):pass
    def reset_input_buffer(self):pass
    def write(self,command):
        words=command.decode().split();self.commands.append(words);self.uptime+=1
        p={'protocol':'benchmate-instrument-v2','boot_id':self.boot,'boot_id_ready':True,'uptime_ms':self.uptime}
        if words[0]=='PING':
            p.update(type='pong',armed=self.armed,current_code=self.code,ref_code=self.code,dc_hold_supported=True,
                     adc_sample_state_channels=[0,1,2,21],adc_sample_states_readback=[255]*4,max_jump_code=self.cfg.max_jump)
        elif words[0]=='ARM':self.armed=True;self.code=int(words[2]);p.update(type='armed')
        elif words[0]=='CAPTURE':
            kind=words[2];n=int(words[3]);period=int(words[4]);amp=int(words[5]);freq=int(words[6])
            p.update(type='capture',source='hardware_uncalibrated',adc_bits=14,dac_bits=12,channels=['A1','A2','A3','A4'],
                timestamp_semantics='analogRead_completion_us',timing_valid=True,overruns=0,adc_sample_states_readback_min=255,
                adc_sample_state_channels=[0,1,2,21],adc_sample_states_readback_before=[255]*4,adc_sample_states_readback_after=[255]*4,
                requested_samples=n,period_us=period,kind=kind,amplitude_or_hold_code=amp,frequency_millihz=freq,parked_ref_code=self.cfg.ref_code)
            if self.fault=='changed_boot':p['boot_id']='c'*32
            if kind=='HOLD':inputs=np.full(n,1.63);outputs=np.full(n,1.64);codes=np.full(n,self.cfg.ref_code)
            else:
                settings=STEP if kind=='STEP' else SINE
                obs=observation(settings,load=9990. if self.loaded else None)
                inputs=obs['data']['input_v'];outputs=obs['data']['output_v']
                codes=self.cfg.ref_code+np.where(np.arange(n)<n//10,-amp,amp) if kind=='STEP' else self.cfg.ref_code+np.round(amp*np.sin(2*np.pi*freq/1000*np.arange(n)*period/1e6)).astype(int)
            rows=[]
            for i in range(n):
                volts=[inputs[i],outputs[i],inputs[i],self.cfg.ref_v+(.20 if self.fault=='bad_ref' else 0)]
                counts=[]
                for j,ch in enumerate(['A1','A2','A3','A4']):
                    if ch=='A4':counts.append(round(volts[j]*16383/self.cfg.vref_v))
                    else:
                        mapping=self.p['voltage_conversion']['channels'][ch]
                        counts.append(round((volts[j]-mapping['offset_v'])/mapping['gain_v_per_count']))
                rows.append([i*period,int(codes[i]),*counts,50,105,160,215])
            p['rows']=rows
        else:raise AssertionError('Unknown command')
        self.response=(json.dumps(p)+'\n').encode();return len(command)
    def read_until(self,*args,**kwargs):return b'' if self.fault=='timeout' else self.response


def make_bench(protocol,fault=None,initial=None,confirm=None):
    board=FakeBoard(protocol,fault);log=Log()
    report={'fixture':'unloaded','USB_connected':True,'USB_off_wiring_confirmed':True,'verbatim':'Fake fixture confirmed'}
    def default_confirm(fixture):
        board.loaded=True;board.armed=False;board.code=0;board.boot='d'*32;board.uptime=0
        return {**report,'fixture':fixture}
    bench=PhysicalBench(protocol,log,confirm or default_confirm,initial_report=report if initial is None else initial,
        previous_boot_id='a'*32,serial_factory=board.factory,
        ports=lambda:[SimpleNamespace(vid=9025,pid=105,serial_number=protocol['USB_identity'][2],device='FAKE_NOT_A_DEVICE')],sleep=lambda _:None)
    return bench,board,log


def test_unloaded_load_pause_and_same_boot_reserved_sequence(protocol):
    bench,board,log=make_bench(protocol)
    for settings,fixture,phase in [(STEP,'unloaded','unloaded_step'),(STEP,'output_load','attach_output_load_step'),(SINE,'output_load','reserved_sine')]:
        observed=bench.acquire(settings,{},fixture,phase)
        assert observed['all_guards_passed'] and observed['fresh_measurement']
    assert bench.frames==7680 and bench.capture_attempts==15 and bench.human_interventions==1
    assert sum(c[0]=='ARM' for c in board.commands)==2
    assert [c[2] for c in board.commands if c[0]=='CAPTURE']==['HOLD','HOLD','HOLD','STEP','HOLD']*2+['HOLD','HOLD','HOLD','SINE','HOLD']
    names=[k for k,v in log.events]
    assert names.index('pre_stimulus_origin_frozen')<names.index('unloaded_step_raw_capture')


@pytest.mark.parametrize('fault,count',[('changed_boot',1),('bad_ref',1),('timeout',0)])
def test_transport_or_reference_failure_stops_without_retry(protocol,fault,count):
    bench,board,log=make_bench(protocol,fault)
    with pytest.raises(ValueError):bench.acquire(STEP,{},'unloaded','unloaded_step')
    assert bench.capture_attempts==count
    before=len(board.commands)
    with pytest.raises(RuntimeError):bench.acquire(STEP,{},'unloaded','unloaded_step')
    assert len(board.commands)==before


def test_missing_initial_human_confirmation_sends_no_command(protocol):
    bench,board,log=make_bench(protocol,initial={'fixture':'unloaded','USB_connected':True})
    with pytest.raises(ValueError):bench.acquire(STEP,{},'unloaded','unloaded_step')
    assert board.commands==[] and board.opens==0


def test_missing_load_confirmation_does_not_open_port_again(protocol):
    bench,board,log=make_bench(protocol,confirm=lambda fixture:{'fixture':fixture,'USB_connected':True})
    bench.acquire(STEP,{},'unloaded','unloaded_step');before=len(board.commands)
    with pytest.raises(ValueError):bench.acquire(STEP,{},'output_load','attach_output_load_step')
    assert board.opens==1 and len(board.commands)==before


def test_unexpected_reboot_on_same_fixture_is_not_automatically_armed(protocol):
    bench,board,log=make_bench(protocol)
    bench.acquire(STEP,{},'unloaded','unloaded_step');board.boot='e'*32
    with pytest.raises(ValueError):bench.acquire(STEP,{},'unloaded','repeat_unloaded_step')
    assert sum(c[0]=='ARM' for c in board.commands)==1


def test_full_tool_loop_uses_new_serial_captures_and_hides_operator_truth(protocol):
    from benchmate.agent import drive_agent
    from benchmate.physical_rc import PhysicalRCSession
    bench,board,log=make_bench(protocol)
    bench.initial_report['operator_only_assembly_marker']='DO_NOT_SEND_ASSEMBLY_TRUTH'
    session=PhysicalRCSession(bench.acquire,log)
    calls=[('inspect_experiment',{}),('measure',{'action':'unloaded_step','reason':'Measure tau'}),
           ('measure',{'action':'attach_output_load_step','reason':'Separate R and C'}),('verify_prediction',{}),
           ('finish_report',{'verdict':'verified','candidate':'c_changed','current_explanation':'Limited physical evidence',
                             'unresolved':'Calibration and other families','next_observation':'Further independent validation'})]
    class Model:
        def __init__(self):self.i=0;self.results=[]
        def next_call(self):
            name,args=calls[self.i];self.i+=1
            return {'call_id':str(self.i),'name':name,'arguments':json.dumps(args)}
        def sanitize(self,value):return value
        def submit_result(self,call_id,result):self.results.append(result)
    model=Model();result=drive_agent(session,model)
    assert result['reserved_check_passed'] and result['scored_capture_count']==3
    assert bench.frames==7680 and board.opens==3
    assert 'DO_NOT_SEND_ASSEMBLY_TRUTH' not in json.dumps(model.results)
    assert any('DO_NOT_SEND_ASSEMBLY_TRUTH' in json.dumps(v) for k,v in log.events if k=='operator_wiring_confirmation')
