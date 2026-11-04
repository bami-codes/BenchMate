# Submission text (Cerebral Valley form) — 4 Nov 2026

**Project name:** BenchMate — forecast-first experiments on a real circuit

(Two other entries in this hackathon are also called BenchMate; the subtitle is on the form, the video title card, the README and the repository description so the three stay distinct.)

**Tagline (one line):** Muse Spark chooses experiments on a real circuit; every forecast is frozen before a $40 Arduino bench measures; the sealed fault is found.

**Track:** Indie Developer · **Problem statement:** Push the Frontier · **Team:** solo (bami-codes), with Codex and Claude as coding agents

**Links:** Live demo https://bami-codes.github.io/BenchMate/ · Repository https://github.com/bami-codes/BenchMate (MIT, public) · Video https://www.youtube.com/watch?v=BFlJHOEapV8

---

**Description**

The drawing is right. The board looks right. The output is wrong. That moment comes to every lab prototype, repair bench and first production board, and today a person settles it by choosing measurements, predicting what each should show, and crossing explanations out. BenchMate gives that job to Muse Spark, on a real bench, under rules that leave a record of every step: forecasts frozen before each measurement, a fault sealed before the first one, and a verifier anyone can run offline.

Spark receives one schematic image and a fixed menu of experiments (steps and sines, with or without a 9.99 kΩ load) on an Arduino UNO R4 bench that costs about $40. It chooses the next experiment and says why. Before the bench moves, every standing explanation of the circuit is simulated in ngspice for the commanded input and that forecast is hashed into the run's event log. The Arduino measures; the candidates are then refitted to every measurement so far, and an explanation whose best fit still misses by more than 9 mV RMS, on the whole step or any region of it, is crossed out. When no value explanation survives, Spark proposes a part the drawing does not show, as a netlist. When two explanations give the same waveforms, Spark names one part to read and the quantity; the expected range under each explanation is frozen and pushed to GitHub before the operator touches a multimeter. The final models are frozen and pushed before two held-back inputs are measured; those are scored by driving each frozen model with the measured input, with no refitting. The fault itself was planted by the operator and committed as a digest before the first measurement; it is opened only after the verdict, its digest is checked by code against that commitment, and the two statements, Spark's answer and what was planted, stand side by side on every report.

Five problems from real forum threads were rebuilt as small circuits, each with one sealed fault: a pin's hidden output resistance, an unpowered chip loading a divider, a filter capacitor of the wrong value, contact resistance on a breadboard, a 555 timing resistor far too small. Spark found where each board disagreed with its drawing. It proposed the hidden diode and the hidden series resistor as parts the drawing lacked; it asked for exactly the readings that separated indistinguishable explanations; in the capacitor case it said the photo could not tell two identical parts apart and let two out-of-circuit readings and the frozen bands decide. Each of the five cases ended with a fresh-context restored rerun that reported no mismatch in the tests Spark chose; the earlier stopped and abstained attempts are retained in the ledger.

Counted from the records: across the five cases, 13 registered workflow attempts started 15 diagnostic runs; 3 stopped before a verdict, 2 abstained, 10 returned a verdict, and those 10 are the runs replayed on the site (5 fault diagnoses with held-back checks passed, 2 structure proposals, 4 readings, 5 seals matched, 5 restored reruns). 101 Muse Spark calls and 6 SAM 3.1 calls, about $1.01, including the stopped and abstained attempts. Every attempt is in the public ledger and named on the reports. These are counts, not an accuracy rate. The model never saw the fault; the developer knew it: model-blind, not a blind trial of the team.

Why this is the frontier and not a circuit tester: the model is not asked to explain a measurement somebody made. It chooses the measurement; the simulator forecasts it before the bench moves; code holds the forecast to measurements the model had not yet seen, with the fault sealed until the verdict. The loop needs six things and nothing more — a description of what was intended, a space of explanations, a simulator, an instrument with a menu, a person for what the instrument cannot do, and a sealed truth — and none of the six is specific to electronics. A circuit was the cheapest real system where that loop could be run honestly in nine days. The experiments in this demo did not exist until the model asked for them.

**How Meta's models are used**

Who does what, in four lines. Muse Spark chooses each experiment from the fixed menu, interprets the misses, proposes new circuit structure when every value explanation has failed, and asks for a reading when the waveforms cannot decide. ngspice and the engine do the numerical fitting, the waveform forecasts, the miss against the 9 mV allowance and the rule-out. SAM 3.1 and Spark vision say which body on the board photo is which part. The operator moves jumpers, reads the multimeter, and never tells the model the fault. Where the model contributed is visible in the records: the two structure proposals (cases 04, 05) and the four readings it asked for. The earlier synthetic benchmark and its baselines are in the README.

Muse Spark 1.3 (Meta Model API) is the agent: it chooses every experiment with a reason, asks for rewiring, decides when to run the held-back check, proposes new netlists when every value explanation has failed, and chooses which part to read and which quantity. Muse Spark vision reads each schematic image into parts and connections before the run and, after the diagnosis, looks at the board photo with SAM 3.1's bodies and names the one that is the part to read (or says it cannot). SAM 3.1 segments the mini board photo with one generic prompt; its native masks are the only outlines shown and no part value is ever read from a photo. Muse Spark Open (Baseten) ran the earlier synthetic benchmark as a development comparison. Spark is never told the fault, the assembly or the operator's reading before it is scored; for the photo stage it receives the operator-confirmed port positions of IN, OUT and REF, never a hidden part. Every request and response is in the records.

**What was built during the hackathon**

Everything, 27 October – 4 November 2026, by one person with Codex and Claude as coding agents: the Arduino instrument firmware (boot-bound captures, reference guard), the bench, the fit engine (ngspice, whole-and-region scoring, forecast freezing and publication), the Spark tool loop, the reading and seal protocol, the SAM/Spark photo stage, the offline verifier, the replay site, and the five physical cases. Third-party libraries, model weights and fonts keep their own licenses.

**Verify it**

`PYTHONPATH=src python3 -S -m benchmate verify <run folder>` re-checks any record offline: every event hash-chained, every forecast hash matched to the event that froze it, forecast → capture → measurement order enforced. The commands and their PASS lines for all five cases are in the README; each case report on the site prints them too.

---

**Short version (if the form caps length)**

BenchMate gives Muse Spark a $40 Arduino bench. It reads the schematic and chooses experiments from a fixed menu; ngspice forecasts each one; the forecast is hashed (and pushed to GitHub before the held-back check) before the bench measures. Explanations are refitted to every measurement and crossed out when their best fit still misses by more than 9 mV; the two held-back inputs are scored against the frozen models with no refitting. When none survive, Spark proposes a part the drawing lacks; when two give the same waveforms, it names one part to read, with ranges frozen first. Five faults from real forum threads were sealed as digests before measurement; all five seals matched the verdict (two by proposing hidden parts), and each restored rerun reported no mismatch in the tests Spark chose. 13 registered attempts started 15 runs: 3 stopped, 2 abstained, 10 reached a verdict and are replayed on the site. 101 Spark calls, 6 SAM 3.1 calls, ≈$1.01. One command verifies any run offline.

---

## Form answers (under 3,000 characters each) — submitted 5 Nov 2026, team bami-codes, team number 2828

**Project Description**

The drawing is right. The board looks right. The output is wrong. What should you measure next?

BenchMate gives Meta's Muse Spark a real $40 Arduino bench to investigate that question. It is built for engineers and students debugging circuits: Spark chooses experiments, proposes explanations, and asks for the measurement that can tell competing explanations apart.

Spark reads the schematic and chooses tests from a fixed menu. Before each measurement, a circuit simulator records what the current explanations predict. The engine fits those explanations to the measurements collected so far and rejects those that cannot fit within the test allowance. If changing component values cannot explain the board, Spark can propose a component absent from the drawing. If the waveforms cannot decide, it can request a specific multimeter reading. A person moves the wires and takes that reading.

Two examples show what this enables. In Case 04, Spark proposed a diode absent from the drawing. After the engine fitted this model, it was locked and published before two new inputs were measured. Both checks passed the 9 mV error allowance. Opening the sealed assembly record revealed a diode in the direction Spark proposed. In Case 01, two explanations produced the same waveforms. Spark requested one resistance reading: 4.71 kΩ showed that R1 was correct and the extra resistance lay before it.

We rebuilt five problems reported on engineering forums as small circuits with deliberately planted faults hidden from Spark. Each case ended with a repaired board and a fresh run reporting no mismatch in the tests Spark chose. Across all 15 diagnostic runs, 10 reached a verdict (five fault diagnoses and five repaired reruns), two abstained and three stopped; every attempt remains public.

The forecasts are recorded before measurement, final circuit models and reading ranges are published before their checks, and the planted fault is documented before the first measurement and revealed only after the verdict. Judges can replay the runs, click through to the underlying events, and verify record integrity offline with Python and no extra packages.

Built solo in nine days, BenchMate demonstrates AI-guided experiments on physical hardware: an unexplained output becomes a concrete next check.

**Describe your use of Meta products to build the submitted project**

BenchMate uses Muse Spark 1.3 through the Meta Model API as the runtime agent, with SAM 3.1 for locating physical components.

Spark vision reads each schematic into components, values and connections, which an operator confirms. In the experiment loop, Spark receives the measurement history and available actions, chooses each test and explains why. It can submit a new circuit description for simulation when all component-value explanations fail, or request a specific component reading when the remaining explanations cannot be separated by the waveforms.

SAM 3.1 segments the board photo into component masks. Spark vision connects a requested part such as R1 to one of those masks, and the operator confirms the selection before measuring. Spark can also report ambiguity: in Case 02, it could not distinguish two visually identical capacitors, so two physical readings were used to resolve their identities.

ngspice and the engine handle numerical fitting, waveform predictions and scoring. They record forecasts before capture and lock the final circuit models before testing them on inputs excluded from fitting. Spark does not score its own answers. A person moves jumpers and reads the multimeter; the fault information is withheld from Spark.

Across all attempts, the records contain 101 Spark calls and 6 SAM 3.1 calls, costing about $1.01 at published rates, including stopped and abstained attempts. Model requests, responses and measurement outcomes are preserved in public records. During development, we also ran Muse Spark Open through Baseten on an earlier synthetic benchmark, as a comparison.

**Why are Meta's models important to your solution?**

Muse Spark supplies the judgment that turns measurements into the next experiment. It combines schematic understanding, reasoning about measurement patterns, and tool calls that produce actions the bench can execute. In this implementation, an engineer would otherwise choose the tests, propose structural changes and select follow-up readings.

Case 04 shows why this matters. Changing component values could not explain why only one side of the signal clipped. Spark proposed a diode and supplied a circuit description the simulator could test. In Case 01, the engine identified two explanations with identical terminal waveforms; Spark chose an isolated resistance measurement to distinguish them. These are two different contributions: revising the circuit's structure and selecting another kind of evidence when the waveforms cannot decide.

SAM 3.1 connects those decisions to the physical bench. Its component masks give Spark concrete regions to associate with a requested part, so "measure R1" can become an operator-confirmed location on the actual board. When the photo cannot settle the identity, Spark can report that uncertainty and use measurements instead.

The simulator and engine provide numerical checks; the models provide interpretation and action selection. Keeping those roles separate makes the models' proposals testable against measurements they did not have when making the proposal.

This is our Push the Frontier result: a model guiding real experiments, revising an explanation and being checked against the physical world. We have demonstrated the loop on five small circuits. Extending it to other physical systems would require their simulators, instruments and action limits; AI-guided experimentation is the broader goal.
