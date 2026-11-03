# Parallel-body correspondence and prospective nullable binding adapter

This is an additive experiment amendment, not a change to the 107 frozen
reading-v1 sources, numerical model, firmware, guard, prior scores or terminal
records. Claude owns presentation. The files here are experiment evidence and
an interface for subsequent orchestration, not frontend work.

## Case02 correction

The two capacitor bodies are **sam-2 and sam-3**, not sam-1 and sam-2. sam-1
is a wire connector. Both capacitor masks must be shown together as candidates
for `{C1,C2}`. Neither body is assigned a schematic identity. Spark's retained
reason correctly says the shared OUT–REF parallel connection cannot distinguish
the reference names from geometry alone. Selection of these two candidate masks
is a post-hoc visual review by Codex prompted by the operator; it is not a group
returned by Spark. All seven native masks remain intact.

The earlier question singling out the upper body as C1 is withdrawn. The operator
has now identified its printed marking as **474**. Preserve that statement as
an already received, non-blind `operator_marking` report about sam-2, not an
isolated capacitance measurement, a fresh prospective observation, confirmation
of the C1 label, or a Spark vision reading. No repeated photo or model call is
needed to represent the ambiguity.

Original parent `20261103T165506-b6ad3e8cf7` remains terminal `run_failed` on its
binding-format validator. Its completed child diagnosis `changed:C1` and reserved
validation remain unchanged. The new sidecar review references its head; no
event is appended to that terminal chain and it is not promoted to a completed
repair pair. It is not a new physical attempt or a replacement first attempt.

## Reading an exchangeable group

Do not declare the body nearest 0.1uF to be C2. Retain body IDs until comparing
all bijections between the observed pair and source-specific intervals for the
two schematic components. Keep every passing bijection. If none passes, reject
that explanation; if several survive, preserve the ambiguity. Only a unique
bijection under the surviving bounded explanation supports a **conditional**
mapping. Do not claim permanent physical identity or use a nearest-value rule.

Expanding Spark's existing C1 request to both parallel bodies is an explicit
**operator-requested amendment** prompted by failed correspondence. Do not
attribute the second requested reading to Spark. The generic pure-stdlib helper
`reading_unordered.compare_unordered` retains all assignments and does no fitting.
It is a low-level interval matcher, **not** a meter-qualification or observation
validator; calling it alone does not authorize measurements or official scoring.

Inherited training-only electrical envelopes, before meter allowance:

| Explanation | C1 actual uF | C2 actual uF | Role |
|---|---:|---:|---|
| changed:C1 | 0.4216965034–0.5623413252 | 0.095–0.105 | Existing sole survivor |
| intended nominal | 0.95–1.05 | 0.095–0.105 | Rejected terminal reference only |

The point estimate is about 0.471774uF for C1 with C2 held at its design value.
These are bounded engineering envelopes, not independently calibrated confidence
intervals and not an exhaustive set of all physical faults. The nominal row is
only a reference: if a new reading matches it while contradicting the survivor,
report that contradiction/all active explanations rejected. Do not resurrect
the nominal terminal hypothesis or rewrite the existing reserved verdict.

For **printed markings**, changed:C1 predicts no finite restriction on the C1
label (damage can leave a nominal label unchanged); C2 retains its nominal-label
allowance. A marking pair can document the fitted repair location and installed
nominal values but cannot measure actual capacitance or independently establish
an electrical fault. No model value candidates or votes enter this pipeline.

The existing meter rules remain capacitance `available:false`; they are not
edited. The operator has now confirmed capacitance mode, dial **2u**, open display
**0.000uF**. This new supplement permits only that **2uF full scale / 0.001uF per
count** range. Freeze an engineering acceptance allowance of **5% plus two counts
(0.002uF)**. This is not a manufacturer specification or an accuracy calibration.
The open display is capability/resolution evidence, not a calibration standard.
Do not accept OL, values at/above 2uF, a different range, coarser display, extra
invented digits, or unstable contact; stop and retain the issue instead of
changing bounds after seeing readings.

Range-adjusted actual-value intervals, uF (the exact SI values live in the
source-hashed `group-reading-forecast.json`):

| Explanation | C1 indicated uF | C2 indicated uF | Role |
|---|---:|---:|---|
| changed:C1 | 0.3986116783–0.5924583914 | 0.08825–0.11225 | Existing sole survivor |
| intended nominal | 0.9005–1.1045 | 0.08825–0.11225 | Rejected reference only |

Both bijections are compared. Bounds come from the pre-photo training catalog
and this declared meter allowance, not from the new marking or electrical
values. The supplement is registered/exported and the forecast is committed and
remotely confirmed **before** requesting new electrical readings. It records the
already received 474 report explicitly. New values are entered per body, with
USB-off, discharge-wait and isolation confirmations. USB must be disconnected,
power LED off, and the existing OUT–REF discharge path given ten seconds. Measure
each capacitor completely removed from the board or with one lead lifted; do
not measure the parallel sum and call it an individual value. Keep the two body
identities separate. The prior board photo documents body association; it is not
claimed to show the DMM screen. Actual values are operator reports, not images
independently authenticated by the software. No extra close-up is required.

This case is known, and the 474 report already exists. Neither the supplement nor
the group observation is a new blind test. The original pre-photo reading
forecast remains intact. No new meter forecast is claimed to precede the 474
marking report. A continuation of repair/restored diagnosis still needs its own
registration and publication, retaining this original failed parent.

## Nullable adapter, effective for future stages

`reading_binding_v2.binding_request` preserves the frozen v1 prompt, image inputs,
tool schema and single-request/no-retry behavior. Only parsing changes:

- JSON null is an abstention.
- The exact literal string `"null"` becomes an abstention, with `raw_arguments`
  and `normalization: exact_string_null_to_JSON_null_abstention` retained in a
  separate parser receipt.
- Existing candidate IDs remain proposals requiring operator confirmation.
- Any other string, list, guessed ID, extra field or invalid reason still fails.

Null does not mean successful correspondence or full-board coverage. The caller
must record the receipt and unresolved state. Do not infer a body from the
selected component, fit, marking or known construction. This adapter is available
for a prospectively registered continuation; **the frozen v1 CLI is unchanged and
still uses its original parser**. No API rerun or retrospective stage promotion
is made here. Tests compare the old/new request content byte-for-byte as Python
data and exercise string-null abstention, rejection, and corrupted crops without
network access. Unordered matching tests cover reversed pairs, all-rejected
values, overlapping assignments and reference-only matches.

The supplement contains a source-hashed registration, group JSON, parser review,
range-adjusted forecast, mask-derived overlay/provenance and hash-chained
events. The overlay uses the two **existing derived SAM body masks** on
the existing clean image; no generated body, segmentation, recoloring of the
source photograph, value inference or retouched part text is added. Both outlines
have the same candidate status. It is an annotation, not a new photograph.

This preparation adds **0 Spark, 0 SAM, $0, 0 hardware commands**. Existing
attempt2 totals remain 9 Spark, 1 SAM, estimated $0.11860230. The existing failed
record and complete valid fault diagnosis remain available to the offline
verifier. Integrity/order checks cannot prove creation time or physical truth.

## Supplement commands

`python -m benchmate.reading_group_experiment register` creates a separate record
under `runs/reading-groups/`, exports it to
`examples/reading-groups/2026-11-04/records/`, and binds the unchanged original
failed parent. This is a non-blind operator-reading supplement, not a new
physical diagnosis attempt, a replacement selected attempt or a completed repair.
It contains snapshots of this amendment and all added sources/tests. The 107
original frozen files must still match before registration.

After committing/pushing the exported forecast and registration,
`python -m benchmate.reading_group_experiment publish <local-record>` checks their
exact Git blobs and remote HEAD, then records the publication receipt.
`observe <local-record> <observation.json>` requires that receipt, accepts only
the frozen source/range/resolution with isolated readings, compares both
assignments and preserves any contradiction. It cannot command the board or
call a model. A completed supplement still does not claim a completed repair
pair. Repair/restored diagnosis remains a subsequent registered stage.

`python -m benchmate.reading_group_experiment verify <record>` audits this
supplement and its original parent in a fresh clone using only the standard
library, no keys or network. It checks source snapshots, bound artifacts, forecast
hash/publication order, observation precision/isolation declarations, deterministic
score and no post-terminal events. The parent remains independently verifiable
with `python -m benchmate verify <original-record>`. The new adapter is frozen and
available; the old CLI has not silently switched parsers. A future photo-stage
orchestrator must opt into v2 and record its normalization receipt.
