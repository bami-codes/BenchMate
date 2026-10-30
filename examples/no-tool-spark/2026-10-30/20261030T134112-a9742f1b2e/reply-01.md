Nothing is wrong with the circuit. You didn't measure $\tau$.

For a series-R shunt-C low pass:

$$\tau = RC = 10k\Omega \times 1\mu F = 10\,ms$$

What you measured at 21.4 ms is $\approx 2.2 \times \tau$.

That is the 10%-90% rise time, not the time constant.

For a step $V_0(1-e^{-t/RC})$:

time to 10%: $0.1 = 1-e^{-t_{10}/RC}$ -> $t_{10}=RC \ln \frac{1}{0.9}$

time to 90%: $0.9 = 1-e^{-t_{90}/RC}$ -> $t_{90}=RC \ln 10$

$$t_r = t_{90}-t_{10} = RC \ln 9 \approx 2.20 RC$$

$$t_r \approx 2.197 \times 10ms = 22.0 ms$$

21.4 ms is that, within R and C tolerance.

Oscilloscopes auto-measure this as "rise time." It is not $\tau$.

$\tau$ is time to 63.2% on charge, or to 36.8% on discharge. Fit the exponential, or measure that point, and you'll get ~10 ms.