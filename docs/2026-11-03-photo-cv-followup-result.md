# Final photo follow-up finished; restoration is next

The bounded follow-up ran from **20:22:08 to 20:26:31 KST**, within the requested
15 minutes. Two Spark requests were made, with no repeat or third request.
Photo work is finished regardless of the limitations below.

OpenCV selected the visible blue box body. White-board reference, HSV selection,
Lab-L CLAHE and exact 3x cubic enlargement were fixed and pushed in `022ec4d`
before either call. The unmodified prior attempt remains preserved. The new
box crop is explicitly OpenCV-derived; it is not a corrected SAM mask.

| Input | Native Spark outcome | Retained interpretation |
|---|---|---|
| Existing SAM resistor box, processed | R, `value_si:null`, uncertain band colors | Resistance unreadable |
| OpenCV blue-box crop, processed | `unsupported`, empty components; text tentatively resembles `105J100`; response calls package six-terminal | No capacitance reading; do not infer 1 uF from the tentative text |

The second response did see a possible marking, but did not accept a component
type or emit a value. This is not counted as successful capacitor transcription.
The reported terminal interpretation remains visible as a model limitation;
no raw argument or component value was corrected from the known assembly.
The enlargement adds no independent spatial detail and the board-reference
normalization is not a calibrated color measurement.

Both fresh-context calls received only their crop and the preserved generic
assembly-photo prompt: no component hint, nominal value, previous diagnosis,
SAM concept or OpenCV selection label. Both complete child event hash chains
passed `read_events` validation. Inputs, reference mask, blue mask, all contour
selection data, library versions, settings, native outputs and observer review
are in `examples/official-photos/2026-11-03/01-faulted-cv-followup/`.

Actual follow-up: **2 Spark requests**, standard-rate usage estimate
**$0.01945720**. All case-01 photo work: **4 Spark + 2 SAM**, estimated
**$0.04201560**. Including F01–F04 diagnosis: **21 Spark + 2 SAM**,
estimated **$0.16821450**. These are usage-based estimates, not invoices.

The operator has been asked to restore with USB off:

| Action | Large-board change |
|---|---|
| Remove first external 10k | E35–E31 |
| Remove second external 10k | D31–D37 |
| Restore direct measured-IN feed | Move green lead A37 end to A35; mini-board A3 end stays |

Keep mini R1/C1, the known B28–B35 1k instrument resistor and A3/A4 REF/GND
wiring. Output-load E30–A55 stays absent. After operator confirmation and a fresh
unarmed PING, preregister 01-R01 and start its fresh Spark context under the same
A3 guard and ten-second reconnect wait. Maximum eight Spark calls; prior photos
and diagnostic results are excluded from that context.
