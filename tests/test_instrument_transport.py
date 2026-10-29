import json
import pytest
import serial
from benchmate import instrument
from benchmate.records import read_events

BOOT='1234567890abcdef1234567890abcdef'
OTHER='abcdef1234567890abcdef1234567890'
CONFIG=instrument.InstrumentConfig(4.7)


def envelope(response_type,uptime=10000,boot=BOOT,**fields):
    return {'protocol':instrument.PROTOCOL,'type':response_type,'boot_id':boot,
            'boot_id_ready':True,'uptime_ms':uptime,**fields}


def pong(uptime=10000,boot=BOOT,armed=True):
    return envelope('pong',uptime,boot,armed=armed,
                    ref_code=CONFIG.ref_code,max_jump_code=CONFIG.max_jump)


def capture():
    return envelope('capture',13000,source='hardware_uncalibrated',adc_bits=14,dac_bits=12,
        channels=['A1','A2','A3','A4'],timestamp_semantics='analogRead_completion_us',
        timing_valid=True,overruns=0,adc_sample_states_readback_min=255,
        adc_sample_state_channels=[0,1,2,21],
        adc_sample_states_readback_before=[255]*4,adc_sample_states_readback_after=[255]*4,
        requested_samples=16,period_us=500,kind='STEP',amplitude_or_hold_code=435,
        frequency_millihz=0,parked_ref_code=CONFIG.ref_code,
        rows=[[i*500,CONFIG.ref_code,1000,1000,1000,1000,20,40,60,80] for i in range(16)])


class Board:
    def __init__(self,responses): self.responses=list(responses);self.writes=[]
    def __enter__(self): return self
    def __exit__(self,*args): pass
    def reset_input_buffer(self): pass
    def write(self,data): self.writes.append(data)
    def read_until(self,*args,**kwargs):
        response=self.responses.pop(0)
        if isinstance(response,Exception): raise response
        return response if isinstance(response,bytes) else json.dumps(response).encode()+b'\n'


def attach(monkeypatch,responses):
    board=Board(responses)
    monkeypatch.setattr(instrument.serial,'Serial',lambda *a,**kw:board)
    monkeypatch.setattr(instrument.time,'sleep',lambda _:None)
    return board


def run(tmp_path,**kwargs):
    return instrument.acquire_block('test',CONFIG,output=tmp_path,expected_boot_id=BOOT,
                                    samples=16,**kwargs)


def test_valid_block_requires_post_capture_same_boot_ping(monkeypatch,tmp_path):
    board=attach(monkeypatch,[pong(),capture(),pong(14000)])
    path,result=run(tmp_path)
    assert result['boot_id']==BOOT and result['boot_continuity_checked'] is True
    assert result['uptime_ms_start']==10000 and result['uptime_ms_end']==14000
    assert board.writes==[b'PING\n',f'CAPTURE {BOOT} STEP 16 500 435 0\n'.encode(),b'PING\n']
    events=read_events(path)
    assert events[-2]['kind']=='firmware_postcheck' and events[-1]['kind']=='run_completed'


@pytest.mark.parametrize('failure',['reset_before_capture','reset_in_capture','reset_after_capture',
                                  'backwards_uptime','partial_json','timeout','disconnect','legacy','unarmed'])
def test_reset_or_ambiguous_response_invalidates_entire_run_without_retry(monkeypatch,tmp_path,failure):
    replies=[pong(),capture(),pong(14000)]
    if failure=='reset_before_capture':replies[0]=pong(10,OTHER)
    if failure=='reset_in_capture':replies[1]=envelope('error',10,OTHER,message='boot identity mismatch')
    if failure=='reset_after_capture':replies[2]=pong(10,OTHER,armed=False)
    if failure=='backwards_uptime':replies[1]['uptime_ms']=10
    if failure=='partial_json':replies[1]=b'{"protocol":"benchmate-instrument-v2","rows":['
    if failure=='timeout':replies[1]=b''
    if failure=='disconnect':replies[1]=serial.SerialException('unplugged')
    if failure=='legacy':replies[0]['protocol']='benchmate-instrument-v1'
    if failure=='unarmed':replies[0]['armed']=False
    board=attach(monkeypatch,replies)
    with pytest.raises(RuntimeError,match='invalid'):run(tmp_path)
    events=read_events(next(tmp_path.iterdir()))
    assert events[-1]['kind']=='run_failed'
    assert events[-2]['kind']=='instrument_run_invalidated'
    assert events[-2]['payload']['accepted_samples']==0
    assert events[-2]['payload']['valid_for_analysis'] is False
    assert not any(e['kind']=='run_completed' for e in events)
    assert not any(cmd.startswith(b'ARM ') for cmd in board.writes)
    assert len([cmd for cmd in board.writes if cmd.startswith(b'CAPTURE ')])<=1
    if failure in ('reset_before_capture','legacy','unarmed'):assert board.writes==[b'PING\n']
    if failure in ('partial_json','timeout'):
        raw=next(e['payload'] for e in events if e['kind']=='incomplete_instrument_response')
        assert raw['raw_text']==replies[1].decode()
    if failure=='reset_after_capture':
        assert next(e['payload'] for e in events if e['kind']=='raw_capture')==capture()


def test_arm_returns_boot_id_only_after_matching_postcheck(monkeypatch,tmp_path):
    board=attach(monkeypatch,[pong(10000,armed=False),envelope('armed',13000),pong(14000)])
    _,result=instrument.acquire_block('test',CONFIG,output=tmp_path,arm_only=True)
    assert result['reference_established'] is True and result['boot_id']==BOOT
    assert board.writes==[b'PING\n',CONFIG.arm_command(BOOT),b'PING\n']


@pytest.mark.parametrize('stage',[1,2])
def test_reset_while_arming_never_returns_success_or_rearms(monkeypatch,tmp_path,stage):
    replies=[pong(10000,armed=False),envelope('armed',13000),pong(14000)]
    replies[stage]=envelope('error',10,OTHER,message='boot identity mismatch')
    board=attach(monkeypatch,replies)
    with pytest.raises(RuntimeError):instrument.acquire_block('test',CONFIG,output=tmp_path,arm_only=True)
    assert len([cmd for cmd in board.writes if cmd.startswith(b'ARM ')])==1
    assert read_events(next(tmp_path.iterdir()))[-1]['kind']=='run_failed'


@pytest.mark.parametrize('boot',[None,'','0'*32,'a'*31,'A'*32,True])
def test_capture_requires_explicit_valid_arm_boot_id_before_opening_port(monkeypatch,tmp_path,boot):
    def forbidden(*a,**kw): pytest.fail('Invalid capture must not open the port')
    monkeypatch.setattr(instrument.serial,'Serial',forbidden)
    with pytest.raises(instrument.BootContinuityError):
        instrument.acquire_block('test',CONFIG,output=tmp_path,expected_boot_id=boot)


def dc_pong(uptime=10000,boot=BOOT,current=None):
    return {**pong(uptime,boot),'dc_hold_supported':True,
            'current_code':CONFIG.ref_code if current is None else current}


def dc_run(tmp_path,hold_v=.6):
    return instrument.set_dc_level('test',CONFIG,hold_v=hold_v,expected_boot_id=BOOT,output=tmp_path)


def test_dc_hold_requires_acknowledged_code_and_postcheck_without_capture(monkeypatch,tmp_path):
    command=instrument.dc_hold_command(CONFIG,boot_id=BOOT,hold_v=.6);code=int(command.split()[2])
    board=attach(monkeypatch,[dc_pong(),envelope('dc_held',13000,held_code=code),dc_pong(14000,current=code)])
    path,result=dc_run(tmp_path)
    assert board.writes==[b'PING\n',command,b'PING\n']
    assert result['held_code']==code and result['output_remains_driven'] is True
    assert result['accepted_samples']==0 and result['calibration_performed'] is False
    assert read_events(path)[-1]['kind']=='run_completed'


@pytest.mark.parametrize('fault',['legacy_support','unarmed','limits','reset_before','reset_during',
                                'reset_after','wrong_ack','wrong_post','settle_failed','timeout',
                                'partial_json','disconnect','backwards_uptime'])
def test_dc_uncertainty_cannot_trigger_rearm_or_success(monkeypatch,tmp_path,fault):
    code=int(instrument.dc_hold_command(CONFIG,boot_id=BOOT,hold_v=.6).split()[2])
    replies=[dc_pong(),envelope('dc_held',13000,held_code=code),dc_pong(14000,current=code)]
    if fault=='legacy_support':replies[0].pop('dc_hold_supported')
    if fault=='unarmed':replies[0]['armed']=False
    if fault=='limits':replies[0]['ref_code']+=1
    if fault=='reset_before':replies[0]['boot_id']=OTHER
    if fault=='reset_during':replies[1]['boot_id']=OTHER
    if fault=='reset_after':replies[2]['boot_id']=OTHER
    if fault=='wrong_ack':replies[1]['held_code']+=1
    if fault=='wrong_post':replies[2]['current_code']+=1
    if fault=='settle_failed':replies[1]=envelope('error',13000,message='DC settling failed')
    if fault=='timeout':replies[1]=b''
    if fault=='partial_json':replies[1]=b'{"type":"dc_held"'
    if fault=='disconnect':replies[1]=serial.SerialException('disconnected')
    if fault=='backwards_uptime':replies[1]['uptime_ms']=9000
    board=attach(monkeypatch,replies)
    with pytest.raises(RuntimeError,match='unconfirmed'):dc_run(tmp_path)
    events=read_events(next(tmp_path.iterdir()))
    assert events[-1]['kind']=='run_failed' and events[-2]['kind']=='DC_hold_invalidated'
    assert events[-2]['payload']['output_state_confirmed'] is False
    assert not any(c.startswith((b'ARM ',b'CAPTURE ',b'STOP ')) for c in board.writes)
    assert sum(c.startswith(b'DC ') for c in board.writes)<=1
    if fault in ('legacy_support','unarmed','limits','reset_before'):assert board.writes==[b'PING\n']


def test_dc_missing_identity_never_opens_port(monkeypatch,tmp_path):
    def forbidden(*a,**kw):pytest.fail('Missing identity must not open serial')
    monkeypatch.setattr(instrument.serial,'Serial',forbidden)
    with pytest.raises(instrument.BootContinuityError):
        instrument.set_dc_level('test',CONFIG,hold_v=.6,expected_boot_id=None,output=tmp_path)


def test_cli_dc_selects_only_persistent_level_transport(monkeypatch,tmp_path,capsys):
    import sys
    from benchmate import cli
    calls=[]
    def hold(port,config,**kwargs):
        calls.append((port,config,kwargs));return tmp_path,{'held_code':523}
    def forbidden(*a,**kw):pytest.fail('DC CLI must not invoke ARM/capture transport')
    monkeypatch.setattr(instrument,'set_dc_level',hold)
    monkeypatch.setattr(instrument,'acquire_block',forbidden)
    monkeypatch.setattr(sys,'argv',['benchmate','instrument','--port','test','--vref-v','4.7',
                                   '--boot-id',BOOT,'--set-dc-v','0.6'])
    assert cli.main()==0
    assert len(calls)==1 and calls[0][2]['expected_boot_id']==BOOT and calls[0][2]['hold_v']==.6
    assert json.loads(capsys.readouterr().out)['held_code']==523


def test_cli_dc_cannot_be_combined_with_arm(monkeypatch):
    import sys
    from benchmate import cli
    monkeypatch.setattr(sys,'argv',['benchmate','instrument','--port','test','--vref-v','4.7',
                                   '--set-dc-v','0.6','--arm-only'])
    with pytest.raises(SystemExit) as exc:cli.main()
    assert exc.value.code==2
