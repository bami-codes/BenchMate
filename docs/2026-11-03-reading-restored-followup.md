# Counted restored-only follow-up after corrected IN connection

The first `reading-assisted-v1` pair stays failed, counted, and selected as the
first attempt. Its failed restored HOLD never produced diagnostic samples.
The operator subsequently reported correcting green IN large A37→A35. Removing
the two external resistors while leaving IN at A37 had left the input path
disconnected. That is consistent with the observed A2 settling failure.

The separately frozen 3-HOLD QA passed 1,536 frames after correction. Its A3
block-mean span was 0.218mV with the unchanged 3mV guard. This qualifies only
one-boot HOLD repeatability, not a new waveform diagnosis. Firmware settling,
sampling, guard limits, fits, menu and reserved inputs stay exactly unchanged.

The user selected QA once, then a new restored follow-up if it passed. This
additive runner preserves all 107 original sources and recovery source, snapshotting
its own version before another paid request. Register as **restored-only follow-up
attempt 2**, not replacement success. Include the complete original failed pair
and successful QA inside the new folder, bound by hashes, retaining failures.

Start with an operator-confirmed post-QA USB power cycle and a fresh unarmed
PING preflight. New Spark context receives only the same reviewed intended design
and its new observations. Do not send old diagnoses, assembly truth, pictures,
operator DMM values or QA outputs to that diagnostic model. Spark chooses up to
three training actions; publish predictions before the same reserved inputs.
No automatic repeat after any failed acquisition. Spark max 8, expected $0.06–0.12.

After the diagnostic report, take a new restored photograph. Use the same frozen
generic SAM/body pipeline and one Spark correspondence call. No surface-value
reader. Operator confirms or explicitly overrides the body assignment. Only then
close the follow-up with the native verdict and, if consistent, exactly
**No mismatch in the tests Spark chose**. Never overwrite a native repair claim.

`python -m benchmate verify <follow-up folder>` checks its root event chain and
frozen diagnostic forecasts/order. For the compound case including the embedded
original failed pair, recovery QA, SAM/binding child records and photo artifacts,
use **`python -m benchmate.reading_followup verify <follow-up folder>`**. This
additional command leaves the originally frozen verifier/entry point unchanged.
Both commands are key/network free. Integrity PASS does not prove record creation
time, actual wiring, human assertions or diagnostic success. Show original failure
and follow-up status separately; do not advertise the first pair as successful.
