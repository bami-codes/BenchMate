# Fixed B5 variant selection — all outcomes retained

The registered selector used its original three-hour wall-time budget. The stop
check occurs between optimizer fits, so a running fit may finish after the deadline.
Actual elapsed time is retained in the publication JSON. No
rule, candidate list, seed, starting point, or numerical limit was changed mid-run.
This is selection work, not a model accuracy evaluation. No hardware or model API
was used. Final Spark evaluation still requires a completed physical B5 attempt.

**Primary set: 0 variants. Selection complete: False.**

| Variant | Selection outcome | Fit failures / confusable alternatives |
|---|---|---|
| D1 | distinguishability_unresolved | fit_failures: netlist:D6, netlist:D7; confusable_with: netlist:D4 |
| D2 | distinguishability_unresolved | fit_failures: netlist:D7 |
| D3 | distinguishability_unresolved | fit_failures: netlist:D6, netlist:D7 |
| D4 | distinguishability_unresolved | fit_failures: netlist:D6, netlist:D7 |
| D5 | distinguishability_unresolved | fit_failures: netlist:D7 |
| D6 | selection_incomplete | — |
| D7 | selection_incomplete | — |
| D8 | selection_incomplete | — |
| L1 | selection_incomplete | — |
| L2 | selection_incomplete | — |
| G1 | selection_incomplete | — |
| G2 | selection_incomplete | — |
| G3 | selection_incomplete | — |

An optimizer failure does not reject an alternative. A confusable circuit does not
establish unique structure. Incomplete cases are not excluded on the basis of model
performance: they never reached a selection decision within the fixed compute budget.
Three noise realizations are an engineering screen, not a confidence guarantee.

**No X/N accuracy headline is available.** Do not turn zero selected cases into
0% or 100% model accuracy, and do not relax the rule to obtain a video result.
For this submission, lead with the retained D01 evidence and the separately labelled
B5 demonstration; leave this attempted broader benchmark in the evidence record.

`selection-records.tar.gz` contains every retained replicate, observation, fitted
alternative and partial result. Its decompressed file hashes are in the manifest.
The JSON classification is an exact byte copy of the selector output. Publication
does not unlock final evaluation by itself; the separate physical-record gate remains.
