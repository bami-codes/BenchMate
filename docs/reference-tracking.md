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

## Same-boot follow-up

The stationary report was D50/D45/C9 = 1.635/1.645/1.635 V. The user
requested a new forecast and new acquisition; no calibration was changed.
The same boot was verified before changing the commanded center from
code 1381 to 1369. The second C-point forecast passed the existing whole
and regional engineering checks, while the R-point failed. The first
failure is preserved. The 1.649 V report is not retrospectively relabeled
as a proven misread.

A4's nominal guard voltage changed from 1.67715 V in attempt 1 to
1.63816 V in attempt 2 despite the same boot; A3 changed by about 14.11 mV
while A4 changed by about 38.99 mV. A later fixed-output snapshot retained
A4 at 1.63814 V. Thus a single stable ADC offset is not established by the
historical sequential DMM/ADC pairs. Actual REF changes and conversion/path
errors need close-in-time observations. The repeat's raw A4-minus-DMM is
about 3.16 mV, outside the earlier four-record difference range.

The code-1369 bracket and one small centering move to code 1374 are now
archived in the [reference-centering follow-up](../examples/hardware-d01-bringup/2026-10-29/reference-centering-followup/README.md).
The independent DMM point check passed, but a later A4 mean changed by
5.53 mV. A subsequent ten-block fixed-output observation was stable in
its block means; the previously saved local anchors give DRIVE minus REF
from -2.012 to -1.415 mV without a new fit. The operator reported roughly
"+- 0.002", but exact ADC/DMM interval overlap and contact continuity were
not established. Automatic tracking, full-range calibration and physical
repair remain unvalidated. The last recorded held code is 1374; recheck
boot and output state before further hardware work.

The [raw comparison and audit](../examples/hardware-d01-bringup/2026-10-29/README.md)
retain the failed voltage predictions and conditional R/C analysis.


## October 30 execution decision

The ten-block A4 mean span was 0.346 mV. It did not reproduce the earlier
5.53 mV change and cannot identify that earlier change's cause. The DMM
reports do not establish a continuously signed +0.002 V during the full
capture. Do not classify this as either an A4 fault or confirmed REF drift.

Automatic A4-to-DAC tracking stays disabled. Continue the limited engineering
workflow with explicit manual supply/REF checks after wiring or USB changes,
the retained provisional conversion policy, frozen predictions and boot,
timing, saturation and reference guards. A failed guard stops that capture;
do not spend the day pursuing full-range automatic tracking before repair.
The [October 30 plan](2026-10-30-plan.md) prioritizes repair, B1/B6 shunt
comparison and the first actual Spark-directed hardware run.
