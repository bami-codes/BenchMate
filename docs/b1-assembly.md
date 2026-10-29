# B1: separate 170-hole RC board

Status, 2026-10-29 Asia/Seoul: operator reports USB disconnected, a separate
white 170-hole board ready, resistor measured outside the circuit at
9.99 kohm, and a 105J100 film capacitor measured at 0.984 microfarad.
The operator subsequently confirms the empty-board topology checks,
assembly, A3–A8 resistance 9.99 kohm and A8–A13 capacitance 0.984 microfarad.
The operator now confirms jumper 15 removal and the three instrument
connections below, made with USB disconnected. IN, OUT and RET continuity
are reported; OUT was checked from U2's actual pin 3, and RET–GND gave
no continuity tone. After USB reconnection the reported supply/REF were
4.88/1.62 V. A fresh boot, REF guards and a 512-frame small-step capture
passed. The fitted effective time constant is 10.11 ms; the component-reading
reference is 9.83 ms. A 5 Hz sine forecast saved before its capture passed
the declared engineering RMS checks without parameter refitting (4.93 mV
overall RMS, +3.96 mV mean difference). The last postcheck confirmed REF
code 1359. This is not full D2 acceptance or separate R/C identification.
See the [evidence](../examples/hardware-b1-bringup/2026-10-29/README.md).

Next setup: the operator reports USB disconnected and an additional
isolated resistor of 9.99 kohm and capacitor of 0.998 microfarad. The
resistor is assigned to the removable output load below. The capacitor
is set aside for D01 preparation, not installed. The operator now confirms
load installation and continuity from its OUT end to U2 pin 3 and from its
REF end to D50. Fresh supply/REF were 4.87/1.627 V. The loaded step forecast
was saved before any loaded ADC block and passed with 2.222 mV RMS;
separate descriptive gain/tau were 0.49852 and 5.093 ms. Final postcheck:
same boot, REF code 1368. The load's REF feed depends on jumper 14.
USB-off preparation of the [D01 capacitor variant](d01-assembly.md) is now
requested, not confirmed; no D01 observation exists yet.

## Coordinates used here

This guide defines coordinates on the **small board**, not the existing
830-hole instrument board. Place the center trench horizontally. In the
upper half, call the five rows A–E from top to bottom and the seventeen
columns 1–17 from left to right. Printed labels in another orientation
do not redefine these coordinates. The lower half is unused.

The layout assumes each five-hole upper column is internally connected,
with different columns isolated. Before inserting parts, check A3–E3
continuity and A3–A8 isolation. If the board does not have this layout or
these checks disagree, resolve its topology before using the table.

## Assembly while disconnected from all power and the instrument

| Part | First lead | Second lead | Role |
|---|---|---|---|
| R1, nominal 10 kohm, reported 9.99 kohm | B3 | B8 | IN to OUT |
| C1, 105J100, nominal 1 microfarad, reported 0.984 microfarad | D8 | D13 | OUT to RET |

Neither part is polarized. Adjust free lead spacing gently if needed;
do not force the capacitor body into a hole pattern it cannot reach.
Keep exposed leads clear of neighboring nodes.

| Reserved contact | Label | Connected node |
|---|---|---|
| A3 | IN | R1 input lead |
| A8 | OUT | R1 output and C1 first lead |
| A13 | RET / REF | C1 return lead; **not board GND** |

```text
IN (A3) ---- R1 ---- OUT (A8)
                       |
                       C1
                       |
                    RET (A13)
```

No extra jumper is needed between B8 and D8: both are in upper column 8.
Label the three contacts IN, OUT and RET. No loose probe posts are needed.

After assembly, while this small board is still isolated:

1. Measure A3–A8 resistance on the 20 kohm range; expect approximately
   the isolated 9.99 kohm report.
2. Measure A8–A13 capacitance on the appropriate microfarad range;
   expect approximately the isolated 0.984 microfarad report.

Both readings and the strip checks were reported before the fixture
connection below. Do not repeat resistance/capacitance measurements
while the instrument is powered.

## Reference values and scope

The reported component readings imply R*C = 9.83016 ms, approximately
9.83 ms. This is a pre-measurement reference for comparison, not an
observed waveform result or a traceable accuracy bound. Meter accuracy
is not established. Keep component truth in assembly/evaluation records;
do not feed the specimen name or component readings into a blind
mystery-diagnosis candidate selection.

## Confirmed fixture connection after mini-board assembly

Keep USB disconnected. Remove **only the C35–C30 calibration jumper
(item 15)** from the large 830-hole instrument board. Keep the B28–B35
shunt bypass (item 11), B50–B23 auxiliary-input park (item 14), input
pull-down and all other fixture wiring in place.

| Signal | Lead color | Large 830-hole fixture | Small 170-hole B1 board |
|---|---|---|---|
| IN | Green | A35 | A3 |
| OUT | Blue | D30 | A8 |
| RET / REF | Gray | C50 | A13 |

The original request used B30 for OUT. The operator used D30 because
B30 was obstructed by a U-shaped jumper. B30 and D30 share the same
upper five-hole strip; U2 pin 3 to the mini-board OUT continuity was
also reported. Historical records retain the original B30 request.

These are three insulated jumper leads. RET goes to buffered REF, never
to the blue GND rail or to 5 V. No loose power-rail probe post is added.

With power still disconnected, verify these three direct connections
using the vacant contacts on the same strips:

1. Large C35 to small E3: continuity.
2. Large C30 to small E8: continuity.
3. Large E50 to small E13: continuity.

Jumper 15 removal and all three connections are now reported complete;
RET–GND also gave no tone. The instruction to retain items 11 and 14
remains in force. These are operator reports, not an independent visual
inspection. Do not interpret in-circuit resistance as a new isolated
component measurement.

Completed first-power check: reconnect Minima USB with the same cable and Mac port. With the
meter black probe on the existing large-board GND contact, measure the
large-board A3 divider-resistor lead (supply, DC 20 V), then D50 (REF,
DC 2 V). These readings were reported before the DAC command.

## Limited first-power scope for this passive B1

This is a known, isolated passive R/C bring-up specimen, not an arbitrary
externally powered circuit. For this specimen only, wiring is performed
with USB off and the next first-power procedure may initialize REF with
the passive R/C already attached. This is an explicit exception to the
general DUT-disconnected ARM workflow: it avoids manipulating live leads
or leaving the OUT buffer input floating during startup. Its 100 V film
capacitor and resistor have no external source. Boot, REF startup and
ARM ramp samples are excluded from experiment data; the input can be
outside REF +/-1 V during this unmeasured startup. Every recorded
stimulus still requires a verified fresh boot, declared limits, settled
REF and the usual capture checks. Do not generalize this exception to
unknown, active, externally powered or holdout circuits.

The first waveform was a small +/-0.2 V step around the configured
REF, a 0.4 V transition within the one-volt jump rule. The proposed 500 us
frame interval and 512-frame block passed this acquisition's timing checks
(497–503 us observed frame intervals, no overruns). A subsequent 5 Hz
sine used 2 ms frames (1991–2011 us observed intervals, no overruns).
These two blocks do not establish a general sample-rate or frequency limit.
A4 and remaining D2 checks are still incomplete. The result is first
RC-response verification, not a confirmed mystery diagnosis or repair.

## Confirmed removable load — first powered check complete

Use vacant upper-half columns 55 and 60 on the **large 830-hole board**.
Keep the mini-board components and all existing fixture leads unchanged.
Jumper 15 remains absent; 11 and 14 remain installed. The new resistor
connects OUT to buffered REF, electrically parallel with B1's capacitor.

| Added item | First contact, large board | Second contact, large board | Role |
|---|---|---|---|
| Nominal 10 kohm resistor, isolated report 9.99 kohm | D55 | D60 | Removable output load |
| Insulated jumper | E30 | A55 | OUT to load |
| Insulated jumper | C23 | A60 | REF to load |

E30 shares the OUT strip with D30 and A30. C23 shares the REF strip with
B23, which remains connected to B50 by jumper 14.

**Jumper 14 dependency:** keep B50–B23 installed while this load uses
C23–A60. Before removing jumper 14 to use the auxiliary probe, disconnect
USB and move the C23 end of the load's REF lead to a confirmed direct REF
distribution contact. Verify continuity from the D60 load lead to D50
again and record the new contact before powering up. Merely removing
jumper 14 disconnects the load from REF; C23 is then the auxiliary-input
node, not a valid load return. No such rerouting is requested or reported
in the present step.

Upper columns 55/60
are terminal strips, not the split power rails. Keep exposed resistor
leads clear of adjacent nodes. If a specified contact is obstructed, stop
before moving existing leads and record the chosen alternative.

With USB still disconnected, check continuity from the D55 resistor lead
to U2's actual pin 3 (F22), and from the D60 resistor lead to the D50 REF
jumper. The 9.99 kohm load itself should not be expected to give a direct
continuity tone between its ends. Do not reinterpret a loaded, in-circuit
resistance as the previously isolated component reading. The operator
reported both continuity tones with USB disconnected. Reconnection with
jumper 14 retained and the fresh supply/REF report preceded the loaded
prediction freeze, new-boot REF guard and step capture.

For this known B1 and two reported equal 9.99 kohm resistors, the ideal
loaded small-signal gain is 0.5 relative to REF. The component-reference
time constant is (R || Rload)*C = 4.91508 ms. Scaling the previously fitted
effective unloaded tau by the same divider factor instead gives 5.05659 ms.
These are separate reference calculations. The later descriptive loaded
fit gave tau=5.093 ms and gain=0.49852. The full voltage forecast was saved
before loaded acquisition and scored without refitting. This known-specimen
engineering comparison must not be presented as blind diagnosis; the
separate conditional R/C estimate assumes the RC topology.

The spare 0.998 microfarad capacitor is not part of this load check. Its
parallel sum with B1's reported 0.984 microfarad would be 1.982 microfarad
for a later D01 preparation; no such modification has been reported.
