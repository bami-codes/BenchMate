# Corrected restored connection: bounded HOLD QA result

Operator reported green IN large-board end A37→A35 with USB off. No R1 lead
misplacement was reported. After removing the external resistors, leaving IN at
A37 had left that path disconnected; this is consistent with the preceding
settling failure, without reconstructing samples that were never captured.

Frozen plan commit: `8c18d3d`. QA record:
`examples/reading-recovery/2026-11-03/records/20261103T140847-47f2534f1a`.
One ARM, three HOLD blocks, 1,536 frames. No step/sine, no model call, $0.
All unchanged guards passed. Block-mean spans: A1 0.346mV, A2 0.068mV,
A3 0.218mV, A4 0.089mV. This validates one-boot HOLD repeatability only.

The next setup PING still saw QA boot `486f508b205ce288c00f6c38bc6df969`
armed at REF. It stopped before ARM or any waveform. The operator then confirmed
board-end USB removal, power LED off, and reconnection. The next PING observed
new boot `0d952d304d6eac10b1a7c05e09531a30`, unarmed. Both setup records are
retained under `setup-preflights/`. No automatic stimulus retry occurred.

A separately registered restored-only follow-up is counted as attempt 2. The
original first pair stays failed and selected as the first attempt. No thresholds,
firmware settling, sampling, fitting, menu or reserved inputs were changed.
