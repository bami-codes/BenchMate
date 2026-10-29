# U2 midpoint and spare Minima bring-up — October 29, 2026

**Hardware preparation, not completed calibration or circuit diagnosis.**
The operator subsequently confirmed transfer of the seven fixture leads
to Minima, with supply 4.88 V and REF 1.62 V. The later RESET/ARM records
below retain the initial unsuccessful identity check as well as the pass.

| Record | Observed result |
| --- | --- |
| `continuity/` | Four additional operator-reported continuity checks; no hardware commands |
| `u2-midpoint/` | Original WiFi HOLD at nominal 1.6 V; D35/D40/D45 each 1.59 V, D50/D21 each 1.62–1.63 V on DMM |
| `wifi-usb-loss/` | Original board absent before ADC capture; kernel transaction errors at 10:12:55 and removal at 10:12:56 KST; zero samples acquired |
| `minima-upload-failed/` | First USB-only upload failed during runtime-to-DFU transition; retained without automatic retry |
| `minima-bringup/` | Operator double RESET, accessible identified DFU, successful upload; three open/close PING cycles, 61/61 USB-presence samples over 60 s, final PING passed |
| `minima-instrument/` | Instrument v2 compiled/uploaded; four PINGs with one valid boot ID and advancing uptime, 31/31 USB-presence samples over 30 s; output unarmed |
| `minima-transfer-precheck/` | Transfer reported, but old ID and continuing uptime did not establish a new boot; stopped before output commands |
| `minima-reset-arm/` | Operator-confirmed single RESET changed ID; host rejected old identity and firmware rejected old-ID ARM/CAPTURE; new-ID ARM at code 1359, 31/31 USB-presence samples over 30 s and final reopened PING passed |

The two USB-only Minima windows used different firmware and are not a
single uninterrupted observation. USB polling was approximately once per
second with serial closed. No ARM, CAPTURE or STOP command was sent during
those two USB-only records. Instrument setup includes initial ADC reads,
but no measurement block was acquired or used.

After transfer, the explicit single-RESET test established ID change and
rejection of two well-formed stale commands. It did not establish that
power was fully removed during transfer, and did not test an interruption
during acquisition. Fresh PINGs after each rejected command remained
unarmed. The subsequent valid ARM leaves A0 at code 1359 (nominal 1.62 V
using the reported 4.88 V supply); DMM output readings are pending. A short
30-second check with the fixture attached passed. Long-duration stability
and the cause of the original WiFi fault remain unestablished.

The U2 voltage readings are sequential operator reports at 0.01 V display
resolution. Resolution is not accuracy. The nominal DAC conversion was
uncalibrated, and these are not ADC calibration readings. Minima will
require its own supply/REF checks and ADC/DAC calibration.

[Provenance](provenance.json) lists exact byte copies, source paths, SHA-256
hashes and event-chain terminal states. Eight chains contain 241 events.
Historical pending instructions remain unchanged; later reports are in
separate sidecars or subsequent records. Hashes detect changes relative
to these copies, not independent proof of the measurements. Upload logs
and source snapshots preserve both unsuccessful and successful attempts.
No binary, API key, holdout contents, private photo or host process listing
is included. Reading the evidence makes no hardware or API calls; executing
controller-source scripts can upload firmware or control hardware.

Next: with USB and fixture wiring unchanged, check D35/D40/D45/D50 voltages
against Arduino GND before the first ADC block. Physical interruption
during acquisition and D2 calibration remain separate pending checks.
