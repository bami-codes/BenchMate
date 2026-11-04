# Photo binding follow-up after mixed-localizer input failure

Case03 pair `20261104T041918-d1084cbeb4` stopped before sending its
photo-binding Spark request. The decoder retained four native SAM objects and
one OpenCV fallback. The frozen v3 candidate builder indexed `native_object`
for every candidate; the OpenCV entry has no native SAM object. This raised
`KeyError` before provider creation. Actual photo-stage usage: **1 SAM,
0 Spark**, estimated **$0.0025** under the retained per-image tariff.

The original failed pair and all native masks remain unchanged and counted.
Its terminal diagnostic result, reading selection and published reading ranges
are preserved. This is an input-adapter failure, not a new physical diagnosis or
a new operator observation. No hardware, new photograph or SAM repeat is needed.

The additive v5 request builder keeps every selected candidate. Native SAM
geometry remains in exact SAM-input coordinates. OpenCV full-photo boxes are
scaled to the input with floor/ceil bounds, explicitly labelled as OpenCV;
they are never fabricated native masks. The full photo, intended schematic,
all retained candidate crops and confirmed port-only map are supplied. No part
values, private assembly, diagnostic fit or operator measurement are supplied.
The candidate parser, abstention semantics and no-value prompt are unchanged.

An offline plan binds the failed parent hash/head, every input, exact request,
source hashes and a public plan path. It is committed and pushed before any
follow-up call. **No follow-up executes until the user chooses it after the
failure.** A follow-up has a separate append-only record, at most one Spark,
zero SAM and zero hardware commands. It never removes or appends after the
original terminal failure. A unique correspondence still requires operator
confirmation; ambiguity retains all candidates and requires prospective group
qualification before numeric readings. One requested target is not a limit of
one observation for the case.

The retained failed pair is checked with the stdlib-only v4 compound auditor.
Offline validation reproduces the mixed SAM/OpenCV input and checks provenance,
all-candidate retention, crop integrity and exclusion of private truth. Building
the real prepared request also validates the actual retained image inventory
without any API or hardware access. These checks do not establish physical
component identity or authenticate future operator values.
