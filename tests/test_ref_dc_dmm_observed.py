import importlib.util
from pathlib import Path
import sys

import pytest

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root/'experiments'))
spec = importlib.util.spec_from_file_location('qa_observed', root/'experiments/ref_dc_dmm_observed.py')
qa = importlib.util.module_from_spec(spec); spec.loader.exec_module(qa)


def test_range_is_not_fabricated_as_three_readings():
    result = qa.observation({'kind':'displayed_range', 'display_strings':['1.630','1.631'],
                             'operator_reply_original':'1.630~1.631'})
    assert result['volts'] == [1.630, 1.631]
    assert result['individual_readings_known'] is False
    assert result['spacing_independently_verified'] is False


@pytest.mark.parametrize('values', [['1.631','1.630'], ['nan','1.630'], ['0','1.630'], ['1.630']])
def test_bad_range_stops_before_any_hardware(values):
    with pytest.raises(ValueError):
        qa.observation({'kind':'displayed_range','display_strings':values,'operator_reply_original':'report'})
