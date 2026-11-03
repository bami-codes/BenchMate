"""No physical/model calls: inherited eligibility, source gates and honest groups."""
from copy import deepcopy
from types import SimpleNamespace
import pytest

from benchmate import reading_restored_v2 as m


def history():
    return ({'passed':True,'run_status':'run_failed'},
            {'passed':True,'run_status':'run_completed'},
            {'fits':['changed:C1'],'conditional_unique_binding':{'C1':'sam-2','C2':'sam-3'},
             'refitted':False,'source':'operator_dmm'})


def test_only_scored_isolated_group_can_qualify_continuation():
    m.eligible(*history())
    for index,key,value in [(0,'passed',False),(0,'run_status','run_completed'),
                            (1,'run_status','group_state'),(2,'refitted',True),
                            (2,'fits',[]),(2,'source','operator_marking'),
                            (2,'conditional_unique_binding',None)]:
        h=deepcopy(history());h[index][key]=value
        with pytest.raises(ValueError):m.eligible(*h)


def test_confirming_two_capacitors_does_not_assign_reference_names():
    group=m.group_confirmation(['sam-3','sam-2'],{'components':[{'id':'sam-2'},{'id':'sam-3'}]})
    assert group['individual_bindings'] is None
    assert group['chosen_by']=='operator' and group['correspondence']=='unresolved_parallel_group'
    assert group['surface_values_used_for_scoring'] is False
    for bodies in (['sam-2','sam-2'],['sam-2','sam-9'],['sam-2']):
        with pytest.raises(ValueError):m.group_confirmation(bodies,{'components':[{'id':'sam-2'},{'id':'sam-3'}]})


def test_diagnosis_calls_preserved_runner_without_inherited_model_input(monkeypatch):
    calls=[]
    log=SimpleNamespace(path=m.ROOT/'runs/reading-cohort/test',control={'preflight_record':'preflight/test'})
    reg={'previous_boot_id':'0'*32}
    monkeypatch.setattr(m,'open_record',lambda *_:(log,reg))
    monkeypatch.setattr(m,'gate',lambda *_:None)
    monkeypatch.setattr(m,'runtime',lambda:SimpleNamespace(diagnose=lambda args:calls.append(vars(args))))
    m.run(SimpleNamespace(record='test',execute=True,initial_report='initial.json',assembly_record='assembly.json'))
    assert len(calls)==1 and calls[0]['state']=='restored'
    assert set(calls[0])=={'record','state','execute','initial_report','assembly_record','previous_boot_id','preflight_run'}
    assert not any('group' in k or 'reading' in k or 'fault' in k for k in calls[0])


def test_execution_is_blocked_before_publication(monkeypatch):
    calls=[]
    monkeypatch.setattr(m,'runtime',lambda:SimpleNamespace(committed=lambda _:calls.append('published')))
    with pytest.raises(ValueError):m.gate(None,{'public_registration':'test.json'},False)
    assert calls==[]
