# ADC-referenced stimulus control: feasibility review, 2026-10-29

Decision: pursue calibrated reference tracking to reduce repeated meter
readings, but **raw A4-to-DAC substitution is not enabled**. The D01 loaded
check retained its DMM-derived supply/REF configuration and the previously
used calibration policy. No firmware or output setting changed for this
review.

The board supports a 14-bit ADC and a 12-bit DAC
([Arduino documentation](https://docs.arduino.cc/hardware/uno-r4-minima/));
the installed instrument requests those resolutions. With a common stable
reference and ideal converters, the centering relation would be
`round(A4_count * 4095 / 16383)`. Real A4, DAC and driver gain/offset errors
do not vanish merely because they share a supply. The controlled quantity
is the physical DRIVE output, including the LM358 path, relative to REF.

Four existing REF-guard records have raw A4 voltage estimates 18.4–28.1 mV
above their associated meter reports; naive conversion changes the center
by 15–23 DAC codes. These are **sequential** ADC/DMM comparisons, so they
include possible actual REF changes and cannot establish a pure A4 offset.
The earlier fixed-REF calibration also did not identify A4 gain. A single
assumed correction is not independently validated across these conditions.

A common static voltage scale cancels from a dimensionless gain under a
linear model, but relative channel gains still need correction. Constant
scale/offset can be nuisance parameters in an exponential time-constant
fit; dynamic REF drift, saturation and nonlinear operation need separate
handling. B5 diode conduction and the declared absolute stimulus amplitudes
still depend on physical voltage and bias. An old supply reading is an
estimate with a timestamp, not a measurement of today's absolute volts.

## Minimal path to fewer meter readings

1. Establish the A4-to-physical-REF and DAC-to-DRIVE relationships near REF,
   retaining the current boot, fixture, calibration version and last DMM
   anchor. Check their alignment on an independent observation before
   enabling code-based centering. Do not fit against OUT verification data.
2. Freeze the controller and model before each scored capture. Use automatic
   boot, REF/path, saturation and timing guards between waveforms. Repeated
   DMM readings are unnecessary for every waveform in a validated session.
3. A fixture/REF-path change, new boot without a validated continuation
   policy, failed guard, stale anchor or proximity to an absolute-voltage
   limit requires a fresh check. Shared-reference counts alone cannot detect
   every common-mode supply change while guaranteeing a fixed amplitude
   in volts. Use a verified supply estimate/bound for voltage limits.
4. If a prediction fails, preserve it. A changed calibration or new control
   policy begins a separately logged development attempt; it does not turn
   the first observation into a passing holdout.

For the current D01 failure, only a stationary DMM check of D50 (REF) and
D45 (DRIVE) has been requested. The output remains at its parked setting;
no further stimulus is sent while awaiting that report. Further action
should follow that evidence, without restarting a long USB investigation.

The [raw comparison and audit](../examples/hardware-d01-bringup/2026-10-29/README.md)
retain the failed voltage predictions and conditional R/C analysis.
