# 제출 폼 초안 (Cerebral Valley)

**Project name:** BenchMate

**Tagline (one line):** Muse Spark chooses the experiment; a $40 Arduino bench decides whether its explanation holds.

**Track:** Indie developer · **Theme:** Push the Frontier

**Description:**

On the Arduino forum, a voltage divider connected to an ESP32 read 1.1 V instead of 1.8 V. Replies guessed resistor tolerance, the meter, bad solder. The right explanation, an unpowered ESP32 loading the divider through its input clamp, came early, but only the poster's own test confirmed it: "Real life testing was the correct way to find the issue." Students and makers hit problems like this every day with no oscilloscope and nobody to ask, and resolving competing physical explanations requires measurements.

BenchMate turns an Arduino UNO R4 into a signal source and recorder and gives Muse Spark the bench as tools. Spark chooses each measurement, asks the human to move a wire when that adds information, and must freeze its model before validation measurements. The engine simulates, fits training data only, and scores every explanation on the whole waveform and every region.

On a real circuit with a fault I deliberately planted (designed τ 10 ms, measured 21.4 ms), Spark recognized that one trace cannot separate a larger R from a larger C, asked for a known load, and kept only the explanation that survived: C changed (3.0 mV RMS vs 32.5 mV for R changed). It then passed a reserved sine it had never seen (3.04 mV) and reported what it still did not know. The whole run took under six minutes with one wiring change. [Physical repair result pending; the actual-Spark mock rehearsal has passed.] On a simplified input-clamp test circuit inspired by the forum problem (simulated bench so far; Spark is not told the wiring), all five starting linear models failed, Spark proposed a structure outside them (series R plus a diode to REF), its prediction was pushed to GitHub before two unseen inputs were measured, and both matched.

**How we use Meta models:** Muse Spark 1.3 runs the experiment loop through tool calls: medium effort for physical diagnosis and repair, max effort for structure discovery, where it writes literal netlists that run in ngspice. Spark vision reads a schematic image into a design candidate the user confirms. SAM 3.1 was evaluated for highlighting the faulty part in a bench photo. Measured findings: in one qualitative no-tool case, all five replies led with a timing-definition hypothesis and recommended re-measuring; at the key decision, medium chose the same experiment as max 5/5 in a third of the time.

**What was built during the hackathon:** BenchMate firmware, instrument protocol, engine, Spark tool loop, viewers, experiments and video (first commit Oct 27, 2026). Third-party libraries, model weights and the bundled font retain their own licenses and credits.

**Links:** [GitHub](https://github.com/bami-codes/BenchMate) · [Public interactive replay and 51-second diagnosis film](https://bami-codes.github.io/BenchMate/) · Final submission video: not uploaded. A 2:36 editing backup is ready locally.

**Evaluation update:** On 30 synthetic Task A cases, Spark with measurement access identified 24/24 in-family cases, matching the engine and fixed plan; without measurement access it identified 8/24. Six cases changed both R and C: Spark completed five justified rejection reports, with one incomplete. Spark Open completed 21/24 in-family identifications and 1/6 rejection reports; eight runs stopped on multiple-tool responses to the single-tool adapter. All first attempts are retained. On Task B, ranking-hidden Spark completed 15/16 versus 16/16 for the engine and fixed plan. We therefore retain engine ranking in the linear workflow and make no LLM-superiority claim. [Full comparisons](../examples/overnight/2026-11-02/README.md).
