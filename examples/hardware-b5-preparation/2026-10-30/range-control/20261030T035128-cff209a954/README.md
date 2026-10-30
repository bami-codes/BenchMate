# Resistor-only range-control attempt

Status: **run_failed**. Retained ADC frames: **0**. API calls: **0**.

Both DUT capacitors and the output-load jumper were removed with USB power off. The tested loose 1N4148 remains outside the circuit. This checks the fixture before any B5 diode observation.

The exact frozen protocol, implementation snapshots, actual connection report and preparation record are retained below. No automatic retry, re-arm, OUT fit or threshold adjustment occurred.

Stopped at `fresh_boot`: Incomplete or malformed instrument response; this run is invalid.

This is a development range control, not B5 discovery, full D2 acceptance, calibrated absolute accuracy or a blinded result.

[Exact execution](execution/events.jsonl), [audit](audit.json), [copy hashes](provenance.json).
