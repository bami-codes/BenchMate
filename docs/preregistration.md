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

## Development revision — 2026-10-27, before hardware arrival

Reason: replace fixed-value milestones with continuous inference, prevent transient errors being diluted by long settled segments, and exercise the nonlinear/repair pipeline before D2. This revision does not rewrite the initial commitment or constitute the final calibration/evaluation freeze. X1/X2 assemblies remain untouched.

- Mystery priors are independent log-uniform R=4.7–47 kohm, C=0.47–4.7 microfarad, optional IN→REF branch Rp=4.7–47 kohm. Two one-state families are shared across mystery cases. Explicit repair mode declares nominal R=9.5–10.5 kohm/C=0.9–1.1 microfarad, changed R=15–25 kohm or C=1.5–2.5 microfarad. This is still narrower than the final planned grammar.
- Fit and evidence are separate. Preserve the original R/C prior under tau/R transformation. Gaussian quadrature orders 4, 7, 10 require consecutive log-evidence difference <0.05 for adequate families; unresolved integration cannot confirm.
- Whole-channel and fixed step regions 0–5/5–20/20–80 ms, or eight sine phase bins, use normalized residual RMS. Development limit=3, sigma=3 mV, rho=0; channel-specific AR(1) values are configurable. These are engineering defaults with no calibrated false-positive interpretation. D2 must measure noise/model error and validate windows against actual timing.
- Six configurable log frequencies default to 1–100 Hz; the software ceiling is 500 Hz. The 85-condition menu and timing are synthetic development settings, not validated hardware capabilities. A 0.3 V step is reserved for ordinary confirmation.
- B5 training uses the common 0.5 V step and 1 Hz sines of 0.2/1.0 V. Development verification reserves a 0.35 V step and a 1 Hz, 1.0 V sine with 10 kohm load. Both predictions precede either verification capture. Physical values still freeze at D2. Generated topology is retained; at most two R/C values may be fit, two proposals and 80 training simulator calls per proposal.
- The first live nonlinear attempt exhausted its 4,096-token output cap before a proposal. A second attempt, explicitly raised to 8,192 tokens/128 KB input per request, completed. Preserve both attempts. This is a development correction, not a fixed-protocol success-rate estimate. Ordinary calls keep the 4,096-token/64 KB limits; all runs retain the eight-request cap.
- D01 repair adds two explicitly counted post-replacement verification captures after diagnosis. Predict before replacement; do not refit on these observations. Current replacements are simulated and assume the declared nominal replacement value.
- D2 firmware stores 512 samples with full per-channel completion timestamps. The first 1,000-sample build exceeded the core's reserved RAM budget. Compression/rate targets await measured jitter. Compilation is not hardware verification.

See [inference details](inference.md), [instrument protocol](instrument.md), and [all development attempts](preboard-validation.json).

## Structure and UI revision — 2026-10-27, before D2

Reason: the previous simulator and proposal library shared diode parameters, so successful prediction did not test parameter mismatch. Truth now uses IS=3 nA/N=1.9; the library starts at 1 nA/1.8 and permits training-only IS=0.1–100 nA/N=1–2.5. RS=1 Ω and 27°C stay fixed. R/C plus shared IS/N is limited to four values, 420 simulator calls and 60 seconds per proposal (individual call timeout 15 seconds); two proposals per run. Require a locally informative log-parameter Jacobian, minimum singular value >1 and condition number <1e5, in addition to optimizer convergence and regional checks. This does not assert physical part calibration.

Add the allowed 4.7 kohm, 1 Hz/1 V loaded sine to training to distinguish R from IS. The 10 kohm load and intermediate-amplitude step remain unused verification conditions. Report all six captures (1 exploration + 3 diagnostic + 2 verification). Freeze both circuit and diode parameters and both command-based predictions before observing verification data. Prior records and their five-capture protocol remain unchanged.

Use neutral structure-discovery wording and English reports. New reports must not invent detection limits or uncertainty that the tools did not report. Keep both live revision attempts: the first completed but its free text asserted an unmeasured capacitance detection limit; the second used the tightened reporting instruction. Report-wording quality is separate from numerical prediction verification.

The English UI uses one renderer for immutable replay and read-only live logs. It shows independent source/mode labels and actor identities; it does not imply a live physical board. No holdout assembly or observation was accessed for this revision.

## Frozen-RC verification comparison — 2026-10-27, before D2

Reason: expose whether reserved conditions distinguish the proposed structure from the best training-fit RC. New runs commit both models' predictions for both reserved conditions before either observation. Record per-model OUT RMS/peak error, existing regional adequacy checks, and prediction RMS/peak separation. If both pass, flag weak discrimination. The proposal's acceptance criteria, parameter priors, conditions and six-capture budget are unchanged. Baseline diagnostics are added to the verification tool result; no extra fitting or simulation of the proposal is introduced.

Older event chains remain byte-for-byte unchanged. Their frozen RC counterfactuals and residual checks are explicitly post-run reconstructions in hash-bound sidecars. The current development record rejects the frozen RC on both reserved conditions; this is not proof of unique topology or calibrated physical discrimination. Physical conditions still freeze at D2, without tuning to final evaluation outcomes. No new real API run or holdout access was needed for this comparison.


## Linear-family and periodic-state revision — 2026-10-27, before hardware

Reason: a positive-C-only comparator mixes absent-capacitance error with nonlinear mismatch. The common mystery grammar now contains five topologies: RC, RC plus IN–REF resistor, R only (C absent), R plus IN–REF resistor, and R plus OUT–REF resistor. All present resistors use independent log-uniform 4.7–47 kohm priors; present capacitors retain 0.47–4.7 microfarad. C=0 is a separate discrete topology with equal initial family mass, not a zero endpoint of a log prior. Output and input leak combinations and arbitrary tiny positive C are not covered. Explicit repair priors are unchanged. Every specimen uses the same mystery grammar; no holdout assembly was accessed.

Fit, normalized prior integration and adequacy remain separate. New resistive families require singular values >max(1, largest*1e-6) for full parameter identification; flat directions retain their priors. At a single load with ideal voltage drive, output leakage only identifies q=R*(1/Rout+1/Rload); conditional quadrature follows that ridge while preserving both original log-uniform priors. The best tested linear comparator is selected by training likelihood, then frozen before both reserved observations. No verification outcome selects the comparator.

A training-only amplitude diagnostic uses sine captures with identical settings except amplitude, matching time grids and no input shunt. Remove each trace's DC mean and compare the large output with the amplitude-ratio-scaled small output. Check IN scaling too. Normalize using the logged channel noise and sqrt(1+ratio^2), with independent-capture noise assumed and the existing development limit 3. This is an uncalibrated diagnostic, not an independent verification or unique diode proof; a nonlinear output buffer could also fail it. No thresholds or verification waveforms were changed in response to this diagnostic.

Capacitive sine proposals now extend the ideal commanded ZOH grid backward, starting with max(one period, 5*sum(R)*sum(C)) of pre-roll, rounded to whole samples. Double the pre-roll and compare all simulated node voltages on the identical capture grid; require maximum change <=10 microvolts. This numerical stopping check is separate from a 50-microvolt analytic waveform regression tolerance and physical calibration. Exceeding 32 seconds or 50,000 command samples without convergence rejects the simulation. Step proposals retain the settled DC operating point; the current memoryless B5 retains its original circuit and stimulus. Non-ideal inputs require a calibrated input-history path and are not silently replaced by ideal commands.

Every ngspice pre-roll invocation consumes the existing 420-call/60-second proposal budget. Exact repeated parameter/input evaluations may be reused within one proposal; actual invocations and reuse counts are recorded. The two-condition verification and six-acquisition budget remain unchanged. Historical event chains and their original RC-only comparisons retain their recorded meaning. A forthcoming development API check uses this revised protocol; it is not a frozen reliability or holdout evaluation.

### Numerical runtime follow-up — 2026-10-27, after that development API check

The capacitive ODE regression exceeded the unchanged 60-second fitting budget on the Linux CI runner, although it passed locally. A full sine period is an unnecessarily long initial guess for a fast RC circuit. Start pre-roll at 10*sum(R)*sum(C), rounded upward to samples with a four-sample minimum. Continue doubling and require the same <=10-microvolt difference on all node voltages over the full capture. The initial estimate alone never permits acceptance. The 32-second/50,000-sample horizon, actual-invocation accounting, 420-call/60-second fitting budget and all observation gates remain unchanged. Independent RC/ODE regressions cover this follow-up. The recorded Spark run used the preceding commit and a capacitor-free proposal, so this change neither rewrites that record nor needs another paid run.
