# Scripted mock integration rehearsal

Source commit `ae6952a`. This is a deterministic software test, not a Spark-authored
proposal or physical B5 result. All eight mock waveforms and both untouched checks
are retained. The separate mock plant uses an independent diode equation solver.
The publication callback was local-only; no GitHub prediction timing claim is made
for this rehearsal. A real Spark mock run remains separately consent-gated.

Reserved results (whole RMS; every region also passed):

- {'kind': 'step', 'samples': 512, 'period_us': 500, 'amplitude_v': 0.35}: conditional 1.667 mV; command forecast 1.925 mV.
- {'kind': 'sine', 'samples': 512, 'period_us': 2000, 'amplitude_v': 0.65, 'frequency_hz': 5.0}: conditional 1.734 mV; command forecast 1.953 mV.

No parameter uniqueness, physical calibration, loaded extrapolation or repair claim.
