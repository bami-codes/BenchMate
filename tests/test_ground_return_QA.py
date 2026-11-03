import importlib.util
from pathlib import Path

import pytest

path=Path(__file__).resolve().parents[1]/'experiments/check_ground_return.py'
spec=importlib.util.spec_from_file_location('ground_qa',path)
qa=importlib.util.module_from_spec(spec);spec.loader.exec_module(qa)


def report():
    return {'USB_off_wiring_confirmed':True,'USB_connected':True,
            'only_existing_Arduino_GND_lead_replaced':True,'new_lead_continuity_checked':True,
            'unloaded_DUT_retained':True,'verbatim':'done',
            'contacts':['Arduino GND','same existing blue GND rail contact']}


@pytest.mark.parametrize('change',[{'USB_off_wiring_confirmed':False},
    {'only_existing_Arduino_GND_lead_replaced':False},{'contacts':['REF','GND']}])
def test_other_interventions_or_live_rewiring_are_rejected(change):
    with pytest.raises(ValueError):qa.confirmed({**report(),**change})


def test_matching_maintenance_confirmation():qa.confirmed(report())
