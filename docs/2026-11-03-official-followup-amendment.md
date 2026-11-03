# Separate official follow-ups, with primary failures retained

01-F01 stopped at the original electrical guard during loaded pre-stimulus
HOLD. Its first-attempt selection, failed/counted status, raw record and source
snapshots are immutable. A separate loaded HOLD QA then passed 12 blocks and
6144 frames at the unchanged guards on a new boot. This supports only that
HOLD condition, not an identified cause or all waveform accuracy.

The original official registration runner allows only the 12 primary slots
and stops at an earlier failure. A new bookkeeping wrapper permits a separate
numbered follow-up (01-F02, etc.) after a matching completed recovery QA. It
adds the follow-up to `index.followups`, never changes `index.slots` to replace
a failed primary, never picks a better run for the demo, and counts every
assigned attempt. Later required slots can proceed after a separately linked
follow-up completes reserved verification. The original failure stays failed.

The model, prompt, intended netlist, menu, initial unloaded fixture, physical
adapter, original guards, numerical fitting, scoring and prediction publisher
are reused unchanged. A thin adapter adds the prospective USB startup wait
described below; no QA OUT or prior result is sent to the fresh model.
The follow-up wrapper and this document are additional pinned source files in
the pre-run binding. The original 80 files remain byte-for-byte preserved.
Registration is committed/pushed before paid requests/stimuli. Forecasts are
committed/pushed before reserved captures by the original publisher.

The operator authorized necessary calls without repeated approval. 01-F01
used 3 requests. Plan at most 8 additional requests for 01-F02 and 8 for 01-R01:
19 maximum across those three attempts. The separate official allowance is
increased prospectively from 16 to 19 reserved request units without resetting
its used counter or the historical ledger. This is an allowance, not billed
dollars. Photo calls are separately disclosed. Each diagnosis retains its
8-request limit and no automatic retry.

Before 01-F02 is registered, the operator added a common startup rule: wait
at least 10 seconds after USB reconnection before measurement. The wrapper
implements a conservative 10-second host wait after the first verified
unarmed PING on each new boot, then confirms the same unarmed boot again
before ARM. It records start, completion and elapsed monotonic duration.
This applies to the initial hookup and every USB-off fixture intervention in
this version, including restored runs. Original voltage/reference thresholds
and scoring remain unchanged. The pre-run binding records the wait explicitly.

01-F01's original device times show its first post-intervention PING at
10.958 s uptime and the failing HOLD completion at 21.556 s. The new rule is
an operating consistency rule, not evidence that USB startup caused or fixes
that failure. Existing records are not retroactively changed.
