# Case 04: publicly intended R2 changes from 22k to available 20k

Before any physical case04 measurement, the operator supplied the actual resistor
inventory. It includes 20k but not 22k. Use one 20k resistor as the intended R2,
OUT–REF; retain intended R1=4.7k, IN–OUT. This changes the nominal unloaded ratio
from 0.823970 to 0.809717. It is a public design amendment, not a hidden fault or
a post-measurement adjustment. No voltage/guard/scoring limit changes.

Keep the original schematic pixels, fresh Spark transcript and its correct
22k extraction unchanged. Record the operator-confirmed 20k amendment separately
before preparing the physical protocol, then supply that amended intended netlist
to the diagnostic Spark context. Do not claim Spark read 20k from the original
image. The original image plus explicit manual amendment are the source; the
image alone is not the complete amended design. A Claude-owned image correction
is requested separately; Codex does not edit those image/source files.

The tentative B30 diode location was superseded before installation confirmation:
B30 is historically obstructed. Use vacant C30 on the same OUT strip instead,
with the striped cathode at D23 (REF). E30 remains reserved for the existing
OUT load jumper. Operator confirmation is required before recording actual
assembly. The circuit's electrical topology is unchanged by this hole choice.

Only the original clean schematic has been sent for intake so far: Spark once,
estimated $0.00552010. All physical measurements remain zero at this amendment.
Any obsolete 22k offline range screen is retained as superseded planning evidence,
never a physical result or a diagnostic training observation.
