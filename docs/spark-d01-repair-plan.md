# Spark-directed physical D01 repair — due before November 2

This is a required future execution, not a completed result. October 30's
physical Spark run diagnosed C change and checked a reserved sine; it did not
perform repair. The earlier capacitor-removal evidence came from a scripted
engineering check. Neither record may be relabelled as Spark-directed repair.

Target: complete and retain one real Spark-directed diagnosis → repair request
→ pre-repair prediction freeze/publication → operator repair → new measurement
→ reserved verification by November 1 evening, before November 2 (Asia/Seoul).
October 31 morning is unavailable. B5 remains first; do not disturb its fixture
or same-boot validation to make the repair footage.

1. After B5 ends, explicitly prepare and confirm the known D01 fixture with
   original and added parallel capacitors. Do not assume the old D01 assembly
   remains installed; the current confirmed preparation has both capacitors out.
2. Let Spark select new observations, distinguish the declared R/C alternatives,
   and request the intervention. Do not attribute an engine-scripted replacement
   choice to the model. Keep operator-only assembly coordinates out of model input.
3. Before disconnecting power, save and push the model's expected post-repair
   behavior and command-input forecast, with a separate measured-IN comparison
   rule. Parameters and scoring must be fixed before new post-repair output.
4. Relay the exact USB-off intervention to the operator, receive a fresh matching
   confirmation, and require a new boot. The fixture's new boot gets new guards;
   old DMM biases or HOLD origins are not reused as fresh measurements.
5. Measure the response and an unused waveform. Preserve both forecast and
   conditional scores, failures, abstentions and actual Spark wording.

Implemented November 1: `scripts/physical_d01_repair.py` now composes the shared
diagnosis tools with a published prediction, a matching USB-off repair report,
a required new boot and two fixed repair checks. The scripted mock and injected
failures are retained in [the rehearsal archive](../examples/d01-repair-rehearsal/2026-11-01/README.md).
This is zero-API software validation, not an actual Spark repair.
The [operator guide](d01-repair-operator.md) and frozen 8-request medium plan are ready.
An actual reviewed intended schematic, fresh D01 hookup report and authorization
for the new physical Meta scope remain necessary before running.
The older `physical_spark_rc.py` remains diagnosis-only.

Video may show the existing D01 diagnosis now. Reserve the repair scene until
this new record exists. Claude's script is separate; the artifact link could not
be retrieved by the web reader in this session, so no script-content review is
claimed here.
