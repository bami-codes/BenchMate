# Prepared physical cost guard — no hardware executed

The old shared ledger reserves $1 per request and currently shows 93/120. Those are
not charged dollars. This wrapper leaves that ledger and every physical runner source
unchanged. It wraps the existing Meta client with an independent **$10 / 32-new-request**
ceiling: reserve $1 before a bounded request, settle returned usage afterwards, keep
the full reservation when usage is missing. Each original run still allows at most 8.
The budget does not authorize extra physical attempts or relax an operator/boot guard.

Check preparation, with no model or hardware:

```sh
.venv/bin/python experiments/physical_budget.py check
```

Later, after the actual operator has supplied the required current reports, prepend
`experiments/physical_budget.py d01 --` to the existing D01 runner's `run ...` arguments,
or use `b5 --` for B5. Keep every existing argument, source freeze and confirmation.
This is an optional accounting wrapper, not a run resumption or new scientific protocol.
It logs its own source and plan hashes in the physical record. If those files change,
re-register the accounting plan before use. Nightly mock guards must never wrap a live
runner: those deliberately disable serial access. This wrapper's `check` mode is the
only mode exercised during the night.

For B5 specifically, the wrapper requires its own `run --execute` markers even though
the original B5 script has no subcommand or execute option. It strips those two markers
before delegating; all actual B5 flags remain unchanged:

```sh
.venv/bin/python experiments/physical_budget.py b5 -- run --execute \
  --bench physical --provider meta --publish-freeze \
  --protocol ACTUAL_FROZEN_PROTOCOL --initial-report ACTUAL_FRESH_REPORT
```

This example is not an operator confirmation and must not be run unattended.
