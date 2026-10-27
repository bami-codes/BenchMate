import copy
import pytest
from benchmate.instrument import InstrumentConfig,capture_command,validate_block,BootContinuity,BootContinuityError

BOOT='1234567890abcdef1234567890abcdef'


def packet():
    return {'protocol':'benchmate-instrument-v2','type':'capture','source':'hardware_uncalibrated',
            'boot_id':BOOT,'boot_id_ready':True,'uptime_ms':13000,'parked_ref_code':1394,
            'adc_bits':14,'dac_bits':12,'channels':['A1','A2','A3','A4'],
            'timestamp_semantics':'analogRead_completion_us','timing_valid':True,'overruns':0,
            'adc_sample_states_readback_min':255,'requested_samples':16,'period_us':500,
            'kind':'STEP','amplitude_or_hold_code':435,'frequency_millihz':0,
            'rows':[[i*500,1394,1000,1000,1000,1000,20,40,60,80] for i in range(16)]}


def test_quantized_commands_keep_one_volt_limit_at_measured_supply():
    for vref in (4,4.7,5,5.5):
        config=InstrumentConfig(vref)
        command=capture_command(config,boot_id=BOOT).decode().split()
        amplitude=int(command[5])
        assert 2*amplitude<=config.max_jump
        assert 2*amplitude*vref/4095<=1
        arm=list(map(int,config.arm_command(BOOT).decode().split()[2:]))
        assert arm[0]-arm[1]<=arm[3] and arm[2]-arm[0]<=arm[3]
    with pytest.raises(ValueError):capture_command(InstrumentConfig(4.7),boot_id=BOOT,amplitude_v=.51)
    with pytest.raises(ValueError):capture_command(InstrumentConfig(4.7),boot_id=BOOT,kind='sine',frequency_hz=500,period_us=200)
    with pytest.raises(ValueError):capture_command(InstrumentConfig(4.7),boot_id=BOOT,samples=1000)


def test_raw_instrument_packet_and_request_match():
    data=packet()
    assert validate_block(data,expected_command=f'CAPTURE {BOOT} STEP 16 500 435 0\n'.encode()) is data
    with pytest.raises(ValueError,match='request'):
        validate_block(data,expected_command=f'CAPTURE {BOOT} SINE 16 500 435 1000\n'.encode())


@pytest.mark.parametrize('fault',['overrun','timestamp','count','range','adc_state','source'])
def test_bad_capture_cannot_be_accepted(fault):
    data=copy.deepcopy(packet())
    if fault=='overrun':data['overruns']=1
    if fault=='timestamp':data['rows'][1][6]=0;data['rows'][1][0]=0
    if fault=='count':data['rows'].pop()
    if fault=='range':data['rows'][0][2]=16384
    if fault=='adc_state':data['adc_sample_states_readback_min']=24
    if fault=='source':data['source']='calibrated'
    with pytest.raises(ValueError):validate_block(data)


def test_millis_rollover_is_not_mistaken_for_reboot():
    guard=BootContinuity(BOOT)
    guard.check({**packet(),'uptime_ms':2**32-10})
    guard.check({**packet(),'uptime_ms':5})
    assert guard.previous_uptime_ms==5


def test_backwards_uptime_is_rejected_even_if_boot_id_repeats():
    guard=BootContinuity(BOOT)
    guard.check(packet())
    with pytest.raises(BootContinuityError,match='backwards'):
        guard.check({**packet(),'uptime_ms':10})


@pytest.mark.parametrize('field',['boot_id','boot_id_ready','uptime_ms'])
def test_unidentified_block_is_never_accepted(field):
    data=packet();data.pop(field)
    with pytest.raises(BootContinuityError):validate_block(data)


def test_block_from_different_boot_cannot_match_same_waveform_request():
    with pytest.raises(BootContinuityError):
        validate_block(packet(),expected_command=f'CAPTURE {"a"*32} STEP 16 500 435 0\n'.encode())
