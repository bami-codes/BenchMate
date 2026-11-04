# Case05: isolated path reading supports the external series path

Pair: `examples/reading-cohort/2026-11-03/records/20261104T021333-c80ef3617e/`.
This pair is still in progress; restoration and a fresh-context restored
diagnosis remain outstanding at this point in the record.

After Spark selected W1 and sam-1, the operator confirmed W1 and the IN/OUT
ports. The resistance observation was reported as:

> USB OFF / 세 선 분리 / W1·R1·C1 유지 / 다이얼 2kΩ / 화면 숫자 0.000kΩ

This answered the requested USB-off, three-lead-isolated measurement after the
10-second wait, across the disconnected IN/OUT lead metal ends. W1, its sockets,
the mini-board lead ends, R1 and C1 remained installed. The floating REF port
prevents the OUT-REF branches from forming a parallel measurement path.

The report is retained verbatim. `0.000kohm` normalizes to an indicated zero
ohms at 1ohm display resolution. This is not proof of exactly zero physical
resistance. The board image retained with the observation is context only;
there is no meter-screen photo authenticating the operator-reported number.

The source/range-specific intervals were published in `7de51d6` before the
photo or reading, under forecast SHA256
`2746d2be2e8ffdab19391646b16693ecfb151f65f921ae1cd5e7474bd4ea3e07`:

| Bounded explanation | Indicated interval, 2kΩ range | Fits report |
|---|---:|---|
| On-board IN-OUT path accounts for the fitted resistance |17,425.138–24,190.012Ω|No|
| Mini-board path is near-short, remaining series resistance external |0–12.2Ω|Yes|

Exactly one declared explanation remains: `external_path:proposal:1`.
`on_board_path:proposal:1` is ruled out by this reading. No interval, terminal
fit, forecast or previous measurement was changed. Other or intermediate
physical explanations are not universally excluded by these bounded tests.

Only after scoring, the specimen seal was opened. It retained the operator's
assembly record: a nominal 20kΩ resistor at large E35-E31, outside the mini-board
after measured IN. The independently fitted terminal series path was
19,851.78774353608Ω. The seal was not provided to Spark's diagnostic, reading
selection or body-selection requests.

Next is USB-off external restoration: remove that 20kΩ resistor, reconnect the
green fixture-side IN lead to large A35 rather than A31, and reconnect OUT/REF
to their previous fixture contacts. Mini-board W1 B3-B8, R1 10kΩ E8-E13 and C1
105 C8-C13 stay unchanged. A fresh-context diagnosis follows actual operator
restoration confirmation, with the unchanged guards and experiment menu.

This stage made zero new API calls and no automated hardware operation. Usage
remains case05 **10 Spark, 1 SAM, estimated $0.10775610**; reading cohort plus the
separately labelled case02 demo reprocessing **75 Spark, 4 SAM, estimated
$0.75359715**. These amounts are estimates, not invoices. A restored diagnosis
is expected to require at most 8 Spark requests, roughly $0.06–0.12.
