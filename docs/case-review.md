# Question → recorded experiments → an answer with evidence

P0 and the recorded-conversation part of P1 are implemented. The screen connects a new local
question and schematic review to the Oct 30 physical D01 record, then walks through Spark’s
choice, the bench’s wiring request, model comparison and sourced answer. It makes **zero new
model requests** and has **no hardware execution routes**. A separate scripted mock backend is now
available; its frontend controls are not yet connected. See [the runner API contract](case-runner.md).

## Start

Use the existing checkout environment, including Pillow:

```sh
.venv/bin/python -m benchmate.case_review --port 8770
```

Open <http://127.0.0.1:8770>. A separate P1 QA preview runs on port 8771. Both local servers
use the new code; their saved case libraries remain separate. No API key, USB board or installation is needed.
The CLI reads pinned examples from this checkout; it is not a standalone wheel application.

1. Enter a question about the recorded D01 example.
2. Check R1’s value and IN–OUT connection, and C1’s value and OUT–REF connection against the schematic.
3. Click **Confirm design & explore record**. The explicit button action creates the review and,
   when eligible, the link. No mandatory note or checkbox is required. The generated action note
   is labeled as generated in the manifest; it is not attributed as user prose.
4. Advance with **Next step**, **Back**, **Play replay**, or the event slider. Hypothesis states,
   plots and the answer follow the selected prefix. Reload restores the selected event from the URL.
5. Click a measurement or waveform link to open its graph. Prepared follow-up questions open
   answers from this record, not newly generated model responses. **Event** links show original
   payloads and hashes in Evidence. The full old viewer is available as a separate link.
6. Return via the saved-case selector or download the local case history from Evidence.

A different circuit can be saved as a question, but this archive cannot diagnose it. Unreadable
values may remain blank and nodes may stay `UNKNOWN`; neither unlocks the record. Linked designs
are sealed. The repair button is disabled: this replay contains no repair.

## Independent origins and responsibility

| Item | Source | Display rule |
| --- | --- | --- |
| Question / design review | Current local operator | Never an input to the historical run; not sent to Spark |
| Schematic reading | Spark, synthetic image, Oct 31 | Separate reading of the same nominal design |
| D01 experiment | Spark + physical bench, Oct 30 | Protocol supplied nominal 10 kΩ / 1 µF; no image-reading step |
| Initial/load reasoning | Spark tool arguments, events 7 / 52 | Original Korean plus “Translated for this screen” |
| Load choice | Event 50 menu; event 52 action | Load test over repeating the unloaded step; two available choices |
| Wiring instructions | Runner template, event 54 | BenchMate; operator confirmation appears only from event 55 |
| Reserved check | Spark’s empty-argument request, event 97 | Spark asks; protocol specifies the 5 Hz waveform |
| Answer / follow-ups | Screen summaries with event references | Observations, assumptions and unresolved questions remain separate |

`design_replay.load_demo` verifies the pinned image, vision/result records and physical event chain.
`case_review.evidence.RecordedConversation` additionally pins the physical bytes and derives each
conversation snapshot from only the selected prefix. It does not fit models, reconstruct curves,
call a provider or operate hardware. These verified snapshots stay in memory until restart.

Models become visible at event 49, before loaded acquisition. Conditional voltage curves appear
only at events 94 / 133, using the predictions already recorded with the measured IN. The graph
uses all 512 output samples, channel-specific acquisition times, and the separately measured HOLD
origin. RMS is taken from the full recorded array, not the plotted shape or rounded labels.
A model passes only if its recorded overall **and regional** checks pass: nominal RC’s reserved
RMS is 8.54 mV but it still fails regional checks. The UI preserves that failure.

## Local contract and gates

`benchmate.case_session.v1` still stores question, design review and replay link. Its photo,
new-measurement, new-answer and current-operator-request fields remain empty. The separate
`benchmate.recorded_conversation.v1` read view contains historical hypotheses, plots and an
answer; it does not write a new experimental result into the case manifest.

Each mutation creates a hash-chained `revision-NNNN.json` in git-excluded `.private/case-review/`.
Previous revisions are never overwritten. This detects corruption, not externally attested identity
or wholesale rewriting of the local history. Exported questions and private notes are not committed.

The server checks each case, current revision, supported RC topology/range, resolved values,
matching 10 kΩ / 1 µF, and recorded-example scope. Stale or duplicate actions conflict. Unknown
or mismatched reviews are saved but remain blocked, and can be corrected without losing history.
Confirmation always submits the current form; unsaved changes cannot reuse an older review.

The loopback service keeps the local Host/Origin and per-server mutation-token requirements.
Recorded-case mutations: create, review, link-replay and confirm. Separate run routes start, confirm or
cancel a scripted mock (see the runner contract). Read-only timeline/event routes require
an eligible linked case and a bounded cursor; original-event reads cannot exceed it. There is no
upload, free-form model-response, serial/DAC, arbitrary command or live-run endpoint. A client
request timeout never automatically retries a mutation. Reload the saved case before retrying.

## Verification — 2026-11-02

```sh
.venv/bin/python -m pytest -q tests/test_case_conversation.py tests/test_case_review.py tests/test_design_replay.py tests/test_known_design.py
node --check src/benchmate/case_review/app.js
```

44 related tests passed. Coverage includes every event prefix (0–139), rewind without future
results, source actors and menu, exact 512-point curves and RMS, regional failure, invalid cursor,
case-specific gates, stale confirmations, revision corruption, archive preservation and HTTP origin guards.

Native Chrome checks: question → unknown C blocks → corrected C confirms → first recorded steps;
final answer → “Could it be the resistor?” updates the loaded waveform. At 400 CSS px the ledger,
waveform, labels and prepared-question waveform link were inspected. The source API was also
checked against the original event and hash. Local QA cases are software fixtures, not user reviews
or new physical evidence. Original physical runners, shared engine, firmware and experiment bytes
are unchanged. Font and OFL license are bundled locally.

## P1 bridge backend; frontend integration next

The [interactive mock bridge](case-runner.md) now transfers the exact reviewed design into the frozen
D01 repair session and uses the existing runner’s operator request/response channel. Thirteen new
subprocess/HTTP checks cover both confirmations, stale/duplicate input, cancellation, timeout, boot
changes, local prediction freezes and numerical failures. The combined related suite has 84 passes.
These are scripted simulated captures, with zero new Spark or hardware use.

Claude owns the frontend redesign. Its controls still need to connect to the new mock endpoints and
be tested in the browser; P1 is not yet complete end to end. Live remains unavailable. Fresh image
intake, photo/component matching, SAM repair highlights and real repair execution remain separate steps.


## P2 photo references — backend available

The [photo evidence API](photo-evidence.md) supplies separate historical fixture photos, the
photo-local grid, all five previous SAM trial outcomes, and the two masks on their exact input.
Local photo observations are saved in their own revision history; the sealed case manifest and
runner confirmations stay unchanged. No photo is asserted to show the Oct 30 or current specimen.
The new frontend can consume these endpoints; its photo controls have not yet been connected.
This adds no new model/API call, measurement or automatic wire-recognition accuracy result.
