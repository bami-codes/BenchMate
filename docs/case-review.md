# Question → design review → recorded evidence

P0 of the [v3.0 implementation plan](photo-bench-implementation-plan.md) is implemented.
The local screen saves a circuit question, reviews a recorded schematic transcription,
and opens a matching recorded D01 experiment. It makes **zero new model requests** and
has **no hardware execution routes**. It is a product-flow prototype, not a new end-to-end physical run.

## Start

From the repository checkout, using the existing development environment (including Pillow):

```sh
.venv/bin/python -m benchmate.case_review --port 8770
```

Open <http://127.0.0.1:8770>. No API key, USB board or package installation is needed in the prepared project environment.
The CLI reads the pinned example files from this checkout; it is not a standalone installed-wheel application.

1. Save a question about the recorded D01 example.
2. Check the schematic. Review R1's value and IN–OUT connection, and C1's value and OUT–REF connection.
3. Add a review note and save the review. Unknown values can remain blank; unknown nodes stay `UNKNOWN`.
4. Open the matching recorded experiment. The scene buttons navigate to the unexpected response,
   Spark's load request, the model comparison, and the reserved-input verification.
5. Use the saved-case selector to return later, or download the case JSON from Evidence.

A different circuit can be saved as a local question, but this archive cannot diagnose it.
The current question is not submitted to Spark. Existing recorded reasoning and conclusions appear in the replay.

## Three independent records

| Record | Origin | Relationship |
| --- | --- | --- |
| Question and design review | Current local operator entry | Not an input to the archived experiment |
| Intended schematic reading | Spark, synthetic schematic, 2026-10-31 | Reviewed nominal R/C values |
| Physical D01 experiment | Spark + physical bench, 2026-10-30 | Same nominal design only; no shared specimen state asserted |

`design_replay.load_demo` verifies the pinned vision event chain, result, input PNG and physical event chain
before the server opens. The case references their original hashes. It does not write to those archives.
The server serves its verified in-memory snapshot until restart.

The replay retains its original labels: physical development experiment, recorded operator requests,
conditional curves calculated using measured IN, and no repair performed in that run.
No historical request becomes a current wiring instruction.

## Local case contract

`benchmate.case_session.v1` is implemented for P0: question, source design, operator review and replay link.
Photo observations, component mappings, capture state, measurement registry, hypotheses, new answers
and current operator requests remain empty. Their presence in the manifest is not an implemented capability.

Each change creates `revision-NNNN.json` under `.private/case-review/<case-id>/`, which git excludes.
Each revision includes its manifest hash chain and the prior revision hash. Older files are not overwritten.
The export includes the current manifest hash and revision-record hash. This detects modified or incomplete
revisions during reads; it is **not external attestation** or protection against someone rewriting all local files.
Private questions and review notes are not included in the committed QA report.

Handoff gates are checked on the server for the specific case and current revision:

- No review, unknown value/node, ambiguity, unsupported topology or unsupported value range: blocked.
- A reviewed design different from 10 kΩ / 1 µF, or a different specimen: blocked.
- Another case's review does not unlock this case.
- Old revision or duplicate link: conflict; no automatic mutation retry.
- A linked case is sealed against design edits. Start a new case for a different design.
- Unsaved form edits disable the link until the new review is saved.

The loopback HTTP service requires its local Host/Origin and a per-server session token for mutations.
It accepts bounded JSON on three routes: create, review, link-replay. No prompt execution, upload,
serial/DAC, arbitrary command, image extraction or live-run route is provided. Session tokens stay local.

## Verification — 2026-11-02

```sh
.venv/bin/python -m pytest -q tests/test_case_review.py tests/test_design_replay.py tests/test_known_design.py
node --check src/benchmate/case_review/app.js
```

31 tests passed. They cover provenance, archive preservation, per-case isolation, incomplete and unsupported
designs, stale/duplicate confirmations, concurrent link attempts, reload persistence, corrupt revisions,
HTTP origin/session guards, strict request fields, exports and absent execution routes.

Native Chrome UI checks completed the desktop question → review → replay flow, selected the actual Spark
load request and final waveform, and reloaded the linked case. At 400 CSS px the question and review forms
were checked; a blank C value was saved and blocked the replay link. Unsaved changes showed the blocking
message. A subsequent corrected review was confirmed in the server's persisted record; the final mobile
redraw was not established through the native browser tool. Mobile replay layout was not fully inspected.

All 84 preexisting tracked files under `src/`, `scripts/` and `firmware/` retained their pre-P0 SHA-256 values.
This check excludes the new module and does not imply a new physical experiment or benchmark result.

## Next: P1

Build event-backed answers and a separate bridge to the existing supported runner contract.
Validate its operator-request lifecycle using the mock bench before enabling any live workflow.
Fresh image intake, direct nominal input, arbitrary circuit questions, photos linked to the current specimen,
SAM highlights, and live repair execution are not enabled by P0.
