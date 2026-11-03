# A3 primary REF waveform QA passed

All 17 raw blocks / 8704 frames passed the new named A1/A2/A3 primary guards;
all seven original waveform timing/DAC checks passed. No regression, fitted
reference, sample deletion, firmware change or wiring change occurred.

| Quantity | Result |
|---|---:|
| A3 raw block-mean span | 1.115 mV |
| A4 auxiliary raw block-mean span | 1.868 mV |
| A4 auxiliary warning blocks | 0 |
| Serial commands / ARM | 37 / 0 |
| Event hashes / source hashes verified | 103 / 84 |
| Spark/API requests | 0 |

The seven waveforms deliberately move A1/IN and A2/OUT; their signal block-mean
changes are not REF instability metrics. All four ADC columns remain recorded.
Boot `6f26caac8ef1d32373dd753753404215` stayed the same; initial and final PINGs
matched the already armed REF state. A logged 10-second wait preceded capture.

This QA supports the new guard in the current unloaded design-01 configuration,
not the root cause or independent absolute REF accuracy. A4 also happened to
remain within its old limits in this run; it is still declared auxiliary for
the new version. Every subsequent capture retains primary A3 protection.

F01 and F02 remain failed/countable. Their replay under the proposed guard was
only a guard check and never retrospective prediction verification. F03 needs
its own committed/pushed pre-run binding and future reserved measurements.

Raw results and four new source snapshots:
`examples/A3-reference-QA/2026-11-03/session01/`. The other original 80 sources
remain preserved in the official record archives. The effective official
profile is specified in `2026-11-03-A3-official-protocol.md`.
