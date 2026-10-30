Good news: nothing is wrong with your circuit.

Expected:

 tau = R*C = 10k * 1u = 10 ms

You measured 21.4 ms, which is ~2.2x too big. That's not tolerance, that's a definition error.

2.2 is ln(9):

For a step: `V(t) = V0 * (1 - e^(-t/RC))`

* time constant = time to 63.2% = `RC`
* 10-90% rise time = time from 10% to 90% = `RC * ln(9)` ≈ `2.197 * RC`

Most scopes auto-measure 10-90% rise time as "Rise Time". That's what you got:

21.4 ms / 2.197 = 9.74 ms ≈ 10 ms

Spot-on within resistor tolerance and cursors.

Measure again to 63.2% rising, or 36.8% falling, and you'll get ~10 ms.