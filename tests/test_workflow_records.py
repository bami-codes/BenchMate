import json
import pytest
from benchmate.workflow import run_synthetic
from benchmate.records import read_events


@pytest.mark.parametrize("case,winner,total",[("b1","rc",4),("b6","rc_input_branch",4),("d01-r","r_changed",3),("d01-c","c_changed",3)])
def test_full_synthetic_loop_and_exact_replay(tmp_path,case,winner,total):
    path,summary=run_synthetic(case,output=tmp_path)
    assert summary["initial_report"]["status"]=="unresolved"
    assert summary["final_report"]["status"]=="verified_within_declared_candidates"
    assert summary["final_report"]["supported_candidates"]==[winner]
    assert summary["total_physical_acquisitions"]==total
    assert summary["requested_human_actions"]==0
    events=read_events(path)
    assert events[-1]["payload"]==summary
    kinds=[e["kind"] for e in events]
    assert kinds.index("prediction_committed")<kinds.index("verification_acquisition")
    assert not summary["llm_used"]


def test_tampered_record_fails_integrity(tmp_path):
    path,_=run_synthetic("b6",output=tmp_path)
    file=path/"events.jsonl"
    lines=file.read_text().splitlines()
    item=json.loads(lines[-1]);item["payload"]["source"]="hardware";lines[-1]=json.dumps(item)
    file.write_text("\n".join(lines)+"\n")
    with pytest.raises(ValueError,match="integrity"): read_events(path)


def test_missing_terminal_event_is_incomplete(tmp_path):
    path,_=run_synthetic("b1",output=tmp_path)
    file=path/"events.jsonl";file.write_text("\n".join(file.read_text().splitlines()[:-1])+"\n")
    with pytest.raises(ValueError,match="incomplete"): read_events(path)

