from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import pytest

from benchmate.netlist_diagnosis.design import digest as design_digest
from benchmate.reproducibility_bench import FixedKPhysicalNetlistBench
from benchmate.reproducibility_session import Session
from test_ref_reproducibility import data,fit,origin,digest
from test_reproducibility_bench import Board,Log

ROOT=Path(__file__).resolve().parents[1]


def module(name):
    spec=importlib.util.spec_from_file_location(name,ROOT/f'scripts/{name}.py')
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m


def qualified():
    cli=module('fixed_k_pilot');records=data();candidate=fit(records,origin(records[:3]),4.9)['candidate']
    receipt={'schema':'benchmate.fixed-k-ref-qualification.v1','passed':True,
        'candidate_sha256':digest(candidate),'fault_injection_passed':True,'qualified_fixtures':['unloaded'],
        'source':'physical_instrument_QA','validation_refit':False,
        'freeze_receipt':{'remote':True,'candidate_sha256':digest(candidate)},'source_sha256':cli.source_hashes()}
    return cli,candidate,receipt


def test_new_protocol_session_filters_loads_without_choosing_an_order():
    cli,candidate,receipt=qualified()
    design=json.loads((ROOT/'examples/passive-pilot-prepared/2026-11-03/design-01-A3REF/reviewed-design.json').read_text())
    p=cli.prepare(design,candidate,receipt,'evaluation')
    assert not p['pilot'] and not p['excluded_from_evaluation']
    initial={'choice':'initial_unloaded','fixture':'unloaded','reviewed_design_sha256':design_digest(design),
             'USB_connected':True,'USB_off_wiring_confirmed':True,
             'verbatim':'USB was off; I checked the intended circuit and IN/OUT/REF wiring, left the output load disconnected, removed probes, and reconnected the same USB port.'}
    bench=FixedKPhysicalNetlistBench(p,Log(),lambda f:None,design=design,initial_report=initial,
        previous_boot_id='a'*32,approved=True,candidate=candidate,qualification=receipt)
    session=Session(bench,Log(),design,lambda *a:None)
    snap=session.snapshot()
    assert not snap['pilot'] and not snap['excluded_from_evaluation']
    assert all(name.startswith('unloaded') for name in snap['allowed_measurements'])
    assert len(snap['allowed_measurements'])==5
    assert not snap['instrument_qualification']['diagnostic_IN_OUT_corrected']


def test_mock_qualification_cannot_prepare_physical_protocol():
    cli,candidate,receipt=qualified()
    design=json.loads((ROOT/'examples/passive-pilot-prepared/2026-11-03/design-01-A3REF/reviewed-design.json').read_text())
    with pytest.raises(ValueError):cli.prepare(design,candidate,{**receipt,'source':'mock'},'pilot')
    with pytest.raises(ValueError):cli.prepare(design,candidate,{**receipt,'source_sha256':{}},'pilot')


@pytest.mark.parametrize('validation_fault',[False,True])
def test_train_freeze_then_validate_same_candidate_without_hardware(tmp_path,monkeypatch,capsys,validation_fault):
    qa=module('fixed_k_qa');protocol=json.loads((ROOT/'examples/passive-pilot-prepared/2026-11-03/design-01-A3REF/protocol.json').read_text())
    from benchmate.instrument import InstrumentConfig
    board=Board(InstrumentConfig(**protocol['configuration']));board.unarmed=True
    original_write=board.write
    def write(command):
        words=command.decode().split()
        if words[0]=='ARM':
            board.unarmed=False;board.uptime+=1;board.commands.append(command)
            board.response=(json.dumps({'protocol':'benchmate-instrument-v2','type':'armed','boot_id':'b'*32,
                'boot_id_ready':True,'uptime_ms':board.uptime})+'\n').encode();return len(command)
        n=original_write(command)
        if words[0]=='PING' and board.unarmed:
            p=json.loads(board.response);p.update(armed=False,current_code=0,ref_code=0);board.response=(json.dumps(p)+'\n').encode()
        return n
    board.write=write;board.reset_input_buffer=lambda:None
    class Port:
        def __enter__(self):return board
        def __exit__(self,*a):pass
    monkeypatch.setattr(qa.serial,'Serial',lambda *a,**k:Port())
    monkeypatch.setattr(qa.list_ports,'comports',lambda:[SimpleNamespace(vid=9025,pid=105,serial_number=protocol['USB_identity'][2],device='FAKE')])
    monkeypatch.setattr(qa.time,'sleep',lambda *a:None)
    prepared=ROOT/'examples/passive-pilot-prepared/2026-11-03/design-01-A3REF'
    plan=tmp_path/'plan';run=tmp_path/'run';auth=tmp_path/'auth.json'
    monkeypatch.setattr(sys,'argv',['qa','plan','--prepared',str(prepared),'--expected-unarmed-boot','b'*32,'--output',str(plan)])
    qa.main();auth.write_text(json.dumps({'fixed_k_QA_authorized':True,'verbatim':'MOCK TEST ONLY'}))
    monkeypatch.setattr(sys,'argv',['qa','train','--plan',str(plan/'plan.json'),'--authorization',str(auth),'--output',str(run),'--execute'])
    qa.main()
    state=json.loads((run/'state.json').read_text());candidate=json.loads((run/'candidate.json').read_text())
    assert state['status']=='training_complete'
    assert len([x for x in board.commands if x.startswith(b'CAPTURE')])==23
    assert not (run/'qualification.json').exists()
    before=digest(candidate)
    receipt=tmp_path/'receipt.json';value={'published':True,'remote':True,'candidate_sha256':before,
        'commit':'a'*40,'public_path':'examples/fixed-k-repro/MOCK/candidate.json'};receipt.write_text(json.dumps(value))
    monkeypatch.setattr(qa.subprocess,'check_output',lambda *a,**k:json.dumps(candidate).encode())
    monkeypatch.setattr(sys,'argv',['qa','validate','--state',str(run/'state.json'),'--freeze-receipt',str(receipt),'--execute'])
    if validation_fault:
        board.extra_k=.012
        with pytest.raises(SystemExit):qa.main()
        assert json.loads((run/'state.json').read_text())['status']=='failed'
        assert not (run/'qualification.json').exists()
        assert len([x for x in board.commands if x.startswith(b'CAPTURE')])==25
        count=len(board.commands)
        with pytest.raises(ValueError):qa.main()
        assert len(board.commands)==count
        return
    qa.main()
    assert digest(json.loads((run/'candidate.json').read_text()))==before
    assert len([x for x in board.commands if x.startswith(b'CAPTURE')])==28
    assert len([x for x in board.commands if x.startswith(b'ARM')])==1
    receipt=json.loads((run/'qualification.json').read_text())
    assert receipt['passed'] and receipt['qualified_fixtures']==['unloaded'] and not receipt['validation_refit']
