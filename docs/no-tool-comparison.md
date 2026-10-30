# No-tool Spark comparison — completed October 30, 2026

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

## Recorded result

[All five original replies and review](../examples/no-tool-spark/2026-10-30/20261030T134112-a9742f1b2e/README.md)
are retained. Each primarily asserted that 21.4ms was a 10–90% rise-time reading,
not the time constant. All suggested measurement rechecks; reply 5 also explicitly
allowed a larger capacitor if the stated time constant was real. The rise-time
hypothesis is plausible, but its asserted measurement method was not supplied.

Use this to motivate testing an explanation, not a general claim that Spark
cannot diagnose circuits. This baseline used max; the completed physical D01
used medium and much richer evidence. It is not a controlled accuracy ablation.
The question was unchanged and all five responses were included; no revised
prompt or selective rerun was used after seeing the result. Five requests were
explicitly approved separately from B5, and all five completed without retries.
