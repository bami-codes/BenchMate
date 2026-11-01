"""A new adapter instance after the explicit USB-off repair, plus a labelled mock."""
from copy import deepcopy
import math
import numpy as np
from .d01_repair import REPAIR_SINE,command_template
from .instrument import InstrumentConfig,validate_boot_id
from .physical_bench import PhysicalBench
from .physical_rc import STEP,SINE


def validate_initial(report,design_sha):
    if (report.get('fixture')!='unloaded' or report.get('USB_connected') is not True
        or report.get('USB_off_wiring_confirmed') is not True or report.get('nominal_design_confirmed') is not True
        or report.get('reviewed_design_sha256')!=design_sha
        or not isinstance(report.get('verbatim'),str) or not report['verbatim'].strip()):
        raise ValueError('Fresh unloaded hookup and exact reviewed nominal-design confirmation required')


def validate_repair_report(report,digest):
    if (not isinstance(report,dict) or report.get('cancelled') is True
        or report.get('action')!='restore_nominal_capacitance' or report.get('fixture')!='output_load'
        or report.get('prediction_sha256')!=digest or report.get('USB_connected') is not True
        or report.get('USB_off_wiring_confirmed') is not True
        or report.get('additional_capacitor_removed') is not True
        or report.get('original_capacitor_and_load_retained') is not True
        or report.get('remaining_wiring_unchanged') is not True
        or not isinstance(report.get('verbatim'),str) or not report['verbatim'].strip()):
        raise ValueError('Matching USB-off capacitor intervention and retained fixture confirmation required')


class PhysicalRepairBench:
    source='physical'
    def __init__(self,protocol,log,confirm,*,initial_report,previous_boot_id,design_sha,**transport):
        validate_initial(initial_report,design_sha);validate_boot_id(previous_boot_id)
        self.p=protocol;self.log=log;self.confirm=confirm;self.transport=transport
        self.config=InstrumentConfig(**protocol['configuration']);self.after=None;self.stopped=False
        self.before=PhysicalBench(protocol,log,lambda fixture:confirm('attach_output_load',None),
            initial_report=initial_report,previous_boot_id=previous_boot_id,**transport)
    @property
    def boot_id(self):return (self.after or self.before).boot_id
    def prepare_repair(self,digest,receipt):
        if self.stopped or self.after is not None or self.before.fixture!='output_load':raise ValueError('Repair fixture unavailable')
        try:
            if receipt.get('remote') is not True or receipt.get('sha256')!=digest:raise ValueError('Publication required')
            report=self.confirm('restore_nominal_capacitance',digest)
            validate_repair_report(report,digest)
            self.log.add('repair_operator_confirmation',report)
            self.after=PhysicalBench(self.p,self.log,lambda _:(_ for _ in ()).throw(ValueError('No more wiring changes')),
                initial_report=report,previous_boot_id=self.before.boot_id,settings_menu=(STEP,REPAIR_SINE),**self.transport)
        except Exception:self.stopped=True;raise
    def acquire(self,settings,models,fixture,phase):
        if self.stopped:raise ValueError('Repair adapter stopped; no retry')
        repair=phase in ('repair_step','repair_reserved_sine')
        if repair!=(self.after is not None):raise ValueError('Acquisition phase does not match intervention state')
        try:return (self.after or self.before).acquire(settings,models,fixture,phase)
        except Exception:self.stopped=True;raise
    def metadata(self):
        parts=[x.metadata() for x in (self.before,self.after) if x is not None]
        return {'source':'physical','capture_attempts':sum(x['capture_attempts'] for x in parts),
            'retained_frames':sum(x['retained_frames'] for x in parts),
            'scored_captures_completed':sum(x['scored_captures_completed'] for x in parts),
            'human_interventions_completed':sum(x['requested_wiring_interventions_completed'] for x in parts)+int(self.after is not None),
            'latest_boot_id':self.boot_id,'output_state_confirmed':parts[-1]['output_state_confirmed'] and not self.stopped,
            'repair_operator_confirmation_received':self.after is not None,'automatic_retry_or_rearm':False}


class MockRepairBench:
    source='mock'
    def __init__(self,protocol,log,*,fault='none',seed=41):
        self.config=InstrumentConfig(**protocol['configuration']);self.log=log;self.fault=fault
        self.rng=np.random.default_rng(seed);self.fixture=None;self.count=0;self.epoch=1;self.repaired=False
        self.capacitance=2e-6;self.resistance=10000.;self.interventions=0;self.stopped=False
    @property
    def boot_id(self):return f'{self.epoch:032x}'
    def prepare_repair(self,digest,receipt):
        self.log.add('operator_action_requested',{'source':'mock','action':'restore_nominal_capacitance',
            'prediction_sha256':digest,'instruction':'Simulated human action only; no hardware or real operator acted.'})
        if self.fault in ('missing_confirmation','wrong_confirmation','cancelled','timeout'):
            self.stopped=True;raise ValueError('Injected mock operator failure: '+self.fault)
        self.repaired=True;self.interventions+=1
        if self.fault!='stale_boot':self.epoch+=1
        if self.fault!='repair_failed':self.capacitance=1e-6
        self.log.add('repair_operator_confirmation',{'source':'mock','simulated':True,'prediction_sha256':digest})
    def acquire(self,settings,models,fixture,phase):
        if self.stopped:raise ValueError('Mock stopped')
        if settings not in (STEP,SINE,REPAIR_SINE):raise ValueError('Unknown mock waveform')
        if fixture!=self.fixture:
            if self.fixture is not None:
                self.epoch+=1;self.interventions+=1
                self.log.add('operator_action_requested',{'source':'mock','action':'attach_output_load','simulated':True})
            self.fixture=fixture
        if self.repaired and phase=='repair_reserved_sine' and self.fault=='reset_during_reserved':self.epoch+=1
        load=None if fixture=='unloaded' else 9990.
        gain=1. if load is None else load/(load+self.resistance)
        tau=self.resistance*self.capacitance*gain
        d=command_template(self.config,settings);u=np.asarray(d['input_v'])*.997
        dt=settings['period_us']*1e-6;decay=math.exp(-dt/tau);delay_decay=math.exp(-105e-6/tau)
        if settings['kind']=='step':state=gain*u[0]
        else:
            # Settle a repeated commanded cycle independently of the predictor.
            cycle=round(1/(settings['frequency_hz']*dt));state=0.
            for x in np.tile(u[:cycle],30):state=decay*state+(1-decay)*gain*x
        y=[]
        for x in u:
            y.append(delay_decay*state+(1-delay_decay)*gain*x)
            state=decay*state+(1-decay)*gain*x
        y=np.asarray(y)+self.rng.normal(0,.0005,len(u))
        if self.repaired and phase=='repair_reserved_sine' and self.fault=='reserved_failure':y+=.04*np.sin(np.arange(len(u))*.19)
        baseline={'input_v':1.646,'output_v':1.653,'source':'mock independent HOLD origin','scored_OUT_samples_used':0}
        d['input_v']=(u+baseline['input_v']+self.rng.normal(0,.0003,len(u))).tolist()
        d['output_v']=(y+baseline['output_v']).tolist();self.count+=1
        obs={'source':'mock','fresh_measurement':True,'all_guards_passed':True,'settings':deepcopy(settings),'fixture':fixture,
            'boot_id':self.boot_id,'baseline':baseline,'data':d}
        self.log.add('mock_rc_observation',{'phase':phase,**obs});return obs
    def metadata(self):return {'source':'mock','waveforms':self.count,'physical_measurements':0,'real_serial_commands':0,
        'operator_actions_simulated':True,'simulated_interventions':self.interventions,'latest_boot_id':self.boot_id}
