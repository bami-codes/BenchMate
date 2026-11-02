# Single-photo board geometry development check

This is a geometry check on one previously inspected development image, not a
blind circuit-recognition evaluation. Eight visually reviewed hole centres fit
two board-plane homographies. Forty other visually labelled holes are held out
from fitting; each strip must have at least twenty checks and p95 error at most
0.25 local pitch. All first results, including failure, are retained.

Indices are **photo-local**: column zero is the rightmost terminal column and
increases to the left; row zero is the image-top row within each five-hole strip.
These are deliberately not electrical addresses. The board has opposing printed
legends; registration does not certify the fixture address convention. No wire
endpoint, occupied hole, rail break or electrical connection is inferred here.

The source photo remains private. Its oriented-master hash, calibration points
and check points are fixed in `design.json` before the first numerical fit.
Both the raw-image feature detector and the point labels are development choices.
The withheld holes test the fit, not generalisation to a new board or camera.

## First result

The design and labels were committed and pushed as
`d1614810254bd604542e8f5bfef9231e9ce96849` before the first numerical fit.
No points or thresholds were changed after seeing the result.

| Photo-local strip | Fit anchors | Withheld holes | RMS, pixels | p95, local pitch | Gate |
| --- | ---: | ---: | ---: | ---: | --- |
| Upper | 4 | 20 | 1.846 | 0.0683 | Pass |
| Lower | 4 | 20 | 1.130 | 0.0387 | Pass |

[All first-result coordinates and errors](first-result.json) are preserved.
The CLI reproduction matches the first result byte for byte. This is an internal
fit check on one development image, not a blind test of board recognition.

The viewer draws only projections inside the anchor rectangle and image bounds
(290 candidate locations in this image). The template includes 630 terminal
positions, but does not claim that 630 holes were observed or verified. The
power rails are not calibrated. All occupancy and electrical addresses remain
unknown. Green circles are fit anchors; amber crosses are withheld checks;
blue rings are projected positions, not confirmed connections.

## Reproduce locally

The original photo is deliberately not published. With the private cleaned
master present, run from the repository root into a **new** result path:

```sh
PYTHONPATH=src .tools/photo-reconstruction/venv/bin/python -m benchmate.photo_bench calibrate --design examples/photo-grid/2026-11-02/design.json --master .private/photo-bench/library-20261102/photo-1dfbb3d87b87add3/master.png --output .private/photo-bench/grid-reproduction/result.json
```

To inspect that result, copy it to `grid.json` in the matching prepared photo
folder and use the local gallery. The viewer checks the master hash before
showing a grid. Point exports can include a photo-local nearest-hole candidate
within 0.25 projected pitch; this is not proof that a wire is inserted there.
