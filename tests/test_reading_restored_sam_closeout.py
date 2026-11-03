"""Scope amendment cannot be made after intake or masquerade as identification."""
import pytest
from benchmate.reading_restored_sam_closeout import pre_photo,validate_SAM,result_value


def diagnosis():
    return [{'kind':'diagnosis_finished','payload':{'state':'restored','agent_report':{'verdict':'consistent','components':[]}}}]


def test_declaration_is_after_consistent_result_but_before_photo():
    pre_photo(diagnosis())
    with pytest.raises(ValueError):pre_photo(diagnosis(),photo_directory_exists=True)
    with pytest.raises(ValueError):pre_photo(diagnosis()+[{'kind':'board_photo_received','payload':{'state':'restored'}}])
    with pytest.raises(ValueError):pre_photo(diagnosis()+[{'kind':'documentary_scope_frozen','payload':{}}])
    d=diagnosis();d[0]['payload']['agent_report']['verdict']='changed'
    with pytest.raises(ValueError):pre_photo(d)


def test_even_zero_masks_never_becomes_absence_or_a_successful_binding():
    for count in (0,1,7):
        r=result_value(count)
        assert r['restored_mask_records']==count
        assert r['photo_Spark_requests']==0 and r['photo_SAM_requests']==1
        assert r['restored_component_identity_verified'] is False
        assert r['SAM_used_as_identification_evidence'] is False
        assert r['prior_restored_binding_requirement_satisfied'] is False
        assert r['native_diagnostic_repair_claim_overwritten'] is False


def sam_events(model='sam-3.1',requests=1):
    return [{'kind':'sam_request_frozen','payload':{'image_sha256':'a'*64,'concept':'electronic component','tool':None,
                                                  'model':model,'requests_max':1}},
            {'kind':'run_completed','payload':{'model':model,'requests':requests}}]


def test_spark_or_repeat_call_cannot_be_counted_as_documentary_sam():
    validate_SAM(sam_events(),'a'*64)
    for model,n in [('muse-spark-1.3',1),('sam-3.1',2)]:
        with pytest.raises(ValueError):validate_SAM(sam_events(model,n),'a'*64)
    with pytest.raises(ValueError):validate_SAM(sam_events(),'b'*64)
