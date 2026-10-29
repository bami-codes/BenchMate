# Measured-IN conditional incremental prediction

`benchmate.measured_input.predict_incremental_rc` accepts measured input and
channel timing, fixed gain/tau, and input/output origins from a **separate
pre-stimulus HOLD**. It accepts no scored output samples. The fixed RC rule is
`d(delta_OUT)/dt = (gain * delta_IN - delta_OUT) / tau`, with REF treated as
stationary under the existing A4 guard.

Each measured A1 sample reconstructs the held input level during its command
frame. The solver propagates the exact exponential through the measured frame
intervals and samples at the A2 read-completion delay. STEP initialization uses
the measured pre-step IN mean after firmware settling. SINE initialization is
the periodic state of the first complete measured IN cycle, assumed representative
of the prior warmup. Every scored sample is retained. ADC read completion is
still only a provisional proxy for the true sample aperture.

Freeze the model, input processing, initial-state rule, guards and acceptance
criteria before collection. Acquire independent stationary origins and freeze
them before the scored waveforms. Compute conditional curves from A1 only, then
compare with A2. Do not estimate an offset or parameters from scored OUT. This
is not an absolute waveform prediction made before observing IN, and is not
absolute voltage calibration.

The software reduces repeated manual center matching for this limited linear
response check. Relative channel gain, REF movement, clipping, timing and supply
limits still matter. It does not eliminate meter use for wiring changes,
component measurements, failed guards or absolute/nonlinear calibration. In
particular, a B5 diode's physical bias cannot be certified by canceling a DC
origin.

Nine numerical tests cover independent closed-form step/jitter, exact periodic
sample-and-hold sine including its first sample, a later input-level change and
invalid data/timing. Isolated fake-device runs accept repaired dynamics with a
separate 12 mV offset, reject unrepaired dynamics, and stop after a changed boot
or failed REF guard. The [new physical repair check](../examples/hardware-d01-repair/2026-10-30/README.md)
passed at 2.118/2.045 mV RMS, while the old absolute checks remain failed.

The ordinary Spark agent remains synthetic-only; this predictor does not by
itself enable unrestricted hardware diagnosis or general automatic A4 control.
