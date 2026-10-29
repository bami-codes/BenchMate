# U2 midpoint and spare Minima bring-up — October 29, 2026

**Hardware preparation, not completed calibration or circuit diagnosis.**
The fixture is still attached to the unpowered original WiFi board at this
record's close. Transfer to Minima has been requested, not confirmed.

| Record | Observed result |
| --- | --- |
| `continuity/` | Four additional operator-reported continuity checks; no hardware commands |
| `u2-midpoint/` | Original WiFi HOLD at nominal 1.6 V; D35/D40/D45 each 1.59 V, D50/D21 each 1.62–1.63 V on DMM |
| `wifi-usb-loss/` | Original board absent before ADC capture; kernel transaction errors at 10:12:55 and removal at 10:12:56 KST; zero samples acquired |
| `minima-upload-failed/` | First USB-only upload failed during runtime-to-DFU transition; retained without automatic retry |
| `minima-bringup/` | Operator double RESET, accessible identified DFU, successful upload; three open/close PING cycles, 61/61 USB-presence samples over 60 s, final PING passed |
| `minima-instrument/` | Instrument v2 compiled/uploaded; four PINGs with one valid boot ID and advancing uptime, 31/31 USB-presence samples over 30 s; output unarmed |

The two USB-only Minima windows used different firmware and are not a
single uninterrupted observation. USB polling was approximately once per
second with serial closed. No ARM, CAPTURE or STOP command was sent to
Minima. Instrument setup includes initial ADC reads, but no measurement
block was acquired or used. Observing one boot ID is not a completed
physical reset/stale-command test. Long-duration and same-fixture stability
are not established, nor is the cause of the original WiFi fault.

The U2 voltage readings are sequential operator reports at 0.01 V display
resolution. Resolution is not accuracy. The nominal DAC conversion was
uncalibrated, and these are not ADC calibration readings. Minima will
require its own supply/REF checks and ADC/DAC calibration.

[Provenance](provenance.json) lists exact byte copies, source paths, SHA-256
hashes and event-chain terminal states. Six chains contain 172 events.
Historical pending instructions remain unchanged; later reports are in
separate sidecars or subsequent records. Hashes detect changes relative
to these copies, not independent proof of the measurements. Upload logs
and source snapshots preserve both unsuccessful and successful attempts.
No binary, API key, holdout contents, private photo or host process listing
is included. Reading the evidence makes no hardware or API calls; executing
controller-source scripts can upload firmware or control hardware.

Next: with USB disconnected, transfer the seven board-side connections
by printed pin name (5V/GND/A0/A1/A2/A3/A4), retain the calibration fixture,
then recheck supply/REF. Compare the new boot ID with this record and test
stale-ID rejection before explicit arming. Physical interruption during
acquisition and D2 calibration remain separate pending checks.
