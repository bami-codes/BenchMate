# Case02 restored follow-up: first reserved step stopped at the original A3 guard

Continuation: `examples/reading-restored-v2/2026-11-04/records/20261103T175520-a925a3910d/`.
Diagnostic child: `diagnosis-restored/20261103T175621-8d699cef12/`.
Both are terminal `run_failed`. No retry, new API call, firmware change, guard
relaxation, new compensation coefficient or further stimulus followed. The
operator was instructed to disconnect USB and retain the restored/unloaded
configuration, and replied `유지했어`. There is no active runner or pending action.

## Exact executed sequence and description correction

Fresh Spark chose the actions below. All three accepted training captures passed
every original A3/trusted-channel guard and the normal-design numerical checks:

| Spark action | Settings | Nominal whole RMS mV | Worst region mV |
|---|---|---:|---:|
| unloaded_step_small | +/-0.2V, no load | 3.550043 | 4.630635 |
| loaded_step_small | +/-0.2V,9.99k load | 2.637281 | 7.105769 |
| unloaded_sine_1hz_large | 1Hz,0.8V amplitude, no load | 2.207263 | 3.324216 |

Codex's earlier messages and temporary progress labels called the second action
"loaded large step". That description was wrong: the immutable Spark call,
frozen forecast and actual command are **loaded_step_small,+/-0.2V**. The 2.64mV
score belongs to that small step. The load-jumper instruction is identical for
both amplitudes, and the runner executed the actual Spark choice. No raw record
or model action was edited to agree with the incorrect prose. This note corrects
the description and the private progress summary now uses the native action IDs.

Spark then requested `verify_prediction`. Prediction SHA-256
`f4fbcfdd3f3bde0f2ef437f2180e21698725e714970bf8e3d61df6ca085a3a82`
was committed and remotely confirmed in
`db9e510ff29bdf0c57b646b3c414af232e9ae33f` before the first reserved capture.
That capture was the fixed **unloaded +/-0.35V step**. Its raw data were acquired
but failed the electrical guard before an accepted reserved observation or score
could be generated. The second reserved sine was **not executed**. There is no
completed restored verdict and no claim of a repaired-and-verified case.

## The failed check

Only `REF_A3_block_mean_span` failed in `verification_4`:

- A3 cumulative block-mean span within that boot: **3.103648313mV**.
- Fixed limit: **3.000000000mV**, unchanged.
- A4 auxiliary cumulative span: **3.174331815mV**. A4 is not a stopping channel.
- Rails, A3 absolute envelope and trusted-channel signal envelopes passed.
- The failed capture reported the REF park; its post-capture PING showed
  `current_code:1376 == ref_code:1376`, before the guard exception stopped work.

The same boot's three pre-sine HOLD A3 means were approximately
1.661232/1.661143/1.661205V, sine block1.661131V, return HOLD1.661280V.
Before the reserved step, three HOLD blocks were1.661569/1.661639/1.661589V.
The step block was1.664234V. HOLD variation alone did not trip the guard; adding
the reserved step expanded the cumulative span beyond3mV. The original guard
was neither reset nor bypassed before verification.

There are19 raw guard blocks/9,728 frames:18 blocks passed, the last failed.
Three scored training observations are retained. The raw failed capture stays
available, but it is not relabelled an accepted validation observation.

## Read-only description of the input-linked signal

The following post-hoc summaries do not change scores, guards or predictions.
Plateau summaries use first40 samples and samples80 onward; OLS uses every sample
of the block and is **descriptive, not a fitted correction**:

| Capture (different boots) | IN late-minus-early V | A3 late-minus-early mV | A4 late-minus-early mV | OLS A3/IN | A3-IN correlation |
|---|---:|---:|---:|---:|---:|
| unloaded small step | 0.386839 | 0.355308 | 1.382463 | 0.001322 | 0.075221 |
| loaded small step | 0.376899 | 7.159064 | 7.518526 | 0.019068 | 0.647203 |
| reserved unloaded step | 0.676321 | 7.388090 | 7.082907 | 0.010882 | 0.895175 |

The failed step clearly includes input-linked motion in both REF readings. Its
coefficient is not stable across boots/fixtures in this run. These data do not
separate actual REF/ground movement from acquisition/reference effects and do
not establish a particular faulty wire or chip. They do not justify a new fixed
k, per-capture regression, per-verification guard reset or a relaxed threshold.

## Before any new physical attempt

No option has yet been selected/executed. Two concrete paths are available:

1. **Power-off return-path reinforcement, then one bounded waveform QA**: retain
   the existing renewed GND wire and add one short parallel wire from another
   Arduino GND pin to the same large-board blue GND rail. Do not connect to REF,
   alter5V or change the specimen. Document the wiring amendment prospectively.
   Then one new-boot QA, at most one ARM and five512-frame blocks: three HOLD,
   the same unloaded reserved +/-0.35V step, one return HOLD. Original guards,
   ten-second wait and stop-on-first-failure remain;0Spark,0SAM,$0, about1–2min.
   This tests a plausible return-path hypothesis, not a confirmed root cause.
2. **One QA with unchanged wiring**: the same bounded five-block plan on a new
   boot,0Spark/0SAM/$0. It probes repeatability without a wiring intervention.
   A pass on one boot does not itself establish a stable bench or fix the cause.

The operator may instead keep USB off and stop. No failed-run replay or new
official diagnosis is automatically launched after either QA. Its actual result
must be reported first; any further direction remains explicit. Executable QA
sources/plan must be frozen and pushed before running. These are choices, not
completed work or permission inferred from elapsed time.

## Preservation and cost

Original107 source hashes still match. Both prior failed case02 parents, the
successful fault child and the completed isolated reading supplement remain
unchanged. This third counted case02 continuation is failed; it does not replace
the first selected attempt. No restored photo/SAM/binding call was made.

This restored diagnosis used **5 Spark,0SAM,estimated$0.05087020** from recorded
tokens, not the$5 SDK reservation. Case02 total including both prior attempts:
**22 Spark,1SAM,estimated$0.26752245**. Whole reading cohort:
**58 Spark,2SAM,estimated$0.57787355**.

Offline compound audit:

```text
PASS events=504 forecasts=10 measurements=10 order_checks=36 prediction_files=4 run_status=run_failed head_sha256=5efae7dc9a4df5e1d004bd476e991f78b98044db4b69a338d3cd0f212c94e59e scope=internal_integrity+recorded_order creation_time=unproven
```

Native restored diagnostic audit:

```text
PASS events=184 forecasts=4 measurements=3 order_checks=12 prediction_files=1 run_status=run_failed head_sha256=2ad7ef876a489a51dbcf6f2a2695a5da307b781d8d4211f17fda2275cd9bb8d7 scope=internal_integrity+recorded_order creation_time=unproven
```

PASS means retained integrity/recorded order, not electrical success, original
creation time, true physical wiring, meter accuracy or operator authenticity.
