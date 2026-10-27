import copy
import pytest
from benchmate.instrument import InstrumentConfig,capture_command,validate_block


def packet():
    return {'protocol':'benchmate-instrument-v1','type':'capture','source':'hardware_uncalibrated',
            'adc_bits':14,'dac_bits':12,'channels':['A1','A2','A3','A4'],
            'timestamp_semantics':'analogRead_completion_us','timing_valid':True,'overruns':0,
            'adc_sample_states_readback_min':255,'requested_samples':16,'period_us':500,
            'kind':'STEP','amplitude_or_hold_code':435,'frequency_millihz':0,
            'rows':[[i*500,1394,1000,1000,1000,1000,20,40,60,80] for i in range(16)]}


def test_quantized_commands_keep_one_volt_limit_at_measured_supply():
    for vref in (4,4.7,5,5.5):
        config=InstrumentConfig(vref)
        command=capture_command(config).decode().split()
        amplitude=int(command[4])
        assert 2*amplitude<=config.max_jump
        assert 2*amplitude*vref/4095<=1
        arm=list(map(int,config.arm_command().decode().split()[1:]))
        assert arm[0]-arm[1]<=arm[3] and arm[2]-arm[0]<=arm[3]
    with pytest.raises(ValueError):capture_command(InstrumentConfig(4.7),amplitude_v=.51)
    with pytest.raises(ValueError):capture_command(InstrumentConfig(4.7),kind='sine',frequency_hz=500,period_us=200)
    with pytest.raises(ValueError):capture_command(InstrumentConfig(4.7),samples=1000)


def test_raw_instrument_packet_and_request_match():
    data=packet()
    assert validate_block(data,expected_command=b'CAPTURE STEP 16 500 435 0\n') is data
    with pytest.raises(ValueError,match='request'):
        validate_block(data,expected_command=b'CAPTURE SINE 16 500 435 1000\n')


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
