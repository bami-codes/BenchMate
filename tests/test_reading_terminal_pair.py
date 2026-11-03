"""Withdrawn observations must not masquerade as performed/scored measurements."""
import json
from pathlib import Path
import subprocess
import sys

import pytest

from benchmate.reading_terminal_pair import verify_pair
from test_reading_verify import pair,rechain


@pytest.fixture
def complete_reports(pair):
    def edit(es):
        for e in es:
            if e['kind']=='diagnosis_finished':
                child=pair/e['payload']['record']/'events.jsonl'
                e['payload']['agent_report']=json.loads(child.read_text().splitlines()[-1])['payload']['agent_report']
    rechain(pair/'events.jsonl',edit)
    return pair


def test_preserved_normal_path_and_stdlib_cli(complete_reports):
    pair=complete_reports
    r=verify_pair(pair);assert r['passed'],r
    out=subprocess.run([sys.executable,'-S','-m','benchmate.reading_terminal_pair','verify',str(pair)],
        cwd=Path(__file__).resolve().parents[1],capture_output=True,text=True)
    assert out.returncode==0,out.stdout+out.stderr


def test_cannot_withdraw_after_a_value_was_already_scored_even_if_rehashed(complete_reports):
    pair=complete_reports
    def edit(es):
        es.insert(-1,{'timestamp':es[-1]['timestamp'],'kind':'operator_reading_cancelled','payload':{}})
    rechain(pair/'events.jsonl',edit)
    r=verify_pair(pair);assert not r['passed'] and r['error']=='unqualified_reading_withdrawal'


def test_rehashed_summary_cannot_relabel_fault_native_verdict(complete_reports):
    pair=complete_reports
    def edit(es):
        next(e for e in es if e['kind']=='diagnosis_finished')['payload']['agent_report']['verdict']='structure_supported'
    rechain(pair/'events.jsonl',edit)
    r=verify_pair(pair);assert not r['passed'] and r['error']=='diagnostic_report_child_mismatch'
