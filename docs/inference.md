# Continuous inference — development revision, 2026-10-27 KST

This revision prepares for component variation. It does not declare physical accuracy or freeze D2 calibration.

## Priors, fit and evidence

Mystery mode shares five topologies across all specimens: RC, RC plus an input-parallel resistor, resistor only, resistor plus an input parallel resistor, and resistor plus an output parallel resistor. Independent log-uniform priors: present resistors 4.7–47 kΩ, present capacitors 0.47–4.7 µF. Absent capacitors have a separate discrete family mass, not a log-C prior endpoint. This remains a limited grammar, not all linear circuits.

Explicit repair mode uses schematic alternatives: nominal R 9.5–10.5 kΩ/C 0.9–1.1 µF; changed R 15–25 kΩ with nominal C; changed C 1.5–2.5 µF with nominal R. These are declared development priors, not secretly selected specimen information or measured component tolerances.

Bounded least squares fits parameters. Evidence separately integrates likelihood against the normalized prior. For tau=RC, `p(tau,R)=p_RC(R,tau/R)/R`. In u=log(tau), v=log(R), the density is constant on the transformed parallelogram, with v limits depending on u. Independent rectangular tau/R priors are not substituted.

Piecewise Gauss–Legendre grids preserve the full support and refine near the fit. Orders 4, 7 and 10 are compared; adequate families require log-evidence refinement delta below 0.05 before confirmation. Prior mass and moments are tested against analytical values. This is numerical convergence, not proof of global model adequacy.

Without loading or transient shunt observations, only tau is separately observed. R/C intervals may change due to prior restrictions; this is not separate identification. Unobserved input-branch prior mass is integrated, not discarded. Fit-Jacobian rank also prevents confirming singular fits.

## Residuals and independent checks

Synthetic defaults: marginal sigma 3 mV, rho=0, model floor=0. Per-channel sigma/rho overrides are supported. AR(1) whitening uses a stationary first residual and subsequent innovations; separately settled DC levels are independent. The optional model floor combines in quadrature with sigma and inherits the channel's AR(1) shape. Cross-channel covariance is not modeled.

Whole traces and predefined regions are checked per channel: 0–5, 5–20 and 20–80 ms after a step, or eight sine phase bins. Regions never depend on observed residual peaks. The current normalized RMS limit is 3, an engineering default, **not a calibrated false-positive rate**. D2 must estimate and freeze these quantities.

A +5% C perturbation can pass the old complete-trace RMS gate while failing a new transient gate. Continuous fitting then estimates the changed value rather than assuming the nominal parameter is exact.

Ordinary confirmation freezes a posterior prediction before a reserved development ±0.3 V step. Predictive variance uses a marginal Gaussian approximation from frozen posterior draws. No confirmation data enters fitting. This is not calibrated hardware confidence. Support, conditional probability, integration convergence and prediction verification remain separate fields.

## Menu

85 synthetic conditions: six log frequencies × sine amplitudes 0.2/1 V × two shunt states × three load states; steps ±0.2/0.5 V over those states; and a two-level shunt DC acquisition. `--max-hz` configures the provisional grid, default 100 Hz. No hardware limit is certified.

Ranking is a posterior predictive separation/spread proxy with the same whitening and explicit engineering cost, not exact information gain. Spark can choose every enumerated action; the top five are shown and settings can be queried. DC pairs cost two acquisitions; mounting changes are counted. Expanded observations may favor a shunt step or 4.7 kΩ load over the earlier DC/10 kΩ examples. D2 must determine which choices survive actual channel timing/noise.

## Nonlinear proposals

The validator accepts 1–6 bounded R/C/D elements, rejects code/directives and disconnected nodes, and preserves connections/orientation. A fixed ngspice harness checks simulated voltage/current bounds. At most two R/C values plus shared diode IS/N are fitted (four values total), with 420 simulator calls and 60 seconds per proposal and two proposals per run. The timer is checked before each call; an in-flight simulator call has its own 15-second timeout.

The diode library **starts** at IS=1 nA, N=1.8; training may fit IS within 0.1–100 nA and N within 1–2.5. RS=1 Ω and temperature=27°C remain fixed. All proposed diodes currently share these parameters. Synthetic truth uses an independent Shockley root solver with IS=3 nA, N=1.9, deliberately different from the initial library. Reversing a proposed diode changes the simulation and fails the matching test. Bounded IS/N adaptation addresses parameter mismatch, not arbitrary model error or physical 1N4148 accuracy.

The simulator uses `reltol=1e-7`, `abstol=1e-14` A and `vntol=1e-8` V. These numerical tolerances are separate from observation adequacy thresholds. Tightening these alone did **not** fix the Linux/ngspice 42 failure: noiseless IS recovery remained 6.24% off, exceeding its unchanged 6% test limit.

Direct reproduction with a separate ngspice 42 build found missed PWL corners, with up to 12.56 mV input error on the 1 V sine. Its source selects a corner infinitesimally ahead of the current time, which the breakpoint scheduler then ignores; the later corner is missed. The [version 47 implementation](https://github.com/imr/ngspice/blob/ngspice-47/src/spicelib/devices/vsrc/vsrcacct.c) advances the selection threshold by `CKTminBreak`. BenchMate now requires ngspice 47+, records its version, and CI builds checksum-pinned 47. It also sets `minbreak=1e-12` s explicitly to preserve both ends of the 10 ns PWL transition on non-XSPICE builds. Setting minbreak alone did not repair version 42. The regression checks source and output agreement within 1 µV before fitting; parameter-recovery and observation adequacy limits remain unchanged. Historical executions used macOS/ngspice 47 and retain their original harness hashes. Neither their records nor their measured results were rewritten.

Training: common step, two unloaded 1 Hz sinusoids at 0.2/1 V, and a 1 V sine with **4.7 kΩ** load. The load separates R from IS, which nearly compensate under unloaded voltage observations. Total budget is one exploration + three diagnostic captures + two verifications = six. Training passes only with optimizer convergence, regional adequacy, and a local log-parameter Jacobian having minimum singular value >1 and condition number <1e5. These are development identifiability checks, not globally calibrated uncertainty bounds.

Reserved development checks remain an unused ±0.35 V step and a 1 V sine with **10 kΩ** load. Both predictions and fitted diode parameters are recorded before either verification observation; no refitting is allowed. Predictions use a circuit-independent commanded waveform, not an RCModel output template. The ideal command must be replaced by a calibrated actuator/timing model for hardware. D2 will freeze the physical conditions separately.

The structure-discovery prompt asks for explanations from observations and reported fit checks, without identifying the hidden circuit as nonlinear or directing attention to two-amplitude patterns. The allowed R/C/D grammar and starting library are declared prior information. The training schedule is fixed by this development protocol; do not claim Spark selected those four conditions.

The first live max-reasoning attempt hit 4,096 output tokens before proposing. The next explicitly used 8,192 and passed both checks. Both remain evidence; neither is final evaluation or a holdout result.

Implementation references: [SciPy least squares](https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.least_squares.html), [Gauss–Legendre quadrature](https://docs.scipy.org/doc/scipy/reference/generated/scipy.special.roots_legendre.html), [ngspice manual](https://ngspice.sourceforge.io/docs/ngspice-manual.pdf).

## Discrete zero-capacitance candidates

Mystery mode has five shared topologies: the two original capacitive families, R only, R with an input parallel resistor, and R with an output parallel resistor. A missing capacitor is represented exactly by C=0 and an algebraic conductance solve. It has its own family prior mass; it is not approximated by a tiny positive C or included in a log-C integral. Positive component bounds and the conditional nature of all claims are logged. Repair families retain their explicit schematic priors.

For a resistor under ideal unloaded drive, R is not identified. With one output load, a two-resistor output-leak circuit may identify only a gain combination. Conditional quadrature concentrates samples along this likelihood ridge without changing the independent component priors. Predictions use command templates for both capacitive and algebraic families. No candidate is chosen from a specimen label.

The amplitude-scaling check is independent of a circuit fit but still assumes matching acquisition conditions, settled states and a linear calibrated measurement path. It removes DC offsets, checks the actual input channel, and reports output mismatch against the recorded development noise. It cannot distinguish DUT nonlinearity from output-buffer saturation and cannot replace the reserved verification conditions.

## Periodic proposal state

Capacitive sine netlists use progressively doubled numerical pre-roll on the same sample grid and phase as the capture. All simulated node voltages must change by at most 10 uV on the capture interval; a bounded horizon rejects unresolved settling. This avoids starting a settled observation prediction from a DC initial state, including frequencies with a non-integer number of samples per period. Every actual ngspice invocation counts against the proposal budget. Training-only repeated evaluations may be reused, with counts logged. Independent analytic RC and Shockley-ODE tests check this path; no holdout fixture or real board result is implied.
