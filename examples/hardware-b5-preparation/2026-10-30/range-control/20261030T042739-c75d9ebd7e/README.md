# Resistor-only range-control attempt

Status: **run_failed**. Retained ADC frames: **512**. API calls: **0**.

Both DUT capacitors and the output-load jumper were removed with USB power off. The tested loose 1N4148 remains outside the circuit. This checks the fixture before any B5 diode observation.

The exact frozen protocol, implementation snapshots, actual connection report and preparation record are retained below. No automatic retry, re-arm, OUT fit or threshold adjustment occurred.

Stopped at `waiting_DMM`: DMM reply timeout; no scored waveform sent.

Manual recovery report: reset 완료. The preceding failed attempt is `runs/hardware-b5-range-control/20261030T035419-baf50eef2e`; it is retained separately.

This is a development range control, not B5 discovery, full D2 acceptance, calibrated absolute accuracy or a blinded result.

[Exact execution](execution/events.jsonl), [audit](audit.json), [copy hashes](provenance.json).
