# Current prospective protocol — October 30, unloaded ADC revision

The historical DMM-anchored attempts below are retained unchanged. Before any
physical B5 diode observation, the user agreed to an unloaded same-boot protocol
with no DMM-voltage pause. Use [b5-unloaded-v2.md](b5-unloaded-v2.md) and the
[operator guide](b5-operator.md) for the next execution. Original loaded
extrapolation checks remain pending. Current power-down has not been confirmed.

# B5 preparation and resistor-only range control — October 30, 2026 KST

Status: prospective preparation; no B5 diode capture or structure-discovery run
has occurred. The previous physical D01 run is complete and preserved. Do not
reuse its RC-only controller as a nonlinear discovery controller.

## Starting point and reversible removal

The last confirmed state has the original mini-board R at B3-B8, original C
at D8-D13, added C at I8-I13 and bridges E8-F8/E13-F13. Large-board OUT load
lead E30-A55 is installed; IN branch A55-C35 and the 996 ohm shunt are absent.
Jumpers 11 B28-B35 and 14 B50-B23 are retained. The load resistor D55-D60 is
9.99 kohm with its C23-A60 REF return. Final D01 boot was
`4faed097aeda0ad9efdd84b22dd1ba4e`, parked at command code 1371.

With USB disconnected and LED off, remove both capacitor leads from D8-D13
and both from I8-I13, and remove both ends of E30-A55. Keep the resistor,
all three DUT leads, mini bridges, jumpers 11/14 and the remaining fixture.
This yields a resistor-only control. No diode is inserted at this stage.

Check the bag identifies a 1N4148. Test that loose part in diode mode in both
probe directions and record the displayed values verbatim. A one-point meter
test is an identity/polarity/health check, not an IS/N fit or a precise physical
threshold measurement. The tested part is kept outside the circuit until the
range control passes. The DO-35 cathode marking is a band; the cited Vishay
part uses a black band ([manufacturer data](https://www.vishay.com/docs/81857/1n4148.pdf),
document 81857, Rev. 1.6). The actual supplied manufacturer is not yet confirmed.

The eventual B5 design remains 10 kohm IN-to-OUT plus one diode with anode at
OUT and cathode at REF, no capacitor. Proposed contact pair after control:
mini D8 (unbanded/anode) to D13 (banded/cathode). This is an assembly plan,
not an instruction to install it before the control result. Assembly truth
stays outside subsequent Spark inputs. X1/X2 assemblies have not been opened.

## Why a separate range/bias check is required

The successful physical RC run checked incremental response around a separate
HOLD origin. A nonlinear diode model depends on actual IN-minus-REF and
OUT-minus-REF bias. Subtracting both origins and silently declaring them zero
would change that physical problem. A resistor-only control also checks whether
the fixture itself introduces clipping or amplitude-dependent error.

After reconnection, obtain fresh supply and REF readings before the first ARM.
Require a new unarmed boot, apply one REF ARM and pass a stationary guard.
While held there, obtain independent DMM IN-minus-REF and OUT-minus-REF readings.
Collect three subsequent HOLD blocks and freeze channel offsets from those
means plus the reported physical differential readings. Retain provisional
channel gains, scaled only by the newly reported supply ratio; never fit gain
or offset from scored waveform OUT. A4 is a stability guard, not an absolute
bias calibration or a DAC servo. A fresh fixture/boot needs a new bias anchor.

The 9 mV whole/region allowance and 3 mV stationary/A4 span are retained as
development engineering checks, without a calibrated confidence interpretation.
The resistor-only prediction is OUT-minus-REF = measured IN-minus-REF, using
each measured input command frame. Any DC difference in the independent DMM
anchor remains in the residual; it is not subtracted to force agreement.
Also compare measured IN with the prior frozen driver-volts-per-code map,
anchored at the independent DMM bias. Apply the same 9 mV whole/region limits
without fitting a new slope from the waveform. This catches drive clipping
even when OUT faithfully follows a distorted IN.

## Prospective first physical amplitudes

The original synthetic B5 example uses +/-1.0 V. Before collecting any B5
observations, choose **+/-0.8 V** as the first physical development large-signal
condition to retain voltage headroom. This is a declared revision while physical
conditions are still unvalidated; it is not a success at the original +/-1.0 V.

Resistor-only control order:

1. 1 Hz, +/-0.2 V sine, 512 frames at 4 ms (2.048 s).
2. +/-0.5 V step, 512 frames at 0.5 ms (one transition <=1 V).
3. 1 Hz, +/-0.8 V sine, 512 frames at 4 ms.

Each waveform returns to REF and requires a HOLD guard. Stop on a failed
electrical, timing or whole/region tracking check before the next waveform;
retain all raw samples and attempts. No retry, firmware change, threshold
adjustment, fitted OUT offset or automatic re-arm is permitted in this control.
This phase makes **zero API calls**.

Subsequent B5 training is planned as the 0.5 V step, 0.2/0.8 V 1 Hz unloaded
sines and a 0.8 V 1 Hz sine with a separately measured nominal 4.7 kohm load.
Reserve the +/-0.35 V step and +/-0.8 V 1 Hz sine with the existing 9.99 kohm
load. Both models/topologies and input processing must freeze before either
reserved B5 observation; neither is used to fit the proposal. A control-only
range pass does not count as B5 training, discovery, independent verification,
full D2 or the November 1 repeated-run/X1 development gate.

## Subsequent operator report: stop the manual bias workflow

The operator reported fluctuating, nonrepeatable IN-minus-REF and OUT-minus-REF
meter readings and requested that repeated measurement work stop consuming the
hackathon schedule. The three attempts are [preserved together](../examples/hardware-b5-preparation/2026-10-30/range-control/README.md).
No scored range waveform or diode observation occurred. The old -8/-8 mV report
was not transferred to the later boot. Cause, fluctuation magnitude and precise
timing remain unknown; the report does not prove ADC or REF failure.

The preceding procedure is retained as history, not an active request to keep
measuring. The waiting process has terminated. Power-down was requested but not
confirmed. Work has moved to reviewable existing physical evidence and offline
B5 integration; physical nonlinear verification remains pending.
