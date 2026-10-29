import numpy as np
import pytest
from benchmate.branch_gate import settled_branch_evidence


@pytest.mark.parametrize('branch_present,shunt',[(False,0.),(True,0.),(False,996.),(True,996.)])
def test_same_rules_for_both_specimens_before_and_after_shunt(branch_present,shunt):
    frames=np.arange(512)*.0005
    drive=np.where(np.arange(512)<51,1.43,1.83)
    fraction=shunt/(shunt+9990.) if branch_present else 0.
    inputs=drive-fraction*(drive-1.63)
    # Distinct constant channel offsets must cancel from the two-level contrast.
    result=settled_branch_evidence(frames,inputs-.003,drive+.012,step_index=51,
                                  shunt_ohm=shunt,branch_ohm=9990.)
    expected=['no_input_branch','input_branch'] if shunt==0 else ['input_branch' if branch_present else 'no_input_branch']
    assert result['supported_alternatives']==expected
    assert result['observed_drop_contrast_v']==pytest.approx(.4*fraction,abs=1e-13)


@pytest.mark.parametrize('bad',['late_window_too_early','small_drive','nonfinite'])
def test_unusable_measurement_is_rejected(bad):
    frames=np.arange(512)*(.0001 if bad=='late_window_too_early' else .0005)
    amplitude=.01 if bad=='small_drive' else .2
    drive=1.63+np.where(np.arange(512)<51,-amplitude,amplitude)
    inputs=drive.copy()
    if bad=='nonfinite':inputs[400]=np.nan
    with pytest.raises(ValueError):
        settled_branch_evidence(frames,inputs,drive,step_index=51,shunt_ohm=996.,branch_ohm=9990.)
