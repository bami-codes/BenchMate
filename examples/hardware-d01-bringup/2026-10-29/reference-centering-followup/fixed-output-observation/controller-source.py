"""About 30 seconds of unchanged-output ADC blocks while DMM reads DRIVE-REF."""
from pathlib import Path
import json,time
from datetime import datetime,timezone
import numpy as np
import serial
from serial.tools import list_ports
from benchmate.records import Recorder
from benchmate.instrument import BootContinuity,receive_response,validate_block
boot='a09aa39f4755ba059967f31ac9221cd3';code=1374
log=Recorder('runs/hardware-simultaneous-ref-difference',mode='fixed_output_ADC_while_operator_observes_differential_DMM')
(log.path/'controller-source.py').write_bytes(Path(__file__).read_bytes())
log.add('operator_ready_report',{'verbatim':'0.002V','differential_v':.002,'requested_black':'D50 REF','requested_red':'D45 DRIVE','range':'DC 2 V','USB_RESET_wiring_unchanged_per_instruction':True,'ready_inferred_from_requested_reading_reply':True})
log.add('predeclared_observation',{'duration_target_s':30,'maximum_blocks':15,'held_code':code,'no_ARM_DC_or_firmware_change':True,'only_same_code_HOLD_and_PING':True,'count_all_blocks_as_calibration':True,'DMM_interval_report_pending':True,'no_automatic_retry':True})
guard=BootContinuity(boot_id=boot)
def req(board,cmd,kind,timeout=5):
 log.add('serial_command',{'request':cmd.decode().strip()});board.timeout=timeout
 if board.write(cmd)!=len(cmd):raise ValueError('Incomplete write')
 b=receive_response(board,log,kind);guard.check(b);return b

def pong(p):
 if not(p.get('type')=='pong' and p.get('armed') is True and p.get('ref_code')==code and p.get('current_code')==code and p.get('max_jump_code')==837 and p.get('adc_sample_states_readback')==[255]*4 and p.get('adc_sample_state_channels')==[0,1,2,21]):raise ValueError('Unexpected held state')
try:
 ports=[p for p in list_ports.comports() if (p.vid,p.pid,p.serial_number)==(9025,105,'3612211F36323632E4B233334B572F52')]
 if len(ports)!=1:raise ValueError('Expected board absent or ambiguous')
 summaries=[]
 with serial.Serial(ports[0].device,115200,timeout=5,write_timeout=2) as board:
  time.sleep(2);board.reset_input_buffer();pong(req(board,b'PING\n','initial_PING'))
  start=time.monotonic();started=datetime.now(timezone.utc).isoformat();log.add('observation_window_started',{'UTC':started});print(json.dumps({'record':str(log.path),'stage':'OBSERVATION_STARTED','UTC':started,'duration_target_s':30}),flush=True)
  while len(summaries)<15 and time.monotonic()-start<30:
   cmd=f'CAPTURE {boot} HOLD 512 2000 {code} 0\n'.encode();b=req(board,cmd,'hold_raw_capture',30);validate_block(b,expected_command=cmd);pong(req(board,b'PING\n','block_postcheck'))
   a=np.asarray(b['rows']);assert np.all(a[:,1]==code)
   means=a[:,2:6].mean(axis=0);item={'block':len(summaries),'elapsed_s':time.monotonic()-start,'mean_counts':dict(zip(['A1','A2','A3','A4'],map(float,means))),'raw_nominal_A3_minus_A4_mV':float((means[2]-means[3])*4.89/16383*1000),'overruns':b['overruns']}
   summaries.append(item);log.add('block_summary',item)
  ended=datetime.now(timezone.utc).isoformat();pong(req(board,b'PING\n','final_PING'))
  result={'UTC_start':started,'UTC_end':ended,'elapsed_s':time.monotonic()-start,'blocks':summaries,'held_code':code,'boot_id':boot,'output_changed':False,'DMM_interval_report_pending':True}
  (log.path/'summary.json').write_text(json.dumps(result,indent=2)+'\n')
 log.add('run_completed',result);print(json.dumps({'record':str(log.path),'stage':'completed','blocks':len(summaries),'UTC_start':started,'UTC_end':ended,'output_changed':False}),flush=True)
except Exception as e:
 log.add('run_failed',{'error':str(e),'no_automatic_retry':True});print(json.dumps({'record':str(log.path),'stage':'failed','error':str(e)}),flush=True);raise
