# LM358 fixture bring-up, October 28–29, 2026

Real hardware preparation on a UNO R4 WiFi compatible board, followed by
an operator assembly report after midnight (Asia/Seoul). **This is not
completed calibration, a physical circuit diagnosis or a repair result.**

The [October 29 follow-up](2026-10-29-followup/README.md) adds U2 midpoint
DMM readings, another WiFi USB loss before ADC capture, and successful
USB-only bring-up/instrument-v2 PING checks on the spare Minima. The
earlier observations below retain their original scope and chronology.

The [assembly history](../../docs/fixture-assembly.md) and
[complete hole-coordinate table](../../docs/fixture-wiring-table.md) describe
the fixture. The [export provenance](export-provenance.json) identifies
each copied source and SHA-256. Original event files and operator sidecars
are copied byte for byte; earlier pending fields are not rewritten when
later reports arrive. The newly timestamped `operator/` record contains
the session-close report and an explicitly retrospective transcription of
the earlier REF readings. Hash chains detect changes relative to these
records; they are not external attestation or proof against rewriting.

## Observed DC behavior

ANENG DM950, DC 20 V, readings relative to Arduino GND. U1 has a 1.001 kΩ
REF pull-down and 0.999 kΩ driver pull-down. No DUT or ADC leads were
attached during these U1 checks.

| Check | Operator display |
| --- | --- |
| Supply | 4.88 V |
| Divider input / buffered REF | 1.62 / 1.62 V |
| Nominal 0.6 V driver, input / output | 0.59 / 0.59 V |
| Nominal 1.6 V driver, input / output | 1.59 / 1.59 V |
| Nominal 2.6 V driver, input / output | Each usually 2.58 V, occasionally 2.59 V |

The input/output readings are sequential, not simultaneous. Equal displays
do not imply zero offset; 0.01 V display resolution is not meter accuracy
or an ADC noise estimate. No waveform or full-range linearity claim is
made from these three points. Nominal settings used the earlier 4.9 V
firmware conversion constant, not a calibrated actuator model.

## USB observations, including unsuccessful attempts

`control/` contains all eight recorded fixture-control/presence sessions
in this sequence: a sandbox serial-open failure before any HOLD, the first
0.6 V point, a missing-device observation, a short spare-cable check, a
second missing-device preflight, the 1.6/2.6 V points and the final
PING-only retained-state check. An observation-only `run_completed` does
not mean the USB device was present; inspect its payload.

The selected kernel lines in `usb/usb-key-events-2026-10-28.txt` show
transaction errors and host device removal at approximately 22:28 and
22:41. The latter occurred after changing the cable. `reset API call` is
a host USB log label, not proof that the RA4M1 rebooted. The original WiFi
`dac_loopback-v1` firmware lacks a boot ID. At the end of that October 28
session, instrument v2 had not been uploaded and the spare was untested;
the October 29 follow-up above records subsequent spare-board checks.

After manual reconnection, two 600-second observation windows passed:

| Condition | Local interval | USB-present samples | Final retained-state PING |
| --- | --- | --- | --- |
| Operator-confirmed hands off | 23:12:35–23:22:35 | 601 / 601 | Passed |
| Ordinary DMM probing, then hands off | 23:28:10–23:38:10 | 601 / 601 | Passed |

Serial was closed during each window; USB enumeration was checked about
once per second. Exact probe-contact times were not measured. Aggregate
CPU/VM counters are included in these event chains; there are no process
listings or research-project contents. Zero within-window swap increments
and these successful windows cannot explain or rule out causes of the
earlier failures. Handling-related loss was not reproduced; neither a
root cause nor a permanent fix has been established. Normal serial-close
`abortGated` lines in the targeted kernel logs are not classified as
device-removal failures.

`usb/` also includes the observer sources, original sidecars and derived
summaries. A summary written before an operator reply may still say
confirmation is pending; its later operator sidecar supplies that reply.
Available command-controller source snapshots are archived in `control/`.
Reviewing the JSON records requires no hardware connection or API call.

## Session-close state (before the subsequent resistance report)

The operator reports completing U2, its resistors/capacitor/jumpers and
the protected A1–A4 connections, plus all requested continuity checks.
The two new 10 kΩ and four ADC-series 1 kΩ resistor values have not been
measured/reported; no new assembly photo or powered U2/ADC verification
has been supplied. The assembly report is not converted into a claim of
calibrated performance. USB removal overnight was instructed, not
independently observed. No further hardware commands were issued while
preparing this commit.

At that point the next work was unpowered resistor checks and photo review, U2 DC/protected ADC
verification, instrument-v2 boot-ID/reset checks, then actual timing,
noise, offsets/gains, pull-down comparison and D2 limits. The current
firmware acquires A1–A4 only; A5 is unconnected. Hardware D01/B5 and final
holdout evaluation remain pending.

## Subsequent resistance report, October 29

The operator later reported series-resistor displays of 0.996, 0.996,
0.999 and 0.994 kΩ at columns 35, 40, 45 and 50, respectively, and 9.98 kΩ
for each 10 kΩ pull-down. They explicitly confirmed USB was disconnected
but the resistors remained installed. These are **in-circuit readings**,
not isolated component measurements; other paths may affect the readings.
Do not use them as calibrated individual resistance values or claim a
verified tolerance from them. The meter range was not specified anew.

The new [operator record](operator/20261029T005333-1caa781976/events.jsonl)
and its [copy provenance](operator/20261029T005333-1caa781976/provenance.json)
retain the readings and clarification. Earlier event chains and the
original export verification remain unchanged. No serial, stimulus or
firmware action was performed for this update. Photo review, isolated
values where required, and powered U2/ADC verification are still pending.

`wiring-design/` retains the proposed table and the connectivity calculation
used before the assembly report. It checks occupied holes, supplies,
feedback, series resistors and removable jumpers; it cannot establish
what was physically plugged in. Private reports, keys, holdout originals,
unreviewed photos and unrelated host diagnostics are not included.
