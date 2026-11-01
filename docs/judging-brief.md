# BenchMate: concise answers grounded in the current record

**Main claim:** Muse Spark chooses an experiment on a real circuit, BenchMate freezes
the models, and a new measurement decides which explanation remains supported.

## Why use an LLM when the deterministic engine also gets the linear cases right?

The engine should do the numeric work. On our synthetic linear benchmark, the engine
and fixed expert plan are excellent; hiding their ranking from Spark did not improve
performance. We keep that ranking in the product. Spark's additional role is to turn
an open-ended problem into tool actions and propose a literal netlist when the starting
models fail. The latter is demonstrated on the B5 simulated bench, not yet physical.
Its R/C/D grammar and bounded search are human-designed; it is not unconstrained discovery.

## What actually ran on hardware?

One retained Spark-directed D01 diagnosis on Oct 30: 21.4 ms instead of the designed
10 ms; a requested 9.99 kΩ load; 32.5 mV error for the resistance-change explanation
versus 3.0 mV for capacitance change; 3.04 mV on a reserved 5 Hz sine. The model values
were frozen before validation. The operator changed the wiring. This is a planted,
known development fixture; it is not a blind physical accuracy benchmark.

Spark-directed physical repair, physical B5 and another operator's completion are
pending. The real Spark + mock repair rehearsal and B5 repeats are labelled simulated.
Do not claim those milestones until the new physical records exist.

## Were the plotted curves truly available before the measurement?

The model parameters were fixed first. Most displayed D01 comparison curves then use
the measured input from that capture, so they are conditional predictions. They do not
use the validation output to refit the model. The video shows the measured trace first
and the conditional overlay afterwards. Repair and B5 command-input forecasts are a
separate premeasurement product, with separate error checks; they may disagree.

## Does it identify the exact failed component or unique hidden topology?

D01's ≈2.1× capacitance statement assumes nominal 10 kΩ resistance within the declared
RC alternatives. B5 proposes a useful nonlinear structure outside five starting linear
models and predicts reserved inputs. Multiple internal circuits or parameters may give
similar external behavior. We do not infer a unique topology, exact diode parameters,
or actual ESP32 internal protection from the simplified fixture.

## What does the benchmark establish?

Task A measures information access: without measurements Spark identified 8/24 in-family
cases and left 22 of all 30 unresolved; with the bench it identified 24/24, matching both
deterministic baselines. On six dual-change cases, Spark completed five rejection reports
and one remained incomplete. Those abstentions and incomplete reports are not wrong-part
claims, but are not all completed diagnoses either.

Task B ranking-hidden Spark completed 15/16, versus 16/16 for engine/fixed plan; random
completed 30/48 runs on the same 16 circuits repeated three times. No LLM superiority
or reduction in wiring is established. All mount counts here are simulated settings.

Spark Open executed the same Task A: 21/24 identified, 1/6 rejected, eight incomplete.
The endpoint returned multiple tools despite the adapter's explicit single-tool setting.
This is end-to-end interface performance, not a pure ranking of the models' reasoning.
A failed later development transport probe is preserved separately and does not replace it.

## Who can use it now?

A maker or electronics student with the documented small passive fixture and an Arduino
UNO R4. The development parts basket was ₩55,980 including spares; it excludes a laptop
and multimeter. The build guide covers wiring, firmware and the first communication check.
The public replay needs neither a board nor an API key. We have not demonstrated factory
QA, general appliance repair, robotic control, or independent novice success yet.

## Why are failures visible?

A held-out result only helps if the test was fixed before it happened and a failed test
cannot vanish. Run chains, frozen model records, publication receipts and first-attempt
benchmark archives are inspectable. A hash chain makes later edits detectable; it does
not by itself prove that a sensor is calibrated or a circuit label is correct.

## What should the final video lead with?

Lead with the actual physical mystery and Spark's recorded reason for adding a load.
Show the new physical repair if it passes, and B5 with its correct source label. Keep
numeric baselines visible, but do not make a weak strategy comparison the climax.
Do not combine separate no-tool replies, later vision intake and the Oct 30 run as one
continuous trial. The 51-second highlight is an already-rendered source for the diagnosis.

Sources: [physical run](../examples/hardware-spark-rc/2026-10-30/20261029T174402-d3eaa8e612/README.md),
[all overnight records](../examples/overnight/2026-11-02/README.md),
[final evaluation scope](final-evaluation-scope.md), [build guide](build-your-own.md).
