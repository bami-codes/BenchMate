# Case02 new restored diagnosis after one passing fresh-boot QA

New counted continuation: `runs/reading-cohort/20261103T182550-4ea22cc3a0/`.
Export: `examples/reading-restored-v2/2026-11-04/records/20261103T182550-4ea22cc3a0/`.
The operator selected **새 복원 후속 진단으로 진행 (추천)** after receiving the
passing QA report. This is a new attempt, never a reopening or replacement.

Unchanged executable: `reading_restored_v2`, with the original107-source engine,
guards, menu, calibration, firmware, ten-second wait and score. No new production
code or numerical rule is introduced. No tests are rerun for a data-only
registration; unchanged source hashes and three independent record audits are
checked instead. All source snapshots in the registration still match.

The original failed fault/photo pair and completed isolated-capacitance supplement
are inherited as in the previous restored continuation. The new parent additionally
records `post_QA_followup_context`, retaining the directly preceding failed restored
run `20261103T175520-a925a3910d`, head
`5efae7dc9a4df5e1d004bd476e991f78b98044db4b69a338d3cd0f212c94e59e`, and the
completed QA `20261103T181948-1a4c8ff1d2`, head
`f31a59a7945e10b6fa26c6adbde88c1c36b16edc3497f6bfc6f1502da88cf191`.
Both audits passed; their substantive outcomes remain failed and QA-passed.
The original first selected attempt and all failed attempts remain counted.

The previous actual restoration declaration (`완료`) is reused as a historical
confirmation of the unchanged specimen. It is **not a newly received restoration
or USB reply**; no second component replacement is claimed. QA itself was selected
and executed without wiring changes. A new actual USB-reconnection confirmation
is still required before preflight, and the initial operator report is created
only after that reply. Native registration retains its original fault-ancestry
boot field. Orchestration additionally requires the new preflight boot to differ
from QA boot **8ac568f48501d20bc0c1178c3c4d8024**, before starting diagnosis.
This check is explicit in the hash-chained context; it does not edit the old runner.

Retain 105/1uF mini C8–C13, same104 E8–E13,10k B3–B8,20k D8–D13, green IN large
A35→mini A3, common1k instrument path and all REF/GND/measurement wiring. Load
C30–A55, A55–C35 bypass and diode remain absent. A new unarmed PING-only preflight
sends no stimulus. The native diagnosis then chooses training experiments through
fresh Spark, and publishes its frozen predictions before both reserved captures.
No prior diagnosis, QA waveform, isolated reading, assembly or photo is supplied
to the new diagnostic model. Actual action descriptions must be read from native
`training_forecasts_frozen.action/settings`, not inferred just from load state.

Maximum new diagnostic usage: **8 Spark**, previous cost estimate$0.06–0.12,
depending on tokens. Standing necessary-call approval applies; the old71 request
reservations are retained and the private ledger allows this run's maximum eight.
The reservation is not an actual charge. At registration:0 new requests,0 serial
commands,0 stimuli. PING and later photo stages are announced separately. Any
failure terminates this attempt without automatic retry or guard adjustment.

A passing restored diagnosis still needs the actual changed-state photo before
completing the case. Existing nullable-v2 body correspondence and unresolved
parallel-group semantics apply; no vision value reader or repeated DMM reading.
Caption only a consistent rerun **No mismatch in the tests Spark chose**. QA pass
does not itself establish root-cause repair or alter any failed diagnostic result.

Core parent audit remains `python -m benchmate.reading_restored_v2 verify <record>`.
The added context is covered by its event-chain integrity check; the preceding
failed run and QA are also separately audited by their existing commands. No new
compound-verifier behavior is claimed. Integrity/order checks do not prove
creation time, physical wiring truth or operator authenticity.
