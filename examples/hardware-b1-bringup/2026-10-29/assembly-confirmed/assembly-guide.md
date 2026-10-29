# B1: separate 170-hole RC board

Status, 2026-10-29 Asia/Seoul: operator reports USB disconnected, a separate
white 170-hole board ready, resistor measured outside the circuit at
9.99 kohm, and a 105J100 film capacitor measured at 0.984 microfarad.
The operator subsequently confirms the empty-board topology checks,
assembly, A3–A8 resistance 9.99 kohm and A8–A13 capacitance 0.984 microfarad.
USB remains disconnected. Instrument connection is now requested below;
it has not yet been reported complete. No hardware commands have been
issued for this assembly step.

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
Label the three contacts IN, OUT and RET. No loose probe posts or
instrument leads need to be installed yet.

After assembly, while this small board is still isolated:

1. Measure A3–A8 resistance on the 20 kohm range; expect approximately
   the isolated 9.99 kohm report.
2. Measure A8–A13 capacitance on the appropriate microfarad range;
   expect approximately the isolated 0.984 microfarad report.

Report both displayed readings and whether the parts fit without
touching another node. Do not reconnect USB or connect the instrument yet.

## Reference values and scope

The reported component readings imply R*C = 9.83016 ms, approximately
9.83 ms. This is a pre-measurement reference for comparison, not an
observed waveform result or a traceable accuracy bound. Meter accuracy
is not established. Keep component truth in assembly/evaluation records;
do not feed the specimen name or component readings into a blind
mystery-diagnosis candidate selection.

## Requested fixture connection after confirmed mini-board assembly

Keep USB disconnected. Remove **only the C35–C30 calibration jumper
(item 15)** from the large 830-hole instrument board. Keep the B28–B35
shunt bypass (item 11), B50–B23 auxiliary-input park (item 14), input
pull-down and all other fixture wiring in place.

| Signal | Large 830-hole fixture | Small 170-hole B1 board |
|---|---|---|
| IN | A35 | A3 |
| OUT | B30 | A8 |
| RET / REF | C50 | A13 |

These are three insulated jumper leads. RET goes to buffered REF, never
to the blue GND rail or to 5 V. No loose power-rail probe post is added.

With power still disconnected, verify these three direct connections
using the vacant contacts on the same strips:

1. Large C35 to small E3: continuity.
2. Large C30 to small E8: continuity.
3. Large E50 to small E13: continuity.

Confirm jumper 15 removal and the three continuity results. Do not
reconnect USB until that connection report is received. Do not interpret
in-circuit resistance as a new isolated component measurement.

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

The first intended waveform is a small +/-0.2 V step around the configured
REF, a 0.4 V transition within the one-volt jump rule. A proposed 500 us
frame interval and 512-frame block must pass actual timing checks before
use; this is not a claim that this sample rate has already been validated.
A4 and remaining D2 checks are still incomplete. The result is first
RC-response verification, not a confirmed mystery diagnosis or repair.
