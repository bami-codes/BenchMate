# Public replay

Read-only, static pages built from retained, hash-checked public records.

```sh
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python web/build.py --output /tmp/benchmate-site
python3 -m http.server --directory /tmp/benchmate-site 8767
```

Open `http://127.0.0.1:8767`. No API key, hardware or inference request is used.
The generated directory alone is published on the `gh-pages` branch. Do not publish the
repository root, private budget ledgers, raw photography or participant videos.

- `d01.html`: retained physical diagnosis, October 30.
- `repair.html`: actual Spark on a mock bench, November 2. Not a physical repair.
- `b5.html`: actual Spark on a mock clamp, October 30. Not a physical B5 result.
- `manifest.json`: source paths and event-file fingerprints.

The D01 and repair views reuse the existing Story/Evidence renderer. The B5 page reads
exact retained observations and predictions, with each channel's acquisition timing.
It labels conditional overlays and separately reports the command-forecast error.
No future trace is animated as if it had been available before capture.

Desktop (1440 px) and mobile (390 px) checks: `browser-check.json`.
After future physical records are available, update the builder's explicit source list
and all matching labels, then regenerate and review before publishing. Do not merely
remove a mock label from the existing record.
