# English experiment workspace

The workspace is an evidence-review surface for the hackathon demonstration. One event reducer and renderer serves an exported replay and a running software log. It does not drive the board, trigger API requests, or certify hardware.

## Open a reviewed result

```sh
uv run benchmate view examples/discovery-story-english --output runs/discovery-report.html
```

Open the HTML locally. Fonts, interface code and the hash-verified record are embedded; no CDN, external script or API is needed. Replay exposes events in order. Before a verification acquisition, only predictions are visible, with recorded versus reconstructed provenance. Later observations and checks are withheld when navigating backward.

## Follow a running experiment

```sh
uv run benchmate watch runs/YOUR_RUNNING_SESSION --port 8765
```

Open the printed loopback URL. The read-only server follows complete JSONL lines, checks the hash chain, and streams verified prefixes to the same UI. Partial writes are withheld. Origin/Host checks reject other hosts and origins; the server binds only to 127.0.0.1. Stop it with Ctrl-C.

Use the timeline to inspect an earlier event; **Follow live** returns to new events. Connection errors remain visible until a valid update arrives. A changed prefix or corrupt record stops updates and requires investigating the source before reload. A live log of a synthetic instrument is labelled **Synthetic observations / Live log**, never live hardware.

## Reading the screen

- Solid orange is observed output; gray dashed is the best RC fit among the declared families; blue dashed is the engine simulation of Spark's structure. Training curves are explicitly labelled **fit**. On a reserved discovery condition, gray becomes the **Frozen RC prediction**, with no refitting, and blue is the **committed prediction** of the proposal. A caption distinguishes reconstructed RC counterfactuals in older records. Drive is optional. All curves use the same axes and match every condition field, including REF. A residual strip shows observed minus model in mV on a common scale; it is not a calibrated confidence band.
- After the verification check, the selected condition displays both OUT RMS errors and whether one, both, or neither model passes. **Both pass · weak discrimination** means that condition does not reject the frozen RC. Evidence retains per-condition RMS/peak error, full noise-normalized regional checks, and RMS/peak separation between predictions. Separation is descriptive, not a calibrated power estimate; a failed best RC does not rule out every alternative circuit.
- The completed discovery view selects the training condition with the largest RMS difference between the RC and proposed fit. Before the proposal is fitted, it selects by RC-versus-observation difference. This selection never uses verification observations. The condition selector keeps all acquired conditions and pending predictions available. Prediction-commit stages still open the prediction-only view.
- The report separates supported explanation, remaining uncertainty and proposed next observation. A diagram comes directly from the recorded element connections and diode orientation, not the simulator's hidden truth. Simple canonical circuits get a connected schematic; other proposals get a labelled connection list. Plain-language reading aids are labelled as such; **Read original report** opens the unchanged model report in Evidence, alongside exact fitted values. Historical Korean reports remain unchanged.
- Timeline badges identify Spark, the numerical engine, simulated acquisition, or the instrument. Spark badges use the provider configuration available at that event: `max`, or `standard` for the recorded API setting `medium` (shown in the tooltip). Missing settings are not guessed. The trail lists only actions known at the cursor, aligns whole recent rows, and keeps the latest known action current at API/tool events without their own display row. Older actions remain scrollable. A four-stage strip remains above the scrolling trail; future stages show pending action labels, never future outcomes. Status follows proposal, training, prediction and verification events.
- Connection diagrams use logical node names. The diagram follows the displayed condition and explicitly says when no new mounting was requested. A new structured measurement request takes precedence, updating instructions before its observation arrives. Earlier requests without settings disclose that absence. Physical breadboard positions await the assembled fixture.
- Data origin and viewing mode are independent. Missing origin remains pending; unknown values are not silently labelled synthetic or hardware. Hardware records remain uncalibrated until D2 integration supplies a validated path.

The report's free-text claims are not a separate numerical proof. Verification is a development check of reserved predictions, not a guarantee of physical accuracy or topology uniqueness.

## Recorded versus reconstructed comparisons

New discovery runs record the best RC training comparison in `initial_family_assessment` and the proposed training curves in `proposal_fit`. The best RC is selected by training likelihood across the declared families. These extra curves are log-only: they do not expand the agent's tool context or add acquisitions, fitting, or simulator calls. They remain distinct from later `prediction_committed` records.

New discovery runs also store RC predictions alongside the proposal in each `prediction_committed` event. Both conditions and both models are frozen before either verification observation arrives. The existing proposal acceptance gate is unchanged; the verification tool result now includes baseline residuals and discrimination diagnostics. There are no additional acquisitions, parameter fits or ngspice calls.

To illustrate an old run without rewriting it, `python -m benchmate.comparison RUN` creates a `comparison.json` sidecar. Where training curves are missing, it refits RC families using only acquisitions before the assessment and simulates recorded proposal parameters on earlier training conditions. For verification, it evaluates the recorded best RC parameters (or that training-only reconstruction) on command waveforms. These RC counterfactuals were computed after the run, not originally committed. Only residual scoring uses verification observations. The loader checks the source-file hash and owning event hashes, and the UI labels reconstructions and gates them at the corresponding event. A test changes all verification outputs: training curves and frozen predictions remain identical, while residual checks change. The sidecar is a presentation aid, not external attestation.

## Design and verification

The user chose a demonstration-first screen and delegated visual direction. Impeccable's Operate guidance informed a scientific-poster hierarchy: the waveform leads, interpretation sits beside it, and methods/actions remain traceable. There is no generated image comp. [PRODUCT.md](../PRODUCT.md), [DESIGN.md](../DESIGN.md) and [the direction contract](viewer-direction.md) preserve the decisions.

IBM Plex Sans regular and semibold are bundled under OFL. Semantic SVG handles plots and connection diagrams. The desktop figure/report/trail/instructions fit a 1440×900 viewport; 1280 and 390 px widths are checked. Mobile orders figure, report, trail, connections. Visible focus, native range keys, report expansion, reduced motion, failure and unknown-source states are part of QA.

`scripts/check_viewer.mjs` exercises a separately launched isolated Chrome on DevTools port 9337. It records viewport geometry, screenshots, console failures and interaction assertions, including early RC-only comparison, proposal before fitting, three-curve training and verification, prediction-only stages, whole recent timeline rows, source labels and effort badges. It does not attach to the user's browser profile. Browser snapshots and developer tool caches remain ignored; the latest results are in [verification comparison validation](verification-ui-validation.json), with the prior actual API/live trial in [story/UI validation](story-ui-validation.json).
