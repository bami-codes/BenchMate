# Before-selection review and implementation notes

No physical B5 result or variant evaluation has been observed. v1.2 amends the
initial unexecuted draft before selection: unknown fits block eligibility; the
actual single-start gate is checked; D8 is correctly named antiparallel; audit
predictions condition on the same input; audit amplitude is bounded; RNG is
condition-keyed; implementation lives outside protected sources. The original
draft is represented by the preceding commits and conversation, not overwritten
as an allegedly executed protocol.

The design allowed at least 20 dynamic substeps. Linear-capacitor truth uses the
exact exponential solution per held segment instead of numerical substeps;
D6 uses 20 implicit substeps/frame and was checked at 40. This is an independent
solver, not the proposal's ngspice implementation. Test results are development
validation, not benchmark scores. No new model calls are made by selection.

Selection is deterministic conditional on machine/optimizer deadlines; deadline
and numerical failures are explicit unknowns. Its three repetitions are an
engineering screen, not a confidence guarantee. Every excluded grid member
remains reportable. An empty primary set is a valid possible outcome.

An additive implementation-v2 supplies the final evaluator and reporter while the
v1 selection process continues. bench.py, fitting.py, run.py and design.json
are byte-identical to selection start. The extra test validates a physical-log
lock and bounded audit inputs. Final evaluation has not been run.
