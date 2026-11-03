# Case04 first physical HOLD: wrong cathode row reported and corrected

The first physical diagnosis child is
`20261103T145152-e948c2e475/diagnosis-faulted/20261103T145652-46ec15c997`.
Spark chose unloaded_step_small, but its first preparatory HOLD failed the
unchanged path checks before any step/sine. One ARM and one HOLD produced512
raw frames, zero qualified diagnostic observations. No automatic repeat occurred.

Raw nominal channel means: IN(A1)=1.451967V, OUT(A2)=0.554740V,
REF(A3)=1.647681V, auxiliary(A4)=1.648421V. Rail checks and the REF checks passed
for this block; the failed checks were HOLD path means, individual sample distance
from REF and channel-mean spread. A single block's zero mean-span is not proof of
long-term REF stability. The generic guard error must not be described as another
3mV REF-drift failure.

The user then reported the diode cathode was actually in E27 instead of E25,
corrected it and reconnected USB. The existing fixture table places the upper
27 strip on board GND. D23–D25 is the intended REF extension. An OUT-to-GND
diode is consistent with an OUT near0.55V and extra current dropping IN across
the public1k instrument resistor. This interpretation is conditional on the
channel map/component assumptions; the reported correction and subsequent guards
are retained separately, without inventing earlier physical verification.

The original assembly seal bound the operator's declared E25 placement, not a
verified physical fact. Preserve that declaration and failed record; the later
E27→E25 correction is a new report. No protocol/guard/firmware/fit threshold changed.
The user chose this wiring correction/reconnect as an alternative to the proposed
unpowered continuity checks or standalone HOLD QA. Neither proposed check was run.

A fresh counted continuation `20261103T150223-18d6f08ac9` reuses the completed
20k schematic extraction with zero extra vision calls. Its new diagnostic model
gets only the same intended4.7k/20k design and new data, never prior measurements,
the correction report or assembly truth. Its original three preparatory HOLD
checks must pass before the selected step can occur. New PING, ten-second wait
and all unchanged guards remain mandatory. Every preceding failure stays counted.

Failed physical-stage usage:2 actual Spark calls, estimated$0.01573015. Case04
cumulative so far:4 Spark (2 schematic,2 diagnostic), no SAM, $0.02832970.
Reading-cohort cumulative:21 Spark +1 SAM, $0.18037550. These are token estimates,
not the SDK's dollar reservations. The corrected continuation is authorized up to
8 diagnostic Spark requests, estimated$0.06–0.12, before its restored rerun.
