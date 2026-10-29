# D01 controlled capacitor-value fault — assembly confirmed

Status, 2026-10-29 Asia/Seoul: **two D01 loaded development attempts are
retained**. The first used reported REF 1.649 V: C-point whole RMS 8.44 mV
but early-region checks failed; R-point RMS 37.43 mV. The operator then
reported D50 REF / D45 DRIVE / C9 divider = 1.635 / 1.645 / 1.635 V.
Whether the earlier value was misread or REF changed remains unresolved.
Lowering REF at fixed IN lowers the prediction; it does not itself explain
away the first positive residual.

At the user's request a second pair of voltage predictions was saved
before any new ADC. The latest supply estimate 4.89 V was retained (not
remeasured), REF changed to 1.635 V, and the same boot/output 1381 was
verified before explicitly changing the park code to **1369**. On this
new capture the C-change representative passed whole and every regional
check: **5.65 mV RMS**. R-change failed at **27.64 mV RMS**. No calibration,
model parameter, phase or offset was refit for either score. This is a
second development attempt, not a first-attempt or holdout success.

The separate repeat fit gives gain 0.49579, tau 10.239 ms and conditional
R 10.159 kohm / C 2.033 uF. The loaded observations favor increased C
within the declared RC alternatives. No Spark diagnosis, physical repair,
full-family posterior or full D2 acceptance is claimed.

Same boot `a09aa39f4755ba059967f31ac9221cd3`, REF code 1369 remains held.
Extra C, OUT load, jumper 11 and jumper 14 are unchanged. A no-output-change
ADC snapshot has been saved, and REF/DRIVE/OUT/REF DMM readings are requested
to check A4 and path alignment before repair validation. No extra part or
wiring change is requested. [Records](../examples/hardware-d01-bringup/2026-10-29/README.md).

## Coordinates and parts

The existing white 170-hole mini-board stays in the same orientation:
center trench horizontal, upper rows A–E top to bottom, lower rows F–J
starting with F nearest the trench. Columns 1–17 run left to right on
both halves. These are mini-board coordinates unless explicitly marked
as the large 830-hole fixture.

Keep the original R1 at B3–B8 (reported 9.99 kohm), C1 at D8–D13
(reported 0.984 uF), and the three IN/OUT/RET leads unchanged.

## Confirmed USB-off changes

Disconnect Minima USB and wait until the power LED is off.

| Action | First contact | Second contact | Purpose |
|---|---|---|---|
| Remove this whole jumper | **Large board E30** | **Large board A55** | Disconnect the output load from OUT |
| Add spare 1 uF film capacitor, reported 0.998 uF | Mini I8 | Mini I13 | Add capacitance in parallel with C1 |
| Add insulated jumper | Mini E8 | Mini F8 | Existing OUT to lower column 8 |
| Add insulated jumper | Mini E13 | Mini F13 | Existing RET to lower column 13 |

Keep the large-board load resistor D55–D60 and its REF lead C23–A60 in
place. The load's OUT end is floating once E30–A55 is removed. Keep
jumper 14 (B50–B23): the load return still uses that REF path. Jumper 15
remains absent and shunt bypass 11 remains installed. Do not confuse the
mini-board column 13 RET with the large-board column 13 DAC input.

If E8 or E13 is obstructed by the original capacitor, do not force a lead
under it or move original parts. Report the obstruction before choosing
alternative contacts. Keep the added capacitor's exposed leads clear
of other nodes; this film capacitor is not polarized.

With USB still disconnected, check continuity between the **actual metal
leads** of the original and added capacitors: D8 to I8, and D13 to I13.
These are same-node continuity checks, not a resistance or capacitance
measurement across a capacitor. Report jumper removal, added parts and
both continuity results. The operator's report was: "USB 분리 / 부하 점퍼 제거 /
추가 C 설치 / 8열 삐 / 13열 삐". No alternate holes were reported.

The operator then reconnected USB and reported "USB 연결 / 4.88V / 1.635V".
The requested contacts were large-board A3 supply on DC 20 V and D50 REF
on DC 2 V, both against the existing blue-rail GND contact. These fresh
readings, rather than the earlier B1 values, configure the next acquisition.
Fresh-boot identity and a REF capture guard subsequently passed for the
unloaded block. Any later reconnection requires new checks.

## Meaning and limits

For the reported installation, the reported capacitor sum is 1.982 uF.
Together with the reported 9.99 kohm resistor this gives a component-reading
reference tau of 19.80018 ms. This is not a waveform measurement or a
meter-accuracy claim. The intended design remains nominal 10 kohm/1 uF.

This is a controlled fault-injection specimen. Assembly truth stays in
assembly/evaluation records and must not be supplied as a diagnosis input.
A no-load waveform may identify tau but cannot distinguish a resistor
increase from a capacitor increase. A later load condition is required
to separate those possibilities under the RC assumption. Any voltage
prediction or repair result must be saved before its corresponding
observation; the new observations must not silently refit that prediction.

The eventual physical repair can remove only the added I8–I13 capacitor,
preserving the original C1 and R1. That action has not yet been requested
or performed. No new topology-selection capability, full D2 acceptance,
or automated hardware diagnostic result is implied by this assembly guide.

## Next experiment order, fixed before D01 acquisition

1. Capture the unloaded response and report what it identifies. A changed
   time constant alone cannot decide between R and C faults.
2. With declared nominal design knowledge only, freeze both fault
   alternatives' predictions before the output-load observation. Use the
   measured fixture load value, not the specimen's assembly truth, to
   separate the alternatives. Full D2 uncertainty remains pending.
3. If the observations support a repair, freeze the repaired response
   before requesting removal of the extra capacitor, then acquire the
   post-repair checks without refitting. Count every physical capture.
4. Once the original B1 is restored, perform the B1/B6 input-branch gate
   below. Do not leave the doubled capacitance installed and call that B6.

The physical gate is still pending; the existing five-family B1/B6
regression uses synthetic observations. D01-first sequencing does not
replace the registered H3/D3 check.

## Planned B1/B6 gate — no further wiring requested yet

All future changes are USB-off and require explicit hookup confirmation,
fresh boot checks and the same provisional calibration policy. Keep jumper
14 throughout: the resistor's C23–A60 return depends on B50–B23.

| Order | Specimen | Series path | D55–D60 resistor role |
|---|---|---|---|
| 1 | Restored B1 | Jumper 11, B28–B35 | Disconnected at its 55-column end; no output load |
| 2 | B6 | Same jumper 11 | Planned A55–C35 lead connects IN to the resistor; C23–A60 stays at REF |
| 3 | B6 | Replace jumper 11 with a separately measured nominal 1 kohm shunt | Same IN–REF branch |
| 4 | Restored B1 | Same measured shunt | Remove the A55–C35 branch lead; no output load |

Remove the entire E30–A55 OUT-load lead before installing any IN-branch
lead. Never bridge OUT and IN through both leads. The same resistor can
serve as a load or an input branch, but not both at once. Before installing
the shunt, measure it outside the circuit and confirm the chosen holes;
do not remove any of the three ADC series resistors. Jumper 11 must be
absent with the shunt installed, or it would bypass the current measurement.

For both specimens use the same candidate families, acquisition settings,
measurement access and budgets; specimen IDs and component truth stay
outside diagnosis. Without the shunt, compare measured IN and OUT and
report the unresolved input-branch alternatives if the observations support
both. The ideal model's equality is not a promise of bit-identical physical
traces from a nonideal driver.

With the shunt, compare settled, time-aligned A3 (DRIVE) minus A1 (IN),
using their calibrated paths and the measured shunt resistance. Capture
both drive levels for both specimens and retain the B1 differential
baseline and its spread; do not classify from a single uncorrected ADC
difference. Predeclare levels and detection limits before the comparison.
The registered 181.818 mV two-level separation assumes ideal 10 kohm/1 kohm
and +/-1 V drive. It is not an observed value or a target to force by
adjusting settings. Intermediate REF returns keep each commanded change
within 1 V. Any narrower physical stimulus must be reported with its own
prediction. This first engineering comparison will not establish the later
repeated-run success target by itself.

## Limited passive startup exception

This confirmed configuration contains only the existing isolated passive
R/C and the added parallel film capacitor, with no external power source.
The B1 USB-off hookup exception also applies to this known passive variant:
initialize REF with it attached, excluding startup and ARM-ramp samples
from experiment data. The unmeasured startup may be outside REF +/-1 V;
recorded stimuli retain the ordinary limits and fresh-boot/REF checks.
This exception does not authorize unknown, active, externally powered or
holdout circuits. The first small step uses the previously exercised
+/-0.2 V command, 512 frames and a 500 us target interval. No individual
R/C fault conclusion follows from this first observation.

## First unloaded result and subsequent intervention

The unconstrained exponential fit reads the waveform and provisional
calibration only. It uses neither the measured specimen R/C values nor the
assembly instructions. Tau is **20.3227 ms**; the first-50-ms sensitivity
fit gives **20.2964 ms**. Regional RMS is retained alongside the full
**2.003 mV** training-fit RMS, including an 18.97 mV maximum residual.
This is not an independent forecast score.

Two conditional loaded feature predictions are now frozen from that tau,
the declared nominal 10 kohm/1 uF design and the measured 9.99 kohm fixture
load. The illustrative C-change point predicts gain **0.49975**, tau
**10.1563 ms**; the R-change point predicts gain **0.32957**, tau
**6.6976 ms**. Repair-prior ranges conditioned on this point tau give gain
0.48755–0.51257 versus 0.30672–0.35096. These are conditional model ranges,
not posterior probabilities or noise/calibration confidence intervals.
The full voltage forecasts and engineering checks were subsequently frozen
after fresh supply/REF readings and before any loaded ADC data. Their
failed checks are retained separately from this conditional feature forecast.

Next requested wiring: USB off; reconnect **large E30–A55 only**, retain
the added capacitor and all other wiring, including jumper 14. Check
D55 load lead to U2 actual pin 3 (F22), and D60 load lead to D50. Report
both results and leave USB disconnected. The operator now reports "USB 분리 / 부하 점퍼 재연결 / OUT 삐 / REF 삐".
Fresh supply/REF of 4.89/1.649 V was reported; loaded acquisition and the
failed voltage checks followed as summarized above. See the
[raw records and graph](../examples/hardware-d01-bringup/2026-10-29/README.md).

## Meter-free centering proposal

The [ADC reference-tracking review](reference-tracking.md) distinguishes
shared-reference ratio control from validated physical centering. Raw A4
is not substituted for this run's REF. Four existing sequential comparisons
show raw A4 estimates 18.4–28.1 mV above the DMM reports; drift and A4
calibration remain confounded. No automatic-control or calibration change
has been made. The failed run remains available even if a future control
revision improves a newly acquired observation.
