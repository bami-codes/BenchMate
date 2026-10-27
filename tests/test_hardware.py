import pytest
from benchmate.hardware import validate_capture


def sample():
    return {"protocol":"benchmate-bringup-v1","type":"capture","source":"hardware_uncalibrated",
            "adc_bits":14,"channels":["A1","A2","A3","A4"],
            "samples":[{"t_us":[10,20,30,40],"raw":[0,16383,100,500]}]}


def test_valid_capture_preserves_raw_counts():
    assert validate_capture(sample())["samples"][0]["raw"][1]==16383


@pytest.mark.parametrize("change",["range","time","source","channels"])
def test_invalid_captures_are_rejected(change):
    data=sample()
    if change=="range": data["samples"][0]["raw"][0]=16384
    elif change=="time": data["samples"][0]["t_us"][2]=0
    elif change=="source": data["source"]="calibrated"
    else: data["channels"].reverse()
    with pytest.raises(ValueError): validate_capture(data)
