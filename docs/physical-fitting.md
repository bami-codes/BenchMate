# Physical-bias training fits

`benchmate.physical_fitting` adds an offline training layer to the measured-input
forward models. It is not connected to a real B5 acquisition or model-provider
session yet. Constructed unit fixtures are software checks, not physical evidence.

Both fit entry points require observations explicitly marked as physical,
independently anchored to physical REF, acquisition-guard passed, and training.
Control traces and reserved verification observations are rejected. The eventual
trusted acquisition/session layer must supply and preserve that provenance;
these dictionary checks alone do not authenticate a measurement.

The five initial families retain the existing R/C/component bounds: RC,
RC with an input branch, resistor, resistor with an input branch, and resistor
with an output leak. Only component parameters are fitted. No extra OUT offset,
channel gain or physical reference is adjusted from scored waveforms. Physical
REF is zero in the circuit equations; nonzero measured IN-minus-REF is retained.
Without a source-current observation, input branches give identical conditional
OUT predictions and remain explicitly tied. Parameter nonidentifiability by
itself does not make a linear family inadequate.

Proposal fitting executes the literal generated topology and initial values
first, then adjusts at most two R/C values and shared bounded diode IS/N.
Every SPICE invocation, including periodic-state comparisons, consumes the
420-invocation allowance; the fitting wall-time budget remains 60 seconds and
individual SPICE calls remain bounded. Cache reuse is recorded. Generated and
fitted topology fingerprints must match. Local parameter-rank/condition checks
are numerical diagnostics, not calibrated uncertainty or proof of uniqueness.

All fits use the same fixed 9 mV development allowance for whole-waveform RMS
and every predeclared time/phase region. A whole-waveform pass cannot override
a failed region. Training adequacy is distinct from later verification. No
posterior probability or calibrated confidence is computed.

The offline tests cover the five-family comparison, conditional input-branch
ties, RC parameter recovery with a changed load, rejection of reserved/control
data, preservation of output bias, regional failures despite a whole-trace pass,
and a generated diode proposal fitted on constructed training observations then
checked on two untouched constructed conditions. No hardware or provider calls
are made by these tests.

The acquisition adapter, operator interaction, provider payload, proposal-limit
state machine and freeze-before-reserved-capture logic are still required before
this layer can be used in a physical structure-discovery run. Slow proposed
circuits also need the initial-state limitations in [physical-netlist.md](physical-netlist.md)
resolved or explicitly bounded by the final protocol.
