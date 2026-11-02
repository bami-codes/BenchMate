# Interactive D01 mock bridge — frontend handoff

The backend can now start a **new scripted mock** from a confirmed case design, pause at the
load and repair requests, accept matching simulated confirmations, and return the repair result.
It composes the frozen D01 repair session, numerical model, and the existing runner's
`operator_channel` UUID/file protocol. The original experiment runner is unchanged.

**This is software verification, not a new Spark or physical result.** No provider or physical
bench is constructed. API calls, serial commands and physical measurements are all zero.
The local question is not passed to a model. The frontend currently remains a recorded viewer;
connecting these endpoints is separate work. Do not enable or label this mode “Live”.

## Frontend ownership and display

Claude owns `case_review/index.html`, `app.js`, and `style.css`. This backend change does not
modify those files or the existing replay/timeline/event response shapes.

- Keep `Replay · Oct 30 · Physical record` distinct from `Scripted mock · Simulated`.
- Use `pending_request.instruction` for an actionable mock card. It explicitly says simulation
  only. Raw evidence preserves the frozen runner's physical wiring template; **do not render
  that template as a request to touch a real board during a mock**.
- Decisions in a new mock belong to `scripted_controller`, never Spark. The Oct 30 decisions
  still belong to the recorded Spark run.
- The repair forecasts are commanded-input forecasts saved before the two repair captures.
  `publication_label` is **Local mock freeze; not published remotely**. `published: true` in
  the frozen runner's receipt does not mean GitHub publication when `remote: false`.
- The Oct 30 diagnosis curves still use measured IN: model parameters were fixed beforehand,
  but the conditional voltage curves must not be animated as pre-measurement forecasts.
- Numerical completion is not success: only `result.repair_verified === true` supports a
  passed mock repair. `completed` with `false` is a completed, unsuccessful check.
- The question and schematic review are new. Neither is retroactively an input to Oct 30.
- Use a real specimen photo only when its state is established; otherwise label it illustrative.
  The recorded duration is a single run's elapsed time, not a benchmark of typical diagnosis time.

## Start and supported input

Use the existing `.venv` and the existing local `python -m benchmate.case_review` server.
Restart a previously started Python server to load the new routes. All routes remain loopback
only. Mutations require the current page's `X-BenchMate-Session` token and the same origin.

Create and explicitly confirm a case via the existing UI/API first. Launch accepts only a
sealed, eligible 10 kΩ / 1 µF reviewed design for the recorded example. The new launch file
pins its case revision, case manifest hash and reviewed-design hash. It copies the reviewed
design into the frozen repair contract without modifying the case manifest or historical data.

This is deliberately not arbitrary-circuit support. No user-supplied program, provider,
command-line argument, device path or waveform is accepted.

## Endpoints

| Method and path | Purpose |
| --- | --- |
| `GET /api/runner-capabilities` | Available mode, faults, timeout; `live_enabled: false` |
| `POST /api/cases/{case_id}/runs` | Start/idempotently recover a launch |
| `GET /api/cases/{case_id}/runs` | List runs attached to this case |
| `GET /api/runs/{run_id}` | Current state and pending operator request |
| `GET /api/runs/{run_id}/events?after=-1` | Up to 50 original, hash-verified events after cursor |
| `GET /api/runs/{run_id}/predictions` | Frozen mock repair forecasts, after local freeze |
| `POST /api/runs/{run_id}/respond` | Submit exactly one matching simulated confirmation |
| `POST /api/runs/{run_id}/cancel` | Cancel this bridge's own child process |

Launch body:

```json
{
  "revision": 3,
  "mode": "scripted_mock",
  "fault": "none",
  "launch_id": "11111111111111111111111111111111"
}
```

Generate a fresh 32-character lowercase hex ID once per explicit new run; persist it before
sending. If the network response is lost, query that ID or send the exact same launch body.
The same launch ID cannot spawn twice. Reusing it with different inputs conflicts. The mock
uses the same seeded development fixture each time; repetition is not independent accuracy data.

States are `running`, `awaiting_operator`, `cancelling`, `completed`, `failed`, `timed_out`,
`cancelled`, and `interrupted`. Only an owned running worker can receive a confirmation.
`interrupted` includes a record reopened without its original process owner; it never resumes.
If cancellation interrupted startup before a terminal experiment event, the cancellation marker
is preserved and `result` remains null; do not fabricate a completed experiment.

At `awaiting_operator`, build the response from the **current** `pending_request`:

```js
const p = snapshot.pending_request;
const response = {
  request_id: p.request_id,
  action: p.action,
  fixture: p.fixture,
  prediction_sha256: p.prediction_sha256,
  expected_boot_id: p.expected_boot_id,
  wiring_revision: p.wiring_revision,
  request_sha256: p.request_sha256,
  simulated: true,
  verbatim: "Operator's explicit software confirmation text"
};
// Only after the user explicitly confirms the simulated action:
for (const key of p.required_checks) response[key] = true;
```

`required_checks` retains the existing runner's report field names (including USB fields),
but the mock card and confirmation must say these are **simulated**. Do not populate them
from a stale card, merely by loading the page, or from speech/photo inference.

Disable the confirmation button while sending. A duplicate, stale request ID, wrong boot,
wrong wiring revision or wrong prediction hash is rejected without another acquisition.
On a lost response, poll the run; do not silently generate a new confirmation. Incomplete
confirmations may be corrected while the same current request is pending. Rejections are
preserved in the separate bridge audit. Cancellation body is `{"reason":"User cancelled"}`.

Load confirmation unlocks the loaded step and reserved diagnostic check. Repair confirmation
is not available until the diagnosis supports C change and the repair model/forecasts have
been frozen locally. It then unlocks the repaired step and the unused 4 Hz sine. Numerical
verdicts, new-boot checks and no-refit rules come from the frozen session.

Events retain their original `sequence`, `timestamp`, `kind`, `payload`, `previous_sha256`,
and `sha256`. Use `next_after` for the next page. Only complete newline-terminated,
hash-verified records are returned. `bridge_operator_response_consumed` distinguishes a
confirmation consumed by the worker from an HTTP submission merely accepted by the bridge.
`mock_rc_observation` contains the recorded mock waveform. `repair_prediction_comparison`
contains command-forecast and measured-IN conditional results separately.

## Limits, persistence and verification

- One active child per bridge; 100 retained runs per local output directory; 300 seconds per
  confirmation. A server shutdown stops its own worker. Restart never adopts a persisted PID
  or automatically retries a run. A worker orphaned by a hard server crash can only finish its
  bounded mock wait; it has no physical or paid-API path.
- Files are in the server's git-excluded output under `runner-runs/{run_id}/`. The launch,
  reviewed design, bridge actions, worker log, original event chain and terminal result are
  preserved. Private questions and operator text are not published by this feature.
- This is a local integrity mechanism, not an independently witnessed or remote-attested run.
- Pinned repair protocol SHA-256:
  `7eaecf38afb676465bad0619da2a49c4a773f313f797e108fcd7e93298b83824`.
  Its 17 source files must match before launch and again inside the worker.

```sh
.venv/bin/python -m pytest -q tests/test_case_runner.py tests/test_case_conversation.py tests/test_case_review.py tests/test_design_replay.py tests/test_known_design.py tests/test_d01_repair.py
```

84 tests passed on 2026-11-02, including 13 new subprocess/HTTP tests. They exercise both
blocking action requests, exact design transfer, forecast ordering, event pagination,
idempotent launches, duplicate/stale acknowledgments, cancellation, timeout, interrupted
ownership, protocol/event/forecast corruption, publication failure, stale boot, reset between
checks, unchanged capacitor and reserved-check failure. A full HTTP mock completes with five
simulated waveforms and no new API/hardware use. The first development test run exposed an
error-code mismatch for a stale load response sent at the repair stage; it was fixed before
these checks passed. These are software tests, not experimental benchmark trials.

Next: wire the redesigned frontend to this explicitly labeled mock mode, exercise its actual
buttons, then separately validate/authorize any future real-model or physical-run integration.
No UI repair button should claim a live repair based on this backend test.
