# Case05: direct input/output wire and parallel decoupled load

Next in the retained order01,04,02,05,03,06. The operator confirmed USB off,
case02 restored mini-board10k B3-B8,20k D8-D13,105 C8-C13,104 E8-E13 and no
C30-A55 output-load jumper. Do not move anything until the fresh schematic
transcription and explicit power-off wiring table are provided.

Fresh intended image: `examples/netlist-diagnosis/designs/2026-11-02/design-05.png`.
Spark reads only the clean drawing. Its R/C schema deliberately does not emit
an ideal wire: the visible IN-OUT connection is added as W1 by operator review,
keeping original image reading and alias ambiguities. No private case map,
assembly truth, prior results or operator readings enter model input.

Planned intended board: W1 IN-OUT, R1 10k and C1 1uF both OUT-REF. Proposed
power-off changes, subject to operator confirmation of the fresh reading:
move the existing10k from B3-B8 to D8-D13, replacing20k; keep105 at C8-C13;
remove104 E8-E13; install a short W1 jumper B3-B8. Reuse the removed20k on the
large board E35-E31; move the green IN lead's large-board end A35 to A31,
keeping its mini A3 end. This resistor is after the measured IN, outside the
photographed mini-board. Keep C30-A55, A55-C35 and the old diode absent. Keep
the instrument1k, A3/A4 REF and new GND return unchanged.

The20k fault severity is chosen before any new measurement; it differs from
the earlier10k software example, which remains a simulation. With10k load and
1uF, nominal fault time constant is about6.67ms unloaded and4.00ms with9.99k
extra load; DC gain about1/3 and1/5 respectively. This is a deliberately
exaggerated series-impedance reduction, not the original forum's5V power supply.
When W1 is ideal, its parallel R/C values cannot be identified from conditional
OUT given measured IN. Only all-inadequate value fits permit a genuine Spark
structural proposal. Experiments and topology are chosen by Spark, not a script.

Preserve the107 frozen sources, raw A3 primary3mV guard, A4 auxiliary-only role,
the common1k drive resistor,9mV whole/regional scoring and at least10s after a
new confirmed unarmed boot. No firmware, voltage or threshold change.

Physical localization is separate from terminal structure support. If a useful
wire-versus-external-path ambiguity remains, qualify an isolated power-off W1
resistance observable and training-only forecast profile before its reading;
do not force an unrelated R1/C1 reading. Numeric wire resistance is not a
beeper threshold, a marking or proof from a missing SAM mask. Any stage adapter
and compound auditor are versioned/published before use; setup declaration does
not claim this future qualification is already implemented.

After diagnosis, use an actual new fault photograph, one generic SAM request,
then one v3 Spark body-candidate/kind request with nullable individual mapping.
Retain all raw masks. After an external-only repair, a consistent fresh-context
rerun does not require another mini-board picture if the operator confirms its
components/layout are unchanged. Caption: **No mismatch in the tests Spark chose**.

Announced planned maximum:19 Spark(8 per diagnosis plus schematic, reading
selection and photo candidate selection),1 SAM, approximately$0.15-0.30 based
on prior usage. First paid stage is only schematic Spark1, about$0.005-0.02.
Standing necessary-call authorization applies. Actual usage is reported; paid
or hardware failures are retained and stop before another attempt.
