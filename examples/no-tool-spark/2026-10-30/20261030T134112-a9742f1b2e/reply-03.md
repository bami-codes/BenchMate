Nothing is wrong with the circuit. You're measuring the wrong thing.

For

$$R=10\,k\Omega,\; C=1\,\mu F$$

$$ \tau = RC = 10\,ms $$

$\tau$ is the time to get to 63.2% of the final value:

$$v(t) = V_0(1-e^{-t/RC})$$

What you measured as 21.4 ms is the 10%-90% rise time.

$$t_{10} = RC \ln\frac{1}{1-0.1}$$
$$t_{90} = RC \ln\frac{1}{1-0.9}$$

$$t_r = t_{90}-t_{10} = RC \ln 9 \approx 2.197\,RC$$

For a nominal 10 ms design:

$$t_r \approx 2.2 \times 10\,ms \approx 22.0\,ms$$

You got 21.4 ms, which is:

$$21.4\,ms / 2.197 = 9.74\,ms$$

for $\tau$, ~2.6% off 10 ms. Perfectly normal for resistor + capacitor tolerance.

Put cursors at 0% and 63.2% for $\tau$, or take your 10-90% number and divide by 2.2.