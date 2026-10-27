"""D2 calibration transport. Raw counts and timing only; never diagnoses hardware."""
from dataclasses import dataclass, asdict
import json
import math
import time
import serial
from .records import Recorder


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

    def arm_command(self):
        center,span = self.ref_code,self.max_jump
        low = max(16,math.floor((self.ref_v-1.1)*16383/self.vref_v))
        high = min(16367,math.ceil((self.ref_v+1.1)*16383/self.vref_v))
        return f'ARM {center} {center-span} {center+span} {span} {self.settle_ms} {self.stable_delta_counts} {low} {high}\n'.encode()


def capture_command(config, *, kind='step', samples=512, period_us=500,
                    amplitude_v=.5, frequency_hz=None, hold_v=None):
    if type(samples) is not int or not 16<=samples<=512 or type(period_us) is not int or not 100<=period_us<=20000:
        raise ValueError('Invalid sample count or requested period')
    if kind not in ('step','sine','hold'):
        raise ValueError('Unsupported waveform')
    if kind=='hold':
        if hold_v is None or not math.isfinite(hold_v) or abs(hold_v-config.ref_v)>1:
            raise ValueError('HOLD needs a voltage within REF ± 1 V')
        amplitude = round(4095*hold_v/config.vref_v)
        amplitude = min(config.ref_code+config.max_jump,max(config.ref_code-config.max_jump,amplitude))
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
    return f'CAPTURE {kind.upper()} {samples} {period_us} {amplitude} {frequency}\n'.encode()


def validate_block(packet, *, expected_command=None):
    if packet.get('protocol')!='benchmate-instrument-v1' or packet.get('type')!='capture':
        raise ValueError('Unexpected instrument protocol')
    if packet.get('source')!='hardware_uncalibrated' or packet.get('adc_bits')!=14 or packet.get('dac_bits')!=12:
        raise ValueError('Unexpected capture provenance')
    if packet.get('channels')!=['A1','A2','A3','A4'] or packet.get('timestamp_semantics')!='analogRead_completion_us':
        raise ValueError('Unexpected channels or timing semantics')
    if packet.get('timing_valid') is not True or packet.get('overruns')!=0:
        raise ValueError('Acquisition timing failed; reduce rate and repeat D2 timing check')
    if packet.get('adc_sample_states_readback_min')!=255:
        raise ValueError('ADC long sampling-state request was not retained')
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
        _,kind,n,period,amplitude,frequency=expected_command.decode().split()
        if (packet.get('kind'),count,packet.get('period_us'),packet.get('amplitude_or_hold_code'),packet.get('frequency_millihz')) != (kind,int(n),int(period),int(amplitude),int(frequency)):
            raise ValueError('Capture does not match request')
    return packet


def acquire_block(port,config,*,output='runs',arm_only=False,**settings):
    request=capture_command(config,**settings)
    log=Recorder(output,mode='hardware_uncalibrated_stimulus')
    log.add('instrument_configuration',{'supply_measurement_v':config.vref_v,'configuration':asdict(config),
             'request':request.decode().strip(),'startup_requirement':'Arm and establish REF with DUT disconnected.',
             'scope':'Calibration acquisition; no hardware inference.'})
    try:
        with serial.Serial(port,115200,timeout=60,write_timeout=2) as board:
            time.sleep(2);board.reset_input_buffer();board.write(b'PING\n')
            pong=json.loads(board.readline())
            if pong.get('protocol')!='benchmate-instrument-v1' or pong.get('type')!='pong':
                raise ValueError('Board did not answer instrument PING')
            log.add('firmware_handshake',pong)
            if arm_only:
                board.write(config.arm_command())
                arm=json.loads(board.readline())
                if arm.get('type')!='armed': raise ValueError('Instrument refused ARM')
                log.add('instrument_armed',arm)
                result={'source':'hardware_uncalibrated','reference_established':True,'diagnosis_performed':False,
                        'instruction':'REF is established. Attach the test circuit, then run instrument without --arm-only.'}
                log.add('run_completed',result)
                return log.path,result
            if pong.get('armed') is not True or pong.get('ref_code')!=config.ref_code or pong.get('max_jump_code')!=config.max_jump:
                raise ValueError('Instrument not armed with matching limits. Disconnect DUT, run --arm-only, then attach DUT for capture.')
            board.write(request)
            raw=board.read_until(b'\n',size=262144)
            packet=json.loads(raw)
            log.add('raw_capture',packet)  # Preserve invalid/partial timing too.
            validate_block(packet,expected_command=request)
            frames=[r[0] for r in packet['rows']]
            intervals=[b-a for a,b in zip(frames,frames[1:])]
            result={'source':'hardware_uncalibrated','samples':len(frames),'diagnosis_performed':False,
                    'stimulus_generated':True,'period_us_requested':packet['period_us'],
                    'frame_interval_us_min':min(intervals),'frame_interval_us_max':max(intervals),
                    'timestamp_semantics':'read completion; sample aperture awaits calibration',
                    'parked_ref_code':packet['parked_ref_code']}
            log.add('run_completed',result)
            return log.path,result
    except Exception as exc:
        log.add('run_failed',{'error':str(exc) if isinstance(exc,ValueError) else type(exc).__name__})
        raise RuntimeError(f'Instrument capture failed ({type(exc).__name__}); record: {log.path}') from None
