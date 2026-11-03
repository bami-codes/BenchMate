"""D2 calibration transport. Raw counts and timing only; never diagnoses hardware."""
from dataclasses import dataclass, asdict
import json
import math
import re
import time
import serial
from .records import Recorder

PROTOCOL = 'benchmate-instrument-v2'


class BootContinuityError(ValueError):
    """The requested boot cannot be established for this measurement."""


def validate_boot_id(value):
    if not isinstance(value, str) or re.fullmatch(r'[0-9a-f]{32}', value) is None or int(value, 16)==0:
        raise BootContinuityError('Missing or invalid boot ID; re-arm explicitly with DUT disconnected')
    return value


def response_identity(packet):
    if not isinstance(packet, dict) or packet.get('protocol')!=PROTOCOL:
        raise ValueError('Expected instrument v2; legacy firmware cannot validate boot continuity')
    if packet.get('boot_id_ready') is not True:
        raise BootContinuityError('Firmware could not establish a boot ID')
    boot=validate_boot_id(packet.get('boot_id'))
    uptime=packet.get('uptime_ms')
    if type(uptime) is not int or not 0<=uptime<2**32:
        raise BootContinuityError('Missing or invalid boot uptime')
    return boot,uptime


@dataclass
class BootContinuity:
    boot_id: str | None = None
    previous_uptime_ms: int | None = None

    def check(self, packet):
        boot,uptime=response_identity(packet)
        if self.boot_id is not None and boot!=self.boot_id:
            raise BootContinuityError('Boot ID changed; this run is invalid')
        if self.previous_uptime_ms is not None:
            # Responses in one bounded acquisition are far less than 2**31 ms apart.
            # Accept normal uint32 millis wrap, reject a backwards/stale clock.
            advance=(uptime-self.previous_uptime_ms) % 2**32
            if advance>=2**31:
                raise BootContinuityError('Boot uptime moved backwards; this run is invalid')
        self.boot_id=boot
        self.previous_uptime_ms=uptime


def receive_response(board, log, kind, *, size=262144):
    raw=board.read_until(b'\n',size=size)
    try:
        if not raw.endswith(b'\n'):
            raise ValueError('Incomplete instrument response')
        packet=json.loads(raw)
    except (ValueError, UnicodeError):
        log.add('incomplete_instrument_response',{'stage':kind,'bytes_received':len(raw),
                'raw_text':raw.decode('utf-8',errors='replace')})
        raise ValueError('Incomplete or malformed instrument response; this run is invalid') from None
    log.add(kind,packet)  # Retain changed-boot, error and partial-block packets too.
    return packet


@dataclass(frozen=True)
class InstrumentConfig:
    vref_v: float
    ref_v: float = 1.6
    settle_ms: int = 1200
    stable_delta_counts: int = 20

    def __post_init__(self):
        if not math.isfinite(self.vref_v) or not 4 <= self.vref_v <= 5.5:
            raise ValueError('Enter the measured UNO supply/DAC reference in 4–5.5 V')
        if not math.isfinite(self.ref_v) or not 1.1 <= self.ref_v <= self.vref_v-1.1:
            raise ValueError('REF must leave the declared stimulus envelope within supply rails')
        if type(self.settle_ms) is not int or not 1200 <= self.settle_ms <= 5000:
            raise ValueError('Development RC prior requires at least 1200 ms settling')
        if type(self.stable_delta_counts) is not int or not 1 <= self.stable_delta_counts <= 1000:
            raise ValueError('Invalid raw-count settling window')

    @property
    def ref_code(self): return round(4095*self.ref_v/self.vref_v)

    @property
    def max_jump(self): return math.floor(4095/self.vref_v)

    def arm_command(self, boot_id):
        validate_boot_id(boot_id)
        center,span = self.ref_code,self.max_jump
        low = max(16,math.floor((self.ref_v-1.1)*16383/self.vref_v))
        high = min(16367,math.ceil((self.ref_v+1.1)*16383/self.vref_v))
        return f'ARM {boot_id} {center} {center-span} {center+span} {span} {self.settle_ms} {self.stable_delta_counts} {low} {high}\n'.encode()


def _dc_code(config,voltage):
    # One float ULP permits decimal endpoints such as 1.6 - 1. Integer
    # clamping still enforces the exact armed envelope for both DC and HOLD.
    low=math.nextafter(config.ref_v-1,-math.inf)
    high=math.nextafter(config.ref_v+1,math.inf)
    if type(voltage) not in (int,float) or not math.isfinite(voltage) or not low<=voltage<=high:
        raise ValueError('DC/HOLD needs a voltage within REF ± 1 V')
    code=round(4095*voltage/config.vref_v)
    return min(config.ref_code+config.max_jump,max(config.ref_code-config.max_jump,code))


def capture_command(config, *, boot_id, kind='step', samples=512, period_us=500,
                    amplitude_v=.5, frequency_hz=None, hold_v=None):
    validate_boot_id(boot_id)
    if type(samples) is not int or not 16<=samples<=512 or type(period_us) is not int or not 100<=period_us<=20000:
        raise ValueError('Invalid sample count or requested period')
    if kind not in ('step','sine','hold'):
        raise ValueError('Unsupported waveform')
    if kind=='hold':
        amplitude = _dc_code(config,hold_v)
        frequency=0
    else:
        if not math.isfinite(amplitude_v) or not 0<amplitude_v<=1 or (kind=='step' and amplitude_v>.5):
            raise ValueError('Stimulus exceeds envelope or one-volt step rule')
        amplitude=math.floor(4095*amplitude_v/config.vref_v)
        if amplitude<1: raise ValueError('Amplitude below one DAC code')
        frequency=0
        if kind=='sine':
            if frequency_hz is None or not math.isfinite(frequency_hz) or not 1<=frequency_hz<=500:
                raise ValueError('Invalid sine frequency')
            frequency=round(frequency_hz*1000)
            if period_us*frequency>50_000_000:
                raise ValueError('Need at least 20 samples per sine cycle')
    return f'CAPTURE {boot_id} {kind.upper()} {samples} {period_us} {amplitude} {frequency}\n'.encode()


def validate_block(packet, *, expected_command=None):
    boot,_=response_identity(packet)
    if packet.get('type')!='capture':
        raise ValueError('Unexpected instrument protocol')
    if packet.get('source')!='hardware_uncalibrated' or packet.get('adc_bits')!=14 or packet.get('dac_bits')!=12:
        raise ValueError('Unexpected capture provenance')
    if packet.get('channels')!=['A1','A2','A3','A4'] or packet.get('timestamp_semantics')!='analogRead_completion_us':
        raise ValueError('Unexpected channels or timing semantics')
    if packet.get('timing_valid') is not True or packet.get('overruns')!=0:
        raise ValueError('Acquisition timing failed; reduce rate and repeat D2 timing check')
    if packet.get('adc_sample_states_readback_min')!=255:
        raise ValueError('ADC long sampling-state request was not retained')
    if packet.get('adc_sample_state_channels') != [0,1,2,21]:
        raise ValueError('Missing or unexpected ADC sampling-state channel mapping')
    for field in ('adc_sample_states_readback_before','adc_sample_states_readback_after'):
        values=packet.get(field)
        if not isinstance(values,list) or len(values)!=4 or any(type(v) is not int or v!=255 for v in values):
            raise ValueError('Active ADC sampling states must be retained before and after capture')
    count=packet.get('requested_samples')
    period=packet.get('period_us')
    if type(count) is not int or not 16<=count<=512 or type(period) is not int or not 100<=period<=20000:
        raise ValueError('Invalid requested timing')
    rows=packet.get('rows',[])
    if len(rows)!=count:
        raise ValueError('Incomplete block')
    previous=-1
    for row in rows:
        if not isinstance(row,list) or len(row)!=10 or any(type(x) is not int for x in row):
            raise ValueError('Invalid block row')
        frame,dac,*rest=row
        if frame<0 or not 0<=dac<=4095 or any(not 0<=v<16384 for v in rest[:4]):
            raise ValueError('Raw sample outside range')
        for offset in rest[4:]:
            if not 0<=offset<=65535 or frame+offset<previous:
                raise ValueError('Invalid per-channel timestamp')
            previous=frame+offset
    if expected_command is not None:
        _,requested_boot,kind,n,period,amplitude,frequency=expected_command.decode().split()
        if boot!=requested_boot:
            raise BootContinuityError('Capture boot ID does not match request')
        if (packet.get('kind'),count,packet.get('period_us'),packet.get('amplitude_or_hold_code'),packet.get('frequency_millihz')) != (kind,int(n),int(period),int(amplitude),int(frequency)):
            raise ValueError('Capture does not match request')
    return packet


def dc_hold_command(config, *, boot_id, hold_v):
    """A persistent calibration level, bounded by the already armed envelope."""
    validate_boot_id(boot_id)
    code=_dc_code(config,hold_v)
    return f'DC {boot_id} {code}\n'.encode()


def set_dc_level(port,config,*,hold_v,expected_boot_id,output='runs'):
    """Explicit, boot-bound calibration hold; no capture, retry or auto-arm."""
    request=dc_hold_command(config,boot_id=expected_boot_id,hold_v=hold_v)
    code=int(request.split()[2]);continuity=BootContinuity(expected_boot_id)
    log=Recorder(output,mode='hardware_uncalibrated_DC_hold')
    log.add('DC_configuration',{'configuration':asdict(config),'request':request.decode().strip(),
        'expected_boot_id':expected_boot_id,'nominal_target_v':hold_v,
        'scope':'DUT disconnected, calibration fixture only. Output remains driven for the DMM reading; no calibrated voltage claim.'})

    def check_state(packet):
        continuity.check(packet)
        if packet.get('type')!='pong' or packet.get('dc_hold_supported') is not True:
            raise ValueError('Firmware does not advertise DC hold support')
        if packet.get('armed') is not True or packet.get('ref_code')!=config.ref_code or packet.get('max_jump_code')!=config.max_jump:
            raise ValueError('Instrument not armed with matching limits; explicit re-arm required')

    try:
        # At most two bounded moves plus a final stability window; allow the
        # configured maximum settle time and a return-to-REF after failure.
        with serial.Serial(port,115200,timeout=40,write_timeout=2) as board:
            time.sleep(2);board.reset_input_buffer();board.write(b'PING\n')
            check_state(receive_response(board,log,'firmware_handshake'))
            start_uptime=continuity.previous_uptime_ms
            board.write(request)
            held=receive_response(board,log,'DC_hold_response');continuity.check(held)
            if held.get('type')!='dc_held' or held.get('held_code')!=code:
                raise ValueError('DC level not acknowledged at the requested code')
            board.write(b'PING\n')
            post=receive_response(board,log,'firmware_postcheck');check_state(post)
            if post.get('current_code')!=code:
                raise ValueError('DC level differs in postcheck')
        result={'source':'hardware_uncalibrated','boot_id':continuity.boot_id,'boot_continuity_checked':True,
                'uptime_ms_start':start_uptime,'uptime_ms_end':continuity.previous_uptime_ms,
                'held_code':code,'nominal_target_v':hold_v,'output_remains_driven':True,
                'accepted_samples':0,'calibration_performed':False}
        log.add('run_completed',result);return log.path,result
    except Exception as exc:
        reason=str(exc) if isinstance(exc,ValueError) else type(exc).__name__
        log.add('DC_hold_invalidated',{'reason':reason,'expected_boot_id':continuity.boot_id,
            'output_state_confirmed':False,'accepted_samples':0,'automatic_rearm_or_retry':False})
        log.add('run_failed',{'error':reason,'valid_for_analysis':False})
        raise RuntimeError(f'DC hold unconfirmed ({type(exc).__name__}); record: {log.path}. '
                           'Output may remain driven; no automatic recovery was attempted.') from None


def acquire_block(port,config,*,output='runs',arm_only=False,expected_boot_id=None,**settings):
    if expected_boot_id is not None or not arm_only:
        validate_boot_id(expected_boot_id)
    request=None if arm_only else capture_command(config,boot_id=expected_boot_id,**settings)
    continuity=BootContinuity(expected_boot_id)
    log=Recorder(output,mode='hardware_uncalibrated_stimulus')
    log.add('instrument_configuration',{'supply_measurement_v':config.vref_v,'configuration':asdict(config),
             'request':request.decode().strip() if request else None,'expected_boot_id':expected_boot_id,
             'startup_requirement':'Arm and establish REF with DUT disconnected; bind capture to the returned boot ID.',
             'scope':'Calibration acquisition; no hardware inference.'})

    def require_armed(packet):
        if packet.get('armed') is not True or packet.get('ref_code')!=config.ref_code or packet.get('max_jump_code')!=config.max_jump:
            raise ValueError('Instrument not armed with matching limits. Disconnect DUT and explicitly re-arm.')

    try:
        with serial.Serial(port,115200,timeout=60,write_timeout=2) as board:
            time.sleep(2);board.reset_input_buffer();board.write(b'PING\n')
            pong=receive_response(board,log,'firmware_handshake')
            continuity.check(pong)
            if pong.get('type')!='pong':
                raise ValueError('Board did not answer instrument PING')
            if arm_only:
                board.write(config.arm_command(continuity.boot_id))
                arm=receive_response(board,log,'instrument_armed_response')
                continuity.check(arm)
                if arm.get('type')!='armed': raise ValueError('Instrument refused ARM')
                result={'source':'hardware_uncalibrated','reference_established':True,'diagnosis_performed':False,
                        'instruction':'Check REF, attach the test circuit, then capture with --boot-id set to this boot_id.'}
            else:
                require_armed(pong)
                board.write(request)
                packet=receive_response(board,log,'raw_capture')
                continuity.check(packet)
                validate_block(packet,expected_command=request)
                frames=[r[0] for r in packet['rows']]
                intervals=[b-a for a,b in zip(frames,frames[1:])]
                result={'source':'hardware_uncalibrated','samples':len(frames),'diagnosis_performed':False,
                        'stimulus_generated':True,'period_us_requested':packet['period_us'],
                        'frame_interval_us_min':min(intervals),'frame_interval_us_max':max(intervals),
                        'timestamp_semantics':'read completion; sample aperture awaits calibration',
                        'parked_ref_code':packet['parked_ref_code']}
            # A complete block alone is not enough: require the same boot afterward.
            board.write(b'PING\n')
            post=receive_response(board,log,'firmware_postcheck')
            continuity.check(post)
            if post.get('type')!='pong': raise ValueError('Missing final instrument PING')
            require_armed(post)
            result.update({'boot_id':continuity.boot_id,'boot_continuity_checked':True,
                           'uptime_ms_start':pong['uptime_ms'],'uptime_ms_end':post['uptime_ms']})
            log.add('run_completed',result)
            return log.path,result
    except Exception as exc:
        reason=str(exc) if isinstance(exc,ValueError) else type(exc).__name__
        log.add('instrument_run_invalidated',{'reason':reason,'expected_boot_id':continuity.boot_id,
                'valid_for_analysis':False,'accepted_samples':0,'automatic_rearm_or_retry':False})
        log.add('run_failed',{'error':reason,'valid_for_analysis':False})
        raise RuntimeError(f'Instrument run invalid ({type(exc).__name__}); record: {log.path}. '
                           'Check the connection; disconnect DUT before explicit re-arming.') from None
