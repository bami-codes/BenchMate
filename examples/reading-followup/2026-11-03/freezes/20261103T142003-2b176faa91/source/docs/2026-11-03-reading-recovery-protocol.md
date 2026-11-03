# Restored case 01 recovery QA

The user selected power-off wiring check → **one** separately frozen HOLD-only
QA → a separately registered restored diagnostic follow-up only if QA passes.
The original first pair remains terminal failed and counted. Never reopen or
rewrite its chain, erase its failure, or substitute the development R01.

The operator checks R1 mini B3–B8 and its shared input/output columns, and reports
any correction while USB is off. Remaining restored wiring and the unloaded
fixture stay unchanged. This is recorded maintenance, not model-chosen diagnosis.

The QA plan snapshots all 107 preserved reading-pipeline sources, the new
`reading_recovery.py` and this note. Commit/push before execution. Use one fresh
unarmed USB boot, initial PING, >=10s wait and second PING, **ARM max 1**, then
**HOLD max 3** (512 frames each) at existing REF, and final PING. At most 11 serial
commands. No step, sine, model, API key read, paid request, firmware upload,
parameter fitting or automatic retry. Scope: one-boot HOLD repeatability only.

Reuse the actual frozen A3 guard and original PhysicalBench capture validation.
The original firmware A2 settling condition, clip limits, 20-count window, and
1.2s+5s settling timeout remain unchanged. Keep raw errors. First settling,
communication, timing, boot or electrical failure stops the run and requires
another operator strategy choice before any repeat. Do not reinterpret an error
packet as samples or bypass settling. Report raw firmware message alongside a
generic host validation error.

Successful QA does not mean the restored waveform diagnosis passed. Before the
next paid diagnostic follow-up, create a new linked record and fix its source,
budget and same diagnostic protocol/menu/reserved inputs. First failure remains
the first attempt; the follow-up is not silently substituted. No original frozen
source or successful fault/read observation is changed.

QA costs **Spark 0 / SAM 0 / $0**, about one minute after confirmed setup.
`python -m benchmate.reading_recovery verify <QA-folder>` checks its full chain
with standard-library-only code; no prediction was made so it is a QA integrity
check, not an experiment prediction PASS or proof of record creation time.
