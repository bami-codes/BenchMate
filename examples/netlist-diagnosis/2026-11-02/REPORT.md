# Netlist diagnosis v1: offline development evidence

This is a software development check. No paid model, serial port or physical
specimen was used. The controller is explicitly scripted, not Muse Spark.
It uses the same three development training settings for every case. The actual
diagnosis session exposes every common menu action and does not choose an order
for a future Spark agent.

The last batch records exact hashes and copies of 66 runtime sources, including
the 53 preserved legacy files. All ten records have a fresh session and an
evaluator-only truth file. Models, parameters and command forecasts are frozen
before reserved acquisition. Reserved output never enters fitting.

| Circuit | Planted development fault | Terminal diagnosis after both reserved checks | Restored circuit, new session |
| --- | --- | --- | --- |
| RC pin-source example | External 20k series R after the IN probe | Effective series path 24.706k; external R and changed R1 remain indistinguishable | Consistent with design |
| Loaded sensor-filter segment | 1u filter replaced by 0.47u; 0.1u bypass in parallel | Filter-C hypothesis, 0.47039u, conditional on a single positive-valued component change | Consistent with design |
| Two-resistor timing chain | One 10k resistor replaced by 2.2k | RA or RB, indistinguishable; each can fit approximately 2.2025k | Consistent with design |
| Divider at an unpowered-input boundary | Unlisted OUT-to-REF diode | Linear/value candidates inadequate; proposed diode passes unused inputs | Consistent with design |
| Parallel decoupled load | Unlisted 10k series impedance instead of the ideal input connection | Value candidates inadequate; proposed series R approximately 9.9986k passes unused inputs | Consistent with design |

Ten outcomes match the development expectations. This is **not physical accuracy
or Spark accuracy**. Both the development truth and candidate predictions use
ngspice. Separate unit tests use an independent RC recurrence and a Shockley
root solver for numerical cross-checking. Proposals in this archive came from
the explicitly labelled software controller; no claim of Spark-authored
structure discovery is made.

The [equivalence checks](identifiability.json) execute both members of each
electrically equivalent pair throughout the public menu. They retain every
numerical difference. The sensor circuit's parallel capacitors expose their
sum. A known output load separates the scale of a divider whose unloaded gain
alone is tied. An input-parallel branch stays unobservable under measured-IN
conditioning. Equivalence on this menu does not establish global uniqueness.

The example circuits preserve fault principles, not the original complete
regulator, 555 oscillator, ESP32 or supply network. Their source links, values,
literal connections and Changed explanations are in `cases.py` and the
[implementation handoff](../../../docs/netlist-diagnosis-v1.md). LED/BJT remains
an explicitly deferred sixth case, with no invented result.

Files:

- [Final source-frozen summary](summary.json): fitted models, expected/actual
  outcomes and record locations for the last ten development runs.
- [Validation receipt](validation.json): tests, environment, source hashes and
  archive hash.
- [Original development records](development-records.tar.gz): three batches,
  all 30 event logs, frozen forecasts and final-batch source copies. The first
  batch used an input-side sensor bypass; the next two use the final parallel
  output capacitors. Earlier batches lack the later source snapshot mechanism
  and are retained as preliminary development records, not silently replaced.
- [Archive member hashes](archive-manifest.json): every archived file plus the
  equivalence result. All event chains and terminal payloads were checked after
  decoding; every archive member was re-read and verified.

Recorded environment: Python 3.11.9, NumPy 2.4.6, SciPy 1.17.1, ngspice 47.
Relevant Python tests: 87 passed, including 18 new tests. Existing JS tests:
7 passed. The physical adapter tests inject a fake byte-protocol board and make
no actual hardware access. A physical pilot still requires the real reviewed
schematic, frozen protocol, operator confirmation and separate authorization.
