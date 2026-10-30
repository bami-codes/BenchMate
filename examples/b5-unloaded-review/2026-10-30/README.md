# Stored-block review and mathematical examples

No new hardware or provider request was used. The stationary-block report uses
archived raw HOLD frames. First-block equivalent-voltage standard deviations
were A1 1.827mV, A2 2.576mV, A4 2.288mV; fitted changes within its 1.022s window
were about +0.102, -0.233, -0.034mV. The second boot, about 33 minutes later,
changed A4 mean by -37.181mV while A1/A2 changed +0.537/-0.050mV. This does not
establish whether physical REF, a channel or another mechanism caused the change.
The short block's small trend is not an absolute calibration or whole-fixture pass.

The reference-absorption file is an illustrative static diode calculation, not
part characterization or hardware evidence. It shows why constant REF offset can
be nearly absorbed in an unloaded diode model but not in a load-to-REF current,
and why unloaded R/IS can trade off. It is not used as training data for Spark.
