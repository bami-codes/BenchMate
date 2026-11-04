# v4 complete regression summary

Original official results are unchanged. These are engineering replay checks on fixed original agent choices, not new Spark decisions.

| Case / attempt | Diagnostic | Original | Engineering replay | Internal changes |
|---|---|---|---|---:|
|01 / 1|faulted|changed|changed|0|
|01 / 1|restored|run_failed|no complete capture|0|
|01 / 2|restored|consistent|consistent|0|
|04 / 2|faulted|run_failed|no complete capture|0|
|04 / 3|faulted|structure_supported|structure_supported|0|
|04 / 3|restored|consistent|consistent|0|
|02 / 1|faulted|abstained|unverified_training_only|1|
|02 / 2|faulted|changed|changed|0|
|02 / 3|restored|run_failed|original_execution_failure|0|
|02 / 4|restored|consistent|consistent|0|
|05 / 1|faulted|structure_supported|structure_supported|0|
|05 / 1|restored|abstained|unverified_training_only|9|
|01 / 01-F01|faulted|run_failed|original_execution_failure|0|
|01 / 01-R01|faulted|consistent|consistent|0|
|01 / 01-F02|faulted|run_failed|original_execution_failure|0|
|01 / 01-F03|faulted|run_failed|original_execution_failure|0|
|01 / 01-F04|faulted|changed|changed|0|

Same-action final verdict flips: **0**. Other-design previously passing waveform failures: **0**. All10 internal changes are listed in all-changes.json:9 are expected05 training improvements and1 is02 proposal:1 fit_error→inadequate. There is no missing reserved pair invented for05.
