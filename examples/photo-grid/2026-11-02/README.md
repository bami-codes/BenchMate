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
