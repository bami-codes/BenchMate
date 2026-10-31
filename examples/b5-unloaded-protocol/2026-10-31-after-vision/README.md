# B5 source-manifest refresh after image-entry implementation

This prospective protocol is generated before any physical B5 observation.
It preserves the October 30 unloaded experiment settings, scoring rules,
voltage-conversion maps, guards and historical calibration provenance.
Only the source manifest gains the separate image-intake modules. No image
reading, assembly photo or vision result enters the B5 experiment input.

The former protocol remains preserved in `../2026-10-30/protocol.json`.
The current runner checks all Python source files, so use this refreshed
protocol (subject to a new hash check at launch) with a fresh actual operator
report. Historical supply/REF readings remain estimates, not new measurements.
