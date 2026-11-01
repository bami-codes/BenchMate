# 제출 폼 초안 (Cerebral Valley)

**Project name:** BenchMate

**Tagline (one line):** Muse Spark chooses the experiment; a $40 Arduino bench decides whether its explanation holds.

**Track:** Indie developer · **Theme:** Push the Frontier

**Description:**

On the Arduino forum, a voltage divider connected to an ESP32 read 1.1 V instead of 1.8 V. Replies guessed resistor tolerance, the meter, bad solder. The right explanation, an unpowered ESP32 loading the divider through its input clamp, came early, but only the poster's own test confirmed it: "Real life testing was the correct way to find the issue." Students and makers hit problems like this every day with no oscilloscope and nobody to ask, and an AI without a bench can only add more plausible guesses.

BenchMate turns an Arduino UNO R4 into a signal source and recorder and gives Muse Spark the bench as tools. Spark chooses each measurement, asks the human to move a wire when that adds information, and must freeze its model before validation measurements. The engine simulates, fits training data only, and scores every explanation on the whole waveform and every region.

On a real circuit with a hidden fault (designed τ 10 ms, measured 21.4 ms), Spark recognized that one trace cannot separate a larger R from a larger C, asked for a known load, and kept only the explanation that survived: C changed (3.0 mV RMS vs 32.5 mV for R changed). It then passed a reserved sine it had never seen (3.04 mV) and reported what it still did not know. The whole run took under six minutes with one wiring change. [Physical repair result pending; the actual-Spark mock rehearsal has passed.] On a simplified input-clamp test circuit inspired by the forum problem (simulated bench so far; Spark is not told the wiring), all five starting linear models failed, Spark proposed a structure outside them (series R plus a diode to REF), its prediction was pushed to GitHub before two unseen inputs were measured, and both matched.

**How we use Meta models:** Muse Spark 1.3 runs the experiment loop through tool calls: medium effort for physical diagnosis and repair, max effort for structure discovery, where it writes literal netlists that run in ngspice. Spark vision reads a schematic image into a design candidate the user confirms. SAM 3.1 was evaluated for highlighting the faulty part in a bench photo. Measured findings: in one qualitative no-tool case, all five replies led with a timing-definition hypothesis and recommended re-measuring; at the key decision, medium chose the same experiment as max 5/5 in a third of the time.

**What was built during the hackathon:** everything in the repository (first commit Oct 27, 2026): firmware, instrument protocol, engine, Spark tool loop, viewer, all experiments and this video.

**Links:** GitHub https://github.com/bami-codes/BenchMate · Video (YouTube, unlisted): TBD
