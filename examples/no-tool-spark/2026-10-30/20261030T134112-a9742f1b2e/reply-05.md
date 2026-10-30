Nothing is wrong with your circuit. You're measuring the wrong thing.

Expected:

$$\tau = RC = 10k\Omega \cdot 1\mu F = 10\,ms$$

You got $21.4\,ms \approx 2.14 \times$ expected.

That 2.2x is the giveaway. You didn't measure the time constant, you measured the 10-90% rise time.

For a 1st-order RC step response:

$$v(t) = V_{final}(1-e^{-t/RC})$$

Time constant is time to 63.2%:
$$t_{63\%} = \tau = RC$$

10-90% rise time is:

$$t_r = t_{90\%} - t_{10\%} = \tau \ln 9 \approx 2.197\,\tau$$

For your design:
$$t_r \approx 2.197 \cdot 10ms = 22.0\,ms$$

You measured 21.4 ms. That means:

$$\tau = 21.4ms / 2.197 = 9.74\,ms$$

That's 2.6% off from 10ms - perfect for a 5% resistor and 10-20% cap.

Most scopes have an automatic "Rise Time" measurement that defaults to 10-90% cursors. That's what you used.

To get $\tau$ correctly:

1. Single step, fit exponential, or measure time from 0 to 63.2% of final, not 10 to 90%
2. Or go to frequency domain: $f_{-3dB} = 1/(2\pi RC) \approx 15.9\,Hz$

If you *did* measure 0 to 63% and really got 21.4ms, then the second most likely culprit is you grabbed a 2.2uF cap instead of 1uF: $10k \cdot 2.2uF = 22ms$.