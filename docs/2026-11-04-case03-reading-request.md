# Case03 first reading request, before photo/value

Pair: `examples/reading-cohort/2026-11-03/records/20261104T041918-d1084cbeb4/`.
The physical pair is in progress. Fault terminal verdict is indistinguishable
between changed:R1 and changed:R2; no operator component reading has occurred.

Spark's actual first request is **R1 resistance**, reason:
“Distinguishes changed:R1 vs changed:R2: first predicts R1 actual ~2-3k,
second predicts R1 stays ~10k nominal.” It also noted that a damaged resistor
may retain a10k marking, so an isolated electrical resistance observation is
more informative than its printed nominal value.

Source/range forecasts were frozen and pushed before photo/value in commit
**8b03b3fe4ca1f03355cc22c443d8ea676d661d1c**, forecast SHA256
`7da515e9e84a08812b19ba36f1154bed5727527ec78ec3cca63a1a28745caa14`.
For the prospective20kΩ DMM range with10Ω display resolution, the indicated
intervals are:

| Explanation | R1 indicated interval |
|---|---:|
| changed:R1 |1,992.455–3,245.523Ω|
| changed:R2 |9,290–10,730Ω|

All allowed ranges/sources and their different error allowances are retained
in `reading-forecast.json`, not selected after the value. Ranges include a
prospective engineering meter allowance, not manufacturer-calibrated accuracy.
No reserved OUT, photo or private assembly was used to set these intervals.

The operator correctly clarified that this is **not a one-part-only rule**.
The first request is not a cap on total observations. The photo stage retains
every plausible model-selected SAM body. If R1 cannot be uniquely located,
preserve the group and freeze a qualified group observable before asking for
its values; do not force an operator-supplied reference label. Reading both
equal-nominal series resistors may identify an abnormal physical body while
R1/R2 names remain unresolved; that remaining ambiguity must not be erased.
The clarification was recorded and published in **d3c449e** before any photo
or operator value. No value has yet been requested from the operator.

The board remains operator-confirmed USB-off, faulted and unloaded. Next is a
new whole mini-board photograph; generic SAM localization and Spark body
correspondence follow, with the confirmed connector map but no numeric part
values. No hardware action or new stimulus is needed for that stage.

New selection usage:1 Spark, estimated **$0.00672045**. Case03 so far:
**8 Spark,0SAM,$0.07098025**. Reading cohort plus labelled case02 demo:
**94 Spark,4SAM,$0.93874215**, retained tariff estimates rather than invoices.
Next photo stage plan:1SAM +1Spark, about$0.015–0.03. No surface-value model
reader, vote ensemble or extra closeup photograph is planned.
