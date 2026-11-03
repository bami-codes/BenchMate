# First official design-01 faulted attempt: 01-F01

**Failed and counted; no completed final diagnosis or reserved verification.**
The original guard stopped in the third loaded pre-stimulus HOLD before the
loaded step. The first unloaded step passed. All eight raw blocks (4096 frames),
80 events and 80 source snapshots are retained.

The operator-only assembly file stays private; its event digest is retained.
No API key, original phone photo or hidden reasoning is included. No sample was
deleted and no guard was relaxed.

See [failure analysis](../../../../../docs/2026-11-03-01-F01-guard-failure.md)
and [raw plot](../../analysis/01-F01/raw-HOLD-failure.png).

From repository root:

```sh
python -m benchmate verify examples/official-runs/2026-11-03/records/20261103T072121-1138ccf241
```

Integrity PASS does not mean experiment success: `run_status=run_failed`.
