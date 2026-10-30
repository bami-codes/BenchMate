# No-tool Spark comparison — prepared, not yet executed

Five independent requests use the exact same question:

> Designed RC low-pass 10 kΩ, 1 µF. Measured time constant 21.4 ms. What is wrong?

Spark max, no tools, fresh context per request, provider-default temperature.
No D01 raw data, assembly information, earlier answers or correct diagnosis is
included. `scripts/no_tool_spark_baseline.py` prints the exact request plan by
default. `--execute` makes at most five paid Meta requests, with no automatic
retry. All visible replies, usage and failures are preserved, without selecting
the most convenient answer. Reasoning internals and keys are not written.

Review the five original replies before choosing the video's opening. The
nominal time constant is 10ms; the observation constrains a product about 2.14
times larger. It does not uniquely identify R versus C. An answer requesting a
load measurement or otherwise acknowledging missing information is appropriate.
Do not frame such an answer as AI failure. The intended comparison can be:
the same AI recognizes the missing evidence, then BenchMate performs the test.

This is a small qualitative illustration, not a statistically established
accuracy comparison. It requires its own explicit paid-call/transmission scope;
the earlier D01 consent and the B5 eight-request consent are separate.
