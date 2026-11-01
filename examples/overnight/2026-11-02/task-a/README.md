# Task A: what access to measurement adds

All 30 registered synthetic specimens, first attempts, same frozen protocol `cf33122`.
Execution wrapper and supplemental budget were committed before this batch at `25a4dcb`.
This is an **information-access comparison**, not matched intrinsic model accuracy.
The no-tool arm sees an ideal time constant and family bounds. The bench arm sees noisy
waveforms, engine fitting results, ranked measurement options and reserved verification.

| Arm | In-family identification | Both changed: final rejection | Other outcome | Wrong IDs |
|---|---:|---:|---|---:|
| Spark, no measurements | 8/24 | 0/6 | 22 cannot-tell replies across all 30 cases | 0 |
| Spark with bench, ranking visible | 24/24 | 5/6 | A19 incomplete after 8 calls | 0 |
| Engine | 24/24 | 6/6 | none | 0 |
| Fixed expert plan | 24/24 | 6/6 | none | 0 |

No-tool abstention is a reasonable response to indistinguishable explanations, not an
error. A19 reached `all_candidates_inadequate` but exhausted its HTTP budget before an
accepted final report. It remains incomplete, not a successful rejection; no retry.
The same registered code computed the complete paired statistics in `score.json`.
Those statistics concern these information conditions; they do not establish that Spark
itself reasons better, nor superiority over the engine or fixed procedure.

**162 requests, $1.23982715 from returned token usage**, all settled locally. This is not
an invoice. Together with the original night batch: **322 requests, $2.98877455**.
The physical shared allowance file was not changed.

`records.tar.gz` retains both arms' full event chains, every response and result row.
`records-manifest.json` identifies the decompressed files by SHA-256. `cost-usage.json`
retains usage and cost calculation without keys. Nothing was sent to hardware.
