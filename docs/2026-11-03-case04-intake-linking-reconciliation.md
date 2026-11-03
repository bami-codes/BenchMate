# Case04: completed 20k extraction retained after a host linking failure

The original case04 registration `20261103T143624-44d6e5850c` remains failed,
counted and selected as the first attempt. There were zero physical commands or
diagnostic measurements. Its first schematic extraction read the old 22k image.
The operator then supplied inventory without 22k; Claude supplied a revised 20k
image, frozen in `4e4a4ca`. Original and revised images remain versioned.

The revised-image Spark child
`schematic-revision-20k-intake/20261103T144919-80c4654879` completed successfully:
R1=4700 IN–OUT, R2=20000 OUT–REF. A subsequent local `linked()` call mixed a
relative child Path with an absolute parent Path and raised ValueError. The outer
handler closed the parent as failed. This was host bookkeeping after a successful
response, not a malformed model response, firmware failure or failed experiment.
The terminal parent chain is not reopened or edited.

Follow-up registration `20261103T145152-e948c2e475` retains the failed parent and
copies the completed child, checking exact input bytes and its terminal chain.
Both paths are resolved before linking. This repeats no provider request.
The reused provider response predates the follow-up registration, explicitly
recorded; the first case04 registration preceded that original request. This is
a continuation of the same case input, not a new blind/fresh schematic trial.
All diagnosis contexts will still be fresh and receive no previous result,
operator value, private assembly, case mapping or photograph.

Usage so far: two actual schematic Spark calls, estimated $0.01259955 total.
The new reading-cohort cumulative total is19 Spark +1 SAM, $0.16464535. Copying
the completed response adds zero requests/$0. Physical commands/measurements
remain zero. Actual final wiring and subsequent execution choice are pending.

The latest wiring proposal accommodates the operator's clearance issue:
D23–D25 REF jumper; 1N4148 C30–E25 with its striped cathode at E25. E30 stays
free for the frozen load-intervention jumper. This is not yet an installation
confirmation. Earlier B30/D23 proposals remain historical, not inferred actual
wiring. The intended mini-board is R1=4.7k and R2=20k with no capacitor.
