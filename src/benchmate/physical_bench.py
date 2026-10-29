"""Small guarded Minima adapter for the explicitly prepared passive RC fixture.

No arbitrary model-provided commands, firmware uploads, retries, servo or re-arm.
Fresh boots are accepted only after a reported USB-off wiring intervention.
"""
import hashlib
import json
import math
import time
import numpy as np
import serial
from serial.tools import list_ports
from .instrument import InstrumentConfig,BootContinuity,capture_command,receive_response,validate_block
from .physical_rc import STEP,SINE


class PhysicalBench:
    def __init__(self,protocol,log,confirm_wiring,*,initial_report,previous_boot_id,
                 serial_factory=None,ports=None,sleep=time.sleep):
        self.p=protocol;self.config=InstrumentConfig(**protocol['configuration']);self.log=log
        self.confirm_wiring=confirm_wiring;self.initial_report=initial_report;self.boot_id=previous_boot_id
        self.serial_factory=serial_factory or serial.Serial;self.ports=ports or list_ports.comports;self.sleep=sleep
        self.fixture=None;self.reference_means=[];self.capture_attempts=0;self.frames=0;self.human_interventions=0
        self.stopped=False;self.acquisitions=0

    def _request(self,board,continuity,command,label,timeout=5):
        self.log.add('serial_command',{'request':command.decode().strip(),'label':label})
        board.timeout=timeout
        if board.write(command)!=len(command):raise RuntimeError('Incomplete serial write; no retry')
        packet=receive_response(board,self.log,label);continuity.check(packet)
        return packet

    def _ping(self,board,continuity,label,armed):
        packet=self._request(board,continuity,b'PING\n',label);code=self.config.ref_code if armed else 0
        if (packet.get('type')!='pong' or packet.get('armed') is not armed
            or packet.get('current_code')!=code or packet.get('ref_code')!=code
            or packet.get('dc_hold_supported') is not True
            or packet.get('adc_sample_state_channels')!=[0,1,2,21]
            or packet.get('adc_sample_states_readback')!=[255]*4
            or (armed and packet.get('max_jump_code')!=self.config.max_jump)):
            raise ValueError('Unexpected firmware or output state; no re-arm')
        return packet

    def _capture(self,board,continuity,label,settings):
        command=capture_command(self.config,boot_id=continuity.boot_id,**settings)
        self.capture_attempts+=1
        block=self._request(board,continuity,command,label+'_raw_capture',30)
        validate_block(block,expected_command=command)
        if block.get('parked_ref_code')!=self.config.ref_code:raise ValueError('REF park not reported')
        self.frames+=len(block['rows'])
        self._ping(board,continuity,label+'_postcheck',True)
        rows=np.asarray(block['rows']);nominal=rows[:,2:6]*self.config.vref_v/16383
        self.reference_means.append({'label':label,'hold':settings['kind']=='hold',
                                    'means':nominal.mean(axis=0).tolist()})
        g=self.p['guard_limits'];means=nominal.mean(axis=0)
        reference=np.asarray([r['means'] for r in self.reference_means])
        checks={'rails':bool(((rows[:,2:6]>16)&(rows[:,2:6]<16367)).all()),
                'A4_envelope':bool((abs(nominal[:,3]-self.config.ref_v)<=g['A4_envelope_v']).all()),
                'A4_block_mean_span':float(np.ptp(reference[:,3]))<=.003}
        if settings['kind']=='hold':
            stationary=np.asarray([r['means'] for r in self.reference_means if r['hold']])
            checks.update(stationary_path_mean_span=bool((np.ptp(stationary,axis=0)<=.003).all()),
                path_means=bool((abs(means-self.config.ref_v)<=g['REF_mean_delta_v_max']).all()),
                path_samples=bool((abs(nominal-self.config.ref_v)<=g['REF_any_sample_delta_v_max']).all()),
                path_spread=float(np.ptp(means))<=g['REF_channel_mean_spread_v_max'])
        else:
            checks['signal_envelope']=bool((abs(nominal[:,:3]-self.config.ref_v)<=g['signal_envelope_v']).all())
        self.log.add('physical_electrical_guard',{'label':label,'checks':checks,'means_v':means.tolist()})
        if not all(checks.values()):raise ValueError('Electrical/reference guard failed; no next stimulus')
        return rows

    def _hold(self,board,continuity,label):
        return self._capture(board,continuity,label,{'kind':'hold','hold_v':self.config.ref_v,'samples':512,'period_us':2000})

    def _waveform_checks(self,rows,settings):
        command=capture_command(self.config,boot_id='1'*32,**settings)
        amplitude=int(command.split()[5]);n=settings['samples'];period=settings['period_us']
        expected=[];warmup=0
        if settings['kind']=='sine':
            warmup=math.ceil(max(self.config.settle_ms*1000,2e6/settings['frequency_hz'])/period)
        for i in range(warmup,warmup+n):
            value=(-amplitude if i<n//10 else amplitude) if settings['kind']=='step' else amplitude*math.sin(2*math.pi*settings['frequency_hz']*i*period/1e6)
            rounded=math.floor(value+.5) if value>=0 else math.ceil(value-.5)
            expected.append(self.config.ref_code+rounded)
        time_error=float(np.max(abs(rows[:,0]+rows[:,7]-(np.arange(n)*period+105))))
        code_error=int(np.max(abs(rows[:,1]-expected)))
        checks={'timing':time_error<=25,'DAC_codes':code_error<=(0 if settings['kind']=='step' else 1)}
        self.log.add('physical_waveform_check',{'settings':settings,'checks':checks,'max_time_error_us':time_error,
                      'max_DAC_code_error':code_error,'unrecorded_warmup_frames':warmup})
        if not all(checks.values()):raise ValueError('Waveform timing/code check failed')

    def acquire(self,settings,models,fixture,phase):
        if self.stopped:raise RuntimeError('Hardware adapter stopped; no retry')
        if settings not in (STEP,SINE) or fixture not in ('unloaded','output_load'):
            raise ValueError('Only the frozen physical menu is allowed')
        fresh=fixture!=self.fixture
        if settings==SINE and (fresh or fixture!='output_load'):
            raise ValueError('Reserved sine requires the already measured loaded fixture')
        try:
            if fresh:
                report=self.initial_report if self.fixture is None else self.confirm_wiring(fixture)
                if (not isinstance(report,dict) or report.get('USB_connected') is not True
                    or report.get('USB_off_wiring_confirmed') is not True or report.get('fixture')!=fixture
                    or not isinstance(report.get('verbatim'),str) or not report['verbatim'].strip()):
                    raise ValueError('Explicit matching USB-off hookup and reconnection confirmation required')
                self.log.add('operator_wiring_confirmation',report)
                if self.fixture is not None:self.human_interventions+=1
                self.reference_means=[]
            self.log.add('physical_acquisition_plan_frozen',{'settings':settings,'models':models,'fixture':fixture,'phase':phase,
                         'baseline':'three separate HOLD blocks before scored waveform','refit_allowed':phase=='unloaded_step' and self.acquisitions==0,
                         'fresh_boot_required':fresh,'previous_boot_id':self.boot_id})
            matches=[p for p in self.ports() if (p.vid,p.pid,p.serial_number)==tuple(self.p['USB_identity'])]
            self.log.add('USB_preflight',{'matching_ports':[p.device for p in matches]})
            if len(matches)!=1:raise ValueError('Expected Minima absent or ambiguous')
            continuity=BootContinuity();previous=self.boot_id
            with self.serial_factory(matches[0].device,115200,timeout=5,write_timeout=2) as board:
                self.sleep(2);board.reset_input_buffer()
                self._ping(board,continuity,'initial_PING',not fresh)
                if fresh:
                    if continuity.boot_id==previous:raise ValueError('New boot not established after operator wiring')
                    arm=self._request(board,continuity,self.config.arm_command(continuity.boot_id),'ARM_response',15)
                    if arm.get('type')!='armed':raise ValueError('ARM not acknowledged')
                    self._ping(board,continuity,'post_ARM_PING',True)
                elif continuity.boot_id!=previous:raise ValueError('Boot changed without a new operator confirmation')
                self.boot_id=continuity.boot_id
                baseline_rows=[self._hold(board,continuity,phase+'_baseline_'+str(i+1)) for i in range(3)]
                means=np.asarray([rows[:,2:6].mean(axis=0) for rows in baseline_rows]).mean(axis=0)
                maps=self.p['voltage_conversion']['channels']
                baseline={name:float(means[index]*maps[channel]['gain_v_per_count']+maps[channel]['offset_v'])
                          for name,index,channel in [('input_v',0,'A1'),('output_v',1,'A2')]}
                baseline.update(calibration_frames=1536,scored_OUT_samples_used=0)
                raw=(json.dumps(baseline,sort_keys=True)+'\n').encode()
                baseline['sha256']=hashlib.sha256(raw).hexdigest()
                self.log.add('pre_stimulus_origin_frozen',{'phase':phase,**baseline})
                rows=self._capture(board,continuity,phase,settings);self._waveform_checks(rows,settings)
                self._hold(board,continuity,phase+'_return_REF');self._ping(board,continuity,'final_PING',True)
            data={'frame_time_s':(rows[:,0]*1e-6).tolist(),'input_delay_s':(rows[:,6]*1e-6).tolist(),
                  'output_delay_s':(rows[:,7]*1e-6).tolist()}
            for name,index,channel in [('input_v',2,'A1'),('output_v',3,'A2')]:
                data[name]=(rows[:,index]*maps[channel]['gain_v_per_count']+maps[channel]['offset_v']).tolist()
            self.fixture=fixture;self.acquisitions+=1
            observation={'source':'physical','fresh_measurement':True,'all_guards_passed':True,'settings':settings,
                         'fixture':fixture,'baseline':baseline,'data':data,'boot_id':self.boot_id,
                         'A4_mean_span_mV':float(np.ptp(np.asarray([r['means'] for r in self.reference_means])[:,3]))*1000}
            self.log.add('physical_observation',{'phase':phase,**observation})
            return observation
        except Exception:
            self.stopped=True
            raise

    def metadata(self):
        return {'capture_attempts':self.capture_attempts,'retained_frames':self.frames,
                'scored_captures_completed':self.acquisitions,'requested_wiring_interventions_completed':self.human_interventions,
                'latest_boot_id':self.boot_id,'output_state_confirmed':self.acquisitions>0 and not self.stopped,
                'automatic_retry_or_rearm':False,'automatic_A4_tracking':False}
