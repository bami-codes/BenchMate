# D01 repair runner: software rehearsal, November 1

**Mock circuit and scripted controller. Zero Spark requests, zero physical
measurements, zero real operator interventions. This is not a Spark repair result.**

Starts from the actual recorded intended-schematic Spark reading, with an explicitly
simulated human review. The runnable physical path requires a fresh actual review
and hookup report. The assembly-photo 1 µF reading is not used as nominal design.

The final normal path makes seven scripted tool choices and five mock waveform
observations: unloaded training, loaded discrimination, diagnostic 5 Hz check,
then prospective post-repair step and unused 0.10 V / 4 Hz sine. Repair predictions
and a local mock publication receipt precede the simulated intervention. Real
mode requires verified remote publication before asking the human to act.

| Check | Restored conditional RMS | Unchanged conditional RMS | Restored command forecast RMS |
| --- | ---: | ---: | ---: |
| step | 0.490 mV | 11.388 mV | 0.563 mV |
| sine | 0.466 mV | 4.197 mV | 0.473 mV |

Both restored conditional checks pass all regions and the unchanged model fails
at least one check. Command-input forecasts are separately saved and scored;
their local mock agreement is not physical absolute-voltage evidence. Only the
first unloaded tau is fitted. Post-repair OUT is never fitted.

[Every retained run and event hash](index.json) includes the initial success,
final success after a provenance-label correction, and nine injected fault runs.
Failed repair and reserved-condition failure end in abstention. Publication,
missing/wrong/cancelled/timed-out confirmation, unchanged repair boot and a reset
between repair checks terminate without an accepted repair. No failed run was
replaced or called a successful retry.

Validation: 25 repair tests, 18 existing physical RC/adapter tests, and 60 B5,
vision/replay, physical viewer/fitting/netlist tests pass (103 total). Three local
web-server tests initially hit the filesystem environment's loopback bind limit;
those three passed when rerun with loopback allowed. No external API was used.
The fake serial path exercises 25 blocks / 12,800 frames / three explicitly
confirmed boots; these are fabricated test bytes, not physical measurements.

Reproduce without API or hardware:

```sh
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python scripts/physical_d01_repair.py run
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python scripts/physical_d01_repair.py run --fault reserved_failure
```

[Physical operator guide](../../../docs/d01-repair-operator.md)
