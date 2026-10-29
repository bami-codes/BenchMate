# B1 passive RC preparation — October 29, 2026

The operator reports a separate 170-hole board with R1 between B3–B8
and C1 between D8–D13, and confirms the empty-board strip checks.
The isolated assembled board reads 9.99 kohm from A3–A8 and 0.984
microfarad from A8–A13. Component readings imply about 9.83 ms;
this is a comparison reference, not a measured waveform or an accuracy claim.

USB-off mini-board assembly and fixture hookup are operator-confirmed.
Jumper 15 (C35–C30) is removed. The actual leads are green A35 to mini
A3 (IN), blue D30 to mini A8 (OUT), and gray C50 to mini A13 (RET).
D30 replaces the obstructed B30 contact on the same OUT strip. All three
connections gave continuity; OUT was checked from U2 pin 3. RET–GND
gave no tone. RET is buffered REF, not GND. Fresh powered supply/REF
readings are pending. No hardware command or diagnostic inference is
part of these records.

[Assembly guide](../../../docs/b1-assembly.md) defines the coordinates,
confirmed connections and the limited passive-RC first-power procedure.
[Provenance](provenance.json) lists exact source copies and chain terminals.
Component truth belongs to assembly/evaluation evidence, not a blind
mystery-diagnosis input. No holdout specimen was accessed.
