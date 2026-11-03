# New case 01 — faulted diagnosis and reading request

The **faulted terminal diagnosis is complete**. The full case pair is still in
progress: new photo/SAM binding, operator reading, seal reveal, restoration and
fresh rerun remain pending. This is `reading-assisted-v1`, known to developers,
**not a blind test**. No old run or assembly truth was supplied to Spark.

Pair: `runs/reading-cohort/20261103T125924-bf8f64512b/`.
Public record: [pair folder](../examples/reading-cohort/2026-11-03/records/20261103T125924-bf8f64512b/).
Fault child: `diagnosis-faulted/20261103T130826-26d83af2df/`.

Spark chose, in order: loaded small step, unloaded large step, loaded 5Hz small
sine. All 25 protection blocks and five waveform checks passed. A3 remained the
primary raw 3mV REF guard; A4 stayed auxiliary. No k correction, firmware change,
guard relaxation, sample deletion or automatic retry was used.

Nominal and changed-C1 families failed training; the changed-R1 terminal family
fit an effective resistance of **25,278.99Ω**. This is an effective path value,
not an isolated measurement of the visible R1. Its frozen prediction was pushed
at [`6e59f33`](https://github.com/bami-codes/BenchMate/blob/6e59f33878f5a3dd9af92ecb66281658dc462af4/examples/reading-cohort/2026-11-03/predictions/20261103T130826-26d83af2df/terminal.json)
before either reserved capture. No reserved OUT fitting occurred.

| Reserved input | Conditional RMS | Worst conditional region | Command RMS | Worst command region |
|---|---:|---:|---:|---:|
| Unloaded ±0.35V step | 4.594mV | 5.455mV | 5.512mV | 6.503mV |
| Unloaded 5Hz, 0.65V sine | 3.623mV | 5.422mV | 3.146mV | 4.322mV |

All are below the unchanged 9mV whole/region allowance. Native report is
`changed: [R1]` with explicit terminal-only/topology limits;
`physical_repair_demonstrated:false` remains unchanged.

## Spark's next reading

The code generated an exact series-equivalent localization alternative from
the verified terminal model; this is **not a new Spark structure-proposal
event**. A fresh Spark request then chose **R1 / resistance**, reasoning that an
isolated, power-off DMM reading separates changed R1 from unchanged R1 plus an
additional series path. It explicitly noted that markings cannot rule out a
damaged part retaining its old label. No photograph or operator value was used.

All source/range-specific predictions were frozen and pushed at
[`edec9d0`](https://github.com/bami-codes/BenchMate/blob/edec9d090bc121b5fab13a7d67ed57d36ae4c3c6/examples/reading-cohort/2026-11-03/predictions/20261103T125924-bf8f64512b/reading.json)
before photo processing. The 20kΩ DMM-range numeric intervals are
23,219.46–27,951.88Ω versus 4,355.70–5,053.70Ω; the first would exceed that meter
range, so an OL display requires a higher preregistered range to obtain a numeric
reading. Higher-range intervals are already frozen too. These are engineering
envelopes, not calibrated confidence intervals. Correct-looking nominal markings
leave both explanations alive. No reading has yet been received or scored.

Calls so far: schematic Spark 1 + diagnosis Spark 6 + reading-selection Spark 1
= **Spark 8, SAM 0**, estimated **$0.06815900**. Reading selection alone used one
request, estimated $0.00671395. Previous-cohort ledgers and records remain intact.

Fault-child offline verification:

```text
PASS events=247 forecasts=4 measurements=5 order_checks=19 prediction_files=1 run_status=run_completed head_sha256=390f8d0cb7a495efc5368f58bf23f9dfa8ead949f3db7d909dc2d1207a90f876 scope=internal_integrity+recorded_order creation_time=unproven
```

This verifies internal record integrity/order, not when records were created or
the truth of physical/operator assertions. The incomplete parent must remain
incomplete until the entire new pair finishes.
