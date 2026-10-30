Nothing is wrong with the parts. Something is wrong with the measurement.

Nominal is:

> tau = R*C = 10k * 1u = 10 ms

You got 21.4 ms, about 2.14x too big.

That's not tolerance. That's:

> 10-90% rise time, not tau

For a low-pass step response:

```
V(t) = Vfinal * (1 - exp(-t/RC))
```

- Time constant tau is time to **0 to 63.2%** = RC
- 10-90% rise time is time to go from **10% to 90%**:

```
tr = t90 - t10 = RC*ln(9) ~ 2.197*RC
```

For your design:

```
expected tr = 2.197 * 10ms = 22.0 ms
```

You measured 21.4 ms. That's within 3% of ideal.

In other words, your real tau is:

```
tau = tr / 2.2 = 21.4ms / 2.2 = 9.7 ms ~ 10 ms
```

This is the classic scope trap: scope auto "Rise Time" means 10-90% by default.

Measure again to 63.2% of the final settled value, or fit the exponential, and you'll get ~10 ms.