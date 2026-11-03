# New case 01 — reading-assisted-v1

Status: **in progress, not a completed physical result**. User requested the new
pipeline and case 01 restart after the development cohort. No previous diagnosis
or image-derived component value is supplied to the new diagnosis.

- Final source/protocol freeze: `4b4e8ad` (107 files, snapshots retained).
- Registration before any request/stimulus: `a34ecab`.
- Local pair folder: `runs/reading-cohort/20261103T125924-bf8f64512b/`.
- Public in-progress copy:
  `examples/reading-cohort/2026-11-03/records/20261103T125924-bf8f64512b/`.
- Protocol and event contract: [reading-experiment protocol](2026-11-03-reading-experiment-protocol.md).
- Validation: [121 passing offline tests](../examples/reading-cohort/2026-11-03/VALIDATION.json).

Fresh schematic request completed: R1 4.7kΩ IN–OUT, C1 1µF OUT–REF,
no ambiguities. Operator confirmation and USB-off faulted setup are pending;
no serial commands, ARM or stimulus have been sent in this new cohort.

Calls to this point: **Spark 1, SAM 0**. Input 2,091 tokens, cached 113,
output 1,701 (including 1,401 reasoning). Estimated cost **$0.00971870** at
the existing standard-rate estimate. Actual billing may differ. A pair has at
most 20 Spark requests and two SAM requests under this fixed version, with no
automatic retries; each stage's count/cost is disclosed before execution.

The first new-cohort attempt remains selected regardless of outcome. Old F01–F04
and R01 retain their original logs and labels as development history relative to
this pipeline. This restarted case is known to developers and is **not blind**.
The public parent chain is intentionally incomplete until both diagnoses, reading,
seal reveal, restoration and state photographs finish; `verify` should not report
a completed-run PASS on this in-progress parent.
