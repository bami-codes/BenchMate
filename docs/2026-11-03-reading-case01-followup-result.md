# Case 01: restored follow-up closed without redundant new photograph

This is counted restored-only attempt 2 after the operator corrected the green
IN end from large A37 to A35 and the separately frozen three-HOLD QA passed.
The first reading-assisted pair remains failed, counted and selected as the
first attempt. Neither its terminal event nor its failure status was changed.

Follow-up registration/source freeze: `ca97828`. Record:
`examples/reading-followup/2026-11-03/records/20261103T142003-2b176faa91/`.
The diagnostic prefix was initially published non-terminal, awaiting another
photograph. That redundant requirement was subsequently withdrawn in the
explicit post-diagnosis amendment `docs/2026-11-03-reading-photo-closeout.md`.
The record is now closed. No new restored photograph, SAM call or correspondence
was made. The earlier photo/SAM/R1 binding retains its fault-state capture scope.

Fresh Spark context received the reviewed intended circuit and new observations,
without the prior diagnosis, DMM reading, QA output or private assembly record.
Spark chose unloaded small step, loaded small step and unloaded 1Hz large sine.
The operator performed the two requested load changes with USB off. Each new
boot was checked unarmed, then waited at least ten seconds before ARM.

All 25 acquisition guard blocks passed; 12,800 frames were retained. The three
training and two reserved waveforms completed without an acquisition retry.
The nominal design's reserved conditional RMS errors were 5.069mV (step) and
3.261mV (sine); their worst region errors were 5.182mV and 4.238mV. All are below
the unchanged 9mV limit. Predictions were frozen and pushed before either
reserved measurement in commit `4a0d76219027ed01b7b8e69c2893c8eeccf60734`,
SHA-256 `931ee55a218a3f49ef5a6b27c7ae7d43de3dafa89c11f93afb479aa3abf0d069`.

Native verdict: `consistent`. Exact caption: **No mismatch in the tests Spark
chose**. Nominal and nearby changed-value models also fit, so this does not
identify every part uniquely or prove that every part is correct. The native
`physical_repair_demonstrated` field stays false. The separate case narrative
may report the operator's removal of the sealed external resistors and this
consistent follow-up, while showing the preceding failed restored attempt.

This diagnostic stage used six actual Spark requests, estimated $0.05800195
from reported tokens. New reading-cohort cumulative usage at this point is
17 Spark requests and one SAM request, estimated $0.15204580. The completed
HOLD-only recovery and USB setup PINGs added zero paid requests.

The final numerical audit checks four frozen forecasts, five measured waveforms
and 19 order relationships. Use `python -m benchmate verify <record folder>` for
the root numerical record, or `python -m benchmate.reading_closeout verify
<record folder>` for the compound record, embedded original failure/QA, and the
explicit waived-photo closeout. Both passed without keys or network. The
original frozen follow-up verifier retains its original photograph requirement;
it was not changed to make this amended closeout pass. Integrity and
recorded-order checks do not establish record creation time.

Restoration evidence is the operator's wiring reports and physical re-execution,
not an inferred present state from the old picture. R1's earlier isolation and
reinstallation remain recorded. This documentation closeout added zero hardware
actions, zero paid calls and $0; cumulative cost remains $0.15204580.
