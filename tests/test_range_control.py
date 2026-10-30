from copy import deepcopy
import math
import numpy as np
import pytest
from benchmate.range_control import CONTROL_WAVEFORMS,freeze_differential_anchor,score_resistor_control


def fixture(settings):
    center=1371;slope=.001193648383144491
    maps={'A1':{'gain_v_per_count':.0002983},'A2':{'gain_v_per_count':.0002986}}
    means=[5480.,5460.,5480.,5480.]
    anchor=freeze_differential_anchor(means,maps,.006,.007,ref_code=center,driver_v_per_code=slope)
    n=settings['samples'];period=settings['period_us'];amp=math.floor(settings['amplitude_v']*4095/4.89)
    if settings['kind']=='step':dcode=np.where(np.arange(n)<51,-amp,amp)
    else:dcode=np.round(amp*np.sin(2*np.pi*settings['frequency_hz']*np.arange(n)*period/1e6))
    delta=slope*dcode
    rows=np.zeros((n,10));rows[:,0]=np.arange(n)*period;rows[:,1]=center+dcode
    rows[:,2]=means[0]+delta/maps['A1']['gain_v_per_count']
    rows[:,3]=means[1]+delta/maps['A2']['gain_v_per_count']
    rows[:,4:6]=5480.;rows[:,6:10]=[50,105,160,215]
    return rows,anchor


@pytest.mark.parametrize('settings',CONTROL_WAVEFORMS)
def test_fixed_linear_control_retains_independent_nonzero_bias(settings):
    rows,anchor=fixture(settings);before=deepcopy(anchor)
    result=score_resistor_control(rows,settings,anchor)
    assert result['passed'] and result['RMS_mV']==pytest.approx(1.,abs=1e-9)
    assert result['input_command_RMS_mV']<1e-9 and anchor==before
    assert anchor['channels']['A1']['independent_DMM_bias_v']==.006
    assert anchor['channels']['A2']['independent_DMM_bias_v']==.007


def test_drive_clipping_is_caught_even_when_OUT_follows_it():
    settings=CONTROL_WAVEFORMS[-1];rows,anchor=fixture(settings)
    for channel,column in [('A1',2),('A2',3)]:
        c=anchor['channels'][channel];volts=rows[:,column]*c['gain_v_per_count']+c['offset_to_physical_REF_v']
        volts=np.minimum(volts,.65+c['independent_DMM_bias_v'])
        rows[:,column]=(volts-c['offset_to_physical_REF_v'])/c['gain_v_per_count']
    result=score_resistor_control(rows,settings,anchor)
    assert result['checks']['whole_RMS'] and not result['checks']['input_command_RMS'] and not result['passed']


def test_buffer_nonlinearity_is_not_assigned_to_input():
    settings=CONTROL_WAVEFORMS[-1];rows,anchor=fixture(settings)
    c=anchor['channels']['A2'];y=rows[:,3]*c['gain_v_per_count']+c['offset_to_physical_REF_v']
    rows[:,3]=(np.minimum(y,.45)-c['offset_to_physical_REF_v'])/c['gain_v_per_count']
    result=score_resistor_control(rows,settings,anchor)
    assert result['checks']['input_command_RMS'] and not result['checks']['whole_RMS']


def test_short_region_failure_cannot_hide_in_whole_trace_RMS():
    settings=CONTROL_WAVEFORMS[1];rows,anchor=fixture(settings)
    rows[53,3]+=.07/anchor['channels']['A2']['gain_v_per_count']
    result=score_resistor_control(rows,settings,anchor)
    assert result['checks']['whole_RMS'] and not result['checks']['all_region_RMS'] and not result['passed']


@pytest.mark.parametrize('dmm_in,dmm_out',[(.04,.005),(.0,.02),(float('nan'),.0)])
def test_bad_bias_anchor_blocks_waveforms(dmm_in,dmm_out):
    with pytest.raises(ValueError):
        freeze_differential_anchor([5000.]*4,{'A1':{'gain_v_per_count':.0003},'A2':{'gain_v_per_count':.0003}},dmm_in,dmm_out,
                                  ref_code=1371,driver_v_per_code=.00119)


def test_unregistered_one_volt_waveform_is_rejected():
    settings=CONTROL_WAVEFORMS[-1];rows,anchor=fixture(settings)
    with pytest.raises(ValueError):score_resistor_control(rows,{**settings,'amplitude_v':1.},anchor)
