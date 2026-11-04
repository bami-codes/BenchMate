# Case03: a two-resistor timing chain, using the common v4 timing model

Next after the completed05 followup, in retained order01,04,02,05,03,06.
The operator has disconnected USB and retained the05 restored board. No03
stimulus or paid request has occurred before its new registration/publication.

Fresh schematic: `examples/netlist-diagnosis/designs/2026-11-02/design-03.png`.
Expected intended topology is R1 10kΩ IN-N1, R2 10kΩ N1-OUT, C1 1µF OUT-REF;
the fresh Spark reading and operator review, not this expectation, become the
reviewed design. The private case map is never read or sent to models.

Planned fault: R1 2.2kΩ in place of10kΩ; R2 remains10kΩ, C1 remains105/1µF.
Both resistors are in the photographed mini-board. This is a bounded passive
timing-chain reproduction of the forum mechanism, not a full555-chip experiment.
Terminal IN/OUT can measure the sum, not uniquely which series resistor changed.
For nominal20kΩ/1µF and fault12.2kΩ/1µF, unloaded time constants are20/12.2ms;
with9.99kΩ output load they are6.66/5.49ms. Both are within the retained range.

Proposed USB-off changes minimize05 wiring moves: remove W1 B3-B8 and replace
it with2.2kΩ R1; leave existing10kΩ E8-E13 as R2. N1 is mini column8. Move
white REF A13→A17 first, then blue OUT A8→A13. Move the old C1 C8 end→C17,
retaining its C13 end, so C1 is C13-C17. Green IN stays mini A3 to large A35.
The large-board instrument1kΩ, A3/A4 REF/GND and no-load/bypass configuration
stay. External20kΩ and the old diode remain absent. Final wiring requires actual
operator confirmation; no hole may be silently reused by two leads.

The already qualified common passive numerical backend is frame-anchored v4,
source/session/qualification published in7675361. Every R/C/D/W hypothesis,
structure fit and training-only reading profile uses that same backend.
Existing107-source freeze, A3 raw3mV, A4 auxiliary role,9mV whole/region scoring,
at-least10s after a fresh unarmed boot, current/voltage/timing bounds remain.
No firmware, gain/k/offset correction or hidden source-impedance fit is introduced.

Workflow: fresh image transcription → review → fault assembly → Spark-chosen
measurements and frozen/published reserved verification → Spark-selected useful
component/quantity → source-specific reading ranges frozen/pushed before photo
or value → actual whole-board photo → generic SAM once → Spark v3 candidate
bodies/kinds and nullable individual correspondence. Operator confirms an actual
model correspondence, never supplies a label based on the known fault. Explicit
operator-confirmed port colors/positions may aid correspondence, without values.
If bodies remain ambiguous, preserve the complete candidate set and qualify an
unordered-group observable before readings; do not force a reference name.
No Spark surface-value candidate or resistor-band reading is used.

After an isolated power-off operator reading and deterministic source/range score,
open the sealed assembly; restore R1 to10kΩ; run a fresh Spark context and the
same reserved settings. The mini-board changes in this repair, so retain a new
restored photograph and generic SAM for the visual before/after record. If the
restored verdict is consistent, no suspicious component is singled out: skip
another Spark body/value request prospectively, with SAM explicitly display-only.
Caption: **No mismatch in the tests Spark chose**. Original failures and first-
attempt selection are preserved; any paid/hardware failure stops before retry.

Stage adapters/catalog and compound audit are versioned and published before
their first paid/physical/reading use, without modifying frozen modules. The
current start scope fixes this route before schematic intake; it does not claim
that future data or a physical outcome already exists.

Planned pair maximum:19 Spark (8 per diagnosis plus schematic, reading choice,
and fault photo correspondence),2 SAM, estimated$0.15-0.30 from prior usage.
First paid stage: schematic Spark1, estimated$0.005-0.02. Standing necessary-call
authorization applies; exact recorded usage is reported and ledgers preserved.
