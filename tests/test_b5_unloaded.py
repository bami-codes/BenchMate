"""Offline discovery and instrument checks. No API or physical device access."""
from copy import deepcopy
import json
from types import SimpleNamespace
import numpy as np
import pytest
from benchmate.b5_bench import MockB5Bench,PhysicalB5Bench
from benchmate.b5_session import B5Session,CONTROL,TRAINING,RESERVED
from benchmate.b5_models import validate,fit_linear,fit_proposal,predict,score
from benchmate.agent import ToolRejected
from benchmate.records import canonical
from benchmate.instrument import InstrumentConfig

class Log:
    def __init__(self):self.events=[]
    def add(self,k,p):self.events.append((k,deepcopy(p)))

ELEMENTS=[dict(name='R1',kind='R',a='IN',b='OUT',value=10000.,model='none'),
          dict(name='D1',kind='D',a='OUT',b='REF',value=0.,model='generic_diode')]

def prepared():
    log=Log();bench=MockB5Bench(log);bench.prepare_specimen()
    return bench,[bench.acquire(s,'training') for s in TRAINING]

@pytest.fixture(scope='module')
def fitted():
    bench,captures=prepared()
    return bench,captures,fit_proposal(ELEMENTS,captures)

def test_unknown_reference_allows_behavioral_fit_without_claiming_identifiable_parts(fitted):
    bench,captures,result=fitted
    assert result['training_passed'] and not result['parameters_identifiable']
    assert result['local_parameter_rank']<result['fitted_parameter_count']
    assert not result['unique_physical_parameters_claimed']
    assert fit_linear(captures)['status']=='all_candidates_inadequate'
    original=canonical(result['model'])
    for s in RESERVED:
        c=bench.acquire(s,'verification');assert score(c,predict(result['model'],c['input_template']))['passed']
    assert canonical(result['model'])==original

@pytest.mark.parametrize('fault',['reserved','control','boot','origin','load','source'])
def test_training_rejects_roles_changed_boot_origin_load_and_false_provenance(fault):
    _,captures=prepared()
    if fault in ('reserved','control'):captures[-1]['purpose']='verification' if fault=='reserved' else 'control'
    if fault=='boot':captures[-1]['boot_id']='other'
    if fault=='origin':captures[-1]['origin_id']='other'
    if fault=='load':captures[-1]['input_template']['settings']['load_ohm']=9990
    if fault=='source':captures[-1]['source']='physical'
    with pytest.raises(ValueError):fit_linear(captures)

def test_regional_failure_cannot_be_hidden_by_whole_wave_rms():
    bench,captures=prepared();c=captures[1]
    y=np.array(c['output_relative_origin_v']);p=y.copy();p[51:61]+=.02
    result=score(c,p)
    assert result['RMS_mV']<9 and not result['passed']

def test_outputs_cannot_enter_prediction(fitted):
    _,captures,result=fitted;c=deepcopy(captures[0]);t=deepcopy(c['input_template'])
    t['data']['output_relative_origin_v']=c['output_relative_origin_v']
    with pytest.raises(ValueError):predict(result['model'],t)

def session_ready(monkeypatch,fitted,*,publication=True):
    log=Log();bench=MockB5Bench(log)
    receipt=[]
    def publish(f,d):
        assert bench.count==6 and 'reserved_output_samples_used' in f
        receipt.append(deepcopy(f));return {'published':publication,'sha256':d,'remote':False}
    session=B5Session(bench,log,publish)
    session.dispatch('inspect_bench',{})
    session.dispatch('measure',{'action':'resistor_control','reason':'Check ADC paths'})
    session.dispatch('prepare_specimen',{})
    session.dispatch('measure',{'action':'amplitude_sweep','reason':'Check amplitude dependence'})
    # Reuse the independently computed fit to keep state-machine failure tests fast.
    monkeypatch.setattr('benchmate.b5_session.fit_proposal',lambda e,c:deepcopy(fitted[2]))
    session.dispatch('propose_netlist',{'elements':ELEMENTS,'rationale':'Test a clamp branch'})
    return session,bench,receipt

def test_complete_shared_tool_flow_freezes_before_reserved_and_hides_assembly(monkeypatch,fitted):
    s,b,receipt=session_ready(monkeypatch,fitted)
    result=s.dispatch('verify_proposal',{})
    assert result['passed'] and b.count==8 and len(receipt)==1
    s.dispatch('finish_report',{'verdict':'verified','explanation':'Mock only','limits':'Unloaded only'})
    names=[k for k,p in s.log.events]
    assert names.index('b5_prediction_publication')<names.index('b5_reserved_check')
    assert receipt[0]['source']=='mock' and s.summary()['instrument']['physical_measurements']==0

def test_failed_publication_does_not_acquire_reserved_data(monkeypatch,fitted):
    s,b,_=session_ready(monkeypatch,fitted,publication=False)
    with pytest.raises(ValueError):s.dispatch('verify_proposal',{})
    assert b.count==6
    with pytest.raises(ToolRejected):s.dispatch('verify_proposal',{})

@pytest.mark.parametrize('fault',['output','boot','origin'])
def test_failed_reserved_or_continuity_never_allows_refit_or_verified_report(monkeypatch,fitted,fault):
    s,b,_=session_ready(monkeypatch,fitted);original=b.acquire
    def bad(settings,role):
        c=original(settings,role)
        if role=='verification':
            if fault=='output':c['output_relative_origin_v']=(np.array(c['output_relative_origin_v'])+.04).tolist()
            else:c['boot_id' if fault=='boot' else 'origin_id']='changed'
        return c
    b.acquire=bad
    if fault=='output':assert not s.dispatch('verify_proposal',{})['passed']
    else:
        with pytest.raises(ValueError):s.dispatch('verify_proposal',{})
    with pytest.raises(ToolRejected):s.dispatch('propose_netlist',{'elements':ELEMENTS,'rationale':'refit forbidden'})
    with pytest.raises(ToolRejected):s.dispatch('finish_report',{'verdict':'verified','explanation':'Invalid','limits':'Invalid'})

class Board:
    def __init__(self,p):
        self.cfg=InstrumentConfig(**p['configuration']);self.boot='b'*32;self.armed=False;self.code=0
        self.commands=[];self.uptime=0;self.ref_shift=0.;self.opens=0
    def factory(self,*a,**kw):self.opens+=1;return self
    def __enter__(self):return self
    def __exit__(self,*a):pass
    def reset_input_buffer(self):pass
    def write(self,command):
        words=command.decode().split();self.commands.append(words);self.uptime+=1
        p=dict(protocol='benchmate-instrument-v2',boot_id=self.boot,boot_id_ready=True,uptime_ms=self.uptime)
        if words[0]=='PING':
            p.update(type='pong',armed=self.armed,current_code=self.code,ref_code=self.code,dc_hold_supported=True,
                adc_sample_state_channels=[0,1,2,21],adc_sample_states_readback=[255]*4,max_jump_code=self.cfg.max_jump)
        elif words[0]=='ARM':self.armed=True;self.code=int(words[2]);p['type']='armed'
        elif words[0]=='CAPTURE':
            kind,n,period,amp,freq=words[2],*map(int,words[3:7])
            codes=np.full(n,self.code)
            if kind=='STEP':codes=self.code+np.where(np.arange(n)<n//10,-amp,amp)
            if kind=='SINE':codes=self.code+np.round(amp*np.sin(2*np.pi*freq/1000*np.arange(n)*period/1e6)).astype(int)
            volts=codes*self.cfg.vref_v/4095;counts=np.round(volts*16383/self.cfg.vref_v).astype(int)
            ref=round((self.cfg.ref_v+self.ref_shift)*16383/self.cfg.vref_v)
            p.update(type='capture',source='hardware_uncalibrated',adc_bits=14,dac_bits=12,channels=['A1','A2','A3','A4'],
                timestamp_semantics='analogRead_completion_us',timing_valid=True,overruns=0,adc_sample_states_readback_min=255,
                adc_sample_state_channels=[0,1,2,21],adc_sample_states_readback_before=[255]*4,adc_sample_states_readback_after=[255]*4,
                requested_samples=n,period_us=period,kind=kind,amplitude_or_hold_code=amp,frequency_millihz=freq,parked_ref_code=self.cfg.ref_code,
                rows=[[i*period,int(codes[i]),int(counts[i]),int(counts[i]),int(counts[i]),ref,50,105,160,215] for i in range(n)])
        self.response=(json.dumps(p)+'\n').encode();return len(command)
    def read_until(self,*a,**kw):return self.response

def physical():
    p={'configuration':{'vref_v':4.90,'ref_v':1.646},'USB_identity':[9025,105,'FAKE'],
       'voltage_conversion':{'channels':{ch:{'gain_v_per_count':4.9/16383,'offset_v':0.} for ch in ['A1','A2','A3']}},
       'guard_limits':{'A4_envelope_v':.15,'REF_mean_delta_v_max':.1,'REF_any_sample_delta_v_max':.15,
                       'REF_channel_mean_spread_v_max':.05,'signal_envelope_v':.95}}
    board=Board(p);log=Log();report={'fixture':'resistor_only','USB_connected':True,'USB_off_wiring_confirmed':True,'verbatim':'Test fixture'}
    def confirm(fixture):
        board.boot='c'*32;board.armed=False;board.code=0;board.uptime=0
        return {**report,'fixture':fixture}
    bench=PhysicalB5Bench(p,log,confirm,initial_report=report,previous_boot_id='a'*32,serial_factory=board.factory,
        ports=lambda:[SimpleNamespace(vid=9025,pid=105,serial_number='FAKE',device='FAKE_NO_DEVICE')],sleep=lambda _:None)
    return bench,board,log

def test_real_adapter_byte_protocol_control_install_training_reserved_no_dmm():
    bench,board,log=physical()
    for s in CONTROL:validate(bench.acquire(s,'control'),'control')
    bench.prepare_specimen();observations=[]
    for role,settings in [('training',TRAINING),('verification',RESERVED)]:
        for s in settings:observations.append(bench.acquire(s,role))
    assert len({(o['boot_id'],o['origin_id']) for o in observations})==1
    assert sum(c[0]=='ARM' for c in board.commands)==2
    assert bench.frames==8*3*512
    assert not any('DMM' in k for k,p in log.events)

@pytest.mark.parametrize('fault',['missing_confirmation','changed_boot','A4_drift'])
def test_real_adapter_stops_without_retry_or_rearm(fault):
    bench,board,log=physical()
    if fault=='missing_confirmation':bench.initial_report['USB_off_wiring_confirmed']=False
    else:
        bench.acquire(CONTROL[0],'control')
        if fault=='changed_boot':board.boot='d'*32
        else:board.ref_shift=.004
    with pytest.raises(ValueError):bench.acquire(CONTROL[0],'control')
    count=len(board.commands)
    with pytest.raises(RuntimeError):bench.acquire(CONTROL[0],'control')
    assert len(board.commands)==count
    assert sum(c[0]=='ARM' for c in board.commands)==(0 if fault=='missing_confirmation' else 1)
