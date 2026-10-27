import pytest
from benchmate.repair import run_repair
from benchmate.records import read_events


@pytest.mark.parametrize('case,part',[('d01-r','R'),('d01-c','C')])
def test_repair_is_predicted_before_replacement_then_independently_checked(tmp_path,case,part):
    path,result=run_repair(case,output=tmp_path,r_scale=1.01,c_scale=1.05)
    assert result['repair_success']
    assert result['repair']['component']==part
    assert result['total_physical_acquisitions']==result['diagnostic_acquisitions_total']+2
    assert not result['verification']['refitted_on_verification']
    events=read_events(path);kinds=[e['kind'] for e in events]
    predictions=[i for i,k in enumerate(kinds) if k=='repair_prediction_committed']
    assert len(predictions)==2 and max(predictions)<kinds.index('repair_applied')<kinds.index('repair_verification_acquisition')


def test_failed_component_replacement_cannot_pass_repair_verification(tmp_path):
    _,result=run_repair('d01-c',output=tmp_path,repair_succeeds=False)
    assert not result['repair_success']
    assert result['status']=='repair_not_verified'
