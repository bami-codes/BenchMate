from copy import deepcopy
import pytest

from benchmate.reading_restored_after_photo_v5 import eligible


def good():
    return ({'passed':True,'run_status':'run_completed'},
            {'outcome':'one_explanation_remains','fits':['changed:R1'],'refitted':False},
            {'reading_outcome':'one_explanation_remains','original_failed_status_preserved':True,
             'repair_completed':False,'restored_diagnosis_completed':False})


def test_completed_reading_allows_restored_only_continuation():
    eligible(*good())


@pytest.mark.parametrize('mutate',[
    lambda a,s,r:a.update(run_status='run_failed'),
    lambda a,s,r:s.update(fits=[]),
    lambda a,s,r:s.update(fits=['changed:R1','changed:R2']),
    lambda a,s,r:s.update(refitted=True),
    lambda a,s,r:r.update(original_failed_status_preserved=False),
    lambda a,s,r:r.update(restored_diagnosis_completed=True),
])
def test_failed_or_ambiguous_or_replaced_history_cannot_start_restored_stage(mutate):
    args=deepcopy(good());mutate(*args)
    with pytest.raises(ValueError):eligible(*args)
