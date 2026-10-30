#!/usr/bin/env python3
"""Resistor-only control, before diode insertion. No provider or model call."""
from pathlib import Path
import argparse,hashlib,json,sys,time,uuid
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from benchmate.records import Recorder
from benchmate.instrument import BootContinuity
from benchmate.physical_bench import PhysicalBench
from benchmate.range_control import CONTROL_WAVEFORMS,freeze_differential_anchor,score_resistor_control


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--protocol',required=True);parser.add_argument('--connection-report',required=True)
    args=parser.parse_args();protocol_path=Path(args.protocol)
    p=json.loads(protocol_path.read_text());report=json.loads(Path(args.connection_report).read_text())
    for rel,digest in p['source_sha256'].items():
        if hashlib.sha256((ROOT/rel).read_bytes()).hexdigest()!=digest:raise ValueError('Source changed after freeze: '+rel)
    if report.get('USB_off_wiring_confirmed') is not True or report.get('USB_connected') is not True or report.get('fixture')!='resistor_only':
        raise ValueError('Confirmed resistor-only hookup/reconnection required')
    if not isinstance(report.get('verbatim'),str) or not report['verbatim'].strip():raise ValueError('Actual operator report required')
    vref=report['supply_v'];ref=report['REF_v']
    if type(vref) not in (int,float) or type(ref) not in (int,float):raise ValueError('Fresh numeric supply and REF readings required')
    p['configuration']={**p['configuration'],'vref_v':vref,'ref_v':ref}
    scale=vref/p['calibration_supply_v']
    for mapping in p['voltage_conversion']['channels'].values():mapping['gain_v_per_count']*=scale
    driver=p['driver_v_per_code']*scale
    log=Recorder(ROOT/'runs/hardware-b5-range-control',mode='resistor_only_control_before_B5_diode')
    (log.path/'protocol.json').write_bytes(protocol_path.read_bytes())
    (log.path/'connection-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    for rel in p['source_sha256']:
        target=log.path/'source'/rel;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes((ROOT/rel).read_bytes())
    log.add('range_control_plan_frozen',{'configuration':p['configuration'],'gain_supply_scale':scale,
        'voltage_conversion':p['voltage_conversion'],'driver_v_per_code':driver,'waveforms':CONTROL_WAVEFORMS,
        'protocol_sha256':hashlib.sha256(protocol_path.read_bytes()).hexdigest(),'API_calls':0,
        'diode_installed':False,'automatic_retry_or_rearm':False})
    (ROOT/'runs/hardware-b5-range-control-current-path.txt').write_text(str(log.path)+'\n')
    bench=PhysicalBench(p,log,lambda _:None,initial_report={},previous_boot_id=p['previous_boot_id'])
    continuity=BootContinuity();scores=[];stage='preflight'
    print(json.dumps({'stage':'started','record':str(log.path),'API_calls':0}),flush=True)
    try:
        ports=[port for port in bench.ports() if (port.vid,port.pid,port.serial_number)==tuple(p['USB_identity'])]
        log.add('USB_preflight',{'matching_ports':[port.device for port in ports]})
        if len(ports)!=1:raise ValueError('Expected Minima absent or ambiguous')
        with bench.serial_factory(ports[0].device,115200,timeout=5,write_timeout=2) as board:
            time.sleep(2);board.reset_input_buffer();stage='fresh_boot'
            bench._ping(board,continuity,'fresh_boot_PING',False)
            if continuity.boot_id==p['previous_boot_id']:raise ValueError('New boot not established after reported wiring')
            bench.boot_id=continuity.boot_id;stage='single_ARM'
            arm=bench._request(board,continuity,bench.config.arm_command(continuity.boot_id),'ARM_response',15)
            if arm.get('type')!='armed':raise ValueError('ARM not acknowledged')
            bench._ping(board,continuity,'post_ARM_PING',True)
            stage='initial_HOLD';bench._hold(board,continuity,'pre_DMM_HOLD')
            request_id=uuid.uuid4().hex
            request={'request_id':request_id,'kind':'independent_DMM_bias','boot_id':continuity.boot_id,
                'held_code':bench.config.ref_code,'response_file':'bias-response-'+request_id+'.json',
                'instruction':'USB・배선・RESET을 그대로 두고 DC 2V에서 검정 프로브를 큰 보드 D50 REF에 고정한다. 빨강으로 A35 IN 점퍼 금속, 이어 E30 OUT 접점을 읽어 IN−REF / OUT−REF를 부호와 마지막 자리까지 보고한다.'}
            log.add('DMM_bias_requested',request)
            (log.path/'bias-request.json').write_text(json.dumps(request,ensure_ascii=False,indent=2)+'\n')
            print(json.dumps({'stage':'awaiting_DMM_bias','request_file':str(log.path/'bias-request.json')},ensure_ascii=False),flush=True)
            response_path=log.path/request['response_file'];deadline=time.monotonic()+1800;last_ping=0.;stage='waiting_DMM'
            while not response_path.exists():
                now=time.monotonic()
                if now>deadline:raise ValueError('DMM reply timeout; no scored waveform sent')
                if now-last_ping>=2:
                    bench._ping(board,continuity,'waiting_DMM_PING',True);last_ping=now
                time.sleep(.25)
            bias=json.loads(response_path.read_text())
            if bias.get('request_id')!=request_id or not bias.get('verbatim'):raise ValueError('DMM reply does not match request')
            log.add('independent_DMM_bias_report',bias)
            # Validate bias before even the post-report HOLD calibration blocks.
            freeze_differential_anchor([5000.]*4,p['voltage_conversion']['channels'],bias['input_minus_REF_v'],bias['output_minus_REF_v'],
                                       ref_code=bench.config.ref_code,driver_v_per_code=driver)
            stage='bias_anchor_HOLDs'
            rows=[bench._hold(board,continuity,'anchor_HOLD_'+str(i+1)) for i in range(3)]
            means=np.asarray([r[:,2:6].mean(axis=0) for r in rows]).mean(axis=0)
            anchor=freeze_differential_anchor(means,p['voltage_conversion']['channels'],bias['input_minus_REF_v'],bias['output_minus_REF_v'],
                                              ref_code=bench.config.ref_code,driver_v_per_code=driver)
            (log.path/'differential-anchor.json').write_text(json.dumps(anchor,indent=2)+'\n')
            log.add('differential_anchor_frozen',anchor)
            for i,settings in enumerate(CONTROL_WAVEFORMS):
                stage=f"control_{i+1}_{settings['kind']}_{settings['amplitude_v']}"
                log.add('control_waveform_requested',{'phase':stage,'settings':settings,'fixed_prediction':'OUT−REF = measured IN−REF; input compared with independently anchored old driver map'})
                captured=bench._capture(board,continuity,stage,settings);bench._waveform_checks(captured,settings)
                score=score_resistor_control(captured,settings,anchor)
                scores.append({'phase':stage,'settings':settings,**score})
                log.add('range_control_comparison',scores[-1]);bench.acquisitions+=1
                print(json.dumps({'stage':stage,'RMS_mV':score['RMS_mV'],'input_command_RMS_mV':score['input_command_RMS_mV'],'passed':score['passed']}),flush=True)
                bench._hold(board,continuity,stage+'_return_REF')
                if not score['passed']:raise ValueError('Fixed resistor-only tracking check failed; no higher/next waveform')
            bench._ping(board,continuity,'final_PING',True)
        result={'source':'physical_resistor_only_control','passed':True,'scores':scores,'anchor':anchor,
                'instrument':bench.metadata(),'boot_id':continuity.boot_id,'held_code':bench.config.ref_code,
                'A4_mean_span_mV':float(np.ptp(np.asarray([r['means'] for r in bench.reference_means])[:,3]))*1000,
                'reference_means':bench.reference_means,'diode_installed':False,'API_calls':0,'B5_discovery_completed':False,
                'absolute_calibration_claim':False,'raw_frames_retained':True}
        (log.path/'result.json').write_text(json.dumps(result,indent=2)+'\n');log.add('run_completed',result)
        print(json.dumps({'stage':'completed','record':str(log.path),'passed':True,'instrument':bench.metadata()}),flush=True)
    except (Exception,KeyboardInterrupt) as exc:
        bench.stopped=True
        failure={'stage':stage,'error':str(exc) or type(exc).__name__,'scores':scores,'instrument':bench.metadata(),
                 'API_calls':0,'passed':False,'automatic_retry_or_rearm':False}
        log.add('run_failed',failure)
        print(json.dumps({'stage':'failed','record':str(log.path),'failed_at':stage,'error':failure['error']}),flush=True)
        raise SystemExit(1)


if __name__=='__main__':main()
