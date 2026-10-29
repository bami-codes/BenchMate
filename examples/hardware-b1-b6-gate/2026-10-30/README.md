# B1/B6 physical gate — protocol frozen, no gate captures yet

The operator removed the E30-A55 OUT-load jumper with USB disconnected and
reported a separate shunt of **996 ohm**. The 9.99 kohm resistor and its REF
return remain installed but disconnected at the OUT end.

The [common plan](plan-freeze/20261029T161106-4d79e30804/plan.json) is fixed before all
four conditions: B1 bypass, B6 bypass, B6 with shunt, B1 with the same shunt.
Both alternatives share the same measured-IN conditional OUT response, with
tau **10.15948 ms** fixed from the earlier pre-repair estimate and the
nominal repair C. Two settled step levels yield the A3-minus-A1 contrast.
The branch-plus-shunt model predicts **0.09066084 times measured DRIVE
excursion**, about **36.264 mV** for 0.4 V drive excursion;
the no-branch model predicts zero. Limits and control comparisons are frozen.

This is a known-passive, two-alternative engineering check, not full five-family
blind diagnosis, two independent DC captures or a calibrated detection limit.
The smaller +/-0.2 V stimulus is reported explicitly; the registered ideal
+/-1 V contrast of 181.8 mV is not being claimed here.

First requested state is restored B1 with jumper 11 retained and no load/input
branch. New shunt installation and later rewiring require their own USB-off
confirmation. All four conditions remain pending.
