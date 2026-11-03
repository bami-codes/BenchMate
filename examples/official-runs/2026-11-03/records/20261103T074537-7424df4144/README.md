# 01-F02: separate official follow-up, failed and counted

Both large steps passed. The raw A4 reference guard stopped during the third
chosen training waveform (unloaded 5 Hz sine). No reserved verification or
final report was reached. This does not replace the failed primary 01-F01.

All 142 events, raw frames and 82 source snapshots are retained. The operator
assembly file remains private; its event digest is recorded.

```sh
python -m benchmate verify examples/official-runs/2026-11-03/records/20261103T074537-7424df4144
```

Integrity PASS is not experiment success: `run_status=run_failed`.
See [analysis](../../../../../docs/2026-11-03-01-F02-guard-failure.md).
