from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,collections
from benchmate.records import Recorder
source=Path('runs/hardware-minima-midpoint-anomaly/20261029T061941-524c4d4bcd')
raw=(source/'usb-kernel-window.json').read_bytes();events=json.loads(raw)
board=[e for e in events if 'UNO R4 Minima' in e.get('eventMessage','')]
loss=[e for e in board if 'hardware connection lost' in e['eventMessage']]
enumeration=[e for e in board if 'enumerated ' in e['eventMessage']]
errors=[e for e in board if 'transaction error' in e['eventMessage']]
selected={e['timestamp']:e for e in loss+enumeration+errors[:2]+errors[-2:]}
review={'query_window_local':'2026-10-29 15:09:00–15:20:30 Asia/Seoul','source_raw_log_sha256':hashlib.sha256(raw).hexdigest(),'source_raw_log_bytes':len(raw),'kernel_query_completed':True,'all_USB_kernel_messages':len(events),'Minima_named_messages':len(board),'Minima_connection_loss_count':len(loss),'Minima_enumeration_count':len(enumeration),'Minima_transaction_error_count':len(errors),'excerpts':[{'timestamp':e['timestamp'],'message':e['eventMessage']} for e in sorted(selected.values(),key=lambda x:x['timestamp'])],'limits':['Selected exact timestamp/message excerpts only; broader kernel log is local and not published.','Port-list snapshots at PING time did not establish uninterrupted USB presence.','Enumeration loss/reappearance does not establish MCU reset, DAC register state or permanent hardware damage.','Rail contact time was not supplied; causal linkage is plausible but not conclusively timed.']}
log=Recorder('runs/hardware-minima-probe-contact',mode='operator_report_and_kernel_evidence_no_hardware_IO')
(log.path/'controller-source.py').write_bytes(Path(__file__).read_bytes())
(log.path/'usb-review.json').write_text(json.dumps(review,ensure_ascii=False,indent=2)+'\n')
log.add('operator_report',{'raw_contact_report':'아 왠지알거같애. 내가 그 빨강 레일 기둥이랑 파란 레일 기둥 아까 프로브 재면서 둘이 닿게 해버렸어','raw_USB_RESET_report':'USB·RESET 모두 건드리지 않았어','reported_event':'Red +5 V and blue GND probe posts contacted during probing','contact_time':'not supplied','contact_duration':'not supplied','actual_meter_range_for_3_28_report':'not supplied','new_four_point_voltage_readings':'not supplied'})
log.add('kernel_evidence',review)
log.add('next_physical_instruction',{'requested_USB_unplug':True,'requested_remove_only_two_added_rail_probe_posts':True,'keep_fixture_and_Arduino_supply_leads_unchanged':True,'unpowered_rail_continuity_check_requested':True,'do_not_reconnect_USB_yet':True,'completion_confirmation_received':False})
log.add('run_completed',{'recording_complete':True,'calibration_sweep_stopped':True,'midpoint_not_accepted_for_calibration':True,'high_point_not_commanded':True,'hardware_IO_performed':False,'cause_scope':'Operator rail contact can explain a supply disturbance; MCU restart, current DAC output and damage remain unestablished.','awaiting':'USB-off confirmation and rail-continuity report'})
print(json.dumps({'record':str(log.path),'review':review},ensure_ascii=False))
