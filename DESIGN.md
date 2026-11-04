# BenchMate demo v3 — design notes

Concept: forecast first, measurement after. The replay is one recorded diagnosis played from its log in
order. Before each measurement the surviving explanations' forecasts are drawn (dashed) and their frozen
hash is stamped; then the measured trace sweeps over them and each explanation's needle moves to the miss
the fit engine logged. A needle that settles in the red (above the 9 mV allowance) gets its explanation
struck and a label-tape stamp. Nothing moves that the log did not record.

Palette (tokens in assets/v3.css): ESD-mat blue-grey #5c6b76 background with a faint dot grid; paper
#fbfbf8 for the notebook and cards; scope #0e1315 with graticule #27343a; cream meter faces #f4ecd6;
jumper colours IN #1f9a52, OUT #2b6bdc, REF #8b949b; forecast violet #7a4fd6; fault/red zone #d5342c;
label tape #f3d25a. Type: Archivo Narrow (headings, labels, instrument text) + Archivo (body).

Pages
- index.html (assets/landing.js): the scope first (the first recorded experiment's measurement sweeping
  over its frozen forecast, on loop), the drawing and the board tile, the claim, replays, six cases, how a
  run works, who does what, scoreboard read from data/results.json (pending until official runs).
- run.html (assets/replay.js): the instrument shelf (scope + meters + one transport row: Play, one speed
  button cycling 1×/4×/16×, scrubber, seal, counters, Report) and the lab-notebook stream, with a sticky
  right rail on desktop (the drawing Spark read, bench state). Idle: the drawing sits in the scope and
  every standing explanation waits at 0. One voice: every block's headline is a plain sentence from a
  per-state template (BM.words), numbers from the log; technical detail sits under it in small text.
  Spark's choice blocks show the whole fixed menu as chips with the pick solid. Model calls are folded
  into the block they belong to, with the role named. Ruled-out meters go dead. Clicking any number,
  hash, needle or verdict opens the evidence popover (run id, sequence, kind, UTC/KST, sha256,
  previous_sha256, copy JSON). Ends at the real guard stop for the pilots, with the ground-wire note;
  counted runs get the seal-opening scene; a structure proposal is drawn as the full proposed circuit.
  ?run=<id>, ?t=<seconds>. ?devsrc= loads a tools/ fixture (development only, watermarked DEV).
  Removed in round 2: "Ask me first", the Plain-words layer, Restart, the three speed buttons, the miss
  bars in the fit table, standalone call blocks, placeholder boxes, "Video coming".
- case.html (assets/report.js): the notebook flattened: stats, model input in its context frame, forum
  Cause/Kept/Changed/Source, every experiment with a static scope and the miss table, the check, outcome,
  hidden fault overlay, repair rerun. Print button.

Data: data/runs/<id>.json from tools/extract_runs.py (reads a Codex run folder; see its docstring).
Round 2 follows docs/2026-11-03-site-evidence-contract.md: classification from run metadata (never a
CLI flag; unknown → "Not counted (unclassified)"); every rendered event keeps its envelope (sequence,
timestamp, sha256, previous_sha256); structure_proposed/structure_fit joined by id with a netlist diff;
the verification chain (frozen models, publication commit, reserved_prediction_scored.conditional,
netlist_verification_completed survivors, agent_report.verdict) copied as written; photo files from the
photo-run root (vision components with reading_status, SAM <concept>-decoded.json masks; never
auto-paired). data/official-run-policy.json is a copy of the preregistered order and selection rule.
tools/make_dev_fixture.py builds tools/DEV-structure-run.json from Pilot A plus Codex's MOCK structure
example to exercise the proposal scene; it is watermarked and never listed.
Wording rule: a restored rerun's verdict is "No mismatch in the tests Spark chose", never "nothing wrong".

Honesty: every number is read from the data files; pilot data is labelled "Pilot run — not counted"
wherever it appears; forum cases are paraphrased with links, no usernames or quotes; the red overlay is
drawn only after the seal opens and was never part of the model input.


## Round 3 (accuracy, dedupe, fills)
- Needles and fit tables show the number that decided pass/fail: the worst of the whole-step RMS and every
  region RMS (`decided_mV`, `worst_region` from tools/extract_runs.py). The evidence popover carries
  `decided_by`, the whole-step RMS and the regions (name, samples, RMS, passed).
- The extractor refuses an explanation that names a part outside the case's reviewed design
  (`check_against_design`). The DEV fixture now uses the example's own R1/R2 hypotheses for case 04.
- Verification stage: `verification_observed` (held-back measurement over its frozen forecast) and
  `verification_scored` (compared by code) render before the verdict; a report with fewer scored inputs
  than reserved inputs gets an "incomplete" card first. The reserved input's index is its order in the run.
- Removed duplicate headlines (experiment, bench), duplicate schematic at idle (scope area only; the rail
  drawing card appears once traces are on the scope), the hero's "Dashed/Solid" paragraph (one caption line).
- Idle notebook shows the case's forum line, Source, Kept, Changed.
- Dates: "3 Nov 2026, 01:08 KST" / "3 Nov 2026, 01:09:16 KST". Default run per page: first counted run for
  the case (`BM.defaultRun`), else the earliest pilot; pilots move under "Development records" once any
  counted run exists. Hero line templates: guard stop / check passed / check failed / several survivors.

## Round 4 (4 Nov evening: five cases, one photo treatment)
- Cases 05 and 03 ingested; case 06 (LED) removed from the site after the operator cancelled it (the frozen
  six-case order stays in `data/official-run-policy.json` as a record; the landing names only the five cases
  that ran). Extractor modes `--pair-wire` (05: structure proposal → the engine splits the one surviving
  proposal into two placements of the same series resistance, Spark picks the W1 path reading, bands frozen,
  Spark names the body, isolated reading, seal; restored rerun from the counted frame-timing follow-up, with
  the pair's own abstained attempt 1 named on the report and in the end scene) and `--pair-chain` (03: one
  restored root record carrying the original pair, the photo-binding follow-up and the reading continuation;
  the pair's local stop before Spark's body call is a notebook entry, not hidden).
- One photo treatment for every case (`tools/photo_derivatives.py`): the same 960×720 window of the 1200×1600
  SAM input, one uniform brightness lift, otherwise untouched; a transparent outline layer (3 px label-tape yellow, 1 px dark edge) drawn only
  from native SAM 3.1 masks that a record ties to a part or a candidate; documentary images (every native
  mask) behind a details toggle only. Case 01's yellow crop, case 02's green full-frame contours and Codex's
  green context crops for 03/05 are replaced by this one rule. Provenance per case in `tools/photos-case0N.json`.
- Verdict wording checked across all ten counted runs: fault runs end in a "Found: …" sentence from the data
  (value, proposal, or placement); every restored rerun ends in "No mismatch in the tests Spark chose", and
  where nearby value-change models also fit, the "What this does not say" card names them.
- `tools/shots_all.js`: every counted run at 1440 and 390 played at 16× to the verdict, landing and all reports;
  errors.txt must read "none".
- Landing restructured for the judges' first minute: claim → scope → "Counted from the records" strip → one block per
  case (fault replay + restored rerun + report, outcome line from the index) → "The bench" (the whole-bench photo,
  `assets/photos/bench-full.jpg`, cropped and brightened uniformly from Codex's metadata-free render, provenance in
  `tools/photos-bench.json`, plus an inline SVG of the signal chain and a Source / Recorder / Reference / Allowance /
  Operator / Cost table) → How a run works → Who does what (Spark vision, Spark agent, SAM 3.1, engine, bench, operator)
  → Built during the hackathon (dates, Meta models, what is new, what is not claimed, open). The separate "Watch a
  diagnosis" list is gone: the runs sit under their case, so the numbers read 01–05 once.
- First screen, looked at coldly (4 Nov evening): the scope and the Drawn/Built tiles share a bottom edge (the Built photo
  fills the remaining height, object-fit cover); the hero sentence names its numbers ("Spark chose 3 experiments; two
  held-back checks passed; one multimeter reading of R1 settled it") and the run caption sits directly under it; the
  at-a-glance rows are three light rules, not boxes, so the headline stays the loudest thing; Watch / Replay buttons
  carry `?play=1` and the replay starts on arrival; buttons and run rows have hover and active states; the idle scope
  no longer appends a literal "null". Copy across the landing was cut to one or two lines per element; registration and
  display rules sit behind a details toggle.

