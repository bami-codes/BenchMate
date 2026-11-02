# Photo evidence and local board references

The case server now exposes four independently identified historical photographs, their exact
image planes, the existing IMG_8887 grid, and **all five archived SAM trials**. A case can also
save a local operator's photo observation, correct it without deleting the earlier observation,
and request a better view when a contact is hidden. No new model/API call or hardware operation
is part of this feature. The case screen now opens these references and their exact-image SAM
overlays in a source-labeled photo dialog. It does not yet edit endpoint observations.

This is P2's data/observation backend, **not completed automatic wiring recognition**. Ten
endpoint targets on the crowded large board are declared for development. They are not ten
verified endpoints: new Spark endpoint trials and independently reviewed endpoint ground truth
are both still absent. No recognition accuracy or successful extra-capacitor localization is claimed.

## What the frontend can show now

| Photo | Material available | Attribution and limits |
| --- | --- | --- |
| IMG_8886 | Metadata-free full-resolution image and overview | Local historical reference; no calibrated grid or known capture-state link |
| IMG_8887 | Image, validated photo-local grid, ten declared endpoint checks | Grid is not an occupancy map or an electrical hole-address convention |
| IMG_8892 | Metadata-free image and overview | Independent historical reference; do not merge it with the other angles |
| IMG_8885 | Published SAM input, two masks and five complete trial outcomes | Recorded SAM output on this exact image; no D01 specimen identity |

The original GPS-bearing HEICs are never served. Three fixture images remain under `.private/`
and are available only in the local checkout. A clone without these private files receives
`available: false`, `issue: private_photo_not_present`, and null image URLs, not a substituted
picture. The already-published SAM input and masks remain available independently.

The SAM results are `capacitor: 0`, `resistor: 1`, `blue capacitor: 0`,
`blue rectangular component: 1`, and `film capacitor: 0`. Keep the misses available in Evidence.
The blue-body mask excludes the leads and is not an identification of the extra D01 capacitor.
Scores are the model's recorded confidence, not calibrated accuracy. A no-match result is not
evidence of absence or removal.

## Read API

All paths use the existing loopback Host/Origin rules. Image URLs are relative to the same server.
The previous replay and runner contracts remain unchanged.

The integrated review server is at `http://127.0.0.1:8774`, using
`.private/case-review/integrated-ui-qa`. Older server processes need a restart to load new
backend routes. Saved cases are separate per output directory.

| GET route | Response |
| --- | --- |
| `/api/photo-evidence` | Historical and registered photo descriptors, independent state groups, default reference ID |
| `/board.jpg?photo={photo_id}` | Pixel-only JPEG of that verified reference |
| `/board.jpg` | Explicitly registered default reference, or 404 if none |
| `/api/photo-evidence/{photo_id}` | Dimensions, transform, target list, SAM trials, image availability |
| `/api/photo-evidence/{photo_id}/image?view=overview` | Verified metadata-free overview PNG |
| `/api/photo-evidence/{photo_id}/image?view=master` | Exact full-resolution coordinate plane PNG |
| `/api/photo-evidence/{photo_id}/grid` | Original grid result, or null when no grid exists |
| `/api/photo-evidence/{photo_id}/masks/{trial_id}/{mask_id}` | Unedited binary mask in that photo's full image plane |
| `/api/photo-evidence/{photo_id}/overlays/{trial_id}/{mask_id}` | Previously rendered, pinned overlay for the same photo |
| `/api/cases/{case_id}/photo-reviews` | Append-only observations and latest observation per target |

Photo IDs are `img_8886`, `img_8887`, `img_8892`, `img_8885`. SAM trial IDs are `sam-1` through
`sam-5`, in the order listed above; masks exist only at `sam-2/0` and `sam-4/0` on `img_8885`.
A request for one of those masks on another photo returns 404. Do not warp the small-board
mask onto a fixture photo or copy its pixel coordinates between images.

Use **Historical photo — specimen state unconfirmed** beside the picture. The catalog's
`same_state_verified`, `can_authorize_repair`, and every observation's electrical-connection
flag remain false. `capture_state_id` is null. The current case is linked only to a *reference*,
not a claimed photograph of its historical or live measurement state.

For a grid overlay, draw only holes with both `in_image` and `within_anchor_domain`. All
`occupancy` values remain `unknown`; `electrical_address` is null. `column_from_right` and
`row_from_image_top` are photo-local indices, not A35/I8 or instructions for wiring.

## Save or correct an observation

Mutation: `POST /api/cases/{case_id}/photo-reviews`, JSON, with the existing
`X-BenchMate-Session` token. The case must already have an eligible, sealed design review.
Use the current case revision and photo-review revision. For example, a hidden contact:

```json
{
  "revision": 3,
  "photo_revision": 0,
  "review_id": "11111111111111111111111111111111",
  "photo_id": "img_8887",
  "photo_sha256": "COPY_CURRENT_DESCRIPTOR_PHOTO_SHA256",
  "target_id": "lower-green-occlusion",
  "view": "master",
  "point": null,
  "visibility": "occluded",
  "proposed_component_ref": null,
  "note": "The thick green wire hides this contact."
}
```

A visible observation requires a finite point inside `master` or `overview`. Convert CSS pointer
coordinates to the displayed image's native pixel plane, accounting for letterboxing/object-fit,
before submission. The server applies the overview-to-master transform itself. Do not pre-scale
a point and still label it `overview`. Rectangle edges are continuous; the right/bottom image
edges are outside a contact's valid pixel domain.

Visibility is `visible`, `occluded`, or `out_of_frame`. Occluded/out-of-frame observations never
snap to a hole, even if a suggested region happens to overlap a grid projection. The returned
`additional_view_request` is a **BenchMate template, not a Spark decision**. It asks for a closer
oblique view with unchanged wiring and a capture-state record. Do not portray this as the planned
live Spark-selected camera-angle experiment.

`proposed_component_ref` can be null, R1 or C1. It remains a proposed visual correspondence;
`component_match_verified: false` and `measurement_support: []` are retained. C2 and fields that
claim removal, electrical verification or same-state identity are rejected. A mask alone cannot
fill these gaps. The existing measured D01 diagnosis is not silently used to identify a photo object.

Generate a fresh lowercase 32-hex `review_id` for each explicit save. Repeating exactly the same
request is idempotent; changing the payload under the same ID conflicts. Correct an observation
with a new ID and the latest `photo_revision`. `latest_by_target` updates while `records` retains
the complete history. `corrections` counts superseding observations, **not model errors**.

Possible evidence statuses:

- `photo_local_candidate_only`: one candidate within the validated anchor domain and 0.25 local
  pitch; occupancy, electrical address, contact continuity and target identity remain unverified.
- `body_point_only`: a body annotation, not an endpoint.
- `needs_view`: hidden/out-of-frame; no inferred connection or removal.
- `grid_unavailable`, `grid_failed`, `outside_calibrated_contacts`, `ambiguous_projection`: no
  candidate is promoted; retain the observation and show the unresolved reason.

Records live in each local case's git-excluded `photo-reviews/revision-NNNN.json`. They pin the
case manifest, exact photo, request, preceding record and new record. They do not mutate the
sealed case, electrical graph, existing measurement evidence, or any runner confirmation file.
The local hash chain detects accidental modification; it is not external attestation.

## Verification and next gate

Nineteen new automated checks cover all five SAM outcomes, wrong-photo masks, absent private
files, corruption and path rejection, overview/master transforms, occlusion, extrapolation,
failed/ambiguous grids, invalid coordinates, correction history, stale reviews and HTTP origin
protection. These checks verify software contracts, not visual-recognition accuracy. Existing
photo geometry/media, case replay and mock repair suites passed together: **117 tests on
2026-11-02**. New paid API calls and hardware operations: zero.

The next P2 gate is a real target-localization trial plus independent visual review on a suitable
capture state. The ten targets here were chosen after seeing the development photo, without
using the fixture wiring table as model input; they are not a blind benchmark. Address orientation,
actual terminal visibility and the additional D01 capacitor still require their own evidence.
New images/paid trials, physical action and case-state assertions are not enabled by this backend.

## Register a new local board photograph

From the project root, after the operator supplies an actual capture:

```sh
.venv/bin/python -m benchmate.photo_bench.board_reference \
  --source /absolute/path/to/board-photo.HEIC \
  --label "Before repair — operator reference" \
  --capture-note "Operator's description of when this picture was taken"
```

This uses the existing native HEIC/Pillow decoder to preserve orientation, create pixel-only
RGB PNGs, and remove EXIF/GPS/ICC metadata. Originals remain untouched. New masters, overviews,
registration records and the default-reference pointer stay in git-excluded `.private/`.
The server discovers registrations without restarting; reload the page to refresh its photo list.
The JPEG route re-encodes verified RGB pixels and includes no inherited metadata.

Registration is an explicit **reference**, not proof that the picture matches the Oct 30 replay
or a current measured state. The caption keeps that distinction even when the operator supplies
a new repair photograph. State linking and component identification require separate evidence.
No picture is sent to an external API or committed by this command. A repeated source is rejected
instead of overwriting its earlier registration. New registrations preserve the previous images.

Four new software checks cover original preservation, metadata stripping, separate registrations,
arbitrary-path rejection and the JPEG route's origin/query guards. Together with the related suites,
**121 Python checks passed on 2026-11-02**. The registration tests use synthetic software fixtures;
no new user repair photograph was supplied or registered during this integration.
