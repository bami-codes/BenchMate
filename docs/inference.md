# Continuous inference — development revision, 2026-10-27 KST

This revision prepares for component variation. It does not declare physical accuracy or freeze D2 calibration.

## Priors, fit and evidence

Mystery mode always uses RC and RC plus an input-parallel resistor. Independent log-uniform priors: R 4.7–47 kΩ, C 0.47–4.7 µF, optional Rp 4.7–47 kΩ. This is a limited one-state grammar.

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

The validator accepts 1–6 bounded R/C/D elements, rejects code/directives and disconnected nodes, and preserves connections/orientation. A fixed ngspice harness checks simulated voltage/current bounds. At most two R/C values are fitted, 80 simulations per proposal, and two proposals per run.

The generic diode is IS=1 nA, N=1.8, RS=1 Ω at 27°C; this is not a characterized physical 1N4148. Synthetic truth uses an independent Shockley root solver. Reversing a proposed diode changes the simulation and fails the matching test.

Training: common step plus two 1 Hz sinusoids at 0.2/1 V. Reserved development checks: an unused ±0.35 V step and a 1 V sine with 10 kΩ load. Both predictions precede both verification observations. D2 will freeze the physical conditions separately.

The first live max-reasoning attempt hit 4,096 output tokens before proposing. The next explicitly used 8,192 and passed both checks. Both remain evidence; neither is final evaluation or a holdout result.

Implementation references: [SciPy least squares](https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.least_squares.html), [Gauss–Legendre quadrature](https://docs.scipy.org/doc/scipy/reference/generated/scipy.special.roots_legendre.html), [ngspice manual](https://ngspice.sourceforge.io/docs/ngspice-manual.pdf).
