import importlib.util
import json
from pathlib import Path

import numpy as np
import pytest

from benchmate.instrument import InstrumentConfig, dc_hold_command, BootContinuityError

path=Path(__file__).resolve().parents[1]/'experiments/ref_dc_dmm.py'
spec=importlib.util.spec_from_file_location('dc_dmm_under_test',path)
qa=importlib.util.module_from_spec(spec);spec.loader.exec_module(qa)
C=InstrumentConfig(vref_v=4.9,ref_v=1.646)
BOOT='2'*32


class Log:
    def add(self,*args):pass


class Board:
    def __init__(self,replies):self.replies=list(replies);self.writes=[]
    def write(self,command):self.writes.append(command);return len(command)
    def read_until(self,*args,**kwargs):return (json.dumps(self.replies.pop(0))+'\n').encode()


def identity(kind,uptime=100):
    return dict(protocol='benchmate-instrument-v2',type=kind,boot_id=BOOT,
                boot_id_ready=True,uptime_ms=uptime)


def pong(code,uptime=101):
    return {**identity('pong',uptime),'armed':True,'current_code':code,'ref_code':C.ref_code,
            'max_jump_code':C.max_jump,'dc_hold_supported':True,
            'adc_sample_state_channels':[0,1,2,21],'adc_sample_states_readback':[255]*4}


def packet(label):
    target=qa.levels(C)[label];code=int(dc_hold_command(C,boot_id=BOOT,hold_v=target).split()[2])
    signal=round(target*16383/4.9);ref=round(1.646*16383/4.9)
    return {**identity('capture'),'source':'hardware_uncalibrated','adc_bits':14,'dac_bits':12,
      'channels':['A1','A2','A3','A4'],'timestamp_semantics':'analogRead_completion_us',
      'timing_valid':True,'overruns':0,'adc_sample_states_readback_min':255,
      'adc_sample_state_channels':[0,1,2,21],'adc_sample_states_readback_before':[255]*4,
      'adc_sample_states_readback_after':[255]*4,'requested_samples':512,'period_us':2000,
      'kind':'HOLD','amplitude_or_hold_code':code,'frequency_millihz':0,
      'parked_ref_code':C.ref_code,
      'rows':[[i*2000,code,signal,signal,ref,ref,52,105,158,215] for i in range(512)]}


def protocol():
    return {'guard_limits':{'signal_envelope_v':.95,'A4_envelope_v':.15}}


def test_planned_levels_are_bounded_and_every_large_transition_uses_center():
    codes={k:int(dc_hold_command(C,boot_id=BOOT,hold_v=v).split()[2]) for k,v in qa.levels(C).items()}
    assert codes=={'C':1376,'L':958,'H':1793}
    assert qa.SEQUENCE[0]==qa.SEQUENCE[-1]=='C'
    assert all(abs(codes[a]-codes[b])<=C.max_jump for a,b in zip(qa.SEQUENCE,qa.SEQUENCE[1:]))


def test_boot_change_is_rejected_before_a_dc_move():
    b=Board([pong(C.ref_code)])
    d=qa.Device(b,Log(),C,boot='1'*32)
    with pytest.raises(BootContinuityError):d.ping(C.ref_code)
    assert b.writes==[b'PING\n']


def test_noncenter_hold_must_be_acknowledged_as_parked_at_center():
    b=Board([packet('H'),pong(C.ref_code)])
    means=qa.Device(b,Log(),C,boot=BOOT).sample('H',protocol())
    assert means[0]==pytest.approx(2.146,abs=.001)
    assert means[2]==pytest.approx(1.646,abs=.001)
    assert b.writes[0].split()[5]==b'1793'
    assert b.writes[-1]==b'PING\n'


def test_missing_ref_park_stops_without_retry_or_next_level():
    b=Board([packet('H'),pong(1793)])
    with pytest.raises(ValueError,match='Unexpected'):qa.Device(b,Log(),C,boot=BOOT).sample('H',protocol())
    assert len(b.writes)==2


def test_three_mv_failure_cannot_become_a_diagnostic_pass():
    s=qa.span_summary([{'ADC_means_nominal_v':[1.6,1.6,1.63,1.63]},
                       {'ADC_means_nominal_v':[2.1,2.1,1.64,1.64]}])
    assert s['A4_within_existing_3mV_limit'] is False
    assert s['diagnosis_use_allowed'] is False
    assert s['existing_limit_mV']==3.


@pytest.mark.parametrize('bad',[['nan','1.630','1.630'],['0','1.630','1.630'],['1.630']])
def test_bad_meter_entries_are_rejected(bad):
    with pytest.raises(ValueError):qa.readings(bad)
