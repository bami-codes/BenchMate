# Overnight results — November 2, 2026

**All new acquisitions here are simulated. No physical board was operated.**
The user authorized autonomous overnight software work. Plan and design were
pushed at `912deb1`, independent variant implementation at `ab814e3`.

## Actual Spark, mock benches

| Run | First-attempt result | HTTP requests |
|---|---|---:|
| D01 repair rehearsal | Repair verified by both frozen-model checks | 7 |
| B5 repeat 1 | One proposal, both held-out checks passed | 7 |
| B5 repeat 2 | One proposal, both held-out checks passed | 7 |
| B5 repeat 3 | One proposal, both held-out checks passed | 7 |
| B5 repeat 4 | One proposal, both held-out checks passed | 7 |
| B5 repeat 5 | One proposal, both held-out checks passed | 7 |

The five B5 repetitions use one unchanged mock circuit and one acquisition seed,
fresh model contexts, and the original max-effort session. They assess execution
repeatability on this case, not five independent circuits or physical reliability.
[D01 original events](rehearsals/d01/events.jsonl) and the five `rehearsals/b5-*`
folders retain all model tool calls, observations and results. No failed attempt
was replaced. Physical repair and physical diode verification remain unperformed.

## Frozen linear benchmark, evaluation specimens

| Task B, 16 circuits | Accepted correct reports | Wrong reports | Mean simulated mountings |
|---|---:|---:|---:|
| Engine ranking | 16/16 | 0 | 1.00 |
| Fixed expert plan | 16/16 | 0 | 1.00 |
| Random, 3 runs/circuit | 30/48 | 0 | 2.81 |
| Spark, ranking hidden | 15/16 | 0 | 2.88 |

Random's 48 runs are only 16 independent circuits. Spark still receives engine
analysis; hiding ranking is not removing the engine. This does not establish
Spark superiority over a fixed plan or lower wiring cost. Product decision:
retain engine ranking for declared linear families; assess Spark's proposed new
structures separately. Do not retune this evaluation after seeing its outcomes.

B14 reached a supported, verified candidate but spent four calls inspecting
measurement details and exhausted eight requests before `finish_report`.
The preregistered metric requires an accepted final report: **incomplete**, not
16/16. Its first attempt remains primary and no retry was made.

Task A: engine/fixed 24/24 in-family and 6/6 correctly rejected dual-change cases;
random 71/72 in-family and 17/18 dual-change rejections. No wrong identification
occurred in the executed arms. Paid Task A and Spark Open were not run.

## Cost, integrity and reproduction

160 HTTP requests: 7 D01, 35 B5, 118 Task B. Reported usage at published standard
rates totals **$1.7489474**, with no unsettled requests; this is a usage calculation,
not an account billing invoice. The cap was $30 and 176 requests. Original shared
physical-run reservation ledger was not changed. [Usage ledger](cost-usage.json).

[Summary and statistics](summary.json) include paired comparisons and intervals.
[Linear raw records](linear-records.tar.gz) contain every first-attempt event log,
row and score; [SHA-256 manifest](records-manifest.json) verifies decompressed
files. Archive paths are relative to `runs/linear-benchmark/v1.1/`. Restore them
there and run `scripts/benchmark_linear.py score`; no API call is needed.

The mock transport adds a declared isolated cost guard; original prompts, tools,
model effort, output limits, inference and scoring sources are unchanged. The
original `$1 reserved` fields in provider metadata are bookkeeping, not charges.

The separate B5 variant bench and selection implementation are frozen. Selection
results are a feasibility screen, not Spark evaluation results. Final variant
model evaluation waits until the physical B5 attempt as registered.

## Later supplements — original snapshot above retained

- [Full Task A information-access comparison](task-a/README.md).
- [Spark Open development gate and all 30 evaluation cases](spark-open/README.md).
- [Retired transport probe and its local implementation failures](open-transport-probe/README.md).

Across these and the original batch: **465 actual requests, $4.08661535 calculated
from returned usage**, all settled locally. Meta $2.98877455; Baseten $1.09784080.
The six local pre-HTTP guard failures in the retired probe are not charged requests.
These totals are not provider invoices. Original per-batch cost files are preserved.
