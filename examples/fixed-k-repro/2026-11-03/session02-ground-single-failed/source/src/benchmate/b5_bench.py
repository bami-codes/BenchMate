"""Matching mock/physical acquisition interface for the unloaded B5 protocol."""
import hashlib
import json
import numpy as np
from scipy.optimize import brentq
from .b5_session import CONTROL, TRAINING, RESERVED, template
from .physical_bench import PhysicalBench
from .instrument import BootContinuity
from .records import canonical


def observation(source,settings,role,boot,origin,data,output):
    return {'source':source,'voltage_basis':'ADC_common_boot_origin_v2','all_guards_passed':True,
            'purpose':role,'settings':settings,'boot_id':boot,'origin_id':origin,
            'input_template':data,'output_relative_origin_v':np.asarray(output).tolist()}


class MockB5Bench:
    """Independent DC root solve, not the proposal's ngspice simulator.

    Only acquired values leave this object. It is explicitly a mock, never
    physical evidence or a scripted model decision presented as Spark's choice.
    """
    source='mock'
    def __init__(self,log,seed=17):
        self.log=log;self.rng=np.random.default_rng(seed);self.prepared=False
        self.boot_id='mock-control';self.origin_id='mock-origin-control';self.count=0
    def prepare_specimen(self):
        if self.prepared:raise ValueError('One fixture change maximum')
        self.log.add('operator_action_requested',{'source':'mock','instruction':'Simulated USB-off specimen installation; no person or board acted.'})
        self.prepared=True;self.boot_id='mock-specimen';self.origin_id='mock-origin-specimen'
        self.log.add('operator_wiring_confirmation',{'source':'mock','simulated':True})
    def acquire(self,settings,role):
        if settings not in CONTROL+TRAINING+RESERVED or (role=='control')==self.prepared:
            raise ValueError('Invalid mock fixture/menu/role')
        t=template(settings,'mock_adc_input_only');u=np.array(t['data']['input_relative_origin_v'])
        # A small imperfect drive and a fixed unknown reference in ADC coordinates.
        u=.997*u+.0012*np.sin(np.arange(len(u))*.31)
        y=u.copy()
        if self.prepared:
            vt=1.380649e-23*300.15/1.602176634e-19
            for i,drive in enumerate(u):
                f=lambda out:(drive-out)/12300-2.7e-9*np.expm1((out-.023-(drive-out)/12300)/(1.87*vt))
                y[i]=brentq(f,min(drive,.023)-.001,max(drive,.023)+.001)
        t['data']['input_relative_origin_v']=(u+self.rng.normal(0,.0012,len(u))).tolist()
        y+=.001+self.rng.normal(0,.0015,len(u));self.count+=1
        return observation(self.source,settings,role,self.boot_id,self.origin_id,t,y)
    def metadata(self):
        return {'source':'mock','waveforms':self.count,'real_serial_commands':0,'physical_measurements':0,
                'operator_actions_simulated':True}


class PhysicalB5Bench(PhysicalBench):
    source='physical'
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.ready_report=self.initial_report;self.origin_v=None;self.origin_id=None
        self.prepared=False;self.continuity=None
    def prepare_specimen(self):
        if self.stopped or self.prepared:raise ValueError('Fixture preparation unavailable')
        self.ready_report=self.confirm_wiring('unknown_unloaded')
        self.prepared=True
    def acquire(self,settings,role):
        if self.stopped:raise RuntimeError('Hardware stopped; no automatic retry')
        if settings not in CONTROL+TRAINING+RESERVED or role not in ('control','training','verification'):
            raise ValueError('Only frozen unloaded settings/roles allowed')
        if (role=='control')==self.prepared:raise ValueError('Fixture and acquisition role mismatch')
        fixture='unknown_unloaded' if self.prepared else 'resistor_only'
        fresh=fixture!=self.fixture
        try:
            if fresh:
                r=self.ready_report
                if (r.get('fixture')!=fixture or r.get('USB_off_wiring_confirmed') is not True or r.get('USB_connected') is not True
                    or not isinstance(r.get('verbatim'),str) or not r['verbatim'].strip()):
                    raise ValueError('Explicit USB-off assembly and reconnection confirmation required')
                self.log.add('operator_wiring_confirmation',r)
                self.reference_means=[];self.origin_v=None;self.continuity=BootContinuity()
            ports=[p for p in self.ports() if (p.vid,p.pid,p.serial_number)==tuple(self.p['USB_identity'])]
            if len(ports)!=1:raise ValueError('Expected Minima missing or ambiguous')
            previous=self.boot_id;phase=f'{role}_{self.acquisitions+1}'
            with self.serial_factory(ports[0].device,115200,timeout=5,write_timeout=2) as board:
                self.sleep(2);board.reset_input_buffer()
                self._ping(board,self.continuity,phase+'_PING',not fresh)
                if fresh:
                    if self.continuity.boot_id==previous:raise ValueError('New boot required after USB-off intervention')
                    packet=self._request(board,self.continuity,self.config.arm_command(self.continuity.boot_id),phase+'_ARM',15)
                    if packet.get('type')!='armed':raise ValueError('ARM not acknowledged')
                    self._ping(board,self.continuity,phase+'_armed',True)
                elif self.continuity.boot_id!=previous:raise ValueError('Boot changed; no re-arm')
                self.boot_id=self.continuity.boot_id
                hold=self._hold(board,self.continuity,phase+'_before')
                maps=self.p['voltage_conversion']['channels']
                if self.origin_v is None:
                    self.origin_v=float(hold[:,2].mean()*maps['A1']['gain_v_per_count']+maps['A1']['offset_v'])
                    origin={'boot_id':self.boot_id,'origin_v':self.origin_v,'source':'pre-waveform A1 HOLD mean','OUT_used':False,'absolute_REF':False}
                    self.origin_id=hashlib.sha256(canonical(origin)).hexdigest()
                    self.log.add('b5_ADC_origin_frozen',{'id':self.origin_id,**origin})
                self.log.add('b5_capture_requested',{'purpose':role,'settings':settings,'boot_id':self.boot_id,'origin_id':self.origin_id})
                rows=self._capture(board,self.continuity,phase,settings);self._waveform_checks(rows,settings)
                self._hold(board,self.continuity,phase+'_after')
            t=template(settings,'adc_input_only')
            t['data']['frame_time_s']=(rows[:,0]*1e-6).tolist()
            t['data']['input_delay_s']=(rows[:,6]*1e-6).tolist();t['data']['output_delay_s']=(rows[:,7]*1e-6).tolist()
            u=rows[:,2]*maps['A1']['gain_v_per_count']+maps['A1']['offset_v']-self.origin_v
            y=rows[:,3]*maps['A2']['gain_v_per_count']+maps['A2']['offset_v']-self.origin_v
            t['data']['input_relative_origin_v']=u.tolist()
            self.fixture=fixture;self.acquisitions+=1
            return observation('physical',settings,role,self.boot_id,self.origin_id,t,y)
        except Exception:
            self.stopped=True
            raise
