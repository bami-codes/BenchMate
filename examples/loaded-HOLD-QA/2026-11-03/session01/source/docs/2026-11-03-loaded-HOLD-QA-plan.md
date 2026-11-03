# Loaded HOLD-only maintenance QA, after 01-F01

Before any repetition, present the operator with two choices: one bounded QA on
the unchanged loaded wiring, or inspect the REF/power wiring first. No new
measurement starts merely because the previous run failed. The operator has
confirmed USB disconnected, E30–A55 retained, and both I10–I16 pull-down and
H16–H13 return installed. The in-circuit reading `0.911` has no recorded unit;
it does not establish a defective 1 kohm part. Do not alter it on this evidence.

If the operator selects QA, reconnect the same USB port with probes removed.
The fixed English confirmation is preserved. The QA requires a new unarmed
boot, issues ARM at most once, then uses **HOLD at REF only**, at most 12 blocks
of 512 frames / 6144 frames and 28 serial commands. Estimated duration: 1–2 min.
Spark/API calls: zero, $0. No diagnostic step/sine, fitting, k correction,
firmware upload, rewiring, manual mV reading, guard change or automatic retry.

The unchanged `PhysicalBench` checks run on every block. Any electrical,
communication or boot error stops immediately. Retain all frames and failures.
PASS establishes constant-HOLD repeatability only for this loaded configuration
on this boot. It does not prove the anomaly's cause or qualify all stimuli.
The counted 01-F01 failure and first-attempt selection remain unchanged.

Plan preparation is offline. The actual plan and sources must be committed
before execution. Any subsequent diagnostic attempt is separate, prospectively
registered, counted and never substituted for the original primary 01-F01.
