# Case 02: post-hoc wiring confirmation and separately registered attempt 2

Attempt 1 remains `abstained` in its diagnostic child and `run_failed` in the
parent, counted and selected as the first attempt. Its original terminal head
is unchanged:
`2bc748cbbae5f8392b3ab567e3c77013058b8ac8ead7409d810dc0a068303efe`.

After that terminal outcome, the operator supplied `case2.dng`, confirmed the
photograph showed the unchanged measured wiring with USB disconnected, then
explicitly acknowledged and corrected the wiring error. Codex's visual review
shows the 474 at **C3–C8**, across R1 / IN–OUT, instead of instructed C8–C13,
OUT–REF. The 104 and 20k branches are at 8–13. Record the post-hoc cause as
**operator wiring error (474 C3–C8), confirmed after diagnosis by photograph and
operator report**. This does not turn the diagnosis into a successful answer or
prove exact electrical values from labels.

Separate documentary evidence, not appended to the terminal experiment:
`examples/reading-cohort/2026-11-03/postmortems/20261103T161130-f20340dd0b/`.
`board-photo.png` is a metadata-free 1200×1600 derivative of the supplied DNG
using the existing pinned RAW conversion and 1600px sanitizer. Original DNG and
full-resolution clean derivatives stay private. The conversion settings, hashes,
operator statement and post-hoc analysis are retained. No SAM/Spark photo call,
body correspondence or numeric reading was performed for this review.

## Comparison of the two proposed explanations

For a fixed intended-fault model C1=0.47uF, C2=0.1uF both OUT–REF, the existing
scorer gives the following **post-hoc** comparison, not a new official fit:

| Retained training capture | Whole RMS mV | 0–5ms | 5–20ms | 20–80ms | after 80ms |
|---|---:|---:|---:|---:|---:|
| Unloaded small step | 28.214 | 192.433 | 34.247 | 2.183 | 2.170 |
| Loaded large step | 52.290 | 369.551 | 31.104 | 3.157 | 3.418 |

The sine whole RMS is14.038mV. Early-time concentration alone is not sufficient
to diagnose a sampling-time problem: the now-observed feedthrough wiring also
produces this pattern. Whole RMS alone is not the protocol criterion; every
region must pass too. Claude's approximate alternative-model RMS values are not
substituted for the original scorer, fitted models or reserved validation.

Raw A1 completion is52–53us after frame start; A2 completion104–106us, a52–53us
difference. These are completion timestamps, not calibrated sample apertures.
The existing predictor already samples OUT at its recorded A2 delay, while
treating each measured IN value as the held level for its command frame. Analog
transitions between samples remain unmeasured. A53us difference corresponds to
0.0954 degrees at5Hz; retained OUT leads IN by about2.95 degrees after nominal
delay treatment. The intended-fault time constants3.8ms unloaded /2.279ms loaded
are correct calculations, but the old D013ms planning advice is not an established
universal bench cutoff. No timing calibration or component-value change follows
from these data alone.

The first case01 restored failure occurred during the preparatory HOLD, before
any step and without a returned raw block. Case04's first HOLD failure had OUT
near0.555V; the operator subsequently reported the diode cathode at E27 rather
than E25. Neither is an observed fast-step residual pattern. Completed restored
reruns later passed nominal reserved checks: case01 step/sine5.069/3.261mV;
case04 step/sine2.975/3.449mV. These observations do not support grouping all
three earlier failures as one short-time-constant defect.

Spark identified a plausible fast IN–OUT path, but its first proposal retained
the intended OUT–REF capacitors and added another capacitor. It did not identify
the complete actual relocation. The10ns reconstructed PWL edges and10mA ideal
source-current limit can reject direct feedthrough capacitors for artificial
edge current. That limitation is documented; it is not evidence of measured
physical overcurrent or a verified missing component. No simulator/guard change
or retrospective official rescoring is made. Any future fix needs a separately
frozen version and qualification, after the remaining case work.

## Attempt 2

The operator explicitly requested a new case02 faulted attempt after moving474
to C8–C13, and confirmed USB-off correction followed by reconnection. Keep the
same intended schematic, source freeze, menu, guards, scores and reserved inputs.
Register and publish attempt2 before its new model/hardware stage. Its context
receives no old result, photograph, assembly truth or correction report. If its
fresh schematic extraction is electrically identical to the already operator-
confirmed intended image, retain that earlier content confirmation explicitly;
do not invent an additional operator response. Any changed/ambiguous extraction
requires operator review. Preserve attempt1 in the index and link the follow-up.

Announced cost: schematic Spark1, faulted diagnostic at most8, estimated
$0.07–0.14. Restoration and any necessary photo stage are reported separately.
This post-hoc review itself used0 paid calls /$0 and0 hardware commands.
