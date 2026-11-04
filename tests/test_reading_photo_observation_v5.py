from copy import deepcopy
import pytest

from benchmate.reading_photo_observation_v5 import binding_receipt


def test_operator_confirms_actual_unique_Spark_choice_without_reassigning_it():
    proposal={'mapping_status':'unique','sam_body':'sam-a','chosen_by':'muse_spark','component':'R1',
              'candidate_bodies':[{'sam_body':'sam-a'},{'sam_body':'sam-b'}],'operator_confirmed':False}
    original=deepcopy(proposal)
    answer=binding_receipt(proposal,{'accepted':True,'operator_verbatim':'Synthetic yes'})
    assert proposal==original
    assert answer['chosen_by']=='muse_spark' and answer['sam_body']=='sam-a'
    assert answer['operator_confirmed'] is True
    assert answer['candidate_bodies']==proposal['candidate_bodies']


@pytest.mark.parametrize('status,body',[('ambiguous',None),('unresolved',None),('unique',None)])
def test_ambiguous_or_missing_reference_cannot_be_operator_truth_label(status,body):
    with pytest.raises(ValueError,match='unique Spark'):
        binding_receipt({'mapping_status':status,'sam_body':body,'chosen_by':'muse_spark'},
                        {'accepted':True,'operator_verbatim':'Synthetic yes'})


def test_operator_body_override_is_rejected():
    with pytest.raises(ValueError):
        binding_receipt({'mapping_status':'unique','sam_body':'sam-a','chosen_by':'muse_spark'},
                        {'accepted':True,'operator_verbatim':'Synthetic yes','operator_body':'sam-b'})


def test_operator_rejection_does_not_create_a_confirmation():
    with pytest.raises(ValueError):
        binding_receipt({'mapping_status':'unique','sam_body':'sam-a','chosen_by':'muse_spark'},
                        {'accepted':False,'operator_verbatim':'Synthetic no'})
