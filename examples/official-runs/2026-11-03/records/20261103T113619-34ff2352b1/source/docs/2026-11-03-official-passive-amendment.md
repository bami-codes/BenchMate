# Official passive evaluation, before its first run

This adds an explicit official cohort wrapper after the unloaded, uncorrected
instrument QA passed. The preserved 76 sources and all historical logs remain
unchanged. The wrapper reuses v2 diagnosis, the public 1 kohm input instrument
resistor model, physical acquisition and original electrical/waveform guards.
No fixed-k correction, new sample-RMS limit, firmware upload or voltage-range
expansion is adopted. Existing calibration remains provisional.

The renewed single Arduino GND return and D50–G50 jumper remain in place.
A1=IN, A2=OUT, A3=REF via A23–A45, A4=REF via I50. GND is distinct from REF.
The earlier QA qualifies unloaded instrument operation; it does not establish
loaded DUT accuracy, a diagnosis, or completed repair. Per-capture guards remain
mandatory and failures stop before another stimulus, with no automatic retry.

The operator explicitly resumed hardware on Nov 3 and authorized necessary
paid calls without repeated approval. Planned request counts are disclosed
before each stage; actual usage and estimated cost remain reported. The old
Meta allowance ledger (109 reserved units) is retained. A separate official
ledger records additional authorized use; reservations are not billed dollars.
Initially it authorizes at most 16 requests for the first fault/restored pair,
with the preserved maximum of 8 requests per independent diagnosis. Photo
calls are a separate stage with a disclosed count before execution. No prompt
receives the budget authorization, local case mapping or operator assembly.

Before any official paid request or stimulus, assign and commit the run ID,
slot, intended-design digest and actual protocol/source digests. The selection
policy in `2026-11-03-official-run-policy.json` determines the 12 primary slots;
every failed or interrupted assigned attempt stays recorded. The first attempt
per case/state remains primary regardless of its outcome. No pilot is relabeled.

The model gets only the reviewed intended netlist, common menu and its new
measurement/fit/verification evidence. It chooses every training action. The
two common reserved settings, original 9 mV whole/region scoring, candidate
families, proposal bounds and fitting operations are preserved. New forecasts
and models are committed/pushed before reserved capture; measured IN may then
condition predictions, but reserved OUT is never fitted.

The first read must match the recorded unarmed PING preflight. If the model's
first choice instead needs a load intervention, its USB-off report must be
followed by a boot different from that observed preflight. Later fixture changes
retain the preserved boot-continuity checks. Operator load requests use the
same fixed English choices; no inferred confirmation is accepted.

Diagnosis completes before photos are sent to independent SAM/Spark vision.
Preserve the faulted assembly until its photos are captured. The operator then
restores power-off, and a fresh Spark context runs the same intended design.
`consistent` is displayed as **No mismatch in the tests Spark chose**; reserved
inputs were fixed by the protocol. Keep raw `physical_repair_demonstrated:false`
and link the operator restoration evidence separately.

This version supports the five reviewed passive designs. LED remains disabled
pending its separate adapter and absolute-DC qualification. Its slots stay
pending until that requirement is met. Software inclusion does not establish
six completed physical cases.
