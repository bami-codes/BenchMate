# Submission text (Cerebral Valley form) — 4 Nov 2026

**Project name:** BenchMate — forecast-first experiments on a real circuit

(Two other entries in this hackathon are also called BenchMate; the subtitle is on the form, the video title card, the README and the repository description so the three stay distinct.)

**Tagline (one line):** Muse Spark designs experiments on a real circuit, forecasts each one before a $40 Arduino bench measures it, and finds the sealed fault.

**Track:** Indie Developer · **Problem statement:** Push the Frontier

**Links:** Live demo https://bami-codes.github.io/BenchMate/ · Repository https://github.com/bami-codes/BenchMate (MIT, public) · Video: (YouTube link)

---

**Description**

The drawing is right. The board is right. The output is wrong. That moment comes to every lab prototype, repair bench and first production board, and today a person settles it by choosing measurements, predicting what each should show, and crossing explanations out. BenchMate gives that job to Muse Spark, on a real bench, under rules that leave a record of every step: forecasts frozen before each measurement, a fault sealed before the first one, and a verifier anyone can run offline.

Spark receives one schematic image and a fixed menu of experiments (steps and sines, with or without a 9.99 kΩ load) on an Arduino UNO R4 bench that costs about $40. It chooses the next experiment and says why. Before the bench moves, every standing explanation of the circuit is simulated in ngspice for the commanded input and that forecast is hashed into the run's event log. The Arduino measures; the same frozen model is then driven by the measured input for a conditional check, and both scores are kept; an explanation that misses by more than 9 mV RMS, on the whole step or any region of it, is crossed out. When no value explanation survives, Spark proposes a part the drawing does not show, as a netlist. When two explanations give the same waveforms, Spark names one part to read and the quantity; the expected range under each explanation is frozen and pushed to GitHub before the operator touches a multimeter. The final forecast is pushed before two held-back inputs are measured. The fault itself was planted by the operator and committed as a digest before the first measurement; it is opened only after the verdict, its digest is checked by code against that commitment, and the two statements, Spark's answer and what was planted, stand side by side on every report.

Five problems from real forum threads were rebuilt as small circuits, each with one sealed fault: a pin's hidden output resistance, an unpowered chip loading a divider, a filter capacitor of the wrong value, contact resistance on a breadboard, a 555 timing resistor far too small. Spark found where each board disagreed with its drawing. It proposed the hidden diode and the hidden series resistor as parts the drawing lacked; it asked for exactly the readings that separated indistinguishable explanations; in the capacitor case it said the photo could not tell two identical parts apart and let two out-of-circuit readings and the frozen bands decide. Each of the five cases ended with a fresh-context restored rerun that reported no mismatch in the tests Spark chose; the earlier stopped and abstained attempts are retained in the ledger.

Counted from the records: across the five cases, 13 registered workflow attempts started 15 diagnostic runs; 3 stopped before a verdict, 2 abstained, 10 returned a verdict, and those 10 are the runs replayed on the site (5 fault diagnoses with held-back checks passed, 2 structure proposals, 4 readings, 5 seals matched, 5 restored reruns). 101 Muse Spark calls and 6 SAM 3.1 calls, about $1.01, including the stopped and abstained attempts. Every attempt is in the public ledger and named on the reports. These are counts, not an accuracy rate. The model never saw the fault; the developer knew it: model-blind, not a blind trial of the team.

Why this is the frontier and not a circuit tester: the model is not asked to explain a measurement somebody made. It designs the measurement, commits to a forecast first, and is checked by code against measurements it had not yet seen, with the fault sealed until the verdict. The loop needs six things and nothing more — a description of what was intended, a space of explanations, a simulator, an instrument with a menu, a person for what the instrument cannot do, and a sealed truth — and none of the six is specific to electronics. A circuit was the cheapest real system where that loop could be run honestly in nine days. The experiments in this demo did not exist until the model asked for them.

**How Meta's models are used**

Muse Spark 1.3 (Meta Model API) is the agent: it chooses every experiment with a reason, asks for rewiring, decides when to run the held-back check, proposes new netlists when every value explanation has failed, and chooses which part to read and which quantity. Muse Spark vision reads each schematic image into parts and connections before the run and, after the diagnosis, looks at the board photo with SAM 3.1's bodies and names the one that is the part to read (or says it cannot). SAM 3.1 segments the mini board photo with one generic prompt; its native masks are the only outlines shown and no part value is ever read from a photo. Muse Spark Open (Baseten) ran the earlier synthetic benchmark as a development comparison. Spark is never told the fault, the assembly or the operator's reading before it is scored; for the photo stage it receives the operator-confirmed port positions of IN, OUT and REF, never a hidden part. Every request and response is in the records.

**What was built during the hackathon**

Everything, 27 October – 4 November 2026, by one person with Codex and Claude as coding agents: the Arduino instrument firmware (boot-bound captures, reference guard), the bench, the fit engine (ngspice, whole-and-region scoring, forecast freezing and publication), the Spark tool loop, the reading and seal protocol, the SAM/Spark photo stage, the offline verifier, the replay site, and the five physical cases. Third-party libraries, model weights and fonts keep their own licenses.

**Verify it**

`PYTHONPATH=src python3 -S -m benchmate verify <run folder>` re-checks any record offline: every event hash-chained, every forecast hash matched to the event that froze it, forecast → capture → measurement order enforced. The commands and their PASS lines for all five cases are in the README; each case report on the site prints them too.

---

**Short version (if the form caps length)**

BenchMate gives Muse Spark a real $40 Arduino bench. It reads the schematic, chooses experiments from a fixed menu, and must forecast each one (hashed, then pushed to GitHub) before the bench measures. Explanations that miss by more than 9 mV are crossed out; when none survive, Spark proposes a part the drawing lacks; when two give the same waveforms, Spark names one part to read with ranges frozen first. Five faults from real forum threads were planted and sealed as digests before measurement; Spark narrowed all five to the planted fault (two by proposing hidden parts), and each case ended with a restored rerun that reported no mismatch. 13 registered attempts started 15 diagnostic runs; 3 stopped, 2 abstained, 10 reached a verdict and are replayed on the site; 101 Spark calls, 6 SAM 3.1 calls, about $1.01. Every attempt, including the stopped and abstained ones, is in the public ledger, and one command verifies any run offline. The experiments did not exist until the model asked for them.
