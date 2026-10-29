# Reference centering follow-up and session continuation

This archive preserves the fixed-output DMM bracket, one local centering move,
its independent DMM check, the later ADC mismatch, and the ten-block observation.
The original event chains and summaries are copied unchanged; their historical
`DMM_interval_report_pending` fields remain as originally recorded. The later
operator reply is added separately in [assessment.json](assessment.json).

The one move from code 1369 to 1374 passed the independent DMM point check
(REF / DRIVE / REF = 1.635 / 1.635 / 1.635 V). A later A4 mean changed by
5.53 mV, so this did not establish automatic reference tracking.

The subsequent capture ran from **23:39:46.829 to 23:40:16.964 KST on October
29, 2026**. All ten 512-frame blocks passed their original transport/timing
validation: 5,120 frames, zero overruns, the same boot and code 1374, and only
PING and fixed-code HOLD commands. The event hash chains verify locally;
they do not provide external attestation.

Across these ten blocks, channel-mean spans were **0.395 / 0.148 / 0.350 /
0.346 mV for A1 / A2 / A3 / A4** under the retained nominal conversion.
These are spans of block means, not per-sample noise or absolute accuracy.
Raw nominal A3-minus-A4 was -4.558 to -3.961 mV. Applying the already saved
local anchors, without any new fitting, gives **-2.012 to -1.415 mV**, mean
**-1.705 mV**.

The operator's later verbatim reply was **“해봤자 +- 0.002?”**. This is an
approximate report of millivolt-scale variation; it does not supply exact
signed extrema, a central value, contact continuity or observation timestamps.
The start notice was recorded at 23:40:06.052 KST, around 19 seconds into
the capture; message delivery/read time is unknown. Exact overlap between
the ADC and the operator's observation is therefore not established.

**Causal conclusion:** during these ten blocks A4's block-mean span was only
0.346 mV; the earlier 5.53 mV change did not recur in this window. The
observation therefore cannot decide whether that earlier change came from
physical REF movement or the ADC/path. A later stable window does not prove
either cause. The initial +0.002 V reading and later approximate variation
report also do not establish a continuously held +0.002 V throughout all ten
blocks.

The existing anchor result is roughly compatible with that approximate
report. This is **not** a new calibration, a scored pass, proof of simultaneous
accuracy, or validation of automatic tracking. Original failed D01 predictions
remain failed. Full D2 acceptance and physical repair remain pending.

The continuation-session user confirmed that the previous session was stopped
and USB/wiring were unchanged. This is an operator status report, not a new
device PING. No hardware command or API call was made by this offline audit.

Resume order: confirm boot/held state; finish the remaining tracking check or
retain explicit manual REF checks for a separately logged repair; freeze the
repair prediction before removing the added capacitor; verify repair without
refitting; restore B1 and perform the B1/B6 shunt comparison. The extra capacitor
and output load are still installed according to the last confirmed setup.
