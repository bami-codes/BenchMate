# Photo v2 frozen; case 01 is nonblind reconfirmation

01-R01 completed first, with **No mismatch in the tests Spark chose**. Its
independent official record and operator restoration pair are published.
Photo-v2 implementation began 20:44 KST. Final source/settings were pushed in
`8d2002d` before surface reads. The first prospective image has not been captured
or tested. Case 01 remains development/nonblind reconfirmation.

Validation: 61 main tests and two image tests passed with zero API/hardware
access. The final policy has 13 source snapshots; all 87 official runtime
sources remain unchanged. A real nonblind smoke test used one generic SAM
request plus 15 surface requests for three retained body candidates.

SAM found resistor, capacitor, board and connector. All four native masks remain.
A geometry-boundary correction reapplied the 25% area limit after body-hull
construction; the board was excluded before surface calls. That source change,
prior policy and initial geometry artifacts remain published. The same SAM
response was explicitly reused; there was no second localization call.

| Body | Derived photo candidate | Support | Interpretation |
|---|---:|---:|---|
| Visible resistor | 46 kohm | 2/5 | Weak and differs from operator-declared R1; not a confirmed part value |
| Blue capacitor | 1 uF | 4/5 | Code-decoded candidate; one mirrored request was incomplete at the token limit |
| Connector | null | 0/5 | No supported numeric code |

4.7 kohm is retained among resistor candidates with 1/5 primary support and
additional alternative transcriptions. No candidate or rule was changed to
match the known assembly. The photo does not establish R1=4.7k or a unique
external 20k contribution. View agreement is not accuracy. The improvement is
that observations are preserved and decoded separately, not a claim of reliable
resistor vision. All 15 view event chains are retained: 14 completed, one failed.

The v2 cost estimate is $0.15268140 Spark + $0.0025 SAM = **$0.15518140**.
This official-case-and-photo scope now totals **42 Spark + 3 SAM**, estimated
**$0.37308860**. Earlier ledgers remain; these are usage-based estimates, not
invoices. No hidden reasoning text, GPS or source DNG is published.

## Site/README/video handoff for Claude

Do not edit old photo results into numeric successes. New file locations:

- `examples/photo-v2/2026-11-03/frozen-v2-final/policy.json`: final source/settings.
- `case1-nonblind-final/decoded/body-manifest.json`: native/derived-mask links,
  localizer, exact five view files/hashes and source coordinate boxes.
- `case1-nonblind-final/decoded/results.json`: `components[].raw_views` links
  every native response. `components[].decoded` is **code-derived**, not native
  Spark numeric output.
- `case1-nonblind-final/decoded/review.json`: evaluation label, actual calls,
  event heads and limitations.
- `examples/official-runs/2026-11-03/analysis/01-R01/restoration-pair.json`:
  completed faulted follow-up and restored run; first-fault failure stays primary.

The compact card uses `decoded.value_si`, `kind`, `vote_count/view_count` and
the label **photo candidate**. A null stays null. Display a tie note when
`ties:true`; detailed alternate values and per-band tallies are expandable.
There is no three-state UI requirement. Never label 5/5 as confidence/accuracy.
Support counts concern the decoded value only: an example's tolerance/voltage
fields do not inherit that count and must not be shown as a voted device rating.

`schematic_ref` remains null pending explicit component binding; SAM index,
left-to-right order and model-assigned names are not automatically circuit IDs.
Use `localizer` to distinguish SAM-derived body masks from OpenCV fallback.
Neutral-background masks are software derivatives, not native SAM outputs.

Photo-only contexts never receive the intended schematic or measured diagnosis.
Current official runs remain measurement-first, followed by independent photos
and explicit posthoc comparison. Do not narrate these photos as having chosen
earlier experiments. New prospective capture must occur after `8d2002d`; a local
file time alone is not independent proof of capture time or full blinding.
