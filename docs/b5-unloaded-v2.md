# Prospective unloaded B5 protocol revision

Agreed October 30, 2026, before any physical B5 diode acquisition. The three
earlier resistor-only attempts and their DMM-anchor protocol stay unchanged.
The revision is encoded in `benchmate.b5_session.PROTOCOL` and the executable
[operator guide](b5-operator.md). It does not complete the original loaded gate.

The shared session runs resistor-only ADC control, a local operator intervention,
three training conditions, five linear-family fits, at most two model-authored
passive proposals, a publication barrier, and two untouched unloaded conditions.
Mock and physical use identical tools and scoring. Mock results always say mock;
the deterministic scripted provider always says scripted, never Spark-authored.
The mock plant uses a separate scalar diode equation solver, not the proposal's
ngspice implementation. Mock rehearsal validates integration, not real accuracy.

Each boot fixes one pre-waveform A1 HOLD mean as the common coordinate origin;
OUT is not independently zeroed. All families get the same constant unknown
reference (+/-80mV) and output-offset (+/-10mV) training parameters. Component
bounds stay 1k–100k ohm, 1n–10u F, shared diode IS 0.1–100nA and N 1–2.5.
Every parameter is frozen before verification; guard failures cannot be fitted
away. A4 supplies block-change checks, not an absolute REF calibration.
Constant-reference compensation alone does not fix gain error, clipping,
temperature drift or unknown dynamic fixture behavior.

The unloaded diode can confound R, effective IS and REF. Local rank is reported
as a diagnostic, not a veto on predictive adequacy or proof of unique topology.
An input branch can remain unobservable. No component is fixed from hidden
assembly truth. Generated connectivity and diode orientation go unchanged into
ngspice; at most two R/C values and shared diode parameters are fitted, plus the
common nuisance allowances. Each proposal has 420 simulator calls / 60 seconds.

Training uses +/-0.2V 1Hz sine, +/-0.5V step, +/-0.8V 1Hz sine. Reserved conditions
are +/-0.35V step and +/-0.65V 5Hz sine. All are unloaded. Whole-waveform RMS and
every predeclared step-time/8-bin sine-phase region must be <=9mV. This remains
a development engineering allowance, not calibrated statistical confidence.

The publication barrier records the exact topology, numerical model, linear
alternatives, processing convention, and command-input forecasts before either
reserved acquisition. Physical mode requires confirmed remote publication.
Command forecasts assume the nominal input/timing. Conditional predictions use
newly measured IN and channel timestamps only. Both receive separate scores;
a command-forecast miss is never erased by a conditional pass. No future OUT
or per-waveform output origin is permitted in the prediction template.

Physical source identity, boot continuity, raw electrical/timing/code checks and
one ARM after each explicitly confirmed USB-off intervention are retained.
All training and verification must share the specimen boot and origin. There is
no DMM-voltage pause, automatic retry/reset, live rewiring or automatic re-arm.
No claim that same boot alone establishes stationarity is made.

Provider configuration: Meta Spark max, <=8 HTTP requests, 8192 output tokens
per request, 128kB payload limit, $1 local reserve/request (not actual billing).
Only settings, tools, 25 sparse training points/waveform, fit summaries, generated
netlist and subsequent verification summaries are model input. Operator assembly
details, original raw ADC arrays, private specimens and prior physical results
stay outside the provider payload.

Physical invocation needs a fresh confirmed resistor-only setup. The current
workspace's previously requested power-down has not been confirmed. No physical
B5 or Spark-directed repair result is implied by this code or its unit tests.

## First actual Spark mock rehearsal completed

[The October 30 Spark max run](../examples/b5-unloaded-spark/2026-10-30/20261030T133514-4ea9a8848e/README.md)
completed in seven API requests. Spark chose the amplitude sweep and generated
one series-R / OUT-to-REF diode proposal outside the five initial linear families.
The exact model and command forecasts were pushed in `9cff3e8` before both reserved
mock acquisitions. Conditional whole RMS was 1.667 / 1.734mV; command-forecast
whole RMS was 1.925 / 1.953mV. Every regional check also passed; frozen linear
alternatives failed. The local parameter rank was 3 of 5, so no unique R/IS/REF
or topology claim is made. Eight mock waveforms, zero physical measurements.

The source hash chain, 40 source files, publication barrier, frozen numerical
models and sparse provider tool results passed the retained local audit. This
completes the bounded mock integration milestone, not physical B5 or the original
loaded/repeated-run gate. B5-specific user consent covered this run only; the
separate no-tool five-request comparison later received its own explicit approval and completed; see [the original replies](../examples/no-tool-spark/2026-10-30/20261030T134112-a9742f1b2e/README.md).
