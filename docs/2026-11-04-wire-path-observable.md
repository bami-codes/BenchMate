# Case05: qualify a whole mini-board path resistance, before its reading

This implements the stage extension declared before case05 schematic intake.
The original107 numerical/firmware/guard sources remain unchanged. This numeric
path-reading adapter and its compound auditor are separately frozen and published
after terminal diagnosis but **before the follow-up choice, photo or operator
value**. The electrical result is not rescored or refitted.

Eligibility is structural, not selected from the hidden assembly: the intended
design contains one explicit IN-OUT W1, and every reserved-surviving model must
retain the intended R/C branches and add exactly one IN-OUT series resistor in
place of W1. Otherwise this adapter does not fabricate a wire-path reading.

For an eligible model, terminal measurements admit at least these two bounded
physical placements of the same series impedance:

- `on_board_path:<model>`: the mini-board IN-OUT path accounts for the fitted
  series resistance. Its interval uses the existing training-only33-point profile
  and fitted point, enclosing passing points and adjacent rejected brackets.
- `external_path:<model>`: the mini-board IN-OUT path is near-short, in the
  **predeclared0-10ohm engineering category**, with the remaining series resistance
  outside. This is not a precise zero-ohm or beeper claim.

Both use the same terminal model, with `R_total = R_board_path + R_external`.
No extra terminal parameter is fitted. Reserved OUT is never used to choose
reading intervals. Mixed/intermediate path resistances are possible beyond these
bounded alternatives; a new reading may reject both or leave them indistinguishable.
Parallel R1/C1 readings have identical intervals between these alternatives and
must not be requested merely to fill a workflow slot. Spark chooses the useful
component and quantity from this explicit catalog.

## Actual observable and isolation

**Do not remove W1 and measure the loose jumper.** That would omit its socket
contacts and would not test the mini-board path explanation.

With USB off and at least10seconds discharge wait, disconnect **all three
mini-board lead ends from the large fixture**. Leave their mini-board ends in
place. Leave W1, R1 and C1 installed. Keep the REF lead's free end floating.
Measure resistance between the free metal ends of the IN and OUT leads. This
retains the input/output leads, mini-board sockets and W1/contact path in the
measurement. IN has no second connection except W1; OUT-REF parallel branches
terminate at the floating REF port, so they do not shunt this measurement.

Record operator confirmation of USB-off, all-three-lead isolation, W1/R/C
retained, discharge wait and the actual DMM probe endpoints. Record the free
numeric value, selected range, displayed resolution and unit exactly; no
explanation is accepted as input. The existing prospective2% plus2counts
engineering allowance is reused for2k/1ohm,20k/10ohm,200k/100ohm,2M/1kohm
ranges. This is not established manufacturer accuracy. OL is not a numeric
measurement; use a predeclared suitable range and report it, without widening
limits after the value. A printed wire marking has no resistance information.

The numeric catalog uses kind R for the resistance dimension with
`physical_kind:W` and an explicit path adapter. This does not change W1 into
a resistor in the intended circuit or add a component to the schematic.

## Photo, scoring and restoration

After the source-specific forecast is published, take the actual fault-state
photo. Generic SAM localization retains all regions. One v3 Spark request returns
candidate body kinds/IDs plus a separate nullable individual binding. The reviewed
intended topology explains the operator-added name W1. No measured reading or
private assembly reaches Spark. Operator confirms the port pair and the model's
candidate set, or records an explicit override/unassigned body set. Do not force
a SAM match or infer absence from a missing body. The electrical observable is
the mini-board port path, not a claim to have visually identified every contact.

Each DMM observation is scored by the already frozen source/range interval. One,
none and several surviving explanations are all possible. If one remains, reveal
the sealed assembly. If the external-path alternative is supported and only the
external resistor is removed, an operator-confirmed unchanged mini-board plus a
fresh-context consistent rerun uses the original photo with its original capture
label; no redundant restored-body/value request or repeated mini-board photo.
If mini-board configuration changes, this external-only closeout does not apply.

A DMM screen photo is optional for this operator-report reading. If absent, the
retained board image is explicitly context only, never evidence authenticating
the numeric value. Hash verification proves retained integrity and recorded
order, not physical wiring truth, original creation time or meter accuracy.

Runtime: `python -m benchmate.reading_wire_stage` with separate `qualify`,
`select`, `bind`, `confirm-path`, `observe`, `close`, `verify` stages. Fresh
diagnoses, SAM, photo preparation and decoding reuse the preserved commands.
The compound verifier remains keyless/network-free; all wire profile generation
and numerical imports are outside its verification path.

Offline checks cover literal-topology eligibility, reserved-output exclusion,
and independently entered low/high/intermediate DMM readings producing either
placement or no fit. These are explicitly shared-simulator software checks,
not physical validation or an experiment sequence for Spark.
