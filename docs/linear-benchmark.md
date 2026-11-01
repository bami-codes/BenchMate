# Linear benchmark (preregistration, linear-benchmark-v1.1)

Machine-readable protocol: [`examples/linear-benchmark/2026-11-01/protocol.json`](../examples/linear-benchmark/2026-11-01/protocol.json).
Harness: [`scripts/benchmark_linear.py`](../scripts/benchmark_linear.py). Specimen truth table:
`specimens.json` next to the protocol, fixed by its SHA-256 in the protocol.

This file, the protocol, the specimen table and the harness are committed and pushed
**before any evaluation specimen is run**. Development checks use a separate seed and
live under `runs/linear-benchmark/v1.1/dev`.

## Question

The physical D01 run showed one case where the choice of experiment mattered: Spark
asked for a load instead of repeating the step. This benchmark asks the same question
over many specimens on the synthetic instrument:

1. Without a new measurement, how often can Muse Spark name the changed part?
2. With the bench, does the choice of experiment change what is correctly identified,
   and how many wiring changes does it cost?
3. Does Spark choose good experiments **without** seeing the engine's ranking?

Synthetic only: ideal drive, 1 mV Gaussian sensor noise, declared linear families.
It is not a hardware accuracy result and not a nonlinear discovery result.

## Tasks

| Task | Mode | Specimens | Correct outcome |
| --- | --- | --- | --- |
| A — Which part changed? | repair | 8 nominal, 8 R changed, 8 C changed (in family); 6 with both changed (outside every family) | name the changed part; for both-changed, verify nothing |
| B — What is connected? | mystery | 8 RC, 8 RC with an input branch | name the structure |

Values are drawn log-uniformly inside declared bounds from master seed 20261101.
Every arm sees the same specimens and the same noise seed per specimen.

## Arms

| Arm | Chooses experiments by | Model calls |
| --- | --- | --- |
| `no_tool` (A only) | cannot measure; one question with the noiseless time constant | 1 per specimen |
| `random` ×3 | uniform among affordable actions | 0 |
| `fixed` | a written plan (load steps first) | 0 |
| `engine` | BenchMate's ranking, top action | 0 |
| `spark` | Muse Spark 1.3 medium, ranking visible (the product) | ≤ 8 per specimen |
| `spark_hidden` | Muse Spark 1.3 medium, ranking withheld | ≤ 8 per specimen |
| `spark_open` | Spark Open on Baseten, ranking visible; only if its adapter passes dev specimens | ≤ 8 per specimen |

Same menu (85 actions), same budget (1 exploration, 3 diagnostic, 1 confirmation),
same frozen-prediction verification for every bench arm. The fixed plans were written
after seeing the engine's first choice on development specimens, which favours them.

## Scoring

- **Correct**: an accepted report with verdict *verified* naming the true class.
  The session refuses *verified* unless the frozen prediction passed.
- **Wrong**: verified a different class, or verified anything on a both-changed specimen.
- **Rejected / false rejection**: all declared families inadequate (right for
  both-changed, wrong for in-family).
- **Abstained**: anything else, including a run that ends without an accepted report.
- Primary: first-attempt correct over in-family specimens, including failed attempts. Safety: wrong over all.
- Wilson 95% intervals use one run per circuit. Random repeats stay together in a circuit-cluster bootstrap; 48 runs are 16 circuits, not 48 independent circuits.
- Complete paired exact McNemar comparisons use first attempts (random replicate 0), with Holm adjustment across all seven registered pairs. Partial tables cannot support superiority claims.
- All attempts, requests and recovery outcomes are retained and reported; a retry never replaces the first result.

## Stated before running

- Tau alone cannot generally separate R and C in overlapping family intervals. The declared bounds also have edges unique to one changed family. There is **no 8/24 accuracy ceiling**: guesses can be correct.
- No-tool receives an ideal tau rounded to 0.1 ms; bench arms receive noisy waveform summaries and engine analysis. This is an information-access condition, not a matched intrinsic model-accuracy ablation. A justified abstention is not a false identification.
- `engine` and `spark` identify at least 23/24 in Task A and verify none of the six
  both-changed specimens.
- In Task B, `random` identifies fewer specimens than `engine` and needs more wiring
  changes. `spark_hidden` is reported against both, whatever it does.
- `engine`, `fixed`, `spark` and `spark_hidden` make no wrong identifications.

## Reporting rules

- One table, every arm, every specimen. Nothing dropped.
- No repeats, except once after a provider transport error with at most one request
  made. Both records stay; first attempts remain primary; all attempts and their costs are reported separately.
- If `spark` does not beat `engine`, we say it matched or trailed the ranking. Spark is
  credited with better choices than an arm only only for a complete comparison with a positive effect and Holm-adjusted p < 0.05.
- If `spark_open` is not run, the table says so and why.
- Any change after the first evaluation run is a new protocol version; earlier results
  stay published.

## Commands

```sh
uv run python scripts/benchmark_linear.py plan
uv run python scripts/benchmark_linear.py run --arm engine        # also fixed, random
uv run python scripts/benchmark_linear.py run --arm spark --execute --task B --max-requests 128
uv run python scripts/benchmark_linear.py score --write
```

Development checks: add `--dev` (and `--limit N`) to `run` and `score`.

## Review amendment — 2026-11-02, before evaluation

The specimen seed/table and experiment engine are unchanged. v1.1 corrects retry
accounting, correlated random repeats, multiple comparisons, the unsupported
no-tool ceiling, and request accounting across errors/resumes. It freezes the
complete imported experiment source in `source-manifest.json` and verifies that
the current files are committed and pushed to `origin/main` before evaluation.
Results go to `runs/linear-benchmark/v1.1`; earlier practice remains separate.

`--task A` / `--task B` selects a complete preregistered task before execution,
never favourable individual specimens. `--max-requests` is a cumulative per-arm
limit, including earlier invocations and failed requests. The full ceilings are
Meta 766 (30 no-tool + 368 ranked + 368 hidden), Baseten 368. Task B alone is
Meta 256 (128 ranked + 128 hidden), Baseten 128, before any separately authorised
adapter development calls or physical experiments. These are request ceilings,
not actual dollar costs. No paid evaluation or local allowance change is authorised
by this document.

This benchmark covers linear model selection. It does **not** supply the nonlinear
classical-extended baseline for B5, and it does not establish physical wiring time.
The hidden-ranking arm still receives engine fitting/identifiability results; it
is a ranking ablation, not an engine-free agent.

The no-tool HTTP attempt is counted even when transport fails. An interrupted
attempt without an indexed result blocks resumption until it is audited.
`--allowance-cap AMOUNT` changes only this process's cumulative local reservation
limit and is logged in every paid run; use it only after explicit approval and
checking the provider account. No shared provider source or hardware protocol is
changed. Baseten evaluation additionally requires successful actual development
runs on both Task A and Task B (up to 16 separate requests); mock HTTP tests do
not satisfy that gate.

Video extraction also preserves first attempts, rejects mixed protocol versions,
and includes the fixed-plan comparator. Its layout must accommodate that extra
row; the complete score table remains the source of record.
