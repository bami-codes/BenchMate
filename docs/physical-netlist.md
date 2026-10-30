# Measured-input passive-netlist prediction

`benchmate.physical_netlist` is an offline forward-model component for future
physical structure discovery. It does not control the board, fit a proposal,
call a model provider, or declare B5 complete. The current resistor-only range
protocol and its source hashes remain unchanged.

The input-only contract accepts an explicitly physical template containing
recorded command-frame times, independently anchored IN-minus-REF voltages,
and A1/A2 completion delays. It rejects any extra data field, including scored
OUT. A separately reported physical output load may use its measured value,
rather than being rounded to a nominal synthetic load. Input DC bias and
nonideal waveform shape are retained. The fixture source holds each measured
IN level for its command frame; predictions are sampled at the corresponding
A2 completion time. This is a conditional prediction available after observing
IN, not an absolute output curve known before acquisition.

The existing passive topology validator, component limits, diode bounds and
fixed simulator harness rules are reused. Element orientation and topology
are preserved. Diode IS/N remain effective model parameters; RS=1 ohm and
27 degrees C are fixed assumptions, not characterization of the loose 1N4148.
The diode-meter reading is not an input to this component.

For a step, the initial operating point assumes the instrument's pre-step
settling was adequate and uses the mean measured low-level IN. This assumption
must be reviewed before accepting slow proposed circuits whose time constants
approach the fixture settling interval. For a capacitive sine proposal, the
first full measured input cycle is repeated into the unobserved past. The
number of repeated cycles doubles until every sampled simulated node changes
by at most 10 microvolts. Every simulator invocation consumes the caller's
budget callback. Bounded duration and point counts stop unmanageable settling.
This checks numerical convergence under the stated repeated-history assumption;
it does not establish that the hardware had reached the same periodic state.

Conditioning on IN removes source-current information from the OUT prediction.
In particular, an additional IN-to-REF resistor can leave conditional OUT
unchanged. Such families must remain tied unless a separate current observation
distinguishes them; the component explicitly reports this limitation.

Offline tests compare resistor/load predictions with voltage division, RC step
and distorted sine predictions with an independent analytic recurrence, and
diode predictions with an independent DC equation. They also check diode
orientation, A2 timing, nonzero bias, input-branch ties, budget accounting and
rejection of OUT leakage or invalid templates. These are software validation
checks, not physical B5 measurements.

Still required before a real discovery run: physical acquisition adapter and
bias/guard records for each fixture, the five-family training comparison,
bounded training-only proposal fitting, topology/parameter/input-processing
freeze before both reserved observations, and a reviewed provider payload.
