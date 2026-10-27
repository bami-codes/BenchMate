# English experiment workspace

The workspace is an evidence-review surface for the hackathon demonstration. One event reducer and renderer serves an exported replay and a running software log. It does not drive the board, trigger API requests, or certify hardware.

## Open a reviewed result

```sh
uv run benchmate view examples/discovery-mismatch-english --output runs/discovery-report.html
```

Open the HTML locally. Fonts, interface code and the hash-verified record are embedded; no CDN, external script or API is needed. Replay exposes events in order. Before a verification acquisition, only the committed prediction is visible. Later results are withheld when navigating backward.

## Follow a running experiment

```sh
uv run benchmate watch runs/YOUR_RUNNING_SESSION --port 8765
```

Open the printed loopback URL. The read-only server follows complete JSONL lines, checks the hash chain, and streams verified prefixes to the same UI. Partial writes are withheld. Origin/Host checks reject other hosts and origins; the server binds only to 127.0.0.1. Stop it with Ctrl-C.

Use the timeline to inspect an earlier event; **Follow live** returns to new events. Connection errors remain visible until a valid update arrives. A changed prefix or corrupt record stops updates and requires investigating the source before reload. A live log of a synthetic instrument is labelled **Synthetic observations / Live log**, never live hardware.

## Reading the screen

- Solid orange is observed output; dashed blue is the prediction committed before it. Drive is an optional third trace. The condition match includes REF as well as stimulus, load and shunt settings. Axes use the same scale for all traces.
- The report separates supported explanation, remaining uncertainty and proposed next observation. New Spark reports are English. Long text can be expanded; raw model text remains available in the source record. Historical Korean records are not rewritten: the English main panel uses an explicitly labelled engine summary, and the original remains in event details.
- Timeline badges identify Spark, the numerical engine, simulated acquisition, or the instrument. A simulated mounting or replacement is not a human action.
- Connection diagrams use logical node names. A new structured measurement request updates the instructions before its observation arrives. Earlier requests without structured settings disclose that absence. Physical breadboard positions await the assembled fixture.
- Data origin and viewing mode are independent. Missing origin remains pending; unknown values are not silently labelled synthetic or hardware. Hardware records remain uncalibrated until D2 integration supplies a validated path.

The report's free-text claims are not a separate numerical proof. Verification is a development check of reserved predictions, not a guarantee of physical accuracy or topology uniqueness.

## Design and verification

The user chose a demonstration-first screen and delegated visual direction. Impeccable's Operate guidance informed a scientific-poster hierarchy: the waveform leads, interpretation sits beside it, and methods/actions remain traceable. There is no generated image comp. [PRODUCT.md](../PRODUCT.md), [DESIGN.md](../DESIGN.md) and [the direction contract](viewer-direction.md) preserve the decisions.

IBM Plex Sans regular and semibold are bundled under OFL. Semantic SVG handles plots and connection diagrams. The desktop figure/report/trail/instructions fit a 1440×900 viewport; 1280 and 390 px widths are checked. Mobile orders figure, report, trail, connections. Visible focus, native range keys, report expansion, reduced motion, failure and unknown-source states are part of QA.

`scripts/check_viewer.mjs` exercises a separately launched isolated Chrome on DevTools port 9337. It records viewport geometry, screenshots, console failures and interaction assertions. It does not attach to the user's browser profile. Browser snapshots and developer tool caches remain ignored; validation results are summarized in [structure/UI validation](structure-ui-validation.json).
