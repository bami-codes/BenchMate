# Spark effort comparison at the D01 load-choice fork

**Both medium (the existing “standard” setting) and max selected the informative output-load step in all five attempts.** Max did not improve the observed decision on this snapshot; it took about 3.15× as long on average. This supports keeping medium for this D01 decision, not a general claim that medium and max are equivalent.

| Setting | Load selected | Mean request time | Median | Output tokens, all 5 | Total tokens, all 5 |
| --- | ---: | ---: | ---: | ---: | ---: |
| Standard / `medium` | 5/5 | 4.54 s | 4.63 s | 4,096 | 11,161 |
| `max` | 5/5 | 14.31 s | 14.27 s | 8,854 | 15,919 |

## What was compared

Ten new paid calls to `muse-spark-1.3` at `https://api.meta.ai/v1/responses`, with five fresh contexts per effort, identical 8,192-token ceilings and identical prompt, recorded observation and tool menu. Only `reasoning.effort` differs. The order was fixed before any call: medium, max, max, medium, medium, max, max, medium, medium, max. No tool was executed, no new physical measurement was made and no automatic retry occurred.

The observation is the unchanged tool result at event 50 of the [physical D01 run](../../../hardware-spark-rc/2026-10-30/20261029T174402-d3eaa8e612/README.md): unloaded τ = 21.383658508 ms, training RMS = 5.502629958 mV, declared nominal / R-change / C-change alternatives, and the two available measurements. Later load/sine results, assembly truth, raw ADC arrays and private files were not sent.

The question is a new, neutral **decision-only replay** prompt. It does not reuse the original instruction explicitly telling Spark to explain why a load distinguishes the alternatives. It also does not recreate the original hidden conversation state. This is a controlled comparison of the two settings on this prompt, not an exact rerun of the original agent.

The [plan](plan.json) and exact payloads ([medium](medium-payload.json), [max](max-payload.json)) were pushed in [5ec90af](https://github.com/bami-codes/BenchMate/commit/5ec90af2f52c02786fcd80e618409a0e491a5a06) before execution. The user requested the comparison with at most ten API calls. Existing credentials were used only for authentication. Ten $1 local allowances were reserved; these are **not actual billed costs**.

## All ten replies — no selection

Every call completed and returned one valid `measure` call with `action=attach_output_load_step`. No repeats, abstentions, invalid outputs or transport failures occurred in this batch. Original tool arguments and any visible messages are retained in each linked JSON. Hidden reasoning content is not logged.

| Call | Effort | Time | Verbatim reason |
| --- | --- | ---: | --- |
| [1](reply-01-medium.json) | medium | 5.05 s | 무부하 tau만으로 R·C 개별 식별 불가하므로 부하 스텝으로 구분 필요 |
| [2](reply-02-max.json) | max | 14.57 s | 무부하만으로 R·C 구분 불가해 부하 스텝 필요 |
| [3](reply-03-max.json) | max | 14.27 s | 무부하 스텝만으로 R·C 개별 식별 불가, 부하 스텝으로 구분 필요 |
| [4](reply-04-medium.json) | medium | 4.63 s | τ만으로 R/C 구분 불가해 부하 스텝 필요 |
| [5](reply-05-medium.json) | medium | 3.62 s | 미부하만으로 R·C 분리 불가, 부하 스텝으로 구분 필요 |
| [6](reply-06-max.json) | max | 13.74 s | 무부하 스텝은 시정수만 식별해 R변화와 C변화 구분이 불가하므로 부하 스텝 측정이 필요함 |
| [7](reply-07-max.json) | max | 15.65 s | 무부하 tau만으로 R·C 구분 불가하므로 부하 스텝 필요 |
| [8](reply-08-medium.json) | medium | 4.35 s | 무부하 타우만으로 R/C 구분 불가하여 부하 스텝 필요 |
| [9](reply-09-medium.json) | medium | 5.07 s | 무부하 tau만으로 R/C 구분 불가하여 부하 응답 필요 |
| [10](reply-10-max.json) | max | 13.29 s | 무부하 τ만으로 R·C 구분 불가, 부하 스텝으로 식별 필요 |

## Interpretation and limits

All ten reasons say that the unloaded response cannot separate R from C and request a load. None explicitly derives the voltage-divider gain or gives predicted separation in its visible reason. None claims to have observed a new result, identified the fault uniquely or completed a repair. This is manual descriptive review, not a blinded quality score. The brief phrases are not substituted for the original longer physical-run rationale.

Only one small, easy, constrained choice was tested. The alternatives and menu are already supplied; this does not test out-of-family structure discovery, general circuit diagnosis or a full agent workflow. Five replies per setting do not establish reliability. One session also does not establish general latency/cost rankings: prompt-cache usage varies across calls and both settings.

Keep medium for this D01 fork. B5 used max successfully in a separate mock discovery run, but these data do not establish that max is required for B5. Do not present this as evidence that “max wins at direction changes.”

## Integrity

All original batch files were copied byte-for-byte. The [manifest](manifest.json) pins them and the source snapshot; the local audit verified the event hash chain, ten distinct response IDs, request order, both frozen payload hashes and equality apart from effort. Hashes detect changes relative to this archive; they are not independent external attestation.

From the repository root, replay without any API call:

```sh
uv run benchmate replay examples/effort-comparison/2026-10-31/20261031T113227-558da839f7
```
