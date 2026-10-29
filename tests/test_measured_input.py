import numpy as np
import pytest
from benchmate.measured_input import predict_incremental_rc


def predict(frames, inputs, **kwargs):
    n=len(frames)
    return predict_incremental_rc(frames, inputs, np.full(n,50e-6), np.full(n,105e-6),
                                 gain=.5,tau_s=.005,baseline_input_v=1.63,
                                 baseline_output_v=1.645,**kwargs)


def test_actual_step_level_and_jitter_match_closed_form():
    # Measured drive carries a 6 mV offset from the nominal command; actual
    # frame intervals alternate. A command-only predictor would miss it.
    n=128;step=20
    frames=np.r_[0,np.cumsum(np.tile([.000497,.000503],64)[:n-1])]
    inputs=np.where(np.arange(n)<step,1.436,1.836)
    result=predict(frames,inputs,kind='step',step_index=step)
    low=1.645+.5*(1.436-1.63);high=1.645+.5*(1.836-1.63)
    t=frames+105e-6-frames[step]
    expected=low+(high-low)*(-np.expm1(-np.maximum(t,0)/.005))
    np.testing.assert_allclose(result['predicted_output_v'],expected,rtol=0,atol=1e-13)


def test_sine_first_frame_matches_independent_periodic_transfer():
    # Exact sample-and-hold transfer, including the OUT read delay, checks
    # the periodic initial state rather than discarding early output samples.
    n=512;dt=.002;frequency=5.;phase=.37;amplitude=.2
    theta=2*np.pi*frequency*dt;indices=np.arange(n)
    inputs=1.63+amplitude*np.cos(indices*theta+phase)
    result=predict(indices*dt,inputs,kind='sine',frequency_hz=frequency)
    a=np.exp(-dt/.005);b=np.exp(-105e-6/.005)
    transfer=.5*((1-b)+b*(1-a)/(np.exp(1j*theta)-a))
    expected=1.645+np.real(amplitude*transfer*np.exp(1j*(indices*theta+phase)))
    np.testing.assert_allclose(result['predicted_output_v'],expected,rtol=0,atol=1e-13)
    assert result['initialization']['input_samples_used']==100


def test_a_later_measured_input_change_is_not_replaced_by_nominal_command():
    n=128;frames=np.arange(n)*.0005;inputs=np.full(n,1.63)
    inputs[64:]+=.006
    result=predict(frames,inputs,kind='step',step_index=20)
    expected=1.645+.003*(-np.expm1(-np.maximum(frames+105e-6-frames[64],0)/.005))
    np.testing.assert_allclose(result['predicted_output_v'],expected,rtol=0,atol=1e-13)


@pytest.mark.parametrize('failure',['nan_input','backward_frame','late_output','output_before_input','missing_step','short_sine'])
def test_invalid_input_or_timing_is_rejected(failure):
    n=64;frames=np.arange(n)*.0005;inputs=np.full(n,1.63)
    di=np.full(n,50e-6);do=np.full(n,105e-6);kind='step';step=10;frequency=None
    if failure=='nan_input':inputs[3]=np.nan
    if failure=='backward_frame':frames[4]=frames[3]
    if failure=='late_output':do[4]=.0006
    if failure=='output_before_input':do[4]=20e-6
    if failure=='missing_step':step=None
    if failure=='short_sine':kind='sine';frequency=5
    with pytest.raises(ValueError):
        predict_incremental_rc(frames,inputs,di,do,gain=.5,tau_s=.005,
            baseline_input_v=1.63,baseline_output_v=1.645,kind=kind,step_index=step,frequency_hz=frequency)
