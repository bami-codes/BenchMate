from copy import deepcopy
import json
from pathlib import Path

import numpy as np
import pytest

from benchmate.instrument import BootContinuity,InstrumentConfig
from benchmate.physical_bench import PhysicalBench
from benchmate.reproducibility_bench import ReproducibilityCaptureMixin
from test_ref_reproducibility import data,fit,origin,digest

ROOT=Path(__file__).resolve().parents[1]
BOOT='b'*32


class Log:
    def __init__(self):self.events=[]
    def add(self,k,v):self.events.append((k,deepcopy(v)))


class Board:
    def __init__(self,config):self.cfg=config;self.commands=[];self.extra_k=0.;self.offset=0.;self.uptime=0
    def write(self,command):
        self.commands.append(command);w=command.decode().split();self.uptime+=1
        p={'protocol':'benchmate-instrument-v2','boot_id':BOOT,'boot_id_ready':True,'uptime_ms':self.uptime}
        if w[0]=='PING':
            p.update(type='pong',armed=True,current_code=self.cfg.ref_code,ref_code=self.cfg.ref_code,
                     max_jump_code=self.cfg.max_jump,dc_hold_supported=True,
                     adc_sample_state_channels=[0,1,2,21],adc_sample_states_readback=[255]*4)
        else:
            assert w[0]=='CAPTURE';kind=w[2];n,period,amp,freq=map(int,w[3:])
            if kind=='HOLD':x=np.zeros(n);codes=np.full(n,amp)
            elif kind=='STEP':
                d=np.where(np.arange(n)<n//10,-amp,amp);codes=self.cfg.ref_code+d;x=d*self.cfg.vref_v/4095
            else:
                warmup=int(np.ceil(max(self.cfg.settle_ms*1000,2e9/freq)/period))
                d=np.rint(amp*np.sin(2*np.pi*freq*(np.arange(n)+warmup)*period/1e9)).astype(int)
                codes=self.cfg.ref_code+d;x=d*self.cfg.vref_v/4095
            refs=self.cfg.ref_v+(.012+self.extra_k)*x+self.offset
            volts=np.column_stack([self.cfg.ref_v+x,self.cfg.ref_v+.5*x,refs,refs])
            counts=np.rint(volts*16383/self.cfg.vref_v).astype(int)
            rows=np.column_stack([np.arange(n)*period,codes,counts,np.tile([52,105,158,215],(n,1))]).tolist()
            p.update(type='capture',source='hardware_uncalibrated',adc_bits=14,dac_bits=12,
                channels=['A1','A2','A3','A4'],timestamp_semantics='analogRead_completion_us',
                timing_valid=True,overruns=0,adc_sample_states_readback_min=255,
                adc_sample_state_channels=[0,1,2,21],adc_sample_states_readback_before=[255]*4,
                adc_sample_states_readback_after=[255]*4,requested_samples=n,period_us=period,
                kind=kind,amplitude_or_hold_code=amp,frequency_millihz=freq,parked_ref_code=self.cfg.ref_code,rows=rows)
        self.response=(json.dumps(p)+'\n').encode();return len(command)
    def read_until(self,*a,**k):return self.response


class Bench(ReproducibilityCaptureMixin,PhysicalBench):pass


def make():
    p=json.loads((ROOT/'examples/passive-pilot-prepared/2026-11-03/design-01-A3REF/protocol.json').read_text())
    records=data();candidate=fit(records,origin(records[:3]),4.9)['candidate']
    log=Log();b=Bench(p,log,None,initial_report={},previous_boot_id=BOOT)
    b.fixed_model=candidate;board=Board(b.config);continuity=BootContinuity(BOOT)
    for i in range(3):b._hold(board,continuity,f'origin{i}')
    return b,board,continuity,log


def test_raw_span_failure_stays_visible_but_fixed_guard_and_data_path_are_separate():
    b,board,c,log=make();before=digest(b.fixed_model)
    s={'kind':'step','samples':512,'period_us':500,'amplitude_v':.5}
    rows=b._capture(board,c,'step',s);b._waveform_checks(rows,s)
    assert b.last_reference_reproducibility['new_guard_passed'] is True
    assert b.last_reference_reproducibility['legacy_3mV_guard_passed'] is False
    assert digest(b.fixed_model)==before
    raw=next(v['rows'] for k,v in log.events if k=='step_raw_capture')
    assert rows.tolist()==raw # guard never modifies diagnostic IN/OUT


@pytest.mark.parametrize('fault',['extra_real_REF','HOLD_drift'])
def test_real_faults_stop_without_reanchoring_or_refitting(fault):
    b,board,c,log=make();old_origin=deepcopy(b.repro_origin);old_model=digest(b.fixed_model)
    if fault=='extra_real_REF':
        board.extra_k=.008;s={'kind':'step','samples':512,'period_us':500,'amplitude_v':.5}
    else:
        board.offset=.004;s={'kind':'hold','samples':512,'period_us':2000,'hold_v':b.config.ref_v}
    with pytest.raises(ValueError):b._capture(board,c,'fault',s)
    assert b.repro_origin==old_origin and digest(b.fixed_model)==old_model
    count=len(board.commands)
    with pytest.raises(RuntimeError):b._capture(board,c,'retry',s)
    assert len(board.commands)==count
