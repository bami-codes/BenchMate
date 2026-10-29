from pathlib import Path
from datetime import datetime,timezone
import json,hashlib
from benchmate.records import Recorder,read_events
log=Recorder('runs/hardware-minima-unpowered-check',mode='operator_physical_confirmation_and_probe_access_plan_no_hardware_IO')
(log.path/'controller-source.py').write_bytes(Path(__file__).read_bytes())
(log.path/'probe-access-design.json').write_bytes(Path('runs/minima-probe-access-design.json').read_bytes())
log.add('operator_physical_confirmation',{'initial_reply':'해결했어','clarified_reply':'USB 분리·기둥 제거 완료, 지속 통전음 없음','USB_disconnected_reported':True,'two_added_rail_probe_posts_removed_reported':True,'persistent_unpowered_rail_continuity_tone_reported':False,'brief_initial_tone_or_silent_from_start':'not distinguished','supply_and_fixture_leads_retained_per_instruction':True,'no_persistent_tone_is_not_proof_of_component_health':True})
log.add('probe_access_requested',{'single_ground_probe':'J27 (bottom row J, top-printed column 27)','J27_ground_continuity_before_power_required':True,'power_reading':'Existing first divider resistor A3-side lead, no extra free +5 V post','REF_reading':'Existing J10 probe','meter':'DC 20 V after unpowered continuity check','USB_reconnection_requested_after_ground_check':True,'new_power_REF_readings_pending':True,'DAC_ARM_not_requested_yet':True,'physical_installation_confirmation_pending':True})
log.add('run_completed',{'operator_USB_off_and_no_persistent_tone_recorded':True,'powered_recovery_not_yet_verified':True,'hardware_IO_performed':False,'calibration_sweep_still_stopped':True})
root=Path('examples/hardware-fixture-bringup/2026-10-29-followup');mp=root/'provenance.json';m=json.loads(mp.read_text());folder='minima-unpowered-check';assert folder not in [r['folder'] for r in m['records']]
for src in log.path.iterdir():
    dest=root/folder/src.name;dest.parent.mkdir(parents=True,exist_ok=True);raw=src.read_bytes();assert not dest.exists();dest.write_bytes(raw)
    m['copies'].append({'source':str(src),'published':str(dest.relative_to(root)),'sha256':hashlib.sha256(raw).hexdigest()})
ev=read_events(log.path);m['records'].append({'folder':folder,'source':str(log.path),'events':len(ev),'terminal':ev[-1]['kind'],'terminal_payload':ev[-1]['payload']})
m['last_appended_at_utc']=datetime.now(timezone.utc).isoformat();mp.write_text(json.dumps(m,indent=2,ensure_ascii=False)+'\n')
print(json.dumps({'record':str(log.path),'copies':len(m['copies']),'chains':len(m['records']),'events':sum(r['events'] for r in m['records'])}))
