# b1_shunt — common physical gate condition

The predeclared conditional OUT score is **5.221 mV RMS**
(worst region 6.502 mV). Both branch
alternatives use the identical fixed OUT model. Supported alternatives after
the common transfer and current checks: **no_input_branch**.

The two settled levels give DRIVE excursion **0.398834 V**
and change in A3-minus-A1 of **0.784371 mV**.
Installed shunt: 996 ohm. No channel offset is fitted to
this contrast. These are two windows of one step block, not separate DC captures.

All 2560 frames are retained (512 scored,
2048 stationary). A4 block-mean span: 0.294 mV.
The protocol predates all device commands, and the separate HOLD origin precedes
the scored waveform. Boot `3f7371bc8d09f17a6bc8484c2bb8a9f6` remained unchanged; output parked
at code 1371. Known-passive engineering evidence only;
absolute voltage, full-family inference and final benchmark accuracy are not claimed.

[Condition](condition/condition.json), [raw result](capture/result.json),
and [source-copy hashes](provenance.json) preserve the complete records.
