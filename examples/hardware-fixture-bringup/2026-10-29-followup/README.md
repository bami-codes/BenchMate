# U2 midpoint and spare Minima bring-up — October 29, 2026

**Hardware preparation, not completed calibration or circuit diagnosis.**
The operator subsequently confirmed transfer of the seven fixture leads
to Minima, with supply 4.88 V and REF 1.62 V. The later records retain the unsuccessful identity/upload checks as well
as the passing checks. The fixed-REF jumper and updated ADC firmware are
now confirmed; three raw midpoint blocks passed acquisition integrity
checks. A later capture attempt failed before CAPTURE because the initial
PING received no bytes. A separate PING-only check also failed while the
serial device remained listed. Calibration and long-duration stability
remain incomplete.

| Record | Observed result |
| --- | --- |
| `continuity/` | Four additional operator-reported continuity checks; no hardware commands |
| `u2-midpoint/` | Original WiFi HOLD at nominal 1.6 V; D35/D40/D45 each 1.59 V, D50/D21 each 1.62–1.63 V on DMM |
| `wifi-usb-loss/` | Original board absent before ADC capture; kernel transaction errors at 10:12:55 and removal at 10:12:56 KST; zero samples acquired |
| `minima-upload-failed/` | First USB-only upload failed during runtime-to-DFU transition; retained without automatic retry |
| `minima-bringup/` | Operator double RESET, accessible identified DFU, successful upload; three open/close PING cycles, 61/61 USB-presence samples over 60 s, final PING passed |
| `minima-instrument/` | Instrument v2 compiled/uploaded; four PINGs with one valid boot ID and advancing uptime, 31/31 USB-presence samples over 30 s; output unarmed |
| `minima-transfer-precheck/` | Transfer reported, but old ID and continuing uptime did not establish a new boot; stopped before output commands |
| `minima-midpoint-attempt/` | Operator midpoint 1.61/1.61/1.61/1.62 V; one requested capture failed validation |
| `minima-midpoint-rejected/` | 512 raw frames retained, zero accepted samples; old host and firmware snapshots match recorded hashes |
| `adc-fix-upload-failed/` | Runtime DFU interface update failed; application serial identity still listed, no automatic retry |
| `adc-fix-upload/` | Operator double RESET then successful manual-mode update, used-channel PING readbacks all 255 and 30-second USB observation passed |
| `corrected-fixture-arm/` | Explicit ARM at new supply/REF settings, expected new boot ID, code 1373 |
| `first-valid-midpoint/`, `valid-midpoint-block-1/` | First 512-frame raw block passes validation, source snapshots and analysis retained |
| `valid-midpoint-block-2/`, `valid-midpoint-block-3/`, `midpoint-repeat-analysis/` | Two additional same-condition blocks investigate larger deviations, all raw samples retained |
| `precise-midpoint-attempt/`, `precise-midpoint-handshake-failed/` | DC 2 V operator readings retained; new attempt stopped at initial PING, no CAPTURE sent and zero accepted samples |
| `minima-handshake-review/` | Separate PING-only diagnostic also received zero bytes; Minima remained enumerated before/after, no output commands |
| `minima-a4-resistance/` | Board A4–5V reported 5.19–5.20 kohm both directions with external A4 lead removed; fixed-REF direct-sense revision requested, not yet confirmed |
| `minima-a4-review/` | D50/G50 1.62/2.15 V; physical voltage difference under investigation, used-register fix compiled/tested but not uploaded |
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
using the reported 4.88 V supply). The later midpoint record supplies the
DMM output readings. A short
30-second check with the fixture attached passed. Long-duration stability
and the cause of the original WiFi fault remain unestablished.

The U2 voltage readings are sequential operator reports at 0.01 V display
resolution. Resolution is not accuracy. The nominal DAC conversion was
uncalibrated, and these are not ADC calibration readings. Minima will
require its own supply/REF checks and ADC/DAC calibration.

[Provenance](provenance.json) lists exact byte copies, source paths, SHA-256
hashes and event-chain terminal states. Twenty-three chains contain 376 events.
Historical pending instructions remain unchanged; later reports are in
separate sidecars or subsequent records. Hashes detect changes relative
to these copies, not independent proof of the measurements. Upload logs
and source snapshots preserve both unsuccessful and successful attempts.
No binary, API key, holdout contents, private photo or host process listing
is included. Reading the evidence makes no hardware or API calls; executing
controller-source scripts can upload firmware or control hardware.

The subsequent ADC attempt was rejected because the old sampling-state
check included unused/reserved register slots. The correction configures
and checks only channels 0/1/2/21 and records states before and after a
block. Related tests: 46 passed; Minima and WiFi compiles passed (logs in
`adc-readback-fix/`). A subsequent manual-mode upload and three captures confirm all four
used registers remain 255 before/after. Rejected data is not retroactively
accepted.

A4 also differs physically: D50 on the REF side is 1.62 V while G50 on
the ADC side is 2.15 V per a separate DMM report. A roughly 5.1 kohm path
toward +5 V is one hypothesis, not yet a confirmed component or wiring
cause. The subsequent board resistance report is 5.19–5.20 kohm both ways with
external A4 disconnected, supporting that model without identifying a
specific physical component. Next requested revision: USB off, replace
only D50–G50's 1 kohm with a short jumper, reconnect H50 to A4, confirm
continuity and recheck supply/D50/G50. The remaining series resistors and
REF pull-down stay installed. This exception is for internal buffered REF
only; its measured noise/load behavior still requires verification. The
original and revised connectivity checks are retained separately.
The operator subsequently confirmed the jumper/continuity/reconnection and
supply/D50/G50 readings of 4.86/1.63/1.63 V. The failed runtime DFU attempt
and successful manual upload are retained separately.

Three HOLD blocks contain 512 frames each at requested 2,000 us intervals.
All passed complete-row, boot-ID, used-register, timing and post-PING
checks; frame intervals were 1,999–2,003 us with no overruns. Approximate
means using 4.86 V and ideal ADC scaling are A1 1.626 V, A2 1.625 V,
A3 1.626 V, A4 1.638–1.639 V. Within-block SDs span about 1.28–2.84 mV,
with larger tails up to 24.4 mV from a block mean. No outliers are deleted.
Read-completion offsets are approximately 52/105/158/216 us, not calibrated
sampling apertures. These are uncalibrated diagnostic observations; no
Gaussian/AR(1) fit, accuracy bound or long-duration reliability is accepted.

The last confirmed output setting was code 1373, nominal 1.63 V. The
operator subsequently reported D35/D40/D45/D50 = 1.631/1.630/1.631/1.629 V
and U1 pin 3 = 1.629 V on the DC 2 V range. These are sequential displays,
not established millivolt accuracy. A subsequent capture attempt received
zero bytes during its initial 60-second PING wait; CAPTURE was never sent.
A separately recorded five-second PING-only diagnostic also received no
response, with the expected serial identity present before/after. No new
ADC comparison was calculated. Current boot continuity and output state
cannot be confirmed over serial. A transient intervening USB removal is
not excluded by these snapshots; no root cause is established.

The next requested DMM check compares breadboard D50 against the board
header labelled SDA (the A4 signal) to distinguish a possible lead/contact
drop from the earlier uncalibrated ADC discrepancy. No reset, stimulus or
firmware change is made during that check. Its result, multi-point
calibration and physical interruption during acquisition remain pending.
