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
- Top of the landing, final (4 Nov evening, after 범수's review): an eyebrow in tape yellow (Muse Spark on a $40 Arduino
  bench · five real circuits, five sealed faults), the headline on one line across the full width (sentences never break
  mid-way; three lines on a phone), a two-line description, the two buttons, then the scope on the left and Drawn / Built
  on the right with a shared bottom edge. Nothing sits beside the headline; the three trust rows (forecast first / sealed
  truth / scored by code) live under the "Counted from the records" numbers. Phone nav: Cases / How it works / GitHub.


### Round 4h — the hero scope explains itself (4 Nov)

- The scope on the landing page is the first thing a judge sees, so it now says what its three lines are in plain words, in one strip across the top: `Experiment 1 · – – forecast from the drawing · — output, measured · — input, measured`. The two-item legend the replay uses is hidden in the hero; the mV/div readout sits bottom-left and the experiment settings (`Step, ±0.2 V, 9.99 kΩ load`) bottom-right as a footnote. On phones the strip wraps to two lines and the settings footnote is dropped.
- Under the scope, one sentence from the run file, symptom first: `Case 01 · Filter output too small. Spark chose 3 experiments, passed two checks on inputs it had never seen, and settled it with one multimeter reading. Watch how →` (the link opens the replay with autoplay). The caption keeps badge · case · date on one line and the forecast-miss sentence on its own line.

### Round 4i — case blocks read result first (4 Nov)

- Each run inside a case block now opens with its result in body type: `● Found it. One explanation left after one multimeter reading; the seal matched.` for the diagnosis, `○ Fixed, then rerun. No mismatch in the tests Spark chose.` for the restored rerun. One button per run (`Watch the diagnosis` / `Watch the rerun`, both autoplay), `Report` beside it, and two numbers at the end of the line: experiments and estimated cost. Dates, Spark and SAM call counts stay on the reports and in the registration details.
- The green `Official run · Spark did not know the fault` badge is no longer repeated five times; the section lede says it once: `10 official runs: a diagnosis on each faulted board, then the same procedure again after the fault was repaired. Spark was never told which fault was planted; the seal was opened only after its verdict.`
- Source lines read `site · thread title · Month Year`, with the month from `source.date` or, failing that, `source.date_label` (case 04); case 03 has no date in the data and shows none.

### Round 4j — The bench, for someone who has never seen one (4 Nov)

- The photo is the main object and now carries three numbered pins (Arduino, instrument board, mini board under test) with a three-line key under it; the pins mark boards, never parts, so the no-pairing rule is untouched. The lede says what the bench is in plain words: one Arduino, a small instrument board, the mini board with the drawing's circuit plus one sealed fault; the model never touches it.
- The right column answers two questions a stranger has: *who does what* (three cards in the replay's colours: Muse Spark asks, the Arduino measures, the operator acts only when asked) and *what the bench's own rules are* (a fixed menu, forecast before measuring, it checks itself). Each card ends with one real line from the Case 01 fault run, read from the run file: Spark's first choice and its reason in its own words, the Arduino's sample count and the forecast miss against the allowance, and the operator's jumper moves and one reading with ranges frozen first. The part that was read is never named here: the seal is closed on this page.
- The analogue signal chain (DAC → LM358 → 1 kΩ → board → LM358 → 14-bit ADC, REF 1.63 V, 9.99 kΩ load) and the six-row specification table are kept in full under `For engineers: signal chain and numbers`, closed by default.

### Round 4k — one box language, the replay's speaker dots, no holes in the grids (4 Nov)

- Colour on this site means one thing: the line or the speaker. The bench's three role cards had been filled purple, blue and yellow, which read as "forecast", "output" and "pilot / not counted" to anyone who had learned the scope and the badges. They are now the same paper-2 boxes as every other list item, with the replay notebook's 8 px speaker dots beside the names (Spark `--fc`, the bench `--tape`, anyone else `--ink-3`); the operator card alone is white with a dashed `--ink-3` border, the site's grammar for "on request".
- The lower sections: `#frontier` is headed `Why this matters` to match the nav; its six needs sit 3 × 2 from 900 px up. `How a run works` is fixed at four columns from 1000 px up and its eighth cell is the `Verify it yourself` card (filled check, two sentences, the command in a block, one Details link), which replaces the long footnote paragraph. The separate `Who does what` section is gone; its six-row table lives under `Built during the hackathon` as `Which model did what`, so the heading no longer collides with the bench's own `Who does what`. The repository link in `Open` is a button.
- The provenance note under the bench photo (taken from above, brightened uniformly, nothing else edited) is gone from the figure; it is a `Photo` row at the end of the engineers fold, so the key under the photo ends on the three boards.

### Round 4l — decks and fact strips instead of grey paragraphs (4 Nov)

- Every section had opened with the same shape: a heading and a four-line grey paragraph at 66 ch, with the right 40 % of the sheet empty. Each now opens with a one-sentence deck in body type at 19 px, full measure, and where the paragraph carried more than one idea the rest is a strip of short facts (a 2 px ink rule, a narrow bold head, one line of text) across the width: the cases (two runs per case · Spark was never told · same procedure · replays are the logs), why this matters (say what it expects · be held to it · keep going). Built lists what was made as plain tags after its deck; the score deck carries its `Updated` stamp at the far right. The bench and How a run works keep a single deck line, since their content is already laid out underneath.
- The bench photo is now the camera's own preview rendering of the ProRAW (Codex's `camera-preview.png`, exported without metadata), resized to 1200 × 1600 with no exposure, tone or colour edits; the earlier fixed-conversion render had needed a ×1.28 lift and still read dark. Mean brightness rose from about 62 to about 106 of 255. The three pins were re-placed for the new framing; provenance in `tools/photos-bench.json`.

### Round 4m — the replay before Play (4 Nov)

- The meter group now says what it is before anything moves: `Explanations on trial · how far each one's forecast misses the board; red past the 9 mV allowance` (the number from the run file), and every waiting meter's readout carries `allowance 9 mV` beside `waiting`. The caption is hidden in the compact shelf on desktop and kept above the chips on phones.
- The idle scope panel keeps one line under the drawing (`The drawing Spark read. Press Play below: every forecast is drawn before the bench measures.`) and points at the transport's Play. A second, larger Play inside the panel was tried and removed the same hour: two Play buttons on one screen make a stranger ask what the difference is, and the landing's links autoplay anyway.
- The notebook's first line says what the run is in the landing's words: `Diagnosis on the faulted board, recorded …` or `Rerun after the fault was repaired, recorded …`, with the model name only when the run file carries one. The short registration label (`Case 01 · Fault run`) stays beside the badge.

### Round 4n–4o — after two independent reviews (4 Nov, evening)

Two reviewers looked at the site without having built it: one as a judge with no prior knowledge, one as a front-end designer with the source. Bugs confirmed and fixed: the report printed the text `nullnull` under the board photo (native `append` stringifies null; the report root now drops null children); the experiment tables crushed the Value column and clipped the `Ruled out` ribbon (scope column fixed at 272 px, ribbons wrap, the mini scope's title hidden); the step headline said `missed by too much` for explanations that had been out since an earlier step (now `stay crossed out from an earlier step`); the phone nav on the replay and report pages was empty; the sticky rail used a `--shelf-h` nobody set.

Design changes from the reviews: the eyebrow is paper-white (the tape yellow failed contrast on the mat) and says `five hidden faults · every forecast made before the measurement`; the sub names Meta's Muse Spark and says it is scored by code against a sealed answer; the score is a 3 × 3 grid of horizontal tiles with `$1.01`; the fixed-menu note and the miss definition appear once per replay, not under every experiment; the shelf toggle says `Compact player ▴ / Full player ▾`; three meters sit three across; `--ink-3` darkened to #687079 for 4.6:1 on paper; focus rings are ink on paper; the `.elsewhere` bars match the other left bars; the red tape uses `--fault`; the `Open` button says `Repository on GitHub`; the two hero tiles' headings are paragraphs so the landing's heading order is h1 → h2.

Left as they were, on purpose: the second Play button in the idle scope (removed again: one Play per screen); the raw verifier PASS line on reports (it is the evidence); the qualifying sentences about what is not claimed.
