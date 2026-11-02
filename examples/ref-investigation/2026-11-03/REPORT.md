# Offline REF investigation

This folder contains descriptive analysis of retained logs, not new hardware
captures, a firmware experiment, or a successful reclassification of rejected data.
The operator's overnight restriction is in effect: no model requests, instrument
commands or wiring requests until the operator returns.

The two waveform-containing design-01 pilots both narrowed their training
hypotheses to increased effective series resistance and stopped on REF guards.
Neither produced a completed verified diagnosis. An earlier HOLD-only startup
stop and separate reference QA records remain separately preserved.

The analysis found signal-correlated reference-channel changes: approximately
19–20 mV between the large step's settled negative/positive regions, and a
9.25 mV peak 1 Hz component close to input phase. These observations do not by
themselves distinguish ADC/conversion coupling from real REF/power coupling.

See [the Korean findings and morning DMM procedure](../../../docs/2026-11-03-ref-investigation.md).
`metrics.json` retains all six stimulus-waveform metrics and input hashes.
The plots use nominal ADC conversion; display smoothing is not used for metrics.
The analysis source is copied alongside the output for reproduction.

Reproduce to a new output folder, without hardware or network:

```sh
.venv/bin/python experiments/analyze_ref_coupling.py --output /tmp/benchmate-ref-analysis-NEW
```

All 76 pre-existing pilot runtime hashes were unchanged. Known-sine arithmetic
self-checks passed, and a rerun from the public raw-data archive reproduced the
first analysis's six waveform metrics and HOLD summaries exactly. The original
3 mV criterion is unchanged. New paid calls and hardware commands: zero.
