# Prospective transport bound after 01-F03

01-F03 remains failed and counted. Its three Spark-selected training captures
and all 15 primary electrical guard blocks passed. After the third tool result,
the accumulated request exceeded the preserved transport's 64,000-byte local
limit. The fifth request was rejected locally, before budget reservation or
HTTP. No reserved predictions, reserved captures or final diagnosis occurred.

The new `official-transport-v2` permits at most 512,000 serialized request bytes.
It preserves the full conversation, including opaque provider reasoning in
memory, without trimming or logging it. Each request records its byte count
and limit, without its body. The effective limit is also in provider metadata
and the prospectively prepared official protocol. This bound is a host-side
serialization limit, not a provider context guarantee or spending cap.

The eight-request limit, 4,096 output-token limit, authorized ledger, no-retry
behavior, tool schema, Spark experiment selection, fitters, scores, publication
ordering, reserved inputs, firmware, A3 primary guards and ten-second reconnect
wait are unchanged. Historical source files and failed runs are unchanged.
New attempts start with a fresh model context and fresh physical training;
F03 measurements are not silently reused or relabeled as a completed run.

Offline verification must exercise a history larger than 128 kB, preservation
of opaque items and tool-call pairing, the eight-request stop, rejection above
512 kB before reservation/HTTP, and equality of all numerical/physical protocol
fields with the A3-v1 profile. No API or hardware call is used for these checks.

Any further attempt is separately registered and published before execution.
The original first-attempt demo selection and every failed official count stay
unchanged. Necessary paid calls remain authorized by the operator's standing
instruction; planned counts and actual usage/cost are reported per stage.

Before F04: 11 requests are already used. The separate official ledger retains
those reservations and prospectively permits 8 for F04 and 8 for the first
restored run, at most 27 across the attempts to date and that restored run.
These local reservations are not actual bills. Offline transport/protocol/
guard/verifier tests: 42 passed, with no paid request or hardware access.
