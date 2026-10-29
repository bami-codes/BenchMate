# U2 midpoint and spare Minima bring-up — October 29, 2026

**Hardware preparation, not completed calibration or circuit diagnosis.**

**Current:** measured 100.8 kohm input pull-down installed at B13–E16.
Operator startup supply/REF/input/driver readings are
4.88/1.631/0.003/0.002 V. The first PING fails without output commands;
confirmed single RESET then restores a new unarmed boot. REF code 1369
and a 512-frame raw midpoint block pass. Fresh DMM readings for that
driven midpoint remain pending; no calibration fit or USB cure is claimed.

The following paragraphs retain the chronological history.
The operator subsequently confirmed transfer of the seven fixture leads
to Minima, with supply 4.88 V and REF 1.62 V. The later records retain the unsuccessful identity/upload checks as well
as the passing checks. The fixed-REF jumper and updated ADC firmware are
now confirmed; three raw midpoint blocks passed acquisition integrity
checks. A later capture attempt failed before CAPTURE because the initial
PING received no bytes. A separate PING-only check also failed while the
serial device remained listed. Calibration and long-duration stability
remain incomplete. The operator subsequently confirmed USB reconnection;
a new boot answered PING, and explicit re-arm plus one additional midpoint
block passed. This does not identify the earlier communication fault.
Fresh supply/D45/D50 displays are 4.89/1.636/1.633 V. A separate offline
comparison uses that later supply. Tested DC-hold firmware has subsequently
been uploaded. The first low-level DMM report and a following 512-frame
block are complete; the same boot then held the midpoint for a fresh report.

**Earlier interruption: high-point ADC pairing paused after a USB failure.** The earlier operator report was
D35/D40/D45 at 3.28 V and then reported contact between the +5 V and GND
probe posts. A PING-only check failed; kernel logs show USB loss and
re-enumeration between the last good response and this check. USB disconnection
and absence of a persistent unpowered continuity tone are operator-confirmed.
The operator clarified that the blue GND post remains and only the red
+5 V post was removed; J27 was not installed. Power/REF read 4.88/1.63 V.
The first reconnect PING failed; a confirmed single RESET then restored
new-boot responses and explicit REF ARM. The subsequent B13/A11/D50 report
is 1.62/3.4/1.64 V: the driver does not follow the DAC input. The operator
clarified that 1.62/3.4 V were measured directly at U1 pins 5/7 because
the B13/A11 posts were already removed. USB-off and LED-off are confirmed,
and B12-to-D11 continuity is reported. The actual metal pin 6-to-7 check
also beeps. The subsequent USB reconnection report gives supply/REF
4.86/1.62 V. A new unarmed boot and explicit REF ARM at code 1365 pass;
actual U1 pin 5/6/7 and D50 voltages then all read 1.62 V, with wiring
unchanged. The next low-point attempt failed at its initial PING, before
any low-level command. USB transaction errors are recorded separately.
After a confirmed single RESET, the 16:45:59–16:55:59 KST continuous-open
REF/PING comparison passed 300 checks in 600.011 s. Its Minima-only kernel
query returned no messages. Operator no-touch confirmation is now recorded.
A same-level DC check passed; the following DMM readings are U1 pin 5 /
D35 / D40 / D45 / D50 = 1.620/1.620/1.619/1.620/1.628 V. The held-level
watch closed after 650 checks, then a same-boot 512-frame midpoint block
passed. The subsequent low report is 0.648/0.648/0.647/0.648/1.628 V;
its monitor closed after 270 checks and the 512-frame block passed. The
2.60 V high hold monitor subsequently failed after 240 PINGs. Corrected
high DMM displays are 1.629/0.975/0.975/0.974/0.975/1.629 V, giving derived
absolute pin 5/D35/D40/D45 values of 2.604/2.604/2.603/2.604 V. These are
not paired to an ADC block. No capture or REF-return command followed the
failure; a single RESET is requested. The USB cause and calibration remain open.

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
| `minima-sda-check/` | D50/SDA both 1.633 V reported; PING answered with new boot ID and unarmed state |
| `minima-reconnected-midpoint/`, `minima-reconnected-arm/`, `minima-reconnected-block/` | Operator USB reconnection confirmed; explicit new-ID ARM and one 512-frame block passed, raw data and source snapshots retained |
| `minima-supply-comparison/` | Later 4.89 V supply and D45/D50 readings compared offline with the preceding block; original data unchanged |
| `dc-hold-preparation/` | 71 targeted tests and both board compiles passed; preparation-only record, not itself an upload |
| `dc-hold-host-endpoints/` | DC and CAPTURE HOLD share endpoint rounding and integer code limits; 71 tests pass, no additional firmware change or hardware IO |
| `minima-dc-upload/` | Confirmed manual DFU, successful upload, four unarmed PINGs with DC support, 30-second presence check passed |
| `minima-dc-arm/`, `minima-dc-low-held/`, `minima-dc-low-setup/` | New boot explicitly armed at code 1368, persistent low level verified at code 531; no low-point ADC block yet |
| `minima-dc-low-point/`, `minima-dc-low-block/`, `minima-dc-mid-held/` | Low-point DMM report and 512-frame raw block completed; same-boot midpoint held for the next DMM report |
| `minima-midpoint-anomaly/` | Operator reports 3.28 V at D35/D40/D45; sequence stopped, PING-only check receives no bytes |
| `minima-probe-contact/` | Operator reports rail-probe contact and no USB/RESET action; selected kernel excerpts establish USB loss/re-enumeration; unpowered checks requested |
| `minima-unpowered-check/` | Operator confirms USB off, added probe posts removed, no persistent rail tone; single J27 ground access and fresh power/REF readings requested |
| `minima-contact-power-recovery-failed/` | Operator clarifies retained blue GND post, removed red +5 V post and 4.88/1.63 V supply/REF; PING still fails, no output command |
| `minima-contact-reset-recovery/`, `minima-contact-recovery-arm/` | Confirmed single RESET, two new-boot unarmed PINGs, explicit REF ARM and postcheck pass; physical output verification pending |
| `minima-driver-voltage-mismatch/` | Later B13/A11/D50 report 1.62/3.4/1.64 V; physical recovery not established, USB-off requested before contact checks, no hardware commands |
| `minima-driver-contact-clarification/` | Prior readings were directly at U1 pins 5/7, B13/A11 posts removed; USB-off confirmed, B12↔D11 beep reported, direct pin 6↔7 check requested |
| `minima-driver-pin-feedback/` | Actual U1 metal pins 6↔7 beep unpowered; unchanged-wiring power reapplication and fresh supply/REF readings requested; no hardware commands |
| `minima-driver-power-reapplication/`, `minima-driver-power-reapplication-arm/` | Reconnect and 4.86/1.62 V supply/REF report, new unarmed boot, explicit code 1365 ARM and postcheck pass; physical driver output still pending |
| `minima-recovered-midpoint-low-attempt/` | U1 pins 5/6/7 and D50 all 1.62 V reported; low-point attempt fails at PING, no DC command sent |
| `minima-recovered-usb-review/` | Selected Minima USB errors, port/filtered power-log review and prepared continuous-connection comparison; cause not established |
| `minima-persistent-ref-watch/` | 600.011 s, 300 same-boot/same-code PINGs pass on one connection; post-run named-device kernel query has zero messages |
| `minima-post-watch-ref/`, `minima-post-watch-ref-held/` | Same-boot 1.62 V DC settling and code postcheck pass; precise operator DMM values pending |
| `minima-midpoint-held-watch/` | Separate PING-only connection passes 650 checks over 1305.597 s, closes explicitly before capture; includes operator DMM probing |
| `minima-dc-recovery-mid-point/`, `minima-dc-recovery-mid-block/`, `minima-dc-recovery-low-held/` | Precise midpoint DMM plus 512-frame raw block pass; same-boot interior low target 0.65 V/code 548 held for the next report |
| `minima-low-held-watch/` | Low level passes 270 same-boot/code checks over 542.202 s, closes explicitly before capture |
| `minima-dc-recovery-low-point/`, `minima-dc-recovery-low-block/`, `minima-dc-recovery-high-held/` | Low DMM plus 512-frame block pass; same-boot high target 2.60 V/code 2191 held |
| `minima-high-DMM-protocol/` | High-point DC 2 V differences and bracketing REF readings requested before data; probe-only moves, no circuit changes |
| `minima-high-held-watch-failed/` | Continuous-open monitor passes 240 PINGs, then receives zero bytes at 17:37:43 KST; failed chain retained, no high ADC capture |
| `minima-high-point-review/` | Original and corrected DMM displays, derived voltages, selected kernel errors and rejection of high ADC pairing; no hardware commands |
| `minima-high-operator-followup/` | No USB/RESET action during high DMM confirmed; extended cause investigation paused, input pull-down proposed |
| `minima-input-pulldown/` | Isolated 100.8 kohm value, C13 obstruction and confirmed B13–E16 installation recorded |
| `minima-pulldown-startup-failed/` | Startup voltages retained; first PING receives no bytes, no ARM or CAPTURE sent |
| `minima-pulldown-reset-startup/` | Manual single RESET, new unarmed boot, explicit REF and one 512-frame midpoint block pass; fresh driven-point DMM pending |
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
hashes and event-chain terminal states. Sixty-eight chains contain 2,161 events.
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

The operator later reported D50/SDA = 1.633/1.633 V and confirmed USB
reconnection. Exact reconnection time and measurement order relative to
reconnection were not supplied. At 14:46 KST a PING returned a new boot ID,
397490 ms uptime and unarmed state. An explicit new-ID ARM at code 1373
then preceded a single 512-frame HOLD block. The same boot ID, timing and
used-register checks passed; frame intervals were 1999–2003 us with zero
overruns. A1/A2/A3/A4 raw means are 5482.87/5477.43/5482.25/5479.18 counts.
Nominal within-block SDs span 1.39–2.08 mV; larger tails remain untrimmed.

The earlier positive A4-to-A3 difference is not reproduced: A4 is about
3.07 counts below A3 in this block. Its cause is not established, and no
cross-boot calibration correction is applied. Nominal volts still use
the older 4.86 V supply reading. Fresh supply/D45/D50 displays are now
requested with output, wiring and USB unchanged. The prior failed runs
remain failed, and this brief success is not a long-duration stability test.

The next DMM report supplied 4.89 V / 1.636 V / 1.633 V. Using that later
supply for an offline conversion gives nominal A3=1.63634 V and
A4=1.63543 V, differing from the displays by +0.34/+2.43 mV. This is not a
simultaneous measurement or a calibrated accuracy result. No original
capture, conversion or failure record was overwritten.

Persistent DC calibration holds are now supported by a separate command.
The boot guard, integer envelope, bounded moves, settling and host
postcheck were tested, then the checked Minima binary was uploaded after
the operator's manual DFU confirmation. Its new boot
`cd496fa1aa18dcb15bae7d05553fe560` was explicitly armed using 4.89 V / 1.633 V
and acknowledged the first low level at code 531. The requested target is
0.633 V; physical DMM values remain pending. A4 is still fixed REF, so this
step alone cannot establish its gain over the stimulus range. There has
been no low-point ADC block, multi-point fit or hardware diagnosis yet.

The subsequent low-point DMM report is 0.629/0.628/0.629/1.633 V at
D35/D40/D45/D50. One same-boot 512-frame block passed, with initial held
code 531, used ADC states all 255, intervals 1998–2003 us and zero overruns.
Raw means are 2110.25/2112.81/2114.90/5478.31 counts. No outliers were
removed; SDs and full descriptive statistics are in the point analysis.
A separate DC command then confirmed midpoint code 1368 on the same boot.
Fresh midpoint displays are pending. A multi-point fit and A4 gain
calibration are still incomplete.

The later 3.28 V report supersedes the assumption that the acknowledged
midpoint remained physically held. PING at 15:19:43 KST received no bytes;
port snapshots were present, but kernel logs show Minima connection loss
at 15:14:47 and re-enumeration at 15:14:49. The reported +5 V/GND probe
contact is consistent with a supply disturbance; its timing/duration and
the board's reset or damage state are not established. No causal conclusion
is extended to earlier faults. Only selected device-specific kernel
excerpts are public. USB removal, removal of the two added probe posts,
and an unpowered rail-continuity check are pending; powered probing and
the sweep do not resume until the physical state is checked.

The operator subsequently confirmed USB disconnected, both extra probe
posts removed and no persistent unpowered rail-continuity tone. Component
health is not established by that check. The next requested arrangement
uses one secured ground probe at J27, validated against the wiring graph
and requiring an operator unpowered continuity check. The existing
divider's A3-side lead serves as the +5 V measurement contact, without an
extra loose +5 V post; J10 remains the REF contact. Placement and new DC
20 V power/REF readings are pending, before any output re-arm.

The next operator report clarified the actual arrangement: retain the
original blue GND probe post and remove only the red +5 V post. J27 was
not used. Supply/REF read 4.88/1.63 V, but the reconnect PING still received
no bytes. After a separately confirmed single RESET, two PINGs verified
new boot `c7992fcbd2cba35e53aa1b2d805b84e4`, unarmed state and the expected
ADC settings. An explicit ARM then confirmed code 1368 using 4.88 V / 1.63 V.
B13/A11/D50 DMM readings are pending. This is staged recovery, not a
completed calibration, proof of no damage, or a diagnosis of every earlier
USB fault. No firmware change or midpoint/high-point capture was made.

The subsequent physical check reports B13/A11/D50 at 1.62/3.4/1.64 V.
This is a driver/input mismatch, not a successful follower check or a
calibration point. USB disconnection and LED-off confirmation are pending
before unpowered U1 input/feedback contact checks. Chip damage is not
established. No hardware command was issued for this report.

A subsequent clarification identifies the actual prior voltage contacts
as U1 pins 5/7, not B13/A11 probe posts, which the operator had removed
the previous night. USB-off and LED-off are confirmed. B12-to-D11 beeps,
but actual pin 6-to-7 continuity is still requested. No new powered reading,
hardware command or chip-fault conclusion follows from this clarification.

The requested direct pin 6-to-7 check subsequently beeps. With wiring and
ICs unchanged, same-cable/port USB reconnection and DC 20 V supply/REF
readings are now requested. Powered output recovery remains unverified;
there is no new DAC command or capture in this record.

The next report confirms reconnection with supply/REF 4.86/1.62 V.
New boot `b4ab5f3bf78ec9374ac381996885027b` was unarmed; explicit REF ARM
and its postcheck then confirmed code 1365. No ADC block or firmware change
was made. Actual U1 pins 5/6/7 and D50 readings are pending, so this is
command verification rather than established physical driver recovery.

The next report gives U1 pins 5/6/7 and D50 all at 1.62 V, showing midpoint
follower agreement at display resolution. The following low-point attempt
receives no initial PING response and sends no DC command. Minima remains
listed; selected kernel logs show endpoint 0x81 transaction errors from
16:27:41 KST. The queried window contains no named loss/enumeration messages,
and a filtered power-log query returns no matching Sleep/Wake events.
The cause remains open; the raw full kernel log stays local.

After confirmed single RESET, a new boot and explicit REF ARM start the
600-second single-open/PING comparison at 16:45:59 KST. It is in progress;
only completed evidence is exported in this manifest. No firmware or
wiring change is part of the comparison.

That comparison subsequently completed in 600.011 s with 300 successful
PINGs, unchanged boot and REF code. Its post-run Minima-only kernel query
returned zero messages; the summary/hash is an added sidecar. Operator
no-touch confirmation is still pending. Same-boot DC at the same 1.62 V
target then passed settling and postcheck. PING-only monitoring now keeps
that level under observation while precise U1 pin 5/D35/D40/D45/D50 DMM
readings are requested. This live monitor is not exported while incomplete.

The operator subsequently confirms the ten-minute no-touch condition and
reports U1 pin 5 / D35 / D40 / D45 / D50 at
1.620/1.620/1.619/1.620/1.628 V on DC 2 V. The held-level watch completes
650 checks over 1305.597 s and closes explicitly. A matched same-boot
512-frame block passes timing/identity/ADC-state checks; all samples,
including deviations up to about 19 mV from the channel mean, are retained.
No fitting or accuracy claim follows from one point. The next target is
0.65 V, inside the envelope with margin against the measured 1.628 V REF.
Its code 548 hold passes; a new PING-only monitor is active for the next
DMM report and remains unexported while incomplete.

The low point subsequently reports pin 5/D35/D40/D45/D50 at
0.648/0.648/0.647/0.648/1.628 V. Its monitor closes after 270 checks;
512 raw frames pass with no overruns and no sample trimming. A same-boot
2.60 V/code 2191 high hold then passes. Its requested six DMM readings
use DC 2 V: REF-to-GND before/after and four node-to-REF differences.
Only probes move. Any absolute high voltage will be derived from these
readings, retaining shared-reference and sequential-measurement limits.
The high monitor subsequently failed after 240 successful PINGs; the
complete failed chain is now exported. Last successful response was
17:37:36.099 KST, kernel transaction errors start at 17:37:36.845, and
the monitor terminates at 17:37:43.111 with zero response bytes. A
Minima-only kernel query from 17:35–17:40 contains 3,002 transaction
errors. Selected messages and the raw-log hash are retained; raw host
logs are not published. The port remains listed at 17:45:23. No unique
cause or reset is established, and the operator's physical actions
during the measurement window are not yet confirmed.

The corrected report is REF before/after 1.629 V, with pin 5/D35/D40/D45
differences of 0.975/0.975/0.974/0.975 V. Absolute derived values are
2.604/2.604/2.603/2.604 V; shared REF error, possible intermediate drift
and unknown meter accuracy remain. The earlier coarse report is also
retained. The requested DC 2 V range was not separately restated by the
operator. No high ADC block or calibration fit is accepted, and no
REF-return command followed the fault. Continuous-open periodic PING
alone did not prevent this failure. A new single RESET has been requested
before verifying a fresh unarmed boot and explicitly restoring REF.

That RESET request was subsequently superseded by a powered-off input
pull-down installation. The isolated resistor reads 100.8 kohm; C13 is
blocked by the divider resistor body, so B13 on the same input strip is
used instead, with the other end at E16 GND. Reconnected input and driver
are reported at 3/2 mV before DAC setup. This is one startup observation,
not a controlled proof that the resistor cured the previous high-output
condition or a USB fix. The first PING after reconnection still fails.

The operator then confirms single RESET with USB and wiring retained.
One serial connection verifies new unarmed boot, explicitly arms REF at
code 1369, captures 512 frames at that same code, and verifies post-PING.
Intervals are 1998–2003 us with no overruns. Before measurement, broad
diagnostic gates were declared: channel means within 100 mV of reported
REF, every sample within 150 mV, mean channel spread at most 50 mV, and
no raw rail samples. All pass using nominal 4.88 V ADC conversion; these
are provisional wiring/saturation checks, not accuracy or noise limits.
Nominal means for A1/A2/A3/A4 are 1.62739/1.62760/1.62839/1.64421 V.
All samples, including larger deviations, remain. The startup input/REF
DMM report is not a driven midpoint calibration pair. Fresh B13 and four
measurement-node DMM readings are requested without changing output.
