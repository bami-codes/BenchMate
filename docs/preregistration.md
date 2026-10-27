# Initial experiment registration — 2026-10-27 KST

Status: initial development protocol, before implementation and physical measurements. This is not a final calibration freeze. Later changes require a dated commit and a stated reason.

## Claims

- H1: With equal measurement access and budgets, adaptive experiment selection may match or improve correctness and/or reduce measurements and total time relative to a fixed expert procedure. Report ties and failures; do not assume superiority.
- H2: Starting with an R/C model family, Muse Spark may propose a missing nonlinear circuit structure that predicts conditions not used for proposal or fitting. Report the actual generated netlist, not a substituted answer template.
- H3: Under ideal voltage drive, B1 and B6 give the same output voltage behavior and the same unresolved input-branch report. A requested shunt enables repeated discrimination.

## Fixed starting conditions

| Item | Initial value / rule |
| --- | --- |
| Reference | REF approximately 1.6 V; use measured REF in the hardware model |
| Stimulus envelope | REF +/- 1.0 V, subject to D2 verification |
| Sine amplitudes | 0.2 V and 1.0 V, peak relative to REF |
| Step increment | At most 1.0 V per transition; settle before the next transition |
| Exploration | One unloaded step, REF - 0.5 V to REF + 0.5 V |
| Ordinary budget | 1 common exploration + 3 diagnostic acquisitions + 1 confirmation |
| Nonlinear verification | 2 verification acquisitions instead of the ordinary single confirmation |
| Verification conditions | Unused intermediate-amplitude step and a specified 10 kohm output-load condition; exact waveform and intermediate amplitude are fixed at D2 |
| Input shunt | 1 kohm replacing the normal 0 ohm jumper |
| Manual output loads | 10 kohm or 4.7 kohm from OUT to RET (REF) |
| B6 expectation | With 10 kohm IN-to-RET and a 1 kohm shunt, +/- 1 V steady drive gives +/- 90.909 mV shunt drop; two-level difference 181.818 mV |
| B1 expectation | Ideal unloaded DC input current is zero; physical conclusion is relative to a measured detection limit |
| B1 values | R=10 kohm, C=1 microfarad, tau=10 ms |
| D01 alternatives | R=20 kohm,C=1 microfarad versus R=10 kohm,C=2 microfarad; both unloaded tau=20 ms |
| D01 with 10 kohm load | Gain/tau: 1/3 and 6.667 ms versus 1/2 and 10 ms |

The exploration acquisition is excluded from the additional-action budget but included in reported total acquisitions and elapsed time. No bundling multiple physical acquisitions into one action to hide measurement cost.

## Pending empirical decisions

D2: actual supply and DAC ranges, sampling rates and channel offsets/jitter, pull-down choice, ADC/buffer calibration, noise and model error, settling criteria, current detection limit, decision thresholds, validated maximum frequency, and exact held-out validation conditions. Default synthetic noise values are engineering fixtures only.

Before final evaluation: hypothesis templates, full parameter priors, numerical grids, prompts, feature extraction, allowed elements, fit/verification metrics and acceptance thresholds. Day-one named hypotheses are a narrow implementation check, not the complete Bayesian engine. Preserve R/C prior density when changing variables: p(tau,R)=p_RC(R,tau/R)/R for R>0.

## Holdouts and information boundaries

- Commit X1 and X2 assembly file hashes before implementation. Private files include a random nonce and remain outside Git, prompts, diagnostics and ordinary tests.
- This is a configuration commitment, not an independently blinded study: the developer can access assembly instructions.
- X1 may be used at the development gate. Any tuning after viewing it makes X1 a development case.
- X2 is first measured only after the final pipeline freeze commit. Preserve its first result even if a later patch is necessary.
- Simulation fixtures own circuit truth. Diagnosis receives observations and explicitly declared candidate knowledge only; never box IDs, fixture labels or hidden component values.
- Proposals/fits must not see verification data before committing a prediction. All comparison methods use the same reserved conditions.

## Evidence and success

Store raw observations, acquisition settings, data source, predictions, chosen action, instrument state, requested versus unrequested human intervention, elapsed time and API usage. Synthetic, recorded-data replay and hardware live execution are distinct modes.

Success means a correct supported conclusion or justified unresolved report within budget. A false confident conclusion is failure. Report all attempts, abstentions and failures. A planned final block of ten runs per development case targets at least nine successful completions; this is an internal engineering target, not a population reliability guarantee. X2's first trial is separate.

## Provider use and limits

Primary: Meta Model API, muse-spark-1.3. Optional secondary: Baseten, exactly meta-models/muse-spark-open-1026. Never silently substitute providers. Default temperature; record actual reasoning setting. Log usage and enforce a conservative application spending budget. Meta stop target $120 against $150 credit; Baseten budget is separate from Meta.

## Human operation

No formal user recruitment. Show component value, physical connection labels and any jumper removal. Record setup/calibration separately from diagnostic interventions. Optional short non-expert instruction check only after D7 if someone is readily available.

