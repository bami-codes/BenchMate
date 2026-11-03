# New case 01 — isolated R1 reading and seal reveal

The operator confirmed Spark's `sam-1 → R1` correspondence and selected
`operator_dmm`. The operator then removed **both R1 leads from the breadboard**
and reported **4.71kΩ**, retaining USB-off state and the confirmed 20kΩ meter
range. The separate DMM photograph shows the off-board resistor and `04.71 kΩ`
on an ANENG DM950. The numeric observation comes from the operator report;
there was no Spark value-reading call or OCR substitution.

The earlier in-circuit 4.71kΩ report and its repeated-stability description are
retained in the parent chain, explicitly not scored as an isolated component
reading. This is **one requested component and one qualified isolated value**;
do not describe it as only one physical probe acquisition in total.

Forecasts were already frozen/pushed at `edec9d0`, before any new board photo
or numeric reading. For the selected 20kΩ range:

| Explanation | Frozen DMM interval | Reported 4,710Ω |
|---|---:|---|
| Actual R1 value increased | 23,219.46–27,951.88Ω | Outside; ruled out |
| Intended R1 plus additional series path | 4,355.70–5,053.70Ω | Inside; survives |

The deterministic outcome is **one_explanation_remains**, with
`fits:["external_equivalent:changed:R1"]` and
`ruled_out_by_reading:["changed:R1"]`. No ranges or fitted parameters changed.
The conclusion is conditional on these declared explanations; it does not
uniquely locate every possible contact/lead resistance in the physical world.
The measured nominal-compatible R1 does not certify every part of the board.

`reading_forecast_frozen.sha256`:
`7215419b175836b4134cbb73a3e165c0d312534f90bc40783ac53eccf182dd38`.
`reading_scored.observation_sha256`:
`beedf78ee19ae746789af4ff23f8600df01fc7b8e033a0b7648776f76ad98d13`.

Only after scoring, the specimen seal was opened. The revealed assembly digest
matches the original pre-diagnosis commitment. It records the actual operator
setup with nominal 10kΩ resistors at large E35–E31 and D31–D37, in series
between measured IN and the mini board. Their nominal sum is 20kΩ. The verified
terminal fit was 25.279kΩ; subtracting the independently read 4.710kΩ gives a
conditional remaining series contribution of about 20.6kΩ. This subtraction is
not another OUT fit or an independently measured exact value of either hidden
resistor. The sealed values were nominal assembly records, not fresh DMM values.

Evidence is `reading-evidence.png` in the
[pair folder](../examples/reading-cohort/2026-11-03/records/20261103T125924-bf8f64512b/).
The original DNG is private; fixed RAW derivatives are in
`reading-evidence-conversion/`. The full clean PNG exceeded the existing 12MB
input bound, so a fixed 1600-edge LANCZOS input was made using the already
declared sanitizer edge. Full derivatives, settings and both hashes are retained.
No extra brightness/color tuning, numeric editing or metadata retention occurred.

Reading scoring and seal reveal used **Spark 0, SAM 0, hardware commands 0**.
Cumulative new-cohort usage remains **Spark 9, SAM 1, estimated $0.08277320**.
The case is still in progress, waiting for operator restoration and a fresh-context
diagnostic rerun, then its new photograph/SAM correspondence. Case 01 remains
known to developers and not blind. The old prototype cohort stays separate.
