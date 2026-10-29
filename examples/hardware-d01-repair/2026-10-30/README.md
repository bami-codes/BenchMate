# D01 physical repair — pre-intervention prediction

Status: model frozen before requesting physical removal; **repair not performed**.

Using the earlier loaded-response estimate R = 10.15948 kohm and the
declared nominal repair capacitance 1 uF, with the same 9.99 kohm output load,
the predicted gain stays **0.49579** while loaded tau changes from
**10.239 ms to 5.037 ms**. Measured specimen
component values are not used. This is conditional on the one-state RC model
and provisional calibration, not a calibrated uncertainty statement.

The [frozen plan](model-freeze/20261029T151250-08a588f6dc/plan.json)
contains both repaired and unchanged counterfactual response curves, settings,
whole/regional limits, and the exact operator intervention. Both full voltage
waveforms will be saved after fresh supply/REF readings and before either
post-repair acquisition. The model is already fixed; fresh power readings
configure the stimulus and conversion, never the circuit parameters.

First check: +/-0.2 V step, 512 frames at 500 us. Second check: 5 Hz sine,
+/-0.2 V, 512 frames at 2000 us after the existing warmup. No post-repair
fit, offset adjustment or phase alignment enters the frozen scores. Original
failures remain visible and automatic reference tracking remains disabled.

Plan SHA-256: `f7adca32ddd08ace55dae31f4c5ce112664240e30d560f58ed2f87f08fa9358d`.
