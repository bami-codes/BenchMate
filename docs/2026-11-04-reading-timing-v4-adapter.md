# Reading-cohort pair adapter: one v4 model for diagnosis and reading profiles

This additive adapter keeps the original107-source freeze and the already
qualified frame-anchored model/session in7675361 unchanged. It is frozen before
the first physical acquisition in the new case03 pair. It changes neither
measurements nor guards: raw A3 primary3mV, auxiliary A4, nine-millivolt whole AND
regional limits, known1kΩ instrument resistor and fresh-boot10second wait remain.

`scripts/reading_experiment_timing_v4.py` preserves the staged pair lifecycle,
fresh schematic review, sealed local assembly, same Spark tool/menu loop,
prediction publication before reserved acquisition and no automatic retry.
Both fault and restored diagnoses use `channel_timing_session_v4.PhysicalSession`.
Model contexts get intended design and current-run evidence only: no earlier
case, diagnosis, photograph, operator value or private case-map information.

`reading_catalog_timing_v4.py` preserves the bounded33-point training-only value
profiles and exact series/parallel-equivalent hypothesis construction, replacing
only the numerical prediction function with `channel_timing_v4.predict`.
The reading selection therefore cannot accidentally revert to the old source
timing model. Reserved OUT does not enter profile generation. Marking and
electrical observations keep their distinct source-specific meter/tolerance
rules, with all ranges frozen and pushed before photo or operator value.

Spark chooses the component and quantity. A choice with identical DMM intervals
for every explanation is rejected before spending an operator reading. An
observation with no single surviving explanation pauses before seal disclosure;
there is no value adjustment or automatic extra reading. A new stage would need
explicitly retained choices and another prospective forecast.

The existing legacy single-reference photo binding is disabled in this adapter.
A separately qualified v3 candidate-kind/set stage retains real SAM IDs, kinds
and nullable individual binding, before any photo correspondence call. It must
not turn an ambiguous set into an operator-supplied truth label. If a group
observable is needed, qualify and freeze that before requesting its values.
Restored consistent photos are documentary with generic SAM only, per the
pre-intake case03 scope; no invented restored suspicious-component correspondence.
The stage-specific compound auditor is fixed before its corresponding use.

Four offline checks use independent analytic source/DUT truth to establish:
two series10kΩ resistors with one changed to2.2kΩ leave both R1/R2 alternatives;
the two total-resistance fits agree with12.2kΩ; the input-capacitor profile uses
v4 rather than the rejected old hold; reserved OUT is excluded; and distinct
free DMM numbers retain changed:R1, changed:R2 or neither. These are software
checks, not claimed hardware or new Spark decisions. No API or hardware action
is performed during qualification.
