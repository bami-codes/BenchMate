# Five-point bare-board DC check

Recorded on 2026-10-27 (Asia/Seoul) with a UNO R4 WiFi compatible board, four
separate 1 kΩ resistors from A0 to A1–A4, and an ANENG DM950 in DC 20 V mode.
No LM358 buffer, circuit under test, or external load resistor was attached.

See the [measurement table and procedure](../../docs/dac-loopback.md) and the
[machine-readable manifest](manifest.json). The manifest links five original raw
blocks, six separate operator-report records, a failed USB preflight, and a later
three-cycle connection check. Copies preserve the original event bytes and hashes.
This bundle is scoped to the DC check; earlier bringup attempts remain local.

- `points/`: 64 raw samples per channel at each held DAC code. The original
  `dmm_reading_v: null` stays unchanged because the DMM report arrived afterward.
- `operator/`: subsequent manual readings, including the initial intermittent
  0 V report and its fixed-probe follow-up. Source hashes tie reports to raw blocks.
- `usb/`: missing-device preflight and the short check after changing Mac ports.

The raw records contain no calibrated voltages or circuit diagnosis. These five
coarse points establish increasing combined DAC/ADC response, not a full code
linearity sweep, independent converter accuracy, waveform quality, or long-term
USB reliability. The 0.6 V point used the original port; later points used another
port with the same cable. The supply was not remeasured after that change.

The final command held A0 at code 2173. The operator was instructed to unplug USB
after reporting the final DMM value; physical disconnection was not observed in
these records. There are no automatic hardware actions when reviewing this bundle.
