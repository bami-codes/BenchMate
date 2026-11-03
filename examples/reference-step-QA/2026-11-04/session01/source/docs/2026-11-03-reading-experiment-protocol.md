# Reading-assisted experiment v1

This protocol implements the user's November 3 change. The experiment is a new
cohort, `reading-assisted-v1`, starting only after software, prompts, rules and
this document are frozen, tested, committed and pushed. Prior records retain
their original contents and registrations; the policy explicitly groups them
as development of this newer pipeline. Case 01 is known to developers and is
**not blind**, even with a fresh model context and new photographs.

Codex owns experiments and evidence. Claude owns all design, frontend and demo
work. This change does not edit those files or any frozen numerical/guard source.
The user's new instruction overrides the old prohibition on free operator input
only for the requested reading and explicit correspondence confirmation. Bench
rewiring confirmations retain the existing fixed English report choices.

## Prospective sequence

1. Register a new pair before any paid request or stimulus. Fresh Spark reads
   only the original intended schematic image; operator confirms its netlist.
2. Operator installs the faulted specimen with USB off; seal the exact assembly
   locally before diagnosis. Do not transmit it or the case mapping to a model.
3. Use the preserved A3-primary bench adapter and numerical engine. Spark picks
   training actions from the existing menu. Freeze/push terminal predictions
   before the same two reserved captures. No reserved OUT fitting or retries.
4. Generate a reading-explanation catalog from surviving terminal families.
   Exact series-R / parallel-C equivalents are additional physical-location
   hypotheses, not observed truths. They are generated without case labels.
   Verify their training predictions agree within 0.1mV; no new values fitted.
5. A fresh Spark request chooses **one component and one quantity** and gives a
   reason. The runner does not choose the component. The choice request gets no
   board photo, truth, prior runs or operator reading.
6. Freeze every explanation's source-specific reading interval and rules. Commit
   and confirm remote receipt **before any board-photo/binding request or value**.
7. New fault-state photo → SAM 3.1 generic `electronic component` → retained native
   masks and derived body crops. Reuse the pinned v2 geometric processing and
   explicit blue OpenCV fallback, but **never call its five-view value reader**.
   Every body, miss, geometry rejection and fallback is retained. Native masks
   are not rewritten. Lead coordinates are unknown unless independently found;
   supply full-board spatial context and never fabricate lead endpoints.
8. Spark receives schematic, clean full photo and indexed body crops and proposes
   correspondence with a reason or null. Operator confirms yes/no. If operator
   assigns instead, preserve the rejected proposal and label the final binding
   `chosen_by: operator`. A fallback mask is labelled OpenCV, never SAM.
9. Operator chooses an allowed source and enters a free numeric value, unit,
   selected meter range where applicable, and evidence photo. No explanation or
   answer choices are accepted. A DMM reading requires USB/power off and the
   component isolated from other paths (normally lift one lead), confirmed by
   the operator. Do not measure resistance on a powered circuit. Restore the
   lifted lead before the electrical rerun.
10. Deterministic source/range-specific comparison produces one survivor,
    multiple survivors, or none. Preserve every rejection and do not change
    intervals or refit. None means all declared explanations failed, not a new
    confirmed fault. More than one means unresolved.
11. Open the original sealed assembly only after reading score. Operator restores
    the intended specimen with power off. Fresh-context Spark diagnosis uses the
    same intended netlist, menu, guard and reserved inputs, with no fault-run or
    reading evidence. Take a new restored photo, SAM-localize and bind again.
12. Close the pair, preserving both state records, costs, failures and photos.
    Caption a consistent rerun **No mismatch in the tests Spark chose**.

## Observables and intervals

`operator_dmm` observes an actual isolated electrical quantity. `operator_marking`
observes a printed nominal value. They are not the same observation with different
error bars. A damaged original resistor can keep its old label: the broad
actual-value-change explanation therefore has an unconstrained printed nominal
interval `[0, null]`. A correct-looking label cannot rule it out. Numeric marking
input is the operator's decoded nominal, with the raw marking visible in evidence.

Changed-value DMM prediction intervals use training-only profiles: 33 logarithmic
grid values across the already bounded fitter domain plus its fitted value.
Evaluate the existing whole AND regional 9mV allowance on every training capture,
holding other parameters fixed. Enclose passing grid points and their adjacent
rejected brackets. A passing domain boundary gives an open end. These are coarse,
conditional **engineering envelopes, not calibrated confidence intervals**.
Unchanged parts use a declared 5% design allowance; no statistical meaning claimed.
Actual part tolerances are not retrospectively read from photos to narrow bounds.

The operator reports a `DM950?` meter with varying ranges. Manufacturer accuracy
has not been established. Freeze an engineering allowance of 2% plus two displayed
counts for allowed resistance ranges; it is not a claim of actual meter accuracy.
Record full scale in ohms and confirm resolution before scoring. Allowed ranges:
2k/1Ω, 20k/10Ω, 200k/100Ω, 2M/1kΩ. If the instrument displays fewer digits, a
different range, OL, unstable contact or lacks the needed quantity, stop rather
than changing the rule after seeing a value. DMM capacitance is disabled pending
capability confirmation. The top-level interval encloses all ranges, with each
range's tighter interval frozen in `rule.intervals_by_meter_range`.

The initial qualified numeric reading is case 01. Later presence/absence or W1
continuity requires an appropriate separately qualified observable, not a numeric
resistance or marking fiction. A SAM miss never proves absence. The active LED
hardware path remains blocked pending absolute-DC qualification.

## Events and files (experiment contract for Claude)

The pair folder is `runs/reading-cohort/<run-id>/`; its `events.jsonl` is the
parent chain. Child schematic, physical diagnoses, SAM and binding requests have
their own complete chains, bound into the parent by relative path, file SHA-256
and terminal event head. Preserve the complete folder when exporting evidence.

- `reading_requested`: `{component, quantity, reason, chosen_by:"muse_spark"}`.
- `reading_forecast_frozen`: `{schema, request, forecasts:[{explanation,source,
  low,high,unit,observable,rule}],catalog_sha256,rules_sha256,observation_received:
  false,photo_received:false,scope,sha256}`. `high:null` means no finite upper
  bound, not missing data. `reading_forecast_publication` records commit/URL/receipt.
- `reading_observed`: `{component,quantity,value,unit,source,meter_range,meter_resolution,photo:
  {file,sha256},power_off_confirmed,component_isolated_confirmed}`. `meter_range`
  is SI full scale for DMM, null for markings. `meter_resolution` is the SI value
  of one displayed count, also null for markings. Source-specific semantics apply.
- `reading_scored`: `{component,source,normalized_value,unit,fits,
  ruled_out_by_reading,outcome,forecast_sha256,observation_sha256,refitted:false,
  scope}`. Outcomes: `one_explanation_remains`, `all_explanations_rejected`,
  `indistinguishable`. No Spark surface-value candidate or vote enters scoring.
- `body_binding`: `{state,sam_body,component,chosen_by,reason,
  operator_confirmed:true,localizer,surface_values_used_for_scoring:false}`.
  `body_binding_proposed` preserves the original Spark choice, including null.

`reading-catalog.json`, `reading-forecast.json`, `reading-observation.json`,
`reading-score.json` and metadata-free `reading-evidence.png` are retained.
`photo-{faulted,restored}/prepared/` holds clean whole/full images, plans and SAM
children; `decoded/` holds native masks, derived crops and `body-manifest.json`.
`body-binding.json` stores final correspondence. The old v2 vote results remain
historical and are not inputs. No original DNG or GPS is published.

`python -m benchmate verify <pair-folder>` verifies parent/child hash chains,
diagnostic prediction hashes and capture order, reading hash/publication order,
body-confirmation order, deterministic source-specific scoring, sealed assembly
commitment and restoration sequence. It needs only the Python standard library,
no keys or network. PASS concerns internal integrity and recorded order; it
**cannot prove when records were originally written**, actual physical wiring,
the truth of an operator assertion, or authenticity without an independent hash
anchor. Protocol/source registration and pre-observation Git publication provide
additional process evidence; the offline verifier does not certify timestamps.

## Calls, authorization and failures

Implementation/verification use 0 paid calls and 0 hardware commands. Per pair:
one fresh schematic Spark, at most eight Spark per diagnosis (two), one reading
selection Spark, one binding Spark per state (two): at most **20 Spark + 2 SAM**.
No automatic repetition. Real usage and tokens remain in child chains and the
existing ledgers are retained. Standing user authorization covers necessary calls;
announce stage count/cost before sending, report actual usage, do not repeatedly
ask paid approval. A failed stage stops and remains counted; offer choices before
another attempt. Physical guards and the ten-second USB startup wait are unchanged.
