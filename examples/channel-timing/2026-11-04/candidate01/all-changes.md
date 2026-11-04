# Complete bidirectional offline regression — unqualified candidate

These are post-hoc fixed-action numerical replay results, not new Spark decisions or replacement official verdicts. All original failures, guards and verdicts remain unchanged.

Coverage: 12 current-cohort diagnostic logs plus 5 assigned prior-protocol official logs (now development), 60 complete guarded captures. One current-cohort attempt stopped before a diagnostic existed. Mirrors/history copies are deduplicated by event-file hash.

| Group | Case | Attempt | State / diagnostic | Original verdict or terminal | Candidate replay outcome | Changed checks |
|---|---|---|---|---|---|---:|
|current|01|1|faulted|changed|abstained|3|
|current|01|1|restored|run_failed|no guarded capture|0|
|current|01|2|restored|consistent|abstained|18|
|current|04|2|faulted|run_failed|no guarded capture|0|
|current|04|3|faulted|structure_supported|abstained|2|
|current|04|3|restored|consistent|consistent|0|
|current|02|1|faulted|abstained|unverified_training_only|1|
|current|02|2|faulted|changed|abstained|9|
|current|02|3|restored|run_failed|original_execution_failure|0|
|current|02|4|restored|consistent|abstained|19|
|current|05|1|faulted|structure_supported|structure_supported|0|
|current|05|1|restored|abstained|unverified_training_only|9|
|prior|01|01-F01|01-F01|run_failed|original_execution_failure|0|
|prior|01|01-R01|01-R01|consistent|abstained|17|
|prior|01|01-F02|01-F02|run_failed|original_execution_failure|0|
|prior|01|01-F03|01-F03|run_failed|original_execution_failure|0|
|prior|01|01-F04|01-F04|changed|changed|1|

An `unverified_training_only` outcome has no held-back pair and cannot establish consistent/changed/structure_supported. `original_execution_failure` preserves the original guard/transport failure regardless of available partial checks.

79 changed decisions below comprise 58 fixed-parameter waveform pass/fail flips (11 fail→pass, 47 pass→fail), 15 training-only refitted candidate-status flips, and 6 same-action replay verdict flips. These are different levels, not 79 independent runs.

| # | Group / case / attempt | Candidate | Comparison | Capture / purpose | Old | New |
|---:|---|---|---|---|---|---|
|1|current / 01 / 1|changed:R1|original_parameters|5 / verification|True|False|
|2|current / 01 / 1|changed:C1|original_parameters|2 / training|False|True|
|3|current / 01 / 1|whole replay|posthoc_fixed_action_outcome|— / —|changed|abstained|
|4|current / 01 / 2|nominal|original_parameters|1 / training|True|False|
|5|current / 01 / 2|nominal|original_parameters|2 / training|True|False|
|6|current / 01 / 2|nominal|original_parameters|3 / training|True|False|
|7|current / 01 / 2|nominal|original_parameters|4 / verification|True|False|
|8|current / 01 / 2|nominal|original_parameters|5 / verification|True|False|
|9|current / 01 / 2|changed:R1|original_parameters|1 / training|True|False|
|10|current / 01 / 2|changed:R1|original_parameters|2 / training|True|False|
|11|current / 01 / 2|changed:R1|original_parameters|3 / training|True|False|
|12|current / 01 / 2|changed:R1|original_parameters|4 / verification|True|False|
|13|current / 01 / 2|changed:R1|original_parameters|5 / verification|True|False|
|14|current / 01 / 2|changed:C1|original_parameters|1 / training|True|False|
|15|current / 01 / 2|changed:C1|original_parameters|2 / training|True|False|
|16|current / 01 / 2|changed:C1|original_parameters|3 / training|True|False|
|17|current / 01 / 2|changed:C1|original_parameters|4 / verification|True|False|
|18|current / 01 / 2|changed:C1|original_parameters|5 / verification|True|False|
|19|current / 01 / 2|nominal|training_refit|— / —|adequate|inadequate|
|20|current / 01 / 2|changed:C1|training_refit|— / —|adequate|inadequate|
|21|current / 01 / 2|whole replay|posthoc_fixed_action_outcome|— / —|consistent|abstained|
|22|current / 04 / 3|proposal:1|original_parameters|4 / verification|True|False|
|23|current / 04 / 3|whole replay|posthoc_fixed_action_outcome|— / —|structure_supported|abstained|
|24|current / 02 / 1|proposal:1|training_refit|— / —|fit_error|inadequate|
|25|current / 02 / 2|nominal|original_parameters|3 / training|False|True|
|26|current / 02 / 2|changed:R1|original_parameters|3 / training|False|True|
|27|current / 02 / 2|changed:C1|original_parameters|2 / training|True|False|
|28|current / 02 / 2|changed:C1|original_parameters|4 / verification|True|False|
|29|current / 02 / 2|changed:C1|original_parameters|5 / verification|True|False|
|30|current / 02 / 2|changed:C2|original_parameters|3 / training|False|True|
|31|current / 02 / 2|changed:R2|original_parameters|3 / training|False|True|
|32|current / 02 / 2|changed:C1|training_refit|— / —|adequate|inadequate|
|33|current / 02 / 2|whole replay|posthoc_fixed_action_outcome|— / —|changed|abstained|
|34|current / 02 / 4|nominal|original_parameters|1 / training|True|False|
|35|current / 02 / 4|nominal|original_parameters|4 / verification|True|False|
|36|current / 02 / 4|nominal|original_parameters|5 / verification|True|False|
|37|current / 02 / 4|changed:R1|original_parameters|1 / training|True|False|
|38|current / 02 / 4|changed:R1|original_parameters|4 / verification|True|False|
|39|current / 02 / 4|changed:R1|original_parameters|5 / verification|True|False|
|40|current / 02 / 4|changed:C1|original_parameters|1 / training|True|False|
|41|current / 02 / 4|changed:C1|original_parameters|5 / verification|True|False|
|42|current / 02 / 4|changed:C2|original_parameters|1 / training|True|False|
|43|current / 02 / 4|changed:C2|original_parameters|5 / verification|True|False|
|44|current / 02 / 4|changed:R2|original_parameters|1 / training|True|False|
|45|current / 02 / 4|changed:R2|original_parameters|4 / verification|True|False|
|46|current / 02 / 4|changed:R2|original_parameters|5 / verification|True|False|
|47|current / 02 / 4|nominal|training_refit|— / —|adequate|inadequate|
|48|current / 02 / 4|changed:R1|training_refit|— / —|adequate|inadequate|
|49|current / 02 / 4|changed:C1|training_refit|— / —|adequate|inadequate|
|50|current / 02 / 4|changed:C2|training_refit|— / —|adequate|inadequate|
|51|current / 02 / 4|changed:R2|training_refit|— / —|adequate|inadequate|
|52|current / 02 / 4|whole replay|posthoc_fixed_action_outcome|— / —|consistent|abstained|
|53|current / 05 / 1|nominal|original_parameters|1 / training|False|True|
|54|current / 05 / 1|nominal|original_parameters|2 / training|False|True|
|55|current / 05 / 1|changed:R1|original_parameters|1 / training|False|True|
|56|current / 05 / 1|changed:R1|original_parameters|2 / training|False|True|
|57|current / 05 / 1|changed:C1|original_parameters|1 / training|False|True|
|58|current / 05 / 1|changed:C1|original_parameters|2 / training|False|True|
|59|current / 05 / 1|nominal|training_refit|— / —|inadequate|adequate|
|60|current / 05 / 1|changed:R1|training_refit|— / —|inadequate|adequate|
|61|current / 05 / 1|changed:C1|training_refit|— / —|inadequate|adequate|
|62|prior / 01 / 01-R01|nominal|original_parameters|1 / training|True|False|
|63|prior / 01 / 01-R01|nominal|original_parameters|2 / training|True|False|
|64|prior / 01 / 01-R01|nominal|original_parameters|3 / training|True|False|
|65|prior / 01 / 01-R01|nominal|original_parameters|4 / verification|True|False|
|66|prior / 01 / 01-R01|nominal|original_parameters|5 / verification|True|False|
|67|prior / 01 / 01-R01|changed:R1|original_parameters|1 / training|True|False|
|68|prior / 01 / 01-R01|changed:R1|original_parameters|2 / training|True|False|
|69|prior / 01 / 01-R01|changed:R1|original_parameters|4 / verification|True|False|
|70|prior / 01 / 01-R01|changed:R1|original_parameters|5 / verification|True|False|
|71|prior / 01 / 01-R01|changed:C1|original_parameters|1 / training|True|False|
|72|prior / 01 / 01-R01|changed:C1|original_parameters|2 / training|True|False|
|73|prior / 01 / 01-R01|changed:C1|original_parameters|4 / verification|True|False|
|74|prior / 01 / 01-R01|changed:C1|original_parameters|5 / verification|True|False|
|75|prior / 01 / 01-R01|nominal|training_refit|— / —|adequate|inadequate|
|76|prior / 01 / 01-R01|changed:R1|training_refit|— / —|adequate|inadequate|
|77|prior / 01 / 01-R01|changed:C1|training_refit|— / —|adequate|inadequate|
|78|prior / 01 / 01-R01|whole replay|posthoc_fixed_action_outcome|— / —|consistent|abstained|
|79|prior / 01 / 01-F04|changed:R1|original_parameters|5 / verification|True|False|

Full original/new regional RMS, settings, preserved parameters, training-only refitted parameters and input hashes are in `replay/regression.json`; unchanged checks are included there as well.
