import ast
import inspect
import numpy as np
import pytest
from benchmate.physics import RCModel,Acquisition,predict,response_properties,confirmation_for
from benchmate.simulation import acquire,FIXTURES
from benchmate.engine import candidate_set,diagnose,rank_actions,verify_prediction
from benchmate import engine


def observation(model,acq=Acquisition(),seed=1,noise=0):
    return acquire(model,acq,rng=np.random.default_rng(seed),noise_sd_v=noise)


def test_rc_step_against_closed_form_not_simulator():
    acq=Acquisition();model=RCModel(10000,1e-6)
    p=predict(model,acq)
    t=np.asarray(p["time_s"])
    # DAC changes at step_at_s; output capacitor voltage is continuous there.
    expected=np.where(t<acq.step_at_s,1.1,2.1-np.exp(-(t-acq.step_at_s)/0.01))
    np.testing.assert_allclose(p["out_v"],expected,atol=1e-12)


@pytest.mark.parametrize("r,c",[(4700,0.47e-6),(10000,1e-6),(47000,2e-6)])
def test_input_branch_is_unobservable_under_ideal_voltage_drive(r,c):
    a=predict(RCModel(r,c),Acquisition());b=predict(RCModel(r,c,10000),Acquisition())
    np.testing.assert_array_equal(a["out_v"],b["out_v"])
    np.testing.assert_array_equal(a["in_v"],b["in_v"])


def test_b1_b6_have_identical_reports_before_shunt():
    cs=candidate_set("input-branch")
    a=diagnose([observation(FIXTURES["b1"])],cs)
    b=diagnose([observation(FIXTURES["b6"])],cs)
    assert a==b and a["status"]=="unresolved"
    assert [p["conditional_probability"] for p in a["candidate_probabilities"]]==pytest.approx([0.5,0.5])
    assert rank_actions(cs,a["supported_candidates"])[0]["action"]=="attach_shunt_dc_pair"


def test_b6_shunt_drop_matches_ohms_law():
    acq=Acquisition(kind="dc_pair",shunt_ohm=1000,amplitude_v=1)
    a=predict(FIXTURES["b1"],acq);b=predict(FIXTURES["b6"],acq)
    np.testing.assert_allclose(a["shunt_drop_v"],[0,0],atol=1e-15)
    np.testing.assert_allclose(b["shunt_drop_v"],[-1/11,1/11],atol=1e-15)
    assert b["shunt_drop_v"][1]-b["shunt_drop_v"][0]==pytest.approx(2/11)


def test_d01_same_tau_then_load_discriminates():
    a,b=FIXTURES["d01-r"],FIXTURES["d01-c"]
    np.testing.assert_allclose(predict(a,Acquisition())["out_v"],predict(b,Acquisition())["out_v"])
    loaded=Acquisition(load_ohm=10000)
    assert response_properties(a,loaded)==pytest.approx({"gain":1/3,"tau_s":1/150})
    assert response_properties(b,loaded)==pytest.approx({"gain":0.5,"tau_s":0.01})
    cs=candidate_set("rc-fault")
    before=diagnose([observation(a)],cs)
    assert before["status"]=="unresolved"
    assert rank_actions(cs,before["supported_candidates"])[0]["action"]=="attach_10k_load"
    for model,winner in [(a,"r_changed"),(b,"c_changed")]:
        report=diagnose([observation(model),observation(model,loaded)],cs)
        assert report["status"]=="verification_required"
        assert report["supported_candidates"]==[winner]


def test_wrong_family_is_rejected_not_confidently_forced():
    capture=observation(RCModel(10000,10e-6))
    report=diagnose([capture],candidate_set("rc-fault"))
    assert report["status"]=="all_candidates_inadequate"
    assert not report["supported_candidates"]


def test_verification_failure_does_not_refit():
    settings=Acquisition(load_ohm=10000,amplitude_v=0.3)
    prediction=predict(FIXTURES["d01-r"],settings)
    result=verify_prediction(prediction,observation(FIXTURES["d01-c"],settings))
    assert not result["passed"] and not result["refitted_on_verification"]


def test_large_step_and_invalid_values_are_rejected():
    with pytest.raises(ValueError): Acquisition(amplitude_v=1)
    with pytest.raises(ValueError): RCModel(float("nan"),1e-6)
    with pytest.raises(ValueError): Acquisition(load_ohm=-1)
    with pytest.raises(ValueError): Acquisition(kind="dc_pair")


def test_hardware_capture_cannot_use_synthetic_calibration():
    capture=observation(FIXTURES["b1"]);capture["source"]="hardware"
    with pytest.raises(ValueError,match="calibration"):
        diagnose([capture],candidate_set("input-branch"))


def test_diagnosis_does_not_import_truth_fixtures():
    source=inspect.getsource(engine)
    tree=ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node,ast.ImportFrom):
            assert node.module not in ("simulation","workflow")
    assert "FIXTURES" not in source and ".private" not in source
