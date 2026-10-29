"""Execute the actual sketch parser with fake IO; compile real boards separately."""
import json
from pathlib import Path
import shutil
import subprocess
import pytest
from benchmate.instrument import BootContinuity,validate_block

ROOT=Path(__file__).resolve().parents[1]


@pytest.fixture(scope='module')
def firmware_binary(tmp_path_factory):
    compiler=shutil.which('c++')
    if compiler is None: pytest.skip('Native C++ compiler unavailable; board compile is separate')
    output=tmp_path_factory.mktemp('instrument-native')/'instrument-protocol'
    subprocess.run([compiler,'-std=c++17','-I',str(ROOT/'tests/firmware_stubs'),
                    str(ROOT/'tests/firmware_stubs/instrument_protocol.cpp'),'-o',str(output)],
                   check=True,capture_output=True,text=True)
    return output


@pytest.mark.parametrize('mode',['ok','init-fail','read-fail','zero'])
def test_real_firmware_parser_guards_drive_commands_and_envelopes_every_response(firmware_binary,mode):
    output=subprocess.run([str(firmware_binary),mode],check=True,capture_output=True,text=True).stdout
    packets=[json.loads(line) for line in output.splitlines()]
    assert packets and all(p['protocol']=='benchmate-instrument-v2' for p in packets)
    assert all(type(p['uptime_ms']) is int for p in packets)
    if mode=='ok':
        guard=BootContinuity()
        for packet in packets:guard.check(packet)
        assert {'pong','error','armed','capture','parked'} <= {p['type'] for p in packets}
        assert [p['held_code'] for p in packets if p['type']=='dc_held']==[2265,523]
        assert all(p['dc_hold_supported'] is True for p in packets if p['type']=='pong')
        assert any(p['type']=='pong' and p['current_code']==2265 for p in packets)
        assert sum('DC settling failed' in p.get('message','') for p in packets)==2
        packet=next(p for p in packets if p['type']=='capture')
        assert validate_block(packet,expected_command=f'CAPTURE {guard.boot_id} HOLD 16 500 1394 0\n'.encode()) is packet
    else:
        assert all(p['boot_id'] is None and p['boot_id_ready'] is False for p in packets)
        assert {p['type'] for p in packets}=={'pong','error'}
