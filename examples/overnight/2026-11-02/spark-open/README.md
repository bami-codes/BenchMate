# Spark Open: the same synthetic bench, first attempts

Plan committed and pushed at `c491769` before the first call. Exact model
`meta-models/muse-spark-open-1026`, hosted by Baseten. Both registered development
gates passed, then **all 30 Task A cases** ran. No model replacement, retry or repair
of the result rows. These are synthetic bench executions, not physical experiments.

| System | In-family identification | Both changed: final rejection | Incomplete | Wrong IDs |
|---|---:|---:|---:|---:|
| Spark Open + bench, frozen adapter | 21/24 | 1/6 | 8 | 0 |
| Spark medium + bench | 24/24 | 5/6 | 1 | 0 |
| Engine / fixed expert plan | 24/24 | 6/6 | 0 | 0 |

**All eight Open failures returned 2–5 tool calls in one response.** The frozen
adapter requires exactly one and stopped without executing the batch. Five of these
had already reached `all_candidates_inadequate`; they remain incomplete because no
accepted final report followed. This measures the full interface and model together,
not isolated reasoning quality. Baseten used provider-default reasoning while Meta
used medium. Tool descriptions, task, engine and the eight-call budget were unchanged.

The frozen adapter already sends `parallel_tool_calls: false`; these multiple-call
responses occurred despite that setting. Baseten documents a true default, but it was
explicitly overridden here. A later [development probe](../open-transport-probe/README.md)
incorrectly assumed the field was absent and failed locally; it did not establish a fix.
Neither the probe nor a future adapter change replaces these first attempts.

**120 requests including development, $0.92318245 from token usage**, no unsettled
reservation. Baseten credits are separate from Meta. This is a local cost calculation,
not a billing receipt. Raw visible replies, tool calls, usage, failures and hash-chained
runs are in `records.tar.gz`; hidden reasoning is not logged. Decompressed file hashes
are in `records-manifest.json`. `score.json` retains every existing comparison arm.
