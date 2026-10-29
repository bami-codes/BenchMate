"""Check operator-confirmed RESET identity, reject stale commands, then arm REF without DUT."""
from pathlib import Path
from dataclasses import asdict
import hashlib
import json
import time
import serial
from serial.tools import list_ports
from benchmate.records import Recorder, read_events
from benchmate.instrument import InstrumentConfig, BootContinuity, BootContinuityError, capture_command

IDENTITY='3612211F36323632E4B233334B572F52'
PRIOR=Path('runs/hardware-minima-instrument/20261029T012934-be3da2d8a1')


def main():
    old=read_events(PRIOR)[-1]['payload']['boot_id']
    config=InstrumentConfig(vref_v=4.88,ref_v=1.62)
    log=Recorder('runs/hardware-minima-fixture',mode='operator_RESET_stale_ID_rejection_and_REF_arm')
    src=Path(__file__).read_bytes()
    (log.path/'controller-source.py').write_bytes(src)
    log.add('operator_configuration',{
        'raw_user_report':'7개 이동 완료 / 4.88V / 1.62V',
        'fixture_attached':True,'board_side_connections':['5V','GND','A0','A1','A2','A3','A4'],
        'DUT_connected':False,'calibration_jumpers_11_14_15':'retained per instruction',
        'meter':'ANENG DM950; DC 20 V per instruction','voltage_reference':'Arduino GND',
        'supply_v':4.88,'REF_v':1.62,'prior_run':str(PRIOR),'prior_boot_id':old,
        'RESET_operator_report':'Minima RESET 한 번 완료',
        'previous_preflight':'runs/hardware-minima-fixture/20261029T013449-0891abd9ba',
        'power_cycle_verified':False,
        'config':asdict(config),'serial_number':IDENTITY,
        'controller_sha256':hashlib.sha256(src).hexdigest(),
        'scope':'Operator-confirmed physical RESET identity/stale-command check and explicit REF arm, no valid ADC capture',
        'same_fixture_long_term_stability_established':False})
    print(json.dumps({'record':str(log.path),'stage':'preflight'}),flush=True)
    continuity=BootContinuity()
    output_may_be_driven=False

    def ports():
        return [p for p in list_ports.comports()
                if (p.vid,p.pid,p.serial_number)==(9025,105,IDENTITY)]

    def require_state(p,armed):
        if p.get('type')!='pong' or p.get('armed') is not armed or p.get('calibrated') is not False:
            raise ValueError('Unexpected instrument state')
        if p.get('ref_code')!=(config.ref_code if armed else 0): raise ValueError('Unexpected REF code')
        if armed and p.get('max_jump_code')!=config.max_jump: raise ValueError('Unexpected output envelope')

    def exchange(board,command,label):
        log.add('serial_command',{'ascii':command.decode().strip(),'label':label})
        board.write(command);board.flush()
        raw=board.read_until(b'\n',size=8192)
        log.add('serial_response_raw',{'ascii':raw.decode('ascii',errors='backslashreplace'),'label':label})
        if not raw.endswith(b'\n'): raise ValueError('Missing or truncated response')
        packet=json.loads(raw);continuity.check(packet)
        log.add('validated_response',{'label':label,'packet':packet})
        return packet

    try:
        found=ports()
        log.add('USB_preflight',{'matching_ports':[p.device for p in found]})
        if len(found)!=1: raise RuntimeError('Expected identified Minima absent or ambiguous')
        port=found[0].device
        with serial.Serial(port,115200,timeout=10,write_timeout=2) as board:
            time.sleep(2);board.reset_input_buffer()
            first=exchange(board,b'PING\n','after_operator_RESET')
            require_state(first,False)
            if first['boot_id']==old: raise ValueError('Expected new boot ID after operator-confirmed RESET')
            try:
                BootContinuity(old).check(first)
            except BootContinuityError:
                log.add('host_stale_boot_rejected',{'previous_boot_id':old,'current_boot_id':first['boot_id']})
            else: raise ValueError('Host accepted changed boot unexpectedly')
            stale=[('stale_ARM',config.arm_command(old)),
                   ('stale_CAPTURE',capture_command(config,boot_id=old,kind='hold',samples=16,period_us=20000,hold_v=1.62))]
            for label,command in stale:
                response=exchange(board,command,label)
                if response.get('type')!='error' or response.get('message')!='boot identity mismatch or unavailable; output not changed':
                    raise ValueError('Stale command not rejected as expected')
                require_state(exchange(board,b'PING\n',label+'_postcheck'),False)
            log.add('stale_commands_rejected',{'commands':['ARM','CAPTURE'],
                    'fresh_PING_unarmed_after_each':True,'accepted_ADC_samples':0})
            output_may_be_driven=True
            response=exchange(board,config.arm_command(continuity.boot_id),'explicit_new_boot_ARM')
            if response.get('type')!='armed': raise ValueError('New boot ARM failed')
            require_state(exchange(board,b'PING\n','post_ARM'),True)
        start=time.monotonic()
        for index in range(31):
            time.sleep(max(0,start+index-time.monotonic()))
            found=ports();present=len(found)==1 and found[0].device==port
            log.add('passive_USB_sample',{'index':index,'elapsed_s':time.monotonic()-start,
                                          'present':present,'serial_closed':True})
            if not present: raise RuntimeError('Minima USB disappeared with fixture attached')
            if index%15==0: print(json.dumps({'stage':'armed_USB_watch','elapsed_s':index}),flush=True)
        with serial.Serial(port,115200,timeout=5,write_timeout=2) as board:
            time.sleep(2);board.reset_input_buffer()
            final=exchange(board,b'PING\n','post_reopen')
            require_state(final,True)
        result={'boot_id':continuity.boot_id,'prior_boot_id':old,'boot_ID_changed_after_operator_RESET':True,
                'host_old_boot_rejected':True,'firmware_stale_ARM_rejected':True,'firmware_stale_CAPTURE_rejected':True,
                'armed':True,'ref_code':config.ref_code,'nominal_DAC_target_v':config.ref_v,
                'conversion_supply_v':config.vref_v,'max_jump_code':config.max_jump,
                'closed_port_USB_samples_present':31,'post_reopen_state_verified':True,
                'ADC_capture_accepted':False,'accepted_samples':0,'calibration_performed':False,
                'output_remains_driven':True,'DMM_output_check_pending':True,
                'physical_acquisition_interruption_test_performed':False}
        log.add('run_completed',result)
        print(json.dumps({'record':str(log.path),'stage':'completed',**result}),flush=True)
    except (Exception,KeyboardInterrupt) as exc:
        result={'error':str(exc) or type(exc).__name__,'accepted_samples':0,'automatic_retry_or_rearm':False,
                'output_may_be_driven':output_may_be_driven}
        log.add('instrument_run_invalidated',result);log.add('run_failed',result)
        print(json.dumps({'record':str(log.path),'stage':'failed',**result}),flush=True)
        raise SystemExit(1)


if __name__=='__main__': main()
