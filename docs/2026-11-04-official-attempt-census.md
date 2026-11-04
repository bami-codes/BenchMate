# Official attempt census — 4 November 2026

Read-only recount at main `b09303f`. No model calls, hardware actions, new execution, or retrospective verdict changes.

The submission cohort has **13 registered workflow attempts across five cases**, comprising **15 diagnostic starts: seven faulted and eight restored**. The site displays **10 official replays**, plus two development pilots. These numbers have different denominators and are not an accuracy rate.

## Counting rules

- Registration: one counted row in the original reading-assisted-v1 index. It can stop at intake or photo handling, so it is not synonymous with a diagnostic run.
- Diagnostic start: a distinct faulted/restored diagnostic record bound by `diagnosis_started`, plus the two standalone restored diagnostic records (01 follow-up and 05 timing-v4 follow-up). An initial HOLD stop counts as a start; this does not claim a completed stimulus, ADC capture, or verdict.
- Inherited history is not counted again. QA, PING-only preflight, photo/reading-only continuations, pre-freeze development, and the cancelled LED case are excluded.
- Native verdicts, failed first selections, later follow-ups and the original cohort policy remain unchanged.

## Per-case count

| Case | Workflow registrations | Faulted starts | Restored starts | Stopped before verdict | Abstained | Other verdicts | Site replays |
|---|---:|---:|---:|---:|---:|---:|---:|
| 01 | 2 | 1 | 2 | 1 | 0 | 2 | 2 |
| 04 | 3 | 2 | 1 | 1 | 0 | 2 | 2 |
| 02 | 4 | 2 | 2 | 1 | 1 | 2 | 2 |
| 05 | 2 | 1 | 2 | 0 | 1 | 2 | 2 |
| 03 | 2 | 1 | 1 | 0 | 0 | 2 | 2 |
| **Total** | **13** | **7** | **8** | **3** | **2** | **10** | **10** |

The three pre-verdict stops are case01 restored (settling/protocol rejection), case04 faulted (A3 guard), and case02 restored (A3 guard). The two abstentions are case02 faulted attempt1 (operator wiring error identified afterwards) and case05 restored attempt1 (timing model limitation). The case04 first registration stopped at schematic intake and never started a diagnostic. Case02 and case03 photo-stage stops do not erase their already completed fault diagnoses.

The root index has six `completed` and seven `failed` workflow statuses. This is not a diagnostic success score: a completed case05 workflow contains an abstained restored diagnosis, and two photo-stage failures contain completed fault diagnoses.

## Copy for README / site / submission

> Across five cases, 13 registered workflow attempts started 15 diagnostic runs: three stopped before a verdict, two abstained, and ten returned a non-abstained verdict. The site replays ten fault/restored runs; all other attempts are retained. These are counts, not an accuracy rate.

Apply this distinction wherever “10 official runs” could be read as the total number attempted, particularly `docs/submission.md` (both long and short submission text) and the site count deck. A displayed replay is not a newly executed experiment.

## Sources

- [Original cohort index](../examples/reading-cohort/2026-11-03/index.json), SHA-256 `98ec3c4be0576c9f9d5cb6f4b7ec832d9ed1a3a0fcb2b81a6e09ce48043cc256`.
- [Original cohort policy](2026-11-03-reading-cohort-policy.json); [five-case submission scope](2026-11-04-five-case-submission-scope.md).
- [Machine-readable census](2026-11-04-official-attempt-census.json): all 13 primary record paths, all 15 diagnostic paths, native verdicts, event sequence references and event-chain heads.
- Public site index: [12 replay entries](../site/data/runs/index.json), ten counted and two development pilots.

This census reads recorded starts and reports; it is not an independent authentication of physical events, wall-clock creation times, or first-attempt accuracy.
