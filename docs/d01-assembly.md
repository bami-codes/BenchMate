# D01 controlled capacitor-value fault — assembly preparation

Status, 2026-10-29 Asia/Seoul: assembly is requested, not yet confirmed.
B1 has passed an unloaded step/sine engineering check and a frozen loaded
step prediction check. The next action is USB-off preparation of a known
capacitor-value fault, using the spare capacitor reported as 0.998 uF.
No D01 capture, diagnosis or repair has occurred.

## Coordinates and parts

The existing white 170-hole mini-board stays in the same orientation:
center trench horizontal, upper rows A–E top to bottom, lower rows F–J
starting with F nearest the trench. Columns 1–17 run left to right on
both halves. These are mini-board coordinates unless explicitly marked
as the large 830-hole fixture.

Keep the original R1 at B3–B8 (reported 9.99 kohm), C1 at D8–D13
(reported 0.984 uF), and the three IN/OUT/RET leads unchanged.

## Requested USB-off changes

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
both continuity results. Do not reconnect USB until the next power check
is requested.

## Meaning and limits

If installed as requested, the reported capacitor sum is 1.982 uF.
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
