import json
import importlib.util
from pathlib import Path
import shutil
import subprocess

import pytest

ROOT=Path(__file__).resolve().parents[1]


@pytest.fixture(scope='module')
def binaries(tmp_path_factory):
    compiler=shutil.which('c++')
    if compiler is None: pytest.skip('Native compiler unavailable')
    out=tmp_path_factory.mktemp('adcqa-native')
    result={}
    for stem in ('protocol','adc_modes'):
        binary=out/stem
        subprocess.run([compiler,'-std=c++17','-I',str(ROOT/'tests/adcqa_firmware_stubs'),
                        str(ROOT/f'tests/adcqa_firmware_stubs/{stem}.cpp'),'-o',str(binary)],
                       check=True,capture_output=True,text=True)
        result[stem]=binary
    return result


@pytest.mark.parametrize('mode',['ok','init-fail','read-fail','zero'])
def test_preserved_parser_and_output_guards(binaries,mode):
    raw=subprocess.run([str(binaries['protocol']),mode],check=True,capture_output=True,text=True).stdout
    packets=[json.loads(x) for x in raw.splitlines()]
    assert packets and all(x['protocol']=='benchmate-instrument-adcqa-v1' for x in packets)
    assert all(x['adc_qa_mode']==0 for x in packets)
    if mode!='ok':assert all(x['boot_id'] is None for x in packets)


def test_single_channel_discard_mode_gate_and_timeout(binaries):
    raw=subprocess.run([str(binaries['adc_modes'])],check=True,capture_output=True,text=True).stdout
    packets=[json.loads(x) for x in raw.splitlines()]
    captures=[x for x in packets if x['type']=='capture']
    assert [x['adc_qa_mode'] for x in captures]==[1,2]
    assert [x['adc_qa_discard_per_channel'] for x in captures]==[0,1]
    assert all(x['timing_valid'] and x['parked_ref_code']==1394 for x in captures)


def test_actual_ADC_QA_capture_packets_match_the_explicit_host_adapter(binaries):
    from benchmate.instrument import validate_block
    spec=importlib.util.spec_from_file_location('adcqa_host',ROOT/'experiments/compare_adc_modes.py')
    host=importlib.util.module_from_spec(spec);spec.loader.exec_module(host)
    raw=subprocess.run([str(binaries['adc_modes'])],check=True,capture_output=True,text=True).stdout
    captures=[p for p in map(json.loads,raw.splitlines()) if p['type']=='capture']
    for packet in captures:
        view=host.validation_view(packet,packet['adc_qa_mode'])
        expected=f"CAPTURE {packet['boot_id']} HOLD 16 500 1394 0\n".encode()
        assert validate_block(view,expected_command=expected) is view
        assert packet['protocol']==host.PROTOCOL
