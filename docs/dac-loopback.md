# Bare-board DC loopback — before the LM358 fixture

This is a combined DAC/ADC functional check, not DAC calibration, a load-driving
test, or evidence that the full fixture works. The A0 DAC is available without an
external LM358 ([Arduino UNO R4 WiFi specifications](https://docs.arduino.cc/hardware/uno-r4-wifi/)).

## Completed functional check — 2026-10-27, Asia/Seoul

The sketch was uploaded to the UNO R4 WiFi compatible board. All five held points
produced 64 raw samples per channel, followed by separate operator DMM readings.
Both the displayed voltage and each channel's mean increased with every command.

| Nominal target | DAC code | DMM display | Range of A1–A4 means, counts |
| --- | ---: | --- | --- |
| 0.6 V | 501 | 0.59–0.60 V with fixed probes | 1999.78–2004.70 |
| 1.1 V | 919 | 1.09 V | 3670.33–3674.16 |
| 1.6 V | 1337 | 1.59 V | 5341.69–5344.63 |
| 2.1 V | 1755 | 2.09 V | 7012.95–7016.89 |
| 2.6 V | 2173 | 2.59 V | 8682.70–8687.05 |

The [evidence bundle](../examples/hardware-dc-loopback/README.md) retains unchanged
raw hash chains, separate operator reports, the failed USB preflight and a later
connection check. DMM readings were not synchronized with the raw blocks. Display
resolution and the old 4.90 V supply estimate do not justify a universal +0.01 V
correction, converter accuracy specification, or separate DAC/ADC linearity claim.

At the first point the operator also reported brief 0 V indications. During a
follow-up with fixed probes (20 seconds requested; duration not independently timed),
the display stayed at 0.59–0.60 V. This supports, but does not prove, a probe-contact
explanation. Both reports are retained.

USB enumeration was intermittently lost before the port change. With the same
cable moved to another direct Mac USB port, three open/PING/close cycles and a
10-second idle check passed (25.113 seconds total). Subsequent 1.1–2.6 V handshakes
also succeeded. Power reconnection accompanied the port change, so this does not
isolate a faulty port or establish long-term reliability. The 0.6 V reading preceded
that change; supply voltage was not remeasured on the new port.

Preparation checks: the sketch compiles for UNO R4 WiFi; 28 targeted loopback,
bringup and instrument tests pass. Earlier GND and 3.29 V bringup captures are
separate checks. Full fixture calibration and circuit diagnosis remain pending.

## Wiring, with USB disconnected

- Remove the common feed from GND (or any other supply rail) before connecting it to A0.
- A0 feeds four separate 1 kΩ series resistors; their other ends go to A1–A4.
- No DUT, external capacitor, or resistor from A0 to GND. Do not tie A0 to 3V3/5V/GND.
- DMM black lead stays in COM and references board GND. Red lead stays in VΩ and
  measures A0/common feed in DC voltage mode. This common feed is **not ground**.

ADC input sampling is a dynamic load even with no external load resistor. Supply
reference errors can also cancel between the DAC and ADC. Compare with independent
DMM readings; do not use loopback alone to claim separate DAC/ADC linearity or mV
accuracy. The current meter's 0.01 V display step is not an accuracy specification.

## One held point at a time

```sh
sh scripts/arduino.sh compile --fqbn arduino:renesas_uno:unor4wifi firmware/dac_loopback
sh scripts/arduino.sh upload --fqbn arduino:renesas_uno:unor4wifi --port ACTUAL_PORT firmware/dac_loopback
.venv/bin/python -m benchmate.dac_loopback --port ACTUAL_PORT --level-mv 600
```

The five nominal levels are 600, 1100, 1600, 2100 and 2600 mV. Their fixed 12-bit
codes are 501, 919, 1337, 1755 and 2173, using the earlier operator supply reading
of 4.90 V as an approximate conversion. They are **not measured voltages** or a
new fixture REF setting. Record the DMM reading at each held point separately.
Three anchor readings (600, 1600, 2600) suffice for an initial gross-response check;
more points are needed to characterize nonlinearity.

Boot and PING do not drive A0. HOLD accepts only the five exact predefined levels,
ramps in increments no larger than 372 codes (under 0.5 V for supply ≤5.5 V), and
holds for 250 ms before replying. This dwell is not measured settling evidence.
CAPTURE records 64 samples per channel with the same default ADC configuration as
bringup and actual read-completion timestamps. Transmission follows acquisition.
The long ADC sampling-state setting in the D2 instrument is not enabled here.

**A0 remains driven after capture, after closing the serial connection, and possibly
after a host error. Unplug USB before rewiring or leaving the setup.** There is no
autonomous sweep and no automatic resume after reset. A fresh HOLD is required.

Raw responses, configuration, selected DAC code and failures are stored under
`runs/hardware-dac-loopback`. Nominal targets are never promoted to observed volts;
DMM values are not filled in automatically. Keep the initial raw GND and 3.29 V
records separate. Near-zero ADC readings are floor-clipped and do not establish a
constant offset, repeatability, or a correction that a later three-point fit will
necessarily remove. Full LM358/A2/A5 path calibration and waveform tests remain D2 work.
