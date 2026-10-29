"""Read a steady REF block in the verified held state; never change center."""
from pathlib import Path
import json,hashlib,time
import numpy as np
import serial
from serial.tools import list_ports
from benchmate.records import Recorder
from benchmate.instrument import InstrumentConfig,BootContinuity,receive_response,capture_command,validate_block
config=InstrumentConfig(vref_v=4.89,ref_v=1374*4.89/4095);boot='a09aa39f4755ba059967f31ac9221cd3'
log=Recorder('runs/hardware-d01-reference-alignment',mode='fixed_code_post_independent_DMM_centering_check')
(log.path/'controller-source.py').write_bytes(Path(__file__).read_bytes());log.add('intent',{'boot':boot,'required_code':1374,'no_ARM_DC_or_firmware_change':True,'next_DMM_contacts':['D50 REF before','D45 DRIVE','D55 actual OUT','D50 REF after'],'same_reference_code_HOLD_only':True,'paired_DMM_report_received':True})
log.add('independent_DMM_report', {'verbatim':'REF 전 1.635 / DRIVE 1.635 / REF 후 1.635', 'contacts':['D50','D45','D50'], 'values_v':[1.635,1.635,1.635], 'range':'DC 2 V', 'ground':'existing blue rail GND', 'centering_trial_record':'runs/hardware-local-ref-centering-trial/20261029T142505-120bb8e3b0', 'ADC_acquisition_after_report_without_output_change':True, 'config_ref_v_is_code_encoding_not_new_physical_measurement':True})
guard=BootContinuity(boot_id=boot,previous_uptime_ms=2292076)
def request(board,cmd,kind,timeout=5):
 log.add('serial_command',{'request':cmd.decode().strip()});board.timeout=timeout
 if board.write(cmd)!=len(cmd):raise ValueError('Incomplete write')
 p=receive_response(board,log,kind);guard.check(p);return p
def pong(p):
 if not(p.get('type')=='pong' and p.get('armed') is True and p.get('ref_code')==1374 and p.get('current_code')==1374 and p.get('max_jump_code')==config.max_jump and p.get('adc_sample_state_channels')==[0,1,2,21] and p.get('adc_sample_states_readback')==[255]*4):raise ValueError('Held state differs; no snapshot')
try:
 ports=[p for p in list_ports.comports() if (p.vid,p.pid,p.serial_number)==(9025,105,'3612211F36323632E4B233334B572F52')]
 if len(ports)!=1:raise ValueError('Expected Minima absent or ambiguous')
 with serial.Serial(ports[0].device,115200,timeout=5,write_timeout=2) as board:
  time.sleep(2);board.reset_input_buffer();pong(request(board,b'PING\n','precheck'))
  cmd=capture_command(config,boot_id=boot,kind='hold',hold_v=config.ref_v,samples=512,period_us=2000)
  b=request(board,cmd,'hold_raw_capture',30);validate_block(b,expected_command=cmd);pong(request(board,b'PING\n','postcheck'))
  rows=np.asarray(b['rows']);assert np.all(rows[:,1]==1374)
  summary={'mean_counts':dict(zip(['A1','A2','A3','A4'],map(float,rows[:,2:6].mean(axis=0)))),'nominal_volts':dict(zip(['A1','A2','A3','A4'],map(float,rows[:,2:6].mean(axis=0)*4.89/16383))),'overruns':b['overruns'],'held_ref_code':1374,'boot_id':boot,'DMM_report_pending':False,'calibration_changed':False}
  (log.path/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
 log.add('run_completed',summary);print(json.dumps({'record':str(log.path),**summary}))
except Exception as e:
 log.add('run_failed',{'error':str(e),'no_auto_retry':True,'accepted_samples':0});raise
