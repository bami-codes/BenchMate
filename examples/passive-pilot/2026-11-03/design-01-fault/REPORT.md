# Design-01 physical pilot — first attempt stopped at REF guard

This actual Spark-directed physical attempt is a pilot, excluded from evaluation.
Operator-confirmed assembly and PING-only preflight were committed before the run.
The public B28–B35 instrument resistor is 1 kΩ; assembly truth was not sent to Spark.

Spark made two requests: inspect the design, then choose `unloaded_step_small`.
The adapter armed the expected device and captured the first 512-frame HOLD at
commanded REF, before sending any diagnostic step or sine command. The reference
guard failed and the attempt stopped without automatic retry or re-arm.

| Channel | Mean, nominal ADC conversion |
|---|---:|
| A1 | 1.642315 V |
| A2 | 1.640632 V |
| A3 | 1.642885 V |
| A4 | 0.869965 V |

A4's declared envelope, stationary path means/samples and inter-channel spread
checks failed. These values are nominal ADC conversions, not new DMM observations
or an established diagnosis of the REF circuit. Operator DMM readings at D50,
G50 and, if accessible, the Arduino A4 contact have been requested to distinguish
actual REF voltage from a sensing-path problem. No cause is established yet.

The final received PING reported the same boot and parked REF code 1376. No
subsequent command was sent. The run's conservative `output_state_confirmed=false`
failure metadata is retained; this report does not replace a fresh state check.

There are no trained component fits, reserved measurements, validated predictions
or completed diagnosis report. This is not a diagnosis success or wrong-part claim.
The selected small step was never physically captured.

Actual Spark calls: **2**. Token-based Standard cost estimate: **$0.00615455**.
Session cumulative including six schematic readings: **8 calls, $0.06165445**.
These are estimates, not account invoices. All terminal events, original tool
calls, raw HOLD rows, source copies and failure metadata are preserved in the
adjacent run directory. Its terminal event chain and secret scan passed.

## Operator DMM follow-up

The operator reported D50 and G50 each at **1.63 V**. No Arduino A4 contact
voltage or meter range was provided. Thus both measured REF distribution points
are near the intended reference, while the earlier A4 nominal ADC conversion was
0.870 V. This narrows the next check to the A4 sensing path; it does not establish
a connector or ADC fault. No additional command or Spark call was made.

The operator has been asked to disconnect USB, check and reseat only the
H50-to-Arduino-A4 lead, retain D50–G50 and all remaining wiring, remove probes,
and reconnect the same port. Completion is pending. The original failed attempt
and guard limits remain unchanged.

## Second attempt after reseating the A4 lead

Run `20261102T160841-eff2b65334` is retained beside the original failed attempt.
The fresh initial REF checks passed with A4 near 1.630 V. Spark chose, in order,
an unloaded small step, a loaded small step, and an unloaded 1 Hz large sine.
All three training captures and their guards passed. After two captures the
joint-fit loaded-waveform RMS was 3.39 mV for the R1-change family and 70.04 mV
for the C1-change family. After the third, only the R1-change family remained
adequate, with effective R1 ≈25.2 kΩ assuming C1=1 µF. This does not locate the
added series resistance or prove that the visible R1 changed.

Spark requested verification. Models, values and both reserved forecasts were
published in commit `443c9a67f4f43831f4417c1621887622a6cbe404` before either
reserved acquisition. The first reserved step was physically captured, but its
A4 block mean made the same-boot A4 mean span **4.368 mV**, above the unchanged
3 mV limit. The capture was rejected and execution stopped. No reserved score
or completed diagnosis report was produced; the second reserved sine was never
sent. The first reserved condition has now been exposed in development and must
not be described as never previously attempted. No reserved OUT was used to refit.

This attempt used **5** real Spark requests, estimated **$0.03445515**. Cumulative
including prior readings/attempts: **13 calls, $0.0961096**. All work remains pilot
development, excluded from evaluation. There was no automatic retry or relaxed
guard. Subsequent instrument-only QA is recorded separately.
