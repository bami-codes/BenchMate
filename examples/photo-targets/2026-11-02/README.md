# Photo target preparation — November 2, 2026

`catalog.json` registers separate image planes for three private fixture photos (IMG_8886,
IMG_8887, IMG_8892) and the already-published IMG_8885 SAM input. The private images are not
included here. Each referenced image, grid and SAM artifact has a SHA-256 digest. No new API
request, electrical measurement or grouping of historical photos was performed.

Ten endpoint checks on IMG_8887 were selected **after visual inspection** as development tasks.
They include occlusion, a body-adjacent contact and an exposed tip outside the calibrated terminal
area. Descriptions specify the object to inspect, not an expected hole address. There are no
independent endpoint truth labels or new Spark outputs yet; do not report X/10 accuracy.
The existing grid remains photo-local, with unknown occupancy and unconfirmed electrical addresses.

All five prior SAM outcomes are retained, including the three zero-match prompts. Two body masks
can be displayed only on their exact source image. Neither mask is a verified additional D01
capacitor or permission for a repair. See [the frontend/API handoff](../../../docs/photo-evidence.md).
