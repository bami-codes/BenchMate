"""One predeclared near-REF correction, bounded and checked; no adaptive retry."""
from pathlib import Path
import hashlib,json,time
import numpy as np
import serial
from serial.tools import list_ports
from benchmate.records import Recorder,read_events
from benchmate.instrument import BootContinuity,receive_response,validate_block
plan_path=Path('runs/hardware-local-ref-centering-plan/20261029T142321-622c7d06f9/plan.json')
plan_events=read_events(plan_path.parent);freeze=next(e['payload'] for e in plan_events if e['kind']=='centering_plan_frozen')
assert hashlib.sha256(plan_path.read_bytes()).hexdigest()==freeze['sha256']
p=json.loads(plan_path.read_text());old=p['old_code'];new=p['new_code'];g=p['guards'];supply=p['supply_estimate_v']
assert abs(new-old)<=g['max_code_move'] and abs(p['predicted_delta_DRIVE_v'])<=g['max_estimated_move_v']
log=Recorder('runs/hardware-local-ref-centering-trial',mode='one_bounded_same_boot_center_move_no_general_auto_control')
for source,name in [(Path(__file__),'controller-source.py'),(plan_path,'plan.json'),(Path('src/benchmate/instrument.py'),'host-instrument.py')]: (log.path/name).write_bytes(source.read_bytes())
log.add('frozen_plan_reference',{'sha256':freeze['sha256'],'old_code':old,'new_code':new,'auto_retry':False,'firmware_upload':False,'DMM_independent_check_pending':True})
guard=BootContinuity(p['boot_id'],p['previous_uptime_ms']);stage='preflight';confirmed_code=None

def req(board,request,kind,timeout=5):
 log.add('serial_command',{'request':request.decode().strip()});board.timeout=timeout
 if board.write(request)!=len(request):raise ValueError('Incomplete write')
 packet=receive_response(board,log,kind);guard.check(packet);return packet

def check_ping(packet,code):
 if not(packet.get('type')=='pong' and packet.get('armed') is True and packet.get('current_code')==code and packet.get('ref_code')==code and packet.get('max_jump_code')==p['old_max_jump_code'] and packet.get('adc_sample_state_channels')==[0,1,2,21] and packet.get('adc_sample_states_readback')==[255]*4):raise ValueError('Unexpected state; no automatic correction')

def hold(board,code,label):
 cmd=f"CAPTURE {p['boot_id']} HOLD 512 2000 {code} 0\n".encode()
 b=req(board,cmd,label+'_raw_capture',30);validate_block(b,expected_command=cmd)
 check_ping(req(board,b'PING\n',label+'_postcheck'),code)
 rows=np.asarray(b['rows']);assert np.all(rows[:,1]==code)
 low,high=g['raw_limits_exclusive']
 if not ((rows[:,2:6]>low)&(rows[:,2:6]<high)).all():raise ValueError('Raw rail guard failed')
 return dict(zip(['A1','A2','A3','A4'],map(float,rows[:,2:6].mean(axis=0))))
try:
 ports=[port for port in list_ports.comports() if (port.vid,port.pid,port.serial_number)==(9025,105,'3612211F36323632E4B233334B572F52')]
 if len(ports)!=1:raise ValueError('Expected board absent or ambiguous')
 with serial.Serial(ports[0].device,115200,timeout=5,write_timeout=2) as board:
  time.sleep(2);board.reset_input_buffer();stage='old_state_check'
  check_ping(req(board,b'PING\n','initial_PING'),old);confirmed_code=old
  before=hold(board,old,'before_move')
  base=json.loads(Path('runs/hardware-d01-reference-alignment/20261029T141757-e5abc8312a/summary.json').read_text())['mean_counts']
  drift={ch:(before[ch]-base[ch])*supply/16383*1000 for ch in before}
  check=all(abs(v)<=g['pre_capture_mean_drift_mV_max'] for v in drift.values())
  log.add('pre_move_guard',{'mean_drift_mV':drift,'passed':check,'output_still_code':old})
  if not check:raise ValueError('Pre-move drift limit exceeded; center not changed')
  stage='one_center_move'
  arm=req(board,(p['arm_command']+'\n').encode(),'ARM_response',15)
  if arm.get('type')!='armed':raise ValueError('ARM not acknowledged')
  check_ping(req(board,b'PING\n','after_ARM_PING'),new);confirmed_code=new
  after=hold(board,new,'after_move');stage='ADC_postcheck'
  anchor=p['control_anchor'];counts=p['anchor_mean_counts']
  drive=anchor['A3']['anchor_v']+anchor['A3']['gain_v_per_count_assumed']*(after['A3']-counts['A3'])
  ref=anchor['A4']['anchor_v']+anchor['A4']['gain_v_per_count_assumed']*(after['A4']-counts['A4'])
  ref_drift=(after['A4']-before['A4'])*supply/16383*1000
  checks={'REF_mean_drift':abs(ref_drift)<=g['post_A4_mean_drift_mV_max'],'local_ADC_DRIVE_minus_REF':abs(drive-ref)*1000<=g['post_ADC_DRIVE_minus_REF_abs_mV_max']}
  result={'boot_id':guard.boot_id,'held_code':new,'max_jump_code':p['old_max_jump_code'],'before_mean_counts':before,'after_mean_counts':after,'local_estimated_DRIVE_v':drive,'local_estimated_REF_v':ref,'local_estimated_difference_mV':(drive-ref)*1000,'A4_mean_drift_mV':ref_drift,'checks':checks,'ADC_checks_passed':all(checks.values()),'independent_DMM_check_pending':True,'general_auto_tracking_enabled':False,'existing_calibration_profile_modified':False,'full_D2_accepted':False}
  (log.path/'result.json').write_text(json.dumps(result,indent=2)+'\n');log.add('local_centering_result',result)
 log.add('run_completed',result);print(json.dumps({'record':str(log.path),**result}))
except Exception as e:
 log.add('run_failed',{'stage':stage,'error':str(e),'last_confirmed_code':confirmed_code,'automatic_retry':False});print(json.dumps({'record':str(log.path),'stage':stage,'error':str(e),'last_confirmed_code':confirmed_code}));raise
