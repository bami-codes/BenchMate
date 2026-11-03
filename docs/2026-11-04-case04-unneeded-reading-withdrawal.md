# Case04: withdraw the non-discriminating R1 reading

The operator challenged the mandatory R1 measurement after `structure_supported`.
The caller had forced a reading-selection request after every successful fault
diagnosis. That is not a useful adaptive rule. In this case one bounded terminal
model survived, and the requested R1 value does not distinguish the remaining
physical-location ambiguity. A further component consistency check is possible,
but it is not required for the next action: remove the suspected external diode
and rerun the intended circuit in a fresh context.

This is a **post-diagnosis workflow correction after results are known**, not a
claim that the original mandatory-reading policy included this branch. Preserve
the completed diagnosis, every failed attempt, paid selection, published reading
forecast and all earlier event bytes. No R1 observation or score was collected;
do not claim the reading forecast was tested. Selection cost$0.00807645 stays in
the totals. No photo pixels or new component reading determined the withdrawal.

`structure_supported` alone is not the general stopping rule. An additional
reading is useful when justified alternatives predict different readings or it
is needed to locate the component to repair. The status does not prove unique
topology or physical location. The current R1 request met neither purpose.
Future cases must assess that need before spending a forced reading-selection
call, rather than mechanically asking for one value every time.

Withdraw R1 value entry/isolation and its body-binding request. The uploaded
original picture remains private and unprocessed; no SAM/body-binding call or
photo-based diagnosis is claimed here. Further documentary use can be separate;
it must not be described as evidence resolving the structure. No repeat restored
mini-board photograph is needed after external diode-only removal.

Append `operator_reading_cancelled`, then open the original assembly seal with
`after_reading_score:false` and `after_reading_cancellation:true`. The operator
removes the actual E30–E25 diode, retaining D23–D25 and the mini-board resistors.
The restoration event states that reading isolation was **not required**, rather
than pretending R1 was removed/reinserted. A new unarmed boot,>=10s wait and the
same frozen Spark menu/guards/fit/scoring/reserved inputs govern the rerun.

All107 original runtime files and the earlier photo-scope extension remain
unchanged. An additive audit in `reading_terminal_pair.py` preserves all their
reading hashes/publication, diagnostic child forecasts/order and seal checks,
while supporting explicit withdrawal without a fictitious reading score.
Completion is a terminal-measurement/restoration pair with a withdrawn extra
reading, not full execution of the original mandatory-reading path.

Verify the complete amended pair with
`python -m benchmate.reading_terminal_pair verify <pair-folder>`. The unchanged
original verifier still expects a completed reading. Both original child
diagnoses remain verifiable with `python -m benchmate verify <child-folder>`.
The new command is standard-library-only, key/network free. PASS establishes
internal hashes and recorded order, not creation time or actual wiring truth.
