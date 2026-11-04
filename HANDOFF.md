# BenchMate demo site — handoff (written 4 Nov 2026, 14:40 KST)

Read this first if you are continuing the site, README, video or submission work from a
session that only has the GitHub repository. Everything the site needs is in this repo.
The person you work for is 범수 (bami). He is the only operator at the bench; Codex (another
agent) runs the experiments and writes the records under `examples/` and `docs/`; the site
under `site/` is ours. Deadline: submission target 4 Nov 22:00 KST, hard deadline 5 Nov 11:00 KST.

## 1. What exists and where

- Live site: https://bami-codes.github.io/BenchMate/ (deployed from `site/` to the gh-pages root;
  the older replay site lives under `/archive/`). Deployed by Codex on request so far; a GitHub-only
  session may commit `site/` itself — agree the rule in §7 first.
- `site/index.html` + `assets/landing.js`: landing (hero scope, Drawn / Built tiles, replays, cases,
  how a run works, who does what, scoreboard from `data/results.json`).
- `site/run.html` + `assets/replay.js`: the replay (instrument shelf + lab notebook). `?run=<id>`,
  `?t=<seconds>`. The shelf collapses (toggle + auto on scroll, state in localStorage).
- `site/case.html` + `assets/report.js`: the post-run report (dossier) per run.
- `assets/common.js`: shared helpers — `BM.words` (per-state plain headlines), `BM.fmtSI`,
  `BM.defaultRun`, evidence popover, equivalence/proposal wording.
- `assets/v3.css`: tokens and layout. `DESIGN.md`: design notes and round history.
- `data/cases.json`: the six cases (symptom-only text before the seal; `cause`, `kept`, `changed`,
  `title_after_reveal` shown only after the seal / in the report). Forum facts were verified
  against the threads on 3 Nov; keep them paraphrased, no usernames, no quotes.
- `data/runs/<id>.json` + `data/runs/index.json`: one replay file per run, produced by
  `tools/extract_runs.py` from Codex's records. `data/results.json`: scoreboard numbers.
- `data/official-run-policy.json`: copy of the preregistered order/selection policy plus the
  display rule added 4 Nov (see §3).
- `assets/photos/`: metadata-free derivatives only (never a DNG/original). Provenance for each
  case in `tools/photos-case0N.json`.
- `tools/shots*.js`, `tools/overflow.js`: Playwright checks (console errors, 390 px overflow,
  16× play-through). Run them after every change: `node tools/shots_official.js` etc. with a local
  `python3 -m http.server --directory site 8790`.
- `tools/DEV-*.json`, `tools/make_dev_*fixture.py`, `tools/fixtures/`: development fixtures built
  from Codex's MOCK examples. Watermarked "DEV", never listed, never shipped as real.

## 2. State of the cases (4 Nov 14:40)

| Case | Title on site (before seal) | Status | Records used |
|---|---|---|---|
| 01 | Filter output too small | official, complete: fault run with one reading (R1 4.71 kΩ, multimeter) → seal → restored rerun | `examples/reading-cohort/2026-11-03/records/20261103T125924-bf8f64512b/` (fault, reading, photo, seal), `examples/reading-followup/2026-11-03/records/20261103T142003-2b176faa91/` (restored) |
| 04 | Divider reads wrong | official, complete: structure proposal (D1 OUT→REF) verified → restored | `examples/reading-cohort/2026-11-03/records/20261103T150223-18d6f08ac9/` (terminal pair, reading withdrawn), amendment `docs/2026-11-03-case04-20k-design-amendment.md` |
| 02 | Erratic sensor board | official, complete: C1 changed → two isolated capacitor readings decide which body is C1 → restored | fault `…/20261103T165506-b6ad3e8cf7/`, readings `examples/reading-groups/2026-11-04/records/20261103T174217-008035637b/`, restored `examples/reading-restored-v2/2026-11-04/records/20261103T182550-4ea22cc3a0/`, Spark candidate reprocessing `examples/photo-reprocess/2026-11-04/case02-candidates-v3/` |
| 05 | Volts lost on a breadboard | planned, not run | — |
| 03 | Blinker stops after one cycle | planned, not run | — |
| 06 | Dim LEDs | planned, needs DC calibration; may stay "not run" | — |

Pilots (2 Nov, case 01) are listed under "Development records" and labelled "Pilot run — not counted".
If 05/03/06 are not run by submission, the site must say so plainly ("planned, not run") — never
imply six completed cases.

## 3. Rules that are not negotiable (agreed with 범수)

1. Every number on the site comes from a data file that was extracted from a record. Nothing is
   typed in by hand, nothing is recomputed except per-token cost at the published rates.
2. Forecast first, measurement after. The replay draws forecasts (dashed) with their frozen sha256
   before the measured trace. Needles and tables show the value that decided pass/fail: the worst
   of whole-step RMS and every region RMS (`decided_mV`), with "worst region: …".
3. No spoilers before the seal opens: before the end scene only the symptom and the Source link
   appear (replay idle header, landing hero caption, case rows). Cause / Kept / Changed /
   `title_after_reveal` appear only in the end scene and the report.
4. The site never pairs a SAM body with a drawing part. Pairing shown on the site must come from a
   record: Spark's `body_binding` / candidate selection (case 01: sam-1 → R1, operator-confirmed;
   case 02: Spark picked sam-2/sam-3 as capacitor bodies, identity decided by the readings).
   Photos are shown as clean crops; outlines only from native SAM masks that a record ties to a part
   or a candidate. No dimming, no site-drawn labels on parts.
5. Wording: a restored rerun's verdict is exactly "No mismatch in the tests Spark chose". Never
   "nothing wrong", "repaired", "blind". Badge before the seal: "Official run · Spark did not know
   the fault"; Codex's full classification ("reading-assisted cohort · known to developers, not
   blind") only on the report's classification line and in evidence popovers.
6. Readings: Spark chooses the component and the quantity; the operator chooses the method
   (`operator_dmm` / `operator_marking`) and types a free value; bands per explanation and per
   source are frozen (and pushed) before the reading; scoring is the engine's `reading_scored` as
   written. A marking confirms the nominal value, not today's resistance. The "Try any value" box
   is a client-side what-if on the frozen bands, collapsed, shown only after the verdict.
7. Equivalence groups (e.g. "R1 changed" vs "an extra resistor between IN and R1") are an ENGINE
   RULE, labelled "engine rule — electrically equivalent"; structure proposals exist only when every
   value hypothesis failed (case 04). Fitted values at a fit bound show "≥ 10 µF (fit limit)".
8. Display rule (written 4 Nov, after results): each case's replay is the first official attempt
   that reached a diagnostic verdict with the board matching the registered fault wiring. Attempts
   stopped before a verdict, or with wiring that differed from the registration (checked by photo),
   stay in the repository ledger and the attempt counts but are not rendered on the site — no
   per-case failure callouts, no DMM photos on cards (the DMM evidence image is linked only from
   the evidence popover). The ledger (`examples/…`, `docs/…`) is public, which is what keeps this
   honest.
9. One voice, fewer elements. Every block's headline is a plain sentence from a per-state template
   (`BM.words`); technical detail sits under it. No second "plain words" layer, no participation
   gimmicks, no duplicated headlines, no placeholder boxes. Before adding an element ask: what would
   a judge miss without it? No answer → leave it out.
10. Never reuse MuseCell's phrases or layout (competitor: https://aleksandrahodzzik.github.io/musecell/).
    Our identity: ESD-mat background, paper notebook, dark scope, cream needle meters, label-tape
    verdicts, jumper colours IN green / OUT blue / REF grey.
11. English only on the site. Korean is for talking with 범수 (direct, casual, no hedging).

## 4. How to add a case (the pattern used for 01, 04, 02)

1. Read Codex's result docs for the case under `docs/2026-11-0N-case0N-*.md` first; they state
   what happened, what was withdrawn, and the verify command lines.
2. Pick the extractor mode in `tools/extract_runs.py`:
   - `--pair <pair folder> --case 0N --label "Fault run" --rates tools/rates.json --photos tools/photos-case0N.json`
     for a reading-assisted pair with the reading inside the pair (case 01 shape);
   - `--followup <record> --case 0N --label "Restored rerun" --pair-of <fault run id>` for a
     restored follow-up record;
   - `--pair-terminal <pair folder> … --amendment tools/amendment-case0N.json` for a terminal
     pair with fault + restored children and a withdrawn reading (case 04 shape);
   - `--pair-group <pair folder> --group <reading-groups record> --restored <reading-restored-v2 record> … --extra <folder>`
     for the unordered two-body reading shape (case 02).
   Codex's record layouts changed between cases; if a new case uses yet another layout, extend the
   extractor (keep envelopes: run id, sequence, timestamp, sha256, previous_sha256) rather than
   hand-editing JSON. `check_against_design` must keep refusing explanations that name parts not
   in the reviewed design.
3. Photos: copy only metadata-free derivatives (`photo-*/conversion/render.png`, `prepared/input.png`,
   native SAM masks/overlays) into `assets/photos/`, record provenance in `tools/photos-case0N.json`.
   Crop the hero/Built tile from the full-resolution render; no outlines on it.
4. Regenerate `data/results.json` from the records (cases run, fault diagnoses completed,
   structure proposals, readings, seals matched, restored reruns, Spark/SAM calls, estimated cost —
   use the cohort totals from Codex's docs; say per-case figures if a total is ambiguous).
5. Run the checks (console errors, 390 px overflow, 16× play-through on every run, idle/mid/end
   screenshots), look at the screenshots, then commit (see §7).

## 5. Remaining work (priority order)

1. If Codex delivers case 05 (contact resistance; second structure-proposal candidate) or 03,
   ingest as in §4. Case 06 (LED) needs the probe-path card (COL→47 kΩ→OUT, OUT→10 kΩ→REF, GND≠REF)
   already supported in the replay.
2. README (repo root): frame as "a diagnostic tool for the first power-on of real hardware";
   tagline "BenchMate's experiments did not exist until the model asked for them."; who does what
   among Meta models (Muse Spark vision reads the drawing and points at bodies; Muse Spark agent
   chooses experiments and proposes structure; SAM 3.1 segments the board); the honesty rules;
   the preregistered policy and the 4 Nov display rule; the verify commands
   (`python -m benchmate verify <run folder>`, `python -m benchmate.reading_terminal_pair verify …`,
   `python -m benchmate.reading_closeout verify …`) with the PASS lines from the docs; the failure
   classification Codex wrote (all failures were miswiring / contact / host bugs; the diagnosis never
   returned a wrong answer; the miswired case abstained). Link the live site and each case report.
3. Video (≤3:00): record the replay itself with Playwright/CDP screencast at 1920×1080 (see MuseCell's
   `scripts/record_video_clips.py` for the approach); scenes: landing fold → case 01 replay (forecast
   first, needles, reading, seal) → case 04 structure proposal → case 02 two readings → scoreboard →
   verify command output. No generated imagery, no music with rights issues, English captions.
4. Submission text: theme fit (models meeting the real world), rubric (Impact 30 / Tooling 25 /
   Tech 20 / Demo 25), bonus "Best Agentic"; do not call it an education chatbot, dashboard or image
   analyzer.

## 6. Known gaps / things not to claim

- Spark call durations for some selection/binding calls are not in the parent logs (cost/tokens only).
- Case 04's schematic image shows R2 22 kΩ; the intended R2 was publicly amended to 20 kΩ before
  measurement (the note is on the site; the amended drawing `design-04-r2-20k` exists under
  `examples/netlist-diagnosis/designs/2026-11-02/`).
- Case 02's Spark candidate selection was a post-hoc photo-stage reprocessing (4 Nov) and is
  labelled so on the site.
- Case 01's hero caption is the official fault run; pilots stay as development records.
- SVGs written through the device bridge carry a C2PA signature; pixels are identical. Spark inputs
  always go through Codex's pixel-sanitising path, never raw files from the site.

## 7. Working agreement for a GitHub-only session

- Branch from `main`, change only `site/` (and the README / submission files), run the checks, commit
  with a message that says which records were ingested, open a PR or push to `main` as 범수 decides.
  Codex commits records/engine; do not edit `src/`, `examples/`, `docs/` except to add a site handoff
  note. If Codex also touched `site/` since your last sync, rebase on it first — never overwrite.
- Deployment: gh-pages root = `site/` contents (keep `/archive/`). Codex has done this with a script;
  ask 범수 whether Codex deploys or you do.
- Never commit originals (DNG), `.private/`, `_stage/`, or anything with GPS/EXIF.
- Ask 범수 before adding any UI element not described here. He rejects features that are not
  needed, and he is right.
