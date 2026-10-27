import numpy as np
import pytest
from benchmate.physics import RCModel, Acquisition, predict
from benchmate.simulation import acquire
from benchmate.noise import NoiseModel, adequacy
from benchmate.inference import Family, prior_grid, families_for, infer
from benchmate.vector import predict_many
from benchmate.menu import MenuConfig, measurement_menu


def observation(model, settings=Acquisition(), noise=0):
    return acquire(model, settings, rng=np.random.default_rng(8), noise_sd_v=noise)


def test_ar1_whitening_matches_dense_covariance():
    residual = np.array([.001,.003,-.002,.004,.002])
    noise = NoiseModel(sigma_v=.002,rho=.6)
    covariance = noise.sigma_v**2 * noise.rho**np.abs(np.arange(5)[:,None]-np.arange(5))
    assert np.sum(noise.whiten(residual)**2) == pytest.approx(residual @ np.linalg.solve(covariance,residual))
    assert np.sum(noise.whiten(residual,independent=True)**2) == pytest.approx(np.sum((residual/.002)**2))


def test_channel_noise_parameters_are_used_without_changing_other_channels():
    model=NoiseModel(channel_sigma_v={'out_v':.006},channel_rho={'out_v':.5})
    residual=np.array([.003,.003,.003])
    np.testing.assert_allclose(model.whiten(residual,channel='in_v'),[1,1,1])
    np.testing.assert_allclose(model.whiten(residual,channel='out_v'),[.5,.25/np.sqrt(.75),.25/np.sqrt(.75)])


def test_transient_mismatch_cannot_hide_in_long_settled_window():
    settings = Acquisition(duration_s=2)
    capture = observation(RCModel(10000,1.05e-6),settings)
    predicted = predict(RCModel(10000,1e-6),settings)
    whole = np.sqrt(np.mean((np.asarray(capture['data']['out_v'])-predicted['out_v'])**2))
    assert whole < .015
    gate = adequacy(predicted,capture)
    assert not gate['passed']
    assert any(not check['passed'] and 'transient' in check['region'] for check in gate['checks'])


@pytest.mark.parametrize('settings', [Acquisition(),Acquisition(load_ohm=4700),
    Acquisition(kind='dc_pair',shunt_ohm=1000,amplitude_v=1),
    Acquisition(kind='sine',frequency_hz=20,amplitude_v=1,shunt_ohm=1000)])
def test_vectorized_predictions_match_scalar_zoh(settings):
    models = [RCModel(9876,1.05e-6),RCModel(23000,.8e-6,9000)]
    capture = observation(models[0],settings)
    rows = [[m.r_ohm,m.c_f,m.input_parallel_ohm or 0] for m in models]
    batch = predict_many(rows,capture)
    for i, model in enumerate(models):
        scalar = predict(model,settings)
        for key in batch:
            np.testing.assert_allclose(batch[key][i],scalar[key],atol=2e-12)


def test_original_prior_and_tau_jacobian_preserve_mass_and_moments():
    family = Family('test',(2,8),(3,12),(5,20))
    models, weights = prior_grid(family,8)
    r,c,rp = models.T
    assert weights.sum() == pytest.approx(1)
    assert weights @ r == pytest.approx((8-2)/np.log(8/2),rel=1e-10)
    assert weights @ c == pytest.approx((12-3)/np.log(12/3),rel=1e-10)
    assert weights @ rp == pytest.approx((20-5)/np.log(20/5),rel=1e-10)
    assert weights @ (r*c) == pytest.approx(((8-2)/np.log(4))*((12-3)/np.log(4)),rel=1e-10)


def test_common_unloaded_family_preserves_branch_ambiguity_and_tau_only():
    a,_ = infer([observation(RCModel(10300,1.05e-6))])
    assert a['status'] == 'unresolved'
    assert a['supported_candidates'] == ['rc','rc_input_branch']
    probs = [c['conditional_probability'] for c in a['candidates']]
    assert probs == pytest.approx([.5,.5,0,0,0],abs=1e-8)
    for candidate in a['candidates'][:2]:
        assert not candidate['identifiability']['r_c_separately_observed']
        tau = candidate['posterior_intervals_2_5_50_97_5_percent']['tau_s']
        assert tau[0] < .010815 < tau[-1]


def test_repair_mode_estimates_off_nominal_values_after_loading():
    truth = RCModel(20300,1.05e-6)
    observations = [observation(truth),observation(truth,Acquisition(load_ohm=10000))]
    result,_ = infer(observations,families_for('repair'))
    assert result['status'] == 'verification_required'
    assert result['supported_candidates'] == ['r_changed']
    fitted = next(c for c in result['candidates'] if c['name']=='r_changed')['fit_model']
    assert fitted['r_ohm'] == pytest.approx(truth.r_ohm,rel=1e-5)
    assert fitted['c_f'] == pytest.approx(truth.c_f,rel=1e-5)


def test_hardware_is_still_rejected_without_calibration():
    obs = observation(RCModel(10000,1e-6));obs['source']='hardware'
    with pytest.raises(ValueError,match='calibration'): infer([obs])


def test_menu_covers_declared_conditions_without_freezing_hardware_limit():
    config = MenuConfig(max_hz=200)
    menu = measurement_menu(config)
    assert len(menu)==85
    assert len({s.frequency_hz for s in menu.values() if s.kind=='sine'})==6
    assert {s.amplitude_v for s in menu.values() if s.kind=='sine'}=={.2,1}
    assert {s.load_ohm for s in menu.values()}=={None,4700,10000}
    assert all(s.amplitude_v != .3 for s in menu.values())
    assert not config.hardware_validated
    assert menu['shunt_dc_pair'].physical_acquisitions==2
