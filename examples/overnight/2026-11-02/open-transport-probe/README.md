# Transport probe — preserved implementation failure

This paired development probe **did not test the proposed change**. Its plan at
`f125866` incorrectly assumed the original adapter omitted `parallel_tool_calls`.
Source inspection shows the frozen `BasetenToolSession.base` already contains
`parallel_tool_calls: false`. The endpoint nevertheless returned multiple calls in
eight original evaluation cases. The old first-attempt evaluation remains 21/24.

The six original-adapter development runs completed five cases and stopped one on
multiple tools. All six proposed-setting runs stopped **locally before HTTP** because
the wrapper refused an already-present setting. They are implementation failures,
not six model failures. Each local provider counter had incremented once before this
check; the metered HTTP ledger correctly contains none of those six attempts.

**23 actual requests; $0.17465835 usage-calculated cost**, from the original-adapter
condition only. All records and the mistaken plan are preserved. This is development
work after observing evaluation failures, not new independent confirmation. The probe
is retired; do not promote `open_serial_tools.py` into the physical or benchmark runner.
No improvement, fix, or default-vs-false effect is claimed. No further Open tuning is
needed before the primary physical D01/B5 work.

The [official field documentation](https://docs.baseten.co/reference/inference-api/chat-completions)
describes a true default; that fact did not establish what our own adapter sent.
