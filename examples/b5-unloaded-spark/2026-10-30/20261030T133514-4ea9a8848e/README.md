# First Spark max unloaded B5 mock execution

Completed October 30, 2026 (Asia/Seoul). Seven paid Meta API requests, one
Spark-authored proposal, eight mock waveforms, zero physical measurements.
This is distinct from the earlier deterministic scripted software rehearsal.
It uses the same B5Session tool API as the prepared physical adapter; physical
ADC behavior and wiring remain untested in this run.

Spark chose resistor control and the amplitude sweep. All five initial linear
families failed. It proposed a series IN–OUT resistor and an OUT-anode / REF-cathode
diode. Its literal topology was simulated and only numerical training parameters
were fitted. Local rank was 3 of 5; individual R, effective IS and REF remain
confounded. Predictive adequacy did not imply unique parameters or topology.

Spark's actual measurement reason:

> Probe linearity across 0.2-0.8V sine and step to reveal amplitude-dependent clipping or rectification indicating diodes versus linear RC.

The proposal, all nuisance parameters, linear alternatives and command-input
forecasts were committed and pushed **before either reserved observation**:
[9cff3e8](https://github.com/bami-codes/BenchMate/blob/9cff3e8c3209c68bf489b5e3b2f95e0f27a8b74c/examples/b5-unloaded-freezes/20261030T133514-4ea9a8848e/predictions.json).

Both forecast types passed whole-waveform and every regional 9mV development
check. The unchanged linear alternatives failed both held-out conditions.

| Unused condition | Before-measurement command forecast: whole / worst region, mV | Measured-IN conditional comparison: whole / worst region, mV | Result |
|---|---:|---:|---|
| ±0.35 V step | 1.925 / 2.594 | 1.667 / 2.228 | PASS |
| ±0.65 V, 5 Hz sine | 1.953 / 2.841 | 1.734 / 1.954 | PASS |

Command forecasts assume nominal commanded input/timing; conditional predictions
use newly measured mock IN and recorded timing afterward. Reserved OUT never
refits either model. Every score and original visible Spark tool call/report is
retained. The prior automatic approval rejection made zero requests; explicit
B5-specific consent preceded this new run and is preserved in authorization.json.

The saved provider tool results contain 25 training points per waveform and fit/
verification summaries, no full waveform arrays, assembly truth, old physical
results or local files. Provider reasoning internals and credentials are absent.
Source snapshots matched the committed source manifest; source hash chain,
publication ordering and frozen models passed the local audit. This is a local
audit, not independent external attestation.

The mock plant is deterministic and deliberately simple, using an independent
diode equation solver. This successful integration rehearsal is not blinded
diagnostic accuracy, physical B5 validation, loaded extrapolation, or repair.
The next [physical procedure](../../../../docs/b5-operator.md) is prepared separately.

[Recorded prediction/observation figure](comparison.png) uses the exact saved arrays, with no new fit or simulation. Its source/output hashes are in comparison.provenance.json.
