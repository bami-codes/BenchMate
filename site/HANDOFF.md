# BenchMate demo site — handoff (updated 4 Nov 2026, evening)

Read this first if you are continuing the site, README, video or submission work from a
session that only has the GitHub repository. Everything the site needs is in this repo.
The person you work for is 범수 (bami). He is the only operator at the bench; Codex (another
agent) runs the experiments and writes the records under `examples/` and `docs/`; the site
under `site/` is ours. Deadline: submission target 4 Nov 22:00 KST, hard deadline 5 Nov 11:00 KST.

## 1. What exists and where

- Live site: https://bami-codes.github.io/BenchMate/ (deployed from `site/` to the gh-pages root;
  the older replay site lives under `/archive/`). Deployed by Codex until the five-case release; from
  then on the GitHub session deploys itself (see §7).
- `site/index.html` + `assets/landing.js`: landing (claim, hero scope, Drawn / Built tiles, the scoreboard strip from
  `data/results.json`, one block per case with its fault replay and restored rerun, development records, the bench
  section, how a run works, who does what, built during the hackathon).
- `site/run.html` + `assets/replay.js`: the replay (instrument shelf + lab notebook). `?run=<id>`,
  `?t=<seconds>`. The shelf collapses (toggle + auto on scroll, state in localStorage).
- `site/case.html` + `assets/report.js`: the post-run report (dossier) per run.
- `assets/common.js`: shared helpers — `BM.words` (per-state plain headlines), `BM.fmtSI`,
  `BM.defaultRun`, evidence popover, equivalence/proposal wording, `verdictWords`.
- `assets/v3.css`: tokens and layout. `DESIGN.md`: design notes and round history (round 4 = five cases).
- `data/cases.json`: the five cases 01, 02, 03, 04, 05 (symptom-only text before the seal; `cause`,
  `kept`, `changed`, `title_after_reveal` shown only after the seal / in the report). Forum facts were
  verified against the threads on 3 Nov; keep them paraphrased, no usernames, no quotes. Case 06 (LED)
  was cancelled by the operator on 4 Nov after the five results and is not on the site at all.
- `data/runs/<id>.json` + `data/runs/index.json`: one replay file per run, produced by
  `tools/extract_runs.py` from Codex's records. `data/results.json`: scoreboard numbers.
- `data/official-run-policy.json`: copy of the preregistered order/selection policy plus the
  display rule added 4 Nov (see §3). It still lists the frozen six-case order; the landing prints only
  the order of the cases that ran.
- `assets/photos/`: metadata-free derivatives only (never a DNG/original), all made by
  `tools/photo_derivatives.py` with one framing and one outline rule; provenance for each case in
  `tools/photos-case0N.json`. `case01-board-crop-full.png` / `case04-board-crop-full.png` are the clean
  hero/Built crops from the full-resolution renders; `case01-reading-evidence.png` is the DMM evidence image
  linked from the evidence popover only.
- `assets/photos/bench-full.jpg` + `tools/photos-bench.json`: the whole-bench photo for "The bench" section (from
  `examples/bench-photos/2026-11-04/full/render.png`, cropped, brightened uniformly, no metadata). The inline SVG signal-chain
  diagram lives in `index.html`; its facts come from `docs/build-your-own.md` (DAC → LM358 follower → 1 kΩ → IN; OUT →
  follower → ADC; buffered REF ≈ 1.63 V; 512 frames per capture; 3 mV guard; 9 mV allowance; 9.99 kΩ load); the Recorder row's sample
  periods (0.5, 2 or 4 ms) are the `period_us` values in the counted runs' step settings, not a fixed 0.5 ms.
- `tools/verify-case0N.json`: outputs of the keyless verifiers (run on the public copies), copied into the
  report's "Verify it yourself" box as written.
- `tools/shots_all.js` (every counted run, both viewports, landing, all reports), `tools/rewind_check.js` (every counted
  run: a seek — scrubber, Jump-to, `?t=` — must equal a forward play to that time; `_shots/rewind/errors.txt` must say "none"), `tools/shots*.js`,
  `tools/overflow.js`: Playwright checks (console errors, 390 px overflow, 16× play-through). Run after every
  change with a local `python3 -m http.server --directory site 8795`; `_shots/all/errors.txt` must say "none".
- `tools/DEV-*.json`, `tools/make_dev_*fixture.py`, `tools/fixtures/`: development fixtures built
  from Codex's MOCK examples. Watermarked "DEV", never listed, never shipped as real.

## 2. State of the cases (4 Nov evening)

| Case | Title on site (before seal) | Status | Records used |
|---|---|---|---|
| 01 | Filter output too small | official, complete: fault run with one reading (R1 4.71 kΩ, multimeter) → seal → restored rerun | `examples/reading-cohort/2026-11-03/records/20261103T125924-bf8f64512b/` (fault, reading, photo, seal), `examples/reading-followup/2026-11-03/records/20261103T142003-2b176faa91/` (restored) |
| 04 | Divider reads wrong | official, complete: structure proposal (D1 OUT→REF) verified → restored | `examples/reading-cohort/2026-11-03/records/20261103T150223-18d6f08ac9/` (terminal pair, reading withdrawn), amendment `docs/2026-11-03-case04-20k-design-amendment.md` |
| 02 | Erratic sensor board | official, complete: C1 changed → two isolated capacitor readings decide which body is C1 → restored | fault `…/20261103T165506-b6ad3e8cf7/`, readings `examples/reading-groups/2026-11-04/records/20261103T174217-008035637b/`, restored `examples/reading-restored-v2/2026-11-04/records/20261103T182550-4ea22cc3a0/`, Spark candidate reprocessing `examples/photo-reprocess/2026-11-04/case02-candidates-v3/` |
| 05 | Volts lost on a breadboard | official, complete: structure proposal (series R in place of the drawn wire W1, fitted 19.85 kΩ) verified → engine splits it into two placements → Spark asks for the W1 path reading (0 Ω on the 2 kΩ range) → off-board placement fits → seal (20 kΩ at large E35–E31) → restored attempt 1 **abstained** (counted) → restored attempt 2 consistent (counted, shown) | pair `examples/reading-cohort/2026-11-03/records/20261104T021333-c80ef3617e/` (fault, wire-path reading, photo, seal, abstained restored child), restored attempt 2 `examples/channel-timing/2026-11-04/records/20261104T034748-10ab5af750/` |
| 03 | Blinker stops after one cycle | official, complete: R1/R2 indistinguishable at the terminals → Spark asks for R1 → bands frozen → photo, SAM → the pair stopped on a local input error (counted failure, shown as a notebook entry) → Spark named sam-1 as R1 in a follow-up → R1 read 2.22 kΩ → seal (R1 2.2 kΩ) → restored rerun consistent, documentary restored photo | one root record `examples/reading-cohort/2026-11-03/records/20261104T051005-fac3d07c86/` (original pair under `history/reading/history/original/`, follow-up under `history/reading/history/body-followup/`, reading under `history/reading/`) |

Pilots (2 Nov, case 01) are listed under "Development records" and labelled "Pilot run — not counted".
Case 06 (LED) was in the frozen order but was never run and was cancelled by the operator; it is not
counted as a success or a failure and does not appear on the site (`docs/2026-11-04-five-case-submission-scope.md`).

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
   record: Spark's `body_binding` / candidate selection (case 01: sam-1 → R1; case 03: sam-1 → R1; case 05:
   sam-1 → W1, all operator-confirmed; case 02: Spark picked sam-2/sam-3 as capacitor bodies, identity decided
   by the readings). Photos are shown as clean crops of the SAM input, one window for every case; outlines
   only from native SAM masks that a record ties to a part or a candidate, one style (3 px label-tape
   yellow, dark edge). No dimming, no site-drawn labels on parts beyond the "<part> — SAM 3.1 mask" tag.
5. Wording: a restored rerun's verdict is exactly "No mismatch in the tests Spark chose". Never
   "nothing wrong", "repaired", "blind". Badge before the seal: "Official run · Spark did not know
   the fault"; Codex's full classification ("reading-assisted cohort · known to developers, not
   blind") only on the report's classification line and in evidence popovers.
6. Readings: Spark chooses the component and the quantity; the operator chooses the method
   (`operator_dmm` / `operator_marking`) and types a free value; bands per explanation and per
   source are frozen (and pushed) before the reading; scoring is the engine's `reading_scored` as
   written. A marking confirms the nominal value, not today's resistance. The "Try any value" box
   is a client-side what-if on the frozen bands, collapsed, shown only after the verdict.
7. Equivalence groups (e.g. "R1 changed" vs "an extra resistor between IN and R1"; case 05: the two
   placements of the proposed series resistance) are an ENGINE RULE, labelled "engine rule — electrically
   equivalent"; structure proposals exist only when every value hypothesis failed (cases 04, 05). Fitted
   values at a fit bound show "≥ 10 µF (fit limit)".
8. Display rule (written 4 Nov, after results): each case's replay is the first official attempt
   that reached a diagnostic verdict with the board matching the registered fault wiring. Attempts
   stopped before a verdict, or with wiring that differed from the registration (checked by photo),
   stay in the repository ledger and the attempt counts but are not rendered on the site — no
   per-case failure callouts, no DMM photos on cards (the DMM evidence image is linked only from
   the evidence popover). Amendment (4 Nov evening, case 05): where a restored attempt reached a verdict
   other than consistency (05: abstained), the counted later attempt is the restored replay and the earlier
   one is named, with its verdict and engine report, in the end scene and on the report. A record that
   stopped on a local error after its diagnostic verdict (03) shows that stop as a notebook entry. The
   ledger (`examples/…`, `docs/…`) is public, which is what keeps this honest.
9. One voice, fewer elements. Every block's headline is a plain sentence from a per-state template
   (`BM.words`); technical detail sits under it. No second "plain words" layer, no participation
   gimmicks, no duplicated headlines, no placeholder boxes. Before adding an element ask: what would
   a judge miss without it? No answer → leave it out.
10. Never reuse MuseCell's phrases or layout (competitor: https://aleksandrahodzzik.github.io/musecell/).
    Our identity: ESD-mat background, paper notebook, dark scope, cream needle meters, label-tape
    verdicts, jumper colours IN green / OUT blue / REF grey.
11. English only on the site. Korean is for talking with 범수 (direct, casual, no hedging).
12. Five cases, not six. Never "5/5 accuracy", never "all first attempts succeeded": completed-case counts are
    not an accuracy rate; failures, abstentions and follow-ups are preserved and named.

## 4. How to add or re-extract a case

1. Read Codex's result docs for the case under `docs/2026-11-0N-case0N-*.md` first; they state
   what happened, what was withdrawn, and the verify command lines.
2. Pick the extractor mode in `tools/extract_runs.py` (all take `--case 0N --label "Fault run" --rates tools/rates.json --photos tools/photos-case0N.json`):
   - `--pair <pair folder>` for a reading-assisted pair with the reading inside the pair (case 01 shape);
   - `--followup <record> --label "Restored rerun" --pair-of <fault run id>` for a restored follow-up record;
   - `--pair-terminal <pair folder> --amendment tools/amendment-case0N.json` for a terminal pair with
     fault + restored children and a withdrawn reading (case 04 shape);
   - `--pair-group <pair folder> --group <reading-groups record> --restored <reading-restored-v2 record> --extra <folder>`
     for the unordered two-body reading shape (case 02);
   - `--pair-wire <pair folder> --restored <channel-timing follow-up record> --verify tools/verify-case05.json`
     for the wire-path reading shape with a counted restored follow-up (case 05);
   - `--pair-chain <restored root record> --verify tools/verify-case03.json` for the chained layout whose
     root carries the original pair and the reading under `history/` (case 03).
   Codex's record layouts changed between cases; if a new case uses yet another layout, extend the
   extractor (keep envelopes: run id, sequence, timestamp, sha256, previous_sha256) rather than
   hand-editing JSON. `check_against_design` must keep refusing explanations that name parts not
   in the reviewed design.
3. Photos: add the case to `PHOTOS` in `tools/photo_derivatives.py` (the SAM input, the native-mask folder,
   the masks a record ties to a part/candidate) and run it; it writes the crop, the outline layer, the
   documentary image and `tools/photos-case0N.json`. `--apply` re-points the already extracted runs 01/02/04.
   Never copy a DNG or anything with EXIF/GPS.
4. Verifiers: run the keyless commands on the public copies and paste the PASS lines into
   `tools/verify-case0N.json` (the report prints them as written).
5. Regenerate `data/results.json` from the records (cases run, fault diagnoses completed,
   structure proposals, readings, seals matched, restored reruns, Spark/SAM calls, estimated cost —
   use the cohort totals from Codex's docs; say per-case figures if a total is ambiguous).
6. Run `node tools/shots_all.js`, read `_shots/all/errors.txt` and `log.txt`, look at the end-scene
   screenshots, then commit and deploy (see §7).

## 5. Remaining work (priority order)

0. README: rewritten 4 Nov evening (five cases table, bench, Meta models, verifier outputs, the failure ledger, the
   prototype-of framing, earlier development results). Screenshots for it live in `site/assets/readme/`.
1. README (notes kept for reference): frame as "a diagnostic tool for the first power-on of real hardware";
   tagline "BenchMate's experiments did not exist until the model asked for them."; who does what
   among Meta models (Muse Spark vision reads the drawing and points at bodies; Muse Spark agent
   chooses experiments and proposes structure; SAM 3.1 segments the board); the five cases with one line
   each and a link to each report; the honesty rules; the preregistered policy and the 4 Nov display rule
   with its case-05 amendment; the verify commands with the PASS lines from `tools/verify-case0N.json`
   and the docs; the failure classification Codex wrote (failures were miswiring / contact / host bugs /
   a timing-model limit; the diagnosis never returned a wrong answer; the miswired case abstained, the
   05 restored attempt 1 abstained). Link the live site.
2. Video (2:58, done): https://www.youtube.com/watch?v=BFlJHOEapV8. `video/film/` composes every frame from `site/data`
   (`shots.html` + `shots.js`), renders at 60 fps (`render.js`, `SCALE=1.3333333` for the 2560×1440 upload master), and
   `audio.py` mixes a synthesized bed, sound effects and the ElevenLabs narration (`voice/s1…s7.mp3`, George; word timings in
   `voice/timings.json` drive the shot starts via `plan_shots.py`). No burned-in captions; `narration_srt.py` writes the CC file.
   Earlier drafts were removed from the tree on 5 Nov and remain in the history.
3. Submission text: `docs/submission.md` (full and short versions, and the three form answers as submitted on 5 Nov, team 2828): theme fit (models meeting the real world),
   rubric (Impact 30 / Tooling 25 / Tech 20 / Demo 25), bonus "Best Agentic"; five cases; do not call it an
   education chatbot, dashboard or image analyzer.

## 6. Known gaps / things not to claim

- Spark call durations for some selection/binding calls are not in the parent logs (cost/tokens only).
- Case 04: an earlier draft of the drawing said R2 22 kΩ; it was publicly amended to the available 20 kΩ part before
  any measurement. The counted pair (`20261103T150223-18d6f08ac9`) read the amended image (intake
  `20261103T144919-80c4654879`, transcription 20 kΩ), so `assets/schem/design-04.svg` shows 20 kΩ, the same drawing as
  `examples/netlist-diagnosis/designs/2026-11-03-stock/design-04.svg`; the 22 kΩ draft is kept as
  `assets/schem/design-04-draft-22k.svg` (not referenced by any run). The amendment note on the site comes from
  `tools/amendment-case04.json`; the extractor refuses it unless the intake transcription matches its `image_value`.
- Case 02's Spark candidate selection was a post-hoc photo-stage reprocessing (4 Nov) and is
  labelled so on the site.
- Case 05: the restored rerun shown is attempt 2 on the frame-anchored timing model (qualified and
  published before it); attempt 1 abstained and is counted. The reading is of the isolated wire path,
  not a part value; the DMM number is an operator report (no meter photo).
- Case 03: the original pair's photo-binding step stopped on a local KeyError; Spark's body call and the
  reading happened in linked records. The fault diagnosis itself is complete and verified.
- Case 01's hero caption is the official fault run; pilots stay as development records.
- SVGs written through the device bridge carry a C2PA signature; pixels are identical. Spark inputs
  always go through Codex's pixel-sanitising path, never raw files from the site.
- Totals (101 Spark, 6 SAM, ≈$1.01) are retained-tariff estimates from recorded tokens, not invoices.

## 7. Working agreement for a GitHub-only session

- Work on `main` (범수's decision, 4 Nov): change only `site/` (and the README / submission files), run the
  checks, commit with a message that says which records were ingested, push `main`. Codex commits
  records/engine; do not edit `src/`, `examples/`, `docs/` except to add a site handoff note. If Codex
  also touched `site/` since your last sync, rebase on it first — never overwrite.
- Deployment (범수's decision, 4 Nov: the GitHub session deploys): gh-pages root = `site/` contents
  (without `_shots/`, `__pycache__`), keep `/archive/` and write `deployment.json` (source commit, site tree,
  previous gh-pages commit, release cases, validation summary) as Codex did. Use a git worktree of
  `origin/gh-pages`, replace the root files, commit, push.
- Never commit originals (DNG), `.private/`, `_stage/`, or anything with GPS/EXIF.
- Ask 범수 before adding any UI element not described here. He rejects features that are not
  needed, and he is right.


## Status, 4 Nov 2026 evening (Claude)

- Demo complete and deployed: landing (hero scope with plain-word key, result-first case blocks, labelled bench photo with role cards, section decks and fact strips, 3 × 3 score), replay (meter caption, plain run sentence, one Play, verdict card with Spark's answer over the planted fault), reports (same card, tables that fit, no `null` text). Design rounds 4h–4p are described in `DESIGN.md`.
- Two independent reviews (judge with no prior knowledge; front-end designer) were run on 4 Nov; what was fixed and what was deliberately left is in `DESIGN.md` under rounds 4n–4p.
- Site-wide rule learned the hard way: the engine checks the seal's digest, it does not compare the answer with the truth; the site prints both and never a `match` of its own.
- The old `web/` builder and root `PRODUCT.md` / `DESIGN.md` were removed from main on 4 Nov (history keeps them). No demo film exists; `video/` holds pipeline drafts only.
- Deploy procedure: run `python3 site/tools/check_data.py` from the repository root first (every id in `site/data/runs/index.json` must exist and be tracked by git; the 4 Nov 404s came from the root `.gitignore`'s `runs/` rule), then commit on the working branch, push to `main`, rebuild the `gh-pages` root from `site/` (keep `archive/`), write `deployment.json`, push. The landing reads `site/data/census.json` (a view of `docs/2026-11-04-official-attempt-census.json`, hash recorded) for the attempt denominator. GitHub returned transient 500s on pushes during the evening; retry with backoff worked every time.
