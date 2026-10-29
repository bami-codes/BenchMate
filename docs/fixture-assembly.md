# D2 physical assembly — coordinate record

Latest status, 2026-10-29 Asia/Seoul: U1 REF and driver gross DC checks
are recorded; two ten-minute USB windows passed after earlier disconnects.
The operator reports U2/A1–A4 assembly and the requested continuity checks
complete. Six in-circuit resistor readings and midpoint U2 DMM readings
have since been reported. USB removal recurred before the first fixture
ADC capture; zero ADC samples were acquired. Spare Minima USB-only
identification succeeded. Its first upload failed at the DFU transition;
after operator-confirmed double RESET, bring-up upload and a 60-second
USB-only observation passed. Instrument v2 then uploaded successfully:
four PINGs reported one valid boot ID and advancing uptime, with output
unarmed. The operator then confirmed the seven-lead transfer and supply
4.88 V / REF 1.62 V. An initial identity check stopped because the old
boot ID and uptime continued. After an explicitly reported single RESET,
the ID changed and stale ARM/CAPTURE commands were rejected. New-ID ARM
now holds code 1359 (nominal 1.62 V); 31/31 USB samples over 30 seconds
and the final reopened PING passed. DMM D35/D40/D45/D50 readings were
1.61/1.61/1.61/1.62 V. The first 512-frame block was received but rejected
by the ADC-state check; zero samples were accepted. A used-register-only
software fix is compiled/tested, not uploaded. D50/G50 DMM readings of
1.62/2.15 V also establish a reported physical A4-series-resistor voltage
difference. The isolated external A4 connection check reported board
A4-to-5V resistance 5.19–5.20 kohm in both probe polarities. Replacing only
D50–G50 with a short jumper is now operator-confirmed, with supply/D50/G50
4.86/1.63/1.63 V. The corrected ADC firmware was uploaded manually after
a failed automatic transition. Three 512-frame blocks passed acquisition
checks; all used sampling-state registers were 255 before/after and boot ID
was unchanged. Rare larger deviations persist. The later DC 2 V displays
are D35/D40/D45/D50 = 1.631/1.630/1.631/1.629 V and U1 pin 3 = 1.629 V.
A fresh capture attempt received no initial PING response, so no CAPTURE
command was sent and zero samples were accepted. A separate PING-only
check also received no response while the Minima serial identity remained
listed. Current boot continuity/output state cannot be confirmed over
serial in that failed check. The operator later reported D50/SDA both
1.633 V and confirmed USB reconnection. A subsequent PING returned a new
boot ID and unarmed state. Explicit re-arm and one new 512-frame block
passed; A4's earlier positive channel difference was not reproduced.
Fresh supply/D45/D50 displays are 4.89/1.636/1.633 V. Offline re-scaling
of the preceding block with 4.89 V gives A3/A4 about 1.63634/1.63543 V;
this is a sequential comparison, not an accuracy claim. A DC-hold firmware
addition passed 71 targeted tests and both board compiles, then was uploaded
after confirmed manual DFU. The new boot passed initial checks, was explicitly
armed at code 1368 and held low-point code 531. The reported low-point
D35/D40/D45/D50 displays are 0.629/0.628/0.629/1.633 V; the following
512-frame block passed. The following midpoint was last acknowledged at
code 1368, but the operator then reported D35/D40/D45 at 3.28 V. A PING-only
check received no response. Kernel logs establish a Minima USB loss at
15:14:47 KST and re-enumeration at 15:14:49. The operator reports the red
and blue rail probe posts touched during probing and no deliberate USB or
RESET operation. The voltage sweep is stopped. USB unplug, removal of only
the two added probe posts, and an unpowered rail-continuity check have been
requested. The operator has now confirmed USB disconnection, removal of
the added probe posts and no persistent rail-continuity tone. The operator
later clarified that only the red +5 V post was removed and the original
blue GND post remains; the requested J27 relocation was not performed.
Fresh power/REF displays are 4.88/1.63 V. PING after reconnect was still
unanswered. An operator-confirmed single RESET restored responses with a
new unarmed boot; explicit ARM then established code 1368. The subsequent
B13/A11/D50-labelled report is 1.62/3.4/1.64 V: the operator clarified
that the first two readings were directly at U1 pins 5/7 because the probe
posts had been removed the previous night. USB disconnection and LED-off
are now confirmed, with B12-to-D11 continuity reported. The subsequent
actual metal pin 6-to-7 check also beeps. USB reconnection is now confirmed,
with fresh supply/REF 4.86/1.62 V. A new unarmed boot was verified, followed
by explicit ARM at code 1365 and a matching postcheck. The operator then
reported actual U1 pins 5/6/7 and D50 all at 1.62 V: midpoint follower
agreement recovered at display resolution. The next low-point attempt
failed at its initial PING; no low command was sent. Kernel logs show
repeated USB transaction errors from 16:27:41 KST, without named loss or
enumeration messages in the queried window. Following a confirmed single
RESET, a ten-minute single-connection REF/PING comparison ran from
16:45:59 to 16:55:59 KST: 300 PINGs passed with the same boot and code.
The named-device kernel query for that window returned no messages.
Same-boot REF DC settling and postcheck subsequently passed. The operator
confirmed no touching during the ten-minute window and reported precise
U1 pin 5 / D35 / D40 / D45 / D50 values of
1.620/1.620/1.619/1.620/1.628 V. The separate held-level monitor completed
650 checks over 1305.597 s and closed before a same-boot 512-frame midpoint
capture, which passed. A subsequent 0.65 V DC hold (code 548) passed;
PING-only monitoring is active during its pending DMM report. Firmware
and wiring are unchanged; the fault cause and multi-point calibration remain open.
This document is chronological; earlier pending instructions below are
historical. See the [public evidence bundle](../examples/hardware-fixture-bringup/README.md)
and [current wiring table](fixture-wiring-table.md).

## Board orientation and observed state

2026-10-28 (Asia/Seoul). The operator supplied a photograph of the empty
830-hole breadboard and five ICs marked LM358N, with ST logos visible.
Markings are identification evidence, not an authenticity test.

- Keep the photograph's orientation: A is at the upper left. Rows A–E
  are above the central trench; F–J are below it.
- Use the upper edge's column numbers, increasing from left to right,
  for BOTH halves. Ignore the reversed numbers printed on the lower edge.
- For example, E10 and F10 are opposite each other across the trench.
- The operator reports a continuity check: power rails are split near
  column 30. Do not treat left and right sections as connected.
- Upper and lower rails are also separate unless explicitly bridged.
- At the initial setup confirmation, USB was unplugged and the previous
  A0 → four individual 1 kΩ → A1–A4 loopback was still assembled.
- All ordered parts have been received and unpacked, per operator report.

## U1 placement — visually checked, not powered

Place U1, one LM358N, across the central trench at columns 10–13.
The package marking faces upward and the semicircular notch faces LEFT.
This puts pin 1 at the lower-left corner, F10.

| Breadboard position | IC pin | Function |
| --- | --- | --- |
| E10 | 8 | Positive supply |
| E11 | 7 | Amplifier 2 output |
| E12 | 6 | Amplifier 2 inverting input |
| E13 | 5 | Amplifier 2 non-inverting input |
| F10 | 1 | Amplifier 1 output |
| F11 | 2 | Amplifier 1 inverting input |
| F12 | 3 | Amplifier 1 non-inverting input |
| F13 | 4 | Negative supply / board 0 V |

Reference: [ST LM358 datasheet, package pin connections, top view](https://www.st.com/resource/en/datasheet/lm358.pdf).

The operator supplied IMG_8850.heic on 2026-10-28. Inspection of the full
image and a crop shows the notch facing left and the pins at E10–E13 and
F10–F13, consistent with the requested placement. No other components or
wires are visible on this breadboard. This is a visual placement check,
not a contact-continuity or powered functional test.

Do not record an installation, powered check, REF measurement or calibration
as complete until the operator supplies the corresponding evidence.

## Divider resistors — operator readings and placement photo received

Keep USB disconnected. Check three separate 10 kΩ resistors with the
multimeter before installation (20 kΩ resistance range; record displayed
values). Install only these three parts:

| Part | Nominal value | First lead | Second lead | Operator DMM reading |
| --- | --- | --- | --- | --- |
| R_DIV_TOP_A | 10 kΩ | A3 | A6 | approximately 9.95 kΩ |
| R_DIV_TOP_B | 10 kΩ | B6 | B9 | approximately 9.97 kΩ |
| R_DIV_BOTTOM | 10 kΩ | C9 | C16 | approximately 9.98 kΩ |

2026-10-28: The operator reports slight fluctuation of the final displayed
digit, tidied/reinserted the leads, and confirmed the coordinates. The
attached placement photo is consistent with these endpoints. No meter
accuracy or resistance uncertainty has been established from this report.
The nominal divider ratio using these readings is 9.98 / 29.90 = 0.333779.
At an assumed 4.90 V supply (the earlier rail reading), this predicts
1.6355 V at the unloaded tap, before amplifier input loading. This is a
calculation, not a new voltage measurement or completed REF calibration.

Within the upper terminal strip, each column's A–E holes are connected.
The resulting chain is column 3 → 10 kΩ → column 6 → 10 kΩ → column 9
→ 10 kΩ → column 16. Column 3 is the positive-supply end; column 16 is
the board-GND end; column 9 is the unbuffered divider tap. The subsequent
jumpers connect these nodes to the unpowered rails and amplifier input.
The divider resistor endpoints avoid U1's columns 10–13.
Resistor orientation is interchangeable. Keep exposed leads clear of other
conductors.

## Six jumpers — operator reports installation and continuity checks

Keep USB disconnected and leave Arduino disconnected from the new fixture.
Use only the UPPER LEFT power-rail sections. Rail hole numbers below mean
actual holes counted from the far left within that color's row; all selected
holes are in the first group of five, well before the central rail split.

| Jumper | First end | Second end | Purpose |
| --- | --- | --- | --- |
| 1 | B3 | Upper-left red rail, hole 3 | Divider positive supply |
| 2 | A10 | Upper-left red rail, hole 5 | U1 pin 8 positive supply |
| 3 | A16 | Upper-left blue rail, hole 3 | Divider board-0-V return |
| 4 | J13 | Upper-left blue rail, hole 5 | U1 pin 4 negative supply / board 0 V |
| 5 | D9 | H12 | Divider tap to U1 pin 3 (non-inverting input) |
| 6 | G10 | G11 | U1 pin 1 output to pin 2 (negative feedback) |

2026-10-28: The operator reports all six jumpers installed, with jumper 6
gray. Reported continuity results: no beep between supply rails, beep from
red rail to U1 pin 8, and beep from blue rail to U1 pin 4. These are operator
reports, not a new photograph or host-acquired measurement. No numerical
rail resistance was supplied; a silent continuity buzzer alone does not
establish the complete circuit's readiness for power.

One probe-access jumper was added to each rail; their hole positions were
not specified. Do not assume rail hole 1 remains vacant. Leave the exposed
probe-access ends separated. Arduino is not yet requested to be connected
to the new fixture. Rail blue is Arduino GND (0 V), not buffered REF.

## Pull-down and amplifier 2 termination — installation reported

Keep USB disconnected. Measure a separate 1 kΩ resistor out of circuit
and record the meter reading, then make these four connections:

| Item | First end | Second end | Purpose |
| --- | --- | --- | --- |
| 1 kΩ resistor | I10 | I16 | REF output pull-down resistor |
| Insulated jumper | H16 | H13 | Pull-down return to U1 pin 4 / board 0 V |
| Insulated jumper | B11 | B12 | Amplifier 2 output (pin 7) to inverting input (pin 6) |
| Temporary insulated jumper | A9 | A13 | Divider tap to amplifier 2 non-inverting input (pin 5) |

I10 is the same lower-strip node as F10 (REF output). I16 connects to H16;
H13 is the same lower-strip node as F13 (board 0 V). This avoids occupied
H12 and J13. Amplifier 2 is temporarily a follower of the divider voltage;
remove the A9–A13 jumper before connecting a DAC signal to its input.

2026-10-28: The operator reports the separate pull-down resistor reading
as 1.001 kΩ on the 2 kΩ range, and 1.00 on the 20 kΩ range. Retain the
1.001 kΩ displayed value without implying that display resolution is meter
accuracy. The operator also reports the capacitor marking as `104J100`
(0.1 µF, ±5%, 100 V), consistent with the ordered film bypass capacitor.
This identifies its nominal rating; capacitance was not reported measured.
The operator subsequently reports all four connections complete and supplies
two photographs of the assembled circuit. Visible component locations are
consistent with the intended arrangement; some insertion points are hidden
by jumper housings and the capacitor. This does not substitute for the
pre-power electrical checks below.

## Supply bypass capacitor — installation reported and photos received

After the pull-down and amplifier 2 connections, with USB still disconnected,
place the 0.1 µF film capacitor between D10 and G13. D10 shares the upper
strip's column 10 with U1 pin 8 (+supply); G13 shares the lower strip's
column 13 with U1 pin 4 (board 0 V). The part is nonpolarized. This is a
supply bypass, not a capacitor from REF output to board GND.

The leads must clear the IC and other exposed conductors. Do not force
the lead spacing or pull at the capacitor body to span the trench. If the
part cannot reach comfortably, obtain a photo and choose an adjacent
mounting position with a short connection instead. Request a full wiring
photo and confirmation of the preceding four connections before power.
The operator reports completion and supplies two photographs showing the
marked film capacitor across the IC, consistent with the requested supply
bypass route. The lower exposed lead passes close to the lower IC pins;
clearance/contact cannot be established conclusively from the photos.
Request an unpowered visual clearance check without forcing or pulling the
leads. No Arduino supply connection or USB power-on has been requested yet.

## Final unpowered continuity checks — operator confirms completion

Keep USB disconnected. The earlier supply checks preceded installation of
the capacitor and pull-down. Request these four checks on the assembled
circuit, using the upper printed column numbers for both terminal strips:

| Probe pair | Expected observation | Purpose |
| --- | --- | --- |
| Upper-left red rail to upper-left blue rail | No sustained beep; a brief charging indication is possible | Check for a newly introduced supply short |
| J10 to J11 | Beep / direct connection | REF amplifier negative feedback |
| A11 to A12 | Beep / direct connection | Amplifier 2 negative feedback |
| G16 to upper-left blue rail | Beep / direct connection | Pull-down return to board 0 V |

All listed terminal holes are unused in the connection plan. In addition,
have the operator verify that the exposed capacitor leads do not touch any
unintended IC pin or other exposed conductor. Do not infer that supply-rail
silence proves every possible wiring error absent. Record the reported
results before proceeding to Arduino 5 V/GND connections and first DC
voltage measurements.

2026-10-28: In response to the four checks and the capacitor-lead clearance
check, the operator replied that all were checked. Record this as operator
confirmation of the requested pass conditions, not numerical resistance
measurements or an independently observed clearance test.

## First powered REF DC check — operator readings received

With USB still unplugged, remove the previous loopback connections from
the Arduino headers (A0 and A1–A4, and any remaining old test jumpers).
The new fixture is to connect to Arduino through ONLY these two wires:

| Arduino pin label | Destination |
| --- | --- |
| 5V | Vacant hole in the upper-left red rail, first group of five |
| GND | Vacant hole in the upper-left blue rail, first group of five |

Existing probe-access jumpers may occupy some rail holes; use vacant holes
without displacing the fixture connections. Leave analog pins disconnected
from the fixture for this initial DC check. With power still off, add
separate probe-access jumpers at J12 (divider tap, U1 pin 3) and J10
(buffered REF output, U1 pin 1). Keep their exposed ends separated.

Change the meter from continuity/resistance to DC 20 V before applying
power. Black lead stays in COM and red in VΩ. Use the previously stable
USB cable and Mac port to supply the board. No serial command, firmware
upload, or DAC stimulus is needed for this check.

With the black probe on the upper-left blue rail, request these readings:

| Red probe location | Expected DC behavior |
| --- | --- |
| Upper-left red rail | Supply voltage; previously 4.90 V, remeasure now |
| J12 probe-access jumper | Approximately 0.333779 times the measured supply |
| J10 probe-access jumper | Close to J12 voltage (approximately 1.64 V if supply is 4.90 V) |

If REF differs from the divider reading by more than 0.10 V, disconnect
USB and report the readings for diagnosis. This is only an initial gross
DC fault check, not a calibrated offset limit or a D2 acceptance threshold.
2026-10-28: The operator reports the requested readings in order:

| Location | Reported DC voltage |
| --- | --- |
| Upper-left red rail relative to blue | 4.88 V |
| J12, divider input to REF amplifier | 1.62 V |
| J10, buffered REF output | 1.62 V |

At the measured 4.88 V supply, the earlier resistor readings predict an
unloaded divider voltage of 1.62884 V. The approximately 8.8 mV difference
from the displayed divider reading is within one 0.01 V display increment;
neither the DMM accuracy nor resistance uncertainties have been calibrated.
The identical 1.62 V displays do not establish a zero amplifier offset.
The REF output is already loaded by the reported 1.001 kΩ pull-down, so
its inferred DC pull-down current is approximately 1.62 mA. This is an
initial DC follower check only, not evidence of dynamic stability, output
sink behavior, full signal-range operation, or completed D2 calibration.
No DAC stimulus or host ADC capture was used for this check. The latest
reported measurements imply the fixture was powered; unplug USB before
the following wiring changes.

## Configure amplifier 2 as DAC driver — operator reports completion

First unplug USB. Leave the REF amplifier, its 1.001 kΩ resistor, supply
bypass capacitor and existing power-rail wiring intact. Measure a DIFFERENT
nominal 1 kΩ resistor out of circuit on the 2 kΩ meter range, then:

| Action / part | Endpoints | Purpose |
| --- | --- | --- |
| Remove the entire temporary jumper | A9–A13 | Separate the divider from the driver input before attaching DAC |
| Insulated jumper | Arduino A0 → A13 | DAC to U1 pin 5, amplifier 2 non-inverting input |
| New 1 kΩ resistor | D11–D16 | Driver output (pin 7) pull-down to board 0 V |
| Probe-access jumper | B13 | Driver input / actual A0 voltage |
| Probe-access jumper | A11 | Driver output voltage |

D16 is already on the upper-strip board-GND node through A16. D11 and
A11 share the output node with E11 (pin 7). Retain B11–B12 negative
feedback. B13 and A13 share the input node with E13 (pin 5). The exposed
probe-access ends must remain separated. No DUT or ADC input is connected
to the new fixture at this stage. The driver pull-down starts at 1 kΩ;
the planned comparison with 2.2 kΩ remains pending.

2026-10-28: The operator reports the new resistor as 0.999 on the 2 kΩ
range (0.999 kΩ), 1.00 on the 20 kΩ range, and reports the wiring step
complete. No new wiring photograph accompanied that report. Treat the
connection confirmation as an operator report, not a visual inspection.
The host did not enumerate a USB serial device at the initial check after
this report, consistent with the instruction to leave USB unplugged; that
alone cannot distinguish an unplugged board from a USB enumeration fault.

Do not start a DAC command until USB reconnection is confirmed. The
currently installed dac_loopback sketch leaves A0 high impedance on boot;
it does NOT guarantee a defined driver output before a HOLD command.
Any initial driver tests must therefore remain DUT-free. No sweep,
firmware upload, power-on, or DAC stimulus is requested in this wiring step.

The subsequent request is to set the meter to DC 20 V and reconnect USB
using the previously stable cable and Mac port, then report completion.
After that report, first verify the firmware with PING, request only
HOLD 600, and verify the reported held state. Do NOT call the bare-board
acquire_point helper: it requests CAPTURE of A1–A4, which are disconnected
in this fixture stage. This step is a DMM-only driver DC check; keep its
records separate from the earlier DAC-to-ADC loopback measurements.

## First driver DC point — DMM pair received; later USB absence observed

2026-10-28: The operator confirmed USB reconnection. The host enumerated
the UNO R4 WiFi serial device and verified the installed
`benchmate-dac-loopback-v1` protocol. Initial PING reported DAC disabled
with code 0. The host issued only `HOLD 600` (12-bit DAC code 501), then
verified two PING responses at that same state, separated by 5 seconds.
No ADC CAPTURE command was sent. The DAC remains driven after serial close.

- Successful control record:
  `runs/hardware-fixture-dc/20261028T132604-d3154d67e3/events.jsonl`.
- An earlier host-sandbox attempt could not open the serial device and
  issued no HOLD. It is retained separately at
  `runs/hardware-fixture-dc/20261028T132515-ae1ebd18bc/events.jsonl`.
  This was an OS permission failure, not evidence of a USB disconnect.
- The installed firmware has no boot ID. These short state checks do not
  validate the pending instrument-v2 reset-detection mechanism.

The operator reports B13 = 0.59 V and A11 = 0.59 V relative to the
upper-left blue rail. The separate operator record is
`runs/hardware-fixture-dc/20261028T132604-d3154d67e3/operator-summary.json`.
This is a DMM DC follower observation under the 0.999 kΩ pull-down; equal
displays do not establish zero offset. The control event chain is unchanged.

Before any next-level command, the board was absent from the host USB
device tree and both normal and elevated serial-device inventories. Four
additional inventories over approximately 15 seconds also found no USB
serial board. No 1.6 V HOLD command was sent. Observation record:
`runs/hardware-fixture-dc/20261028T133159-dc0ed7a315/events.jsonl`.

While the host could not see USB, the operator reported no cable/USB
manipulation after the measurement, power LED still on, and B13 still
0.59 V. Power/A0 persistence and USB absence are recorded separately; do
not infer a whole-board reset, a proven cable fault, or uninterrupted
communication during the manual readings. The firmware has no boot ID.

The operator then confirmed replacing only the USB cable with a spare
data cable, retaining the Mac port and fixture wiring as instructed.
This also power-cycled the board, so subsequent recovery would not by
itself isolate the cable as the cause. The board re-enumerated with the
same USB identity. Both operator reports are retained at
`runs/hardware-fixture-dc/20261028T133159-dc0ed7a315/operator-summary.json`.
The next check repeats the FIRST 600 mV nominal point after open/close
tests, before advancing to a new level.

## Spare-cable first-point repeat — DMM received; USB absence recurred

Control record: `runs/hardware-fixture-dc/20261028T133855-2170af3217/events.jsonl`.
Over 40.037 seconds, three open/PING/close cycles reported the initial DAC
disabled state and retained USB enumeration. The host then issued only
`HOLD 600` (code 501), checked its state, closed serial, observed USB
presence during a 15-second idle interval, reopened and verified the same
held state, and checked USB presence again 5 seconds after closing.
No ADC capture or 1.6 V command was issued. Output remains driven.

This is a short successful check with the spare cable, not proof of a
permanent fix or identification of the failed component. The requested
manual readings are now supply (upper-left red rail), B13 input and A11
output, all relative to the blue rail, because changing the cable may
also change supply voltage.

The operator reports supply = 4.88 V, B13 = 0.59 V, A11 = 0.59 V.
These readings are stored separately in that run's `operator-summary.json`.
Before a 1.6 V command, the board was again absent from both normal and
elevated serial-device inventories and from the USB device tree. No
`HOLD 1600` was sent. The short 40-second check did not establish sustained
USB reliability. A read-only inspection of host power/sleep records did
not find a sleep/wake event matching this loss; no power settings were
changed and the failure cause remains undetermined.

## Next requested comparison — spare board, USB only

The parts list identifies the spare as an R4 Minima compatible board.
The operator was asked to unplug USB from the original R4 WiFi while
leaving its 5 V/GND/A0 fixture wiring attached. The spare is to have NO
jumpers or external circuit, and to connect by USB only using the same
Mac port and spare cable. Identification and a minimal bring-up PING test
come before transferring the fixture or issuing any DAC command.

Connection of the spare has not yet been confirmed. Its model must be
checked from enumeration/operator confirmation before upload. The
bring-up sketch is being compiled for `arduino:renesas_uno:minima`;
compilation is not evidence of upload or physical operation. Any later
board change requires new supply/REF and ADC/DAC checks; original-board
measurements must not be presented as calibration of the spare board.

## Review before spare-board comparison — kernel USB evidence

The operator requested a review of existing connection, reboot and host-load
evidence before proceeding with the spare, noting a concurrent local
research workload. The spare-board step is held during this review; no
spare-board connection or upload has been confirmed. Its bring-up compile
completed (40,208 B flash, 5,512 B static RAM), but it has not been uploaded.

Read-only macOS unified-log inspection found the following events on
2026-10-28, Asia/Seoul:

| Time | Recorded event for UNO WiFi R4 CMSIS-DAP |
| --- | --- |
| 22:28:02.363 | USB transaction errors begin (0xe00002ed) |
| 22:28:02.965 | Host terminates the USB device; log labels this `reset API call` |
| 22:41:41.904 | USB transaction errors recur with the spare cable |
| 22:41:42.504 | Host again terminates the USB device |

The host USB-reset label does not establish a reset of the RA4M1 MCU.
These errors/device-removal events are more specific than a Python
response timeout. They do not identify which board component, cable,
host controller/driver, power transient or other condition caused them.
The separate 22:25:15 sandbox serial-open denial was an OS permission
failure resolved before any HOLD; do not conflate it with these removals.

The running `dac_loopback-v1` sketch has no boot ID or uptime field.
Those fields exist in instrument v2, which has not been uploaded. Thus
there is no before/after boot-ID evidence for these incidents. A lit power
LED and the operator's persistent 0.59 V A0 reading are useful evidence,
but do not rule out a transient or a fault confined to the USB bridge.

No historical CPU-percentage or swap-rate series was collected at the
incident times. A CURRENT sample at 22:55:48–22:55:58 showed 84.92% CPU
idle on its second sample, 2,173.19 MiB swap used, and zero additional
swap-in or swap-out pages during the 10-second observation. These numbers
cannot be backdated to the incidents. The targeted historical log query
returned idle-exit memory-management events, but no explicit `memory
pressure` matches; that absence is not proof of no earlier memory pressure.

Review artifacts (local/ignored, including restricted host diagnostics):
`runs/hardware-usb-review/review-2026-10-28.json` and
`runs/hardware-usb-review/usb-key-events-2026-10-28.txt`.
No research process, OS setting, board output or installed firmware was
changed during this review. The original board's current USB device
remains absent; no 1.6 V command has been sent.

## Hands-off comparison before a board change — 10-minute window completed

The operator proposed testing the original fixture without touching it,
then comparing ordinary DMM probing under the same conditions. The operator
confirmed the original R4 WiFi was reconnected with its 5 V/GND/A0 fixture
wiring unchanged and hands removed. The spare board remains untested.

Record: `runs/hardware-usb-review/20261028T141232-5e47c051c9`.
The 600-second observation window began at 23:12:35 Asia/Seoul on
2026-10-28, with planned end 23:22:35. Before the window, the host verified
the old firmware, issued only `HOLD 600` and checked code 501, then CLOSED
the serial port. No periodic PING is sent during the window, preserving
the serial-idle condition of the earlier manual readings. Cached USB
enumeration and CPU tick deltas are sampled approximately once per second;
VM counters and swap usage are sampled every 15 seconds. Sample gaps are
recorded so host scheduling delays are distinguishable from an observed
absent USB device. No process or OS power setting is changed.

The operator was asked to leave the board, cable, breadboard and probes
untouched until the end signal. This is an operator-controlled condition,
not something independently observed by the software. Existing firmware
is retained for this comparison; its missing boot ID remains a limitation.
Any USB disappearance ends the run without automatic reconnect/rearm and
triggers capture of matching kernel USB logs. The observer source is
copied into the run directory separately from the live event chain.

A passing interval would not prove a handling-related cause, and failure
without handling would not by itself prove a defective board. Ordinary
probing needs a monitored comparison with operator-reported start/end
markers; software receipt times are not exact physical contact timestamps.
The earlier host-load hypothesis also remains unproven, rather than
categorically ruled out. Do not describe the earlier USB removals as
automatic reconnection: recovery was only observed after manual USB
reconnection.

The requested window completed at 23:22:35. All 601 approximately one-second
enumeration samples found the expected board; the maximum observed sample
gap was 1.009975 seconds. A post-window PING verified the same code 501
held state. There was no automatic reconnect or rearm. Source, event chain,
matching USB kernel log and `observation-summary.json` are retained in the
run directory. The operator subsequently confirmed no physical handling
throughout the full interval and readiness for a monitored ordinary-probing
comparison. This confirmation is saved separately in `operator-summary.json`;
the earlier analysis file retains its then-pending confirmation status.
The observation does not establish handling as the cause of previous loss.

## Ordinary-probing comparison — 10-minute window completed

Record: `runs/hardware-usb-review/20261028T142807-1cebd19533`.
The window ran from 23:28:10 to 23:38:10 Asia/Seoul on 2026-10-28.
The original board, spare data cable, Mac port, fixture and firmware were
retained. No USB reconnection or reset was requested between the two
phases. Before starting, PING verified the retained nominal 600 mV/code 501
state; the same HOLD was issued and verified, then serial was closed.
The observer used the same approximately one-second enumeration/CPU and
15-second VM sampling, with no periodic serial PING during the window.

After recording started, the operator was instructed to probe normally:
DC 20 V, black at the upper-left blue GND rail, red at the supply rail,
B13 DAC input and A11 driver output. Deliberate cable movement and
USB/RESET manipulation were excluded. The reported readings remained
4.88 V / 0.59 V / 0.59 V. No transient excursion was reported. The operator
was then asked to leave the probes and fixture untouched for the remainder.
Instruction and report sidecars are saved; their timestamps are not exact
physical contact start/end times, and handling was not independently observed.

All 601 samples found the expected USB device. The maximum sampling gap
was 1.005010 seconds, weighted mean CPU busy was 7.02%, and the 41 VM
samples showed zero swap-in/out page increments. The matching USB kernel
log contained no transaction-error or device-termination lines. A final
PING verified code 501 without rearming. The event hash chain was checked;
source, kernel log and analysis are retained alongside the operator report.

Both conditions passed once. A handling-related disconnect was NOT
reproduced, and neither the original fault's cause nor its resolution is
established. The old firmware still provides no boot ID. Resume the
supervised driver DC check while preserving this limitation; do not claim
that either the spare cable or the original board is now proven reliable.

## Second driver DC point — nominal 1.6 V, DMM readings received

After both ten-minute windows completed, the host resumed the driver check
without a wiring, firmware, cable or board change. Record:
`runs/hardware-fixture-dc/20261028T144003-6173753885`.
The initial PING had to match the retained nominal 600 mV/code 501 state;
only then was `HOLD 1600` sent. The old firmware ramps in bounded code
increments. The holding response and subsequent PING verified code 1337.
All 16 approximately one-second USB observations over 15 seconds found
the board with serial closed; reopening and PING verified the held state.
No ADC capture, reset, firmware upload or automatic recovery occurred.
The event hash chain was checked and controller source is saved in the run.

The operator reported `4.88 1.59 1.59`, interpreted in the established
supply / B13 DAC input / A11 driver output order. The raw report and
interpretation are retained in `operator-summary.json`. The measurement
reference is the upper-left blue Arduino GND rail, with the DMM on DC 20 V.
Both input and output display 1.59 V; this is a gross DC tracking check at
the meter's 0.01 V display resolution, not evidence of zero offset.
No transient excursion was mentioned. The nominal setting is not a
measured voltage or a calibration result. The brief post-command
observation does not establish long-term stability.

## Third driver DC point — nominal 2.6 V, DMM readings received

Record: `runs/hardware-fixture-dc/20261028T144904-7237239a5d`.
With the same physical setup, the host verified the retained nominal
1600 mV/code 1337 state before issuing `HOLD 2600`. The response and PING
verified code 2173. All 16 USB enumeration samples over the subsequent
15 seconds found the expected board while serial was closed. Reopening
and PING verified the same held state. The event hash chain was checked.
No ADC capture, reset, firmware change or automatic recovery occurred.

The operator reported `4.88 2.58 2.58(2.59 가끔 흔들려 둘다)`: supply
4.88 V; B13 input and A11 output each usually 2.58 V, occasionally 2.59 V.
The raw report and interpretation are saved in `operator-summary.json`.
Both nodes were probed relative to the upper-left blue Arduino GND rail,
using DC 20 V. The 0.01 V display changes are not a sampled noise estimate;
the two readings were separate and their fluctuations are not established
as simultaneous. Matching displays do not establish zero buffer offset.

A subsequent PING-only check found the expected USB device and retained
nominal 2600 mV/code 2173 state, with no capture or output command:
`runs/hardware-fixture-dc/20261028T145341-1421b0dcfc`. The event hash chain
was checked. This establishes a response at that check time, not uninterrupted
enumeration throughout the interval since the preceding command.

The three initial driver points are now recorded under the 0.999 kΩ
pull-down: input/output displays of 0.59/0.59, 1.59/1.59 and
2.58–2.59/2.58–2.59 V. This completes the gross DC follower check only.
Dynamic waveform quality, loaded source/sink behavior, the 2.2 kΩ
comparison and quantitative ADC/buffer calibration remain pending.

## U2 measurement buffers — unpowered placement requested, not confirmed

Next, unplug USB before any component placement or resistance measurement.
Leave U1 and its existing wiring intact. The latest PING showed A0 still
driven; do not treat serial closure as removing power. No further output
command or firmware upload is requested for this placement step.

Place a second LM358N across the central trench at columns 20–23, marking
up and notch LEFT, using the upper printed column numbers on both halves.
This follows the same top-view pin orientation as U1, checked against
[ST's package pin connections, page 4](https://www.st.com/resource/en/datasheet/lm358.pdf).

| Hole | U2 pin | Intended role |
| --- | --- | --- |
| E20 | 8 | Positive supply |
| E21 | 7 | Auxiliary measurement-buffer output |
| E22 | 6 | Auxiliary buffer inverting input |
| E23 | 5 | Auxiliary buffer non-inverting input |
| F20 | 1 | OUT measurement-buffer output |
| F21 | 2 | OUT buffer inverting input |
| F22 | 3 | OUT buffer non-inverting input |
| F23 | 4 | Board GND |

For this step, request only IC placement and a photo, plus preparation of
two additional 10 kΩ resistors measured separately out of circuit on the
20 kΩ range, and one additional 104J100 0.1 µF capacitor. Do not connect
U2 supplies, signal jumpers or ADC inputs yet. Do not reconnect USB until
the later wiring and unpowered checks are complete. Installation, values,
placement photo and USB disconnection are all pending operator confirmation.

## Expanded U2 / ADC wiring instruction — requested, not installed

The operator requested all remaining connections in one hole-coordinate
table, including U2 supplies, feedback, pull-downs, bypass, jumpers and
Arduino A1–A4. The complete current instruction is
[U2 and A1–A4 wiring table](fixture-wiring-table.md). This supersedes the
prior placement-only limit for the next unpowered assembly step; it does
not record any of those new connections as installed or authorize a host
stimulus before the operator confirms wiring and power-on readiness.

The initial configuration uses a removable B28–B35 shunt bypass and
C35–C30 IN-to-OUT calibration jumper, with the auxiliary non-inverting
input parked at REF through B50–B23. A5 is not connected or acquired.
Reserved future DUT terminals are A35=IN, B30=OUT, C50=RET/REF.
Before a DUT is attached remove C35–C30; change the other removable
jumpers only for their explicitly labeled later functions.

A connectivity calculation using the confirmed U1 hole assignments found
no occupied-hole conflicts, supply short, shorted follower outputs,
bypassed ADC series resistor, or hidden bypass around the removable
shunt. Removing the calibration jumper separates IN and OUT. This is a
design check only; actual placement, resistance readings, unpowered
continuity checks, photo and USB disconnection remain unconfirmed.

## Session close — operator confirms assembly and continuity, values pending

On 2026-10-29 Asia/Seoul the operator reports completing the full U2 and
A1–A4 table and all requested continuity checks, but not the resistor
measurements, and asks to stop for the night. This supersedes the pending
installation/continuity status in the preceding instructions. It is an
operator report, not a new photo, measured resistor values or powered
host verification. No subsequent serial command or firmware upload is
performed during this record-publication step. USB disconnection for
overnight storage is instructed, not independently verified.

Next session: keep USB disconnected; confirm the two new 10 kΩ and four
ADC-series 1 kΩ resistor values, obtain an assembly photo, and check the
recorded connections. An in-circuit reading can include parallel paths;
lift one lead when necessary and restore its exact table position before
rechecking. Then perform U2 DC and protected ADC checks, upload/validate
instrument v2 and continue calibration. The current four-channel firmware
does not acquire A5. No D01/B5 hardware diagnosis has yet been demonstrated.

The [reviewed public bundle](../examples/hardware-fixture-bringup/README.md)
preserves ten original control/USB event chains, their operator sidecars,
available controller/observer sources and selected USB kernel evidence.
Local logs are not automatically published: unrelated host-process
diagnostics, credentials, holdout originals, private coursework PDFs and
unreviewed images are excluded. A separately timestamped session report
records the latest operator confirmation without backdating it or
rewriting older `pending` events.

## Follow-up resistance readings — in circuit, USB disconnected

On 2026-10-29 the operator supplied the following displays and explicitly
confirmed that USB was unplugged but all resistors remained installed.
Units are interpreted as kΩ from the established wiring context; no new
meter range or photograph was supplied.

| Location | Role | Nominal | Operator display |
| --- | --- | --- | --- |
| D35–G35 | A1 series | 1 kΩ | 0.996 kΩ |
| D40–G40 | A2 series | 1 kΩ | 0.996 kΩ |
| D45–G45 | A3 series | 1 kΩ | 0.999 kΩ |
| D50–G50 | A4 series | 1 kΩ | 0.994 kΩ |
| I20–I27 | OUT buffer pull-down | 10 kΩ | 9.98 kΩ |
| D21–D27 | Auxiliary buffer pull-down | 10 kΩ | 9.98 kΩ |

The reports and clarification are retained in the new operator record
`examples/hardware-fixture-bringup/operator/20261029T005333-1caa781976`,
copied unchanged from `runs/hardware-fixture-resistors/20261029T005333-1caa781976`.
The earlier session-close record is unchanged. These numbers are near
nominal but may include other circuit paths; they are not certified
individual resistor values, tolerance measurements or calibrated model
parameters. No hardware command or powered acquisition was performed
during this update. Photo review and powered U2/ADC checks remain pending.

## Additional continuity report and staged power-check instruction

On 2026-10-29 the user forwarded four additional checks described as
performed the preceding night: IN (column 35 upper resistor leg) to GND
silent; REF (column 50 upper leg) to GND silent; drive (column 45) to IN
beep; IN to U2 pin 3 beep. These are forwarded operator observations, not
host measurements. Buzzer silence does not prove isolation, and the set
does not independently establish the IC's physical orientation.

The next limited power check no longer requires a photograph: overlapping
wires may obscure hole placement, while the reported continuity checks
plus explicit operator inspection can support staged power verification.
The operator is instructed, with USB still disconnected, to verify U2
at E20–E23/F20–F23, marking up and notch LEFT, and capacitor-lead clearance.
Then retain jumpers 11/14/15, leave the DUT disconnected, set the DMM to
DC 20 V, and reconnect using the same cable/port. Request supply and J10
REF voltages relative to the upper-left blue GND rail. Orientation and
power-on completion are pending the operator's reply.

No DAC command, ADC capture or firmware upload was issued for this
instruction. The installed old loopback sketch leaves A0 high impedance
at boot, so an uncommanded drive/OUT voltage must not be interpreted as
a failed follower or a guaranteed 0 V output. Photo review remains useful
but is no longer an absolute prerequisite for this supply/REF check.
Quantitative resistor calibration remains separate from this step.

## U2 first power-on — orientation, supply and REF reported

The operator replied `확인했어 / 4.88V / 1.62V` to the staged power-check
instruction: orientation and capacitor-lead clearance checked, supply
4.88 V and buffered REF at J10 1.62 V, with the DMM on DC 20 V relative
to Arduino GND. These are operator reports; no assembly photo has been
supplied. They confirm supply/REF displays after the new wiring, not the
two U2 follower outputs or ADC performance.

The next authorized action is a single nominal 1.6 V hold, with no DUT,
the calibration bridge/shunt bypass retained, and A1–A4 connected through
their four series resistors. The new control helper records this changed
wiring and requires a fresh disabled DAC state before issuing HOLD. It
does not reuse the earlier helper's "no ADC leads" configuration, does
not capture ADC data, and does not upload new firmware. The old firmware
still lacks a boot ID. The auxiliary buffer input stays parked at REF.

Control record `runs/hardware-fixture-buffer/20261029T011147-9f245763af`
completed: fresh disabled state verified, `HOLD 1600` acknowledged at
code 1337, all 16 enumeration samples over 15 seconds present, and a
post-reopen PING verified the retained state. The event hash chain was
checked. This is a short command check, not proof of long-term USB
stability. A0 remains driven for the requested DMM readings: D35 (IN),
D40 (OUT-buffer output), D45 (driver), D50 (REF), and D21 (auxiliary
buffer output). The last location is the column-21 end of the upper
10 kΩ pull-down, not its column-27 ground end. All five readings are
relative to Arduino GND and are pending the operator's report.

## Midpoint DMM received; USB loss prevents first fixture ADC capture

The operator reports D35 / D40 / D45 / D50 / D21 as
`1.59 / 1.59 / 1.59 / 1.62~1.63 / 1.62~1.63` V. The first three are
IN, OUT-buffer output and driver; the last two are REF and the auxiliary
buffer output. These sequential DMM readings support gross follower
operation at this point, not zero offset, simultaneous tracking or
calibrated accuracy. The sidecar `operator-summary.json` in
`runs/hardware-fixture-buffer/20261029T011147-9f245763af` retains them.

Before the intended raw ADC capture, both normal and elevated serial
inventories and the elevated IOUSB tree lacked the original board.
The elevated check was at 10:16:52 Asia/Seoul on 2026-10-29. No serial
open, CAPTURE, HOLD or firmware upload followed the absence. Zero fixture
ADC samples were acquired. Kernel logs show transaction errors beginning
10:12:55.460 and device termination at 10:12:56.056, after the earlier
15-second post-HOLD check. This recurrence does not negate the two
previous passing ten-minute windows, but does prevent claiming a fix.
Probe-contact times and physical cause remain undetermined; the old
firmware supplies no boot-ID evidence.

The next instruction is to unplug only USB from the original WiFi board,
leaving its seven 5V/GND/A0/A1–A4 fixture leads attached, and connect the
spare Minima with USB ONLY on the same cable and Mac port. No fixture
transfer or spare upload has occurred. Identification/basic communication
comes first; any later reliability comparison must use the actual fixture
and ordinary measurement conditions, and replacement-board calibration
must be performed anew. A USB-only pass would not establish a board fault
or full fixture stability.

## Spare Minima identified; first upload fails before communication checks

The operator confirmed the spare is connected by USB only, leaving the
seven fixture leads on the unpowered original WiFi board. Host enumeration
and Arduino CLI both identify UNO R4 Minima (`arduino:renesas_uno:minima`),
VID/PID 2341:0069, serial `3612211F36323632E4B233334B572F52`, application
port `/dev/cu.usbmodem3101`. This is USB identification, not an authenticity
test or evidence that the original board is faulty.

The non-driving bring-up sketch was recompiled for Minima: 40,208 bytes
flash and 5,512 bytes static RAM. One upload attempt is retained in
`runs/hardware-minima-bringup/20261029T012150-1077040f71`, with source,
binary hash and full upload log. The tool reached the runtime DFU detach
request, then reported `Lost device after RESET?` (dfu-util exit 74,
Arduino CLI return code 1). The run stopped without retry. No successful
flash, PING cycle, idle interval or ADC/DAC test is claimed.

Afterward, the serial inventory and CLI target list were empty; IOUSB
showed a `Santiago DFU` entry marked `!registered, !matched`, but an
elevated `dfu-util --list` listed no accessible target. A tree label alone
does not prove a usable bootloader connection. This upload-time event
must not be conflated with the original WiFi's idle USB losses.

The operator is asked to keep the spare USB-only and double-press RESET
to request manual bootloader mode, then report completion and any L LED
behavior. This is based on Arduino's documented bootloader-entry/reset
procedure, not a bootloader erase/reflash. Confirmation is pending.
Before any subsequent attempt, inspect the current device mode/identity.
No fixture transfer has occurred; calibration cannot be reused across boards.

References: [Arduino reset procedure](https://support.arduino.cc/hc/en-us/articles/5779192727068-Reset-your-board)
and the local Renesas 1.6.0 Minima board definition (application 2341:0069,
bootloader 2341:0369, native DFU, no 1200-baud touch).

## Minima manual bootloader recovery and USB-only instrument v2 check

2026-10-29: The operator replied “했어” to the double-RESET instruction;
L LED behavior was not reported. `dfu-util` then found the expected
2341:0369 target with the previously identified serial number, including
its two alternate flash interfaces. The next bring-up upload succeeded.
Three open/PING/close cycles passed, followed by 61/61 USB-present samples
over 60 seconds with serial closed and a successful final PING. The failed
first upload remains in the record; there was no automatic recovery loop.

The existing instrument-v2 firmware was freshly compiled for Minima
(65,748 flash bytes; 15,920 static RAM bytes) and uploaded successfully
from application mode. Four PINGs over three open/close cycles plus the
post-observation check reported a valid hardware-generated boot ID,
`822b338fda3756061f3e46605a879dc0`, with uptime advancing from 3,447 to
42,509 ms. The 30-second serial-closed interval contained 31/31 successful
USB-presence samples. All PINGs reported `armed:false`. No ARM, CAPTURE
or STOP commands were sent, and no ADC block was acquired. The firmware
performs initial ADC reads during setup; these are not recorded measurement
blocks or calibration results.

This establishes basic USB-only operation and boot-ID generation on this
spare. A physical reset/power-cycle ID-change test, stale-ID command
rejection, interrupted acquisition and same-fixture operation remain
untested. The original WiFi USB fault remains unexplained.

Reviewed original bytes, firmware/controller snapshots, failed/successful
upload logs and hashes are in the [October 29 follow-up bundle](../examples/hardware-fixture-bringup/2026-10-29-followup/README.md).

Next physical instruction: unplug USB from both boards, move only the
seven board-side fixture connections to the matching printed Minima pin
names (5V, GND, A0, A1, A2, A3, A4), keeping breadboard ends and calibration
jumpers 11/14/15 unchanged. No DUT. Reconnect only Minima using the same
cable/Mac port and report supply and J10 REF relative to Arduino GND.
This transfer and replacement-board voltage readings are pending. No DAC
drive is authorized by a mere USB reconnection; explicit ARM follows
identity and operator voltage checks. Earlier WiFi calibration is not
applied to Minima.

## Minima fixture transfer, single RESET and stale-ID rejection

The operator reported “7개 이동 완료 / 4.88V / 1.62V”, following the
seven-lead transfer instruction. The first check received the previous
boot ID `822b338fda3756061f3e46605a879dc0` and uptime 309,620 ms.
No new boot was established. That attempt stopped before any ARM or
CAPTURE command; the recorded output state was unarmed. This is not
classified as a USB loss or a defective RNG. The exact transfer/power
sequence is not independently known.

After the operator explicitly reported “Minima RESET 한 번 완료”, PING
returned ID `f17b838790daf6d542844f859c0c3d32` and uptime 22,926 ms.
The host rejected this response when checked against the old ID. On the
board, well-formed ARM and HOLD-CAPTURE commands addressed to the old ID
both returned the boot-identity-mismatch error; fresh PINGs after each
still showed `armed:false`, `ref_code:0`. No samples were accepted.
This is a physical single-RESET/stale-command test, not an acquisition
interruption test or a verified full USB power-cycle experiment.

Only then was an ARM command sent with the new ID and the reported
4.88 V supply / 1.62 V REF. The reference code is 1359 and maximum
per-update change is 839 codes. The nominal voltage is a command
conversion, not a calibrated physical measurement. After ARM, 31/31
USB-presence samples over 30 seconds with serial closed and the reopened
PING confirmed the same ID and armed configuration. The output remains
at the requested reference code; no valid ADC capture has been requested.

The operator has been asked for D35/D40/D45/D50 voltages relative to
Arduino GND, with wiring unchanged. Those DMM reports are pending.
Long-duration fixture stability, calibration and interrupted acquisition
remain untested. Both the stopped initial identity check and the
successful RESET/ARM record are retained in the October 29 follow-up
bundle as `minima-transfer-precheck/` and `minima-reset-arm/`.

## First Minima block rejected; A4 voltage difference investigated

The operator confirmed Minima and reported D35/D40/D45/D50 as
1.61/1.61/1.61/1.62 V (DC 20 V, Arduino-GND reference). One HOLD capture
requested 512 four-channel frames at a 2,000 us period, bound to boot
`f17b838790daf6d542844f859c0c3d32`. The response contained 512 rows and
reported no timing overruns, but the sampling-state minimum was zero.
The host rejected the block and retained it; no automatic retry occurred.
These timing flags are diagnostic contents of a rejected packet, not a
completed calibrated timing validation or accepted acquisition.

Review found the firmware wrote/read all 16 dedicated sampling-state
slots, including unused/reserved ones. The correction touches only the
actual A1/A2/A3 channels 0/1/2 and A4 channel 21 via ADSSTRL. PING now
reports those states, and CAPTURE records them before/after acquisition.
The host requires explicit [0,1,2,21] mapping and four integer 255 values
at both checks. A native test leaves unused slots zero; corrupt/missing
active readback still fails. 46 related tests and both board compiles
passed. The revised firmware has not been uploaded; actual used-register
readbacks remain to be checked. The old rejected block is not reclassified.

The rejected block's uncorrected voltage estimates were approximately
1.616/1.615/1.617/2.156 V using the reported 4.88 V supply. A separate
operator DMM check then reported D50=1.62 V and G50=2.15 V, without a
firmware or stimulus change during the requested check. This indicates
a physical voltage difference across the A4 series resistor, independently
of the ADC-state-check bug. A simple +5 V pull-up model would imply about
5.12 kohm using the earlier in-circuit 0.994 kohm reading, but that is a
hypothesis, not confirmation of a board resistor or wiring cause.

The [official Minima schematic](https://docs.arduino.cc/resources/schematics/ABX00080-schematics.pdf)
marks R1/R2 I2C pullups not mounted. The compatible board's actual assembly
has not been established. The operator is asked to unplug USB, confirm
power off, check the H50 wire terminates at the printed A4 pin, remove
only that board-side end, then measure board A4-to-5V resistance in both
probe polarities at the 20 kohm range. Leave USB and that wire disconnected.
This resistance report is pending. No bypass, resistor replacement or
board modification has been requested.

The failed wrapper/capture and subsequent operator/software review are
retained in `minima-midpoint-attempt/`, `minima-midpoint-rejected/` and
`minima-a4-review/` in the October 29 public bundle. Archived old firmware
and host source hashes match the actual acquisition; new code does not
replace the source associated with that failed record.

## A4 board resistance report and fixed-REF sense revision

The operator reported A4 pin location confirmed and A4-to-5V resistance
5.19–5.20 kohm in both probe polarities (20 kohm range), following the
instruction to unplug USB and remove only the external A4 board-side lead.
This is a board in-circuit measurement, not identification of a particular
SMD resistor. Together with D50/G50=1.62/2.15 V, it strongly supports a
pull-up-like path. A 5.195 kohm pull-up and the earlier 0.994 kohm series
reading predict about 2.14 V on A4, consistent with the coarse DMM result.

The revised fixture replaces only D50–G50's series resistor with a short
jumper, then reconnects H50 to A4. A1–A3 series resistors and both existing
U1 pull-downs remain. This direct connection is restricted to sensing the
internal buffered REF; it is not an external-input protection policy.
At the previous 4.88/1.62 V readings, the inferred board path contributes
about 0.63 mA into REF. Its existing 1.001 kohm pull-down draws about
1.62 mA, leaving roughly 0.99 mA net source demand on the REF buffer at
idle with no DUT. These are design estimates, not dynamic-load verification.

The operator is asked to keep USB disconnected during replacement, check
D50–G50 continuity, reconnect A4, then reconnect USB and report supply,
D50 and G50 against Arduino GND. Confirmation is pending. The corrected
ADC-readback firmware remains compiled but not uploaded. After wiring
confirmation, recheck active-channel registers and REF DC/noise behavior;
no completed calibration is claimed.

The revised [connectivity checker](../examples/hardware-fixture-bringup/wiring-design/connectivity-check-a4-direct.py)
passes hole-occupancy, supply separation, three remaining series paths,
A4-to-buffered-REF continuity, output separation and removable calibration/
shunt connections. The original four-resistor checker remains historical.
This is a design check, not proof of physical assembly or stability.

## Corrected fixture, uploaded ADC fix and first three valid raw blocks

The operator reported “완료 / 4.86 / 1.63 / 1.63” after the requested
D50–G50 short jumper, A4 reconnection, continuity and supply/REF checks.
The two sides now display the same REF voltage on the DC 20 V range.
This resolves the previously visible approximately 0.53 V division at
that node; equal displays do not establish sub-resolution equality.

The first update attempt failed in the runtime DFU interface with
`Cannot set alternate interface zero: LIBUSB_ERROR_OTHER` (dfu exit 74).
The application serial identity remained listed, and the DFU query showed
runtime 2341:0069 with language-identifier warnings. This was an upload
mode problem, not evidence of another idle USB disappearance. That failed
attempt is preserved. After the operator reported “두번완료”, the expected
2341:0369 bootloader and Minima serial were accessible; manual-mode upload
succeeded. Four unarmed PINGs and 31/31 presence samples over 30 seconds
passed. PING now reads [255,255,255,255] for channels [0,1,2,21].

With no DUT attached, a new explicit ARM used the reported supply 4.86 V
and REF target 1.63 V: code 1373, boot ID
`7dd3b19411ed4ecda7e4f286c8ce45f5`. One HOLD block and two additional
same-condition blocks were recorded at 512 frames each and requested
period 2,000 us. The repeats were planned after observing larger tails in
the first block, not automatic recovery of a failed run. All three have
complete rows, unchanged boot ID, all four used ADC state registers at
255 before/after, no overruns, and frame intervals 1,999–2,003 us.

| Channel | Nominal mean across three blocks | Within-block sample SD range |
| --- | --- | --- |
| A1 | approximately 1.626 V | 2.40–2.84 mV |
| A2 | approximately 1.625 V | 1.73–2.07 mV |
| A3 | approximately 1.626 V | 1.90–2.50 mV |
| A4 | approximately 1.638–1.639 V | 1.28–1.34 mV |

These conversions use the reported 4.86 V and ideal ADC full scale, not
calibrated per-channel gain/offset. Read-completion offsets were about
52/105/158/216 us; these are not sampling apertures. Larger deviations
repeat: worst deviation from a block mean is about 24.4 mV on A1 and
9.9 mV on A4. No samples were trimmed. A single Gaussian or AR(1) noise
model is not declared calibrated from these blocks; further noise and
accuracy work remains. Three short passing blocks do not establish
long-duration USB reliability or the original WiFi fault's cause.

The current output stays at code 1373. The operator is asked to keep
USB/wiring unchanged, use DC voltage 2 V range, and report D35/D40/D45/D50
relative to Arduino GND to the available displayed precision. Those
readings are pending; no stimulus/firmware change is made during that
requested check. No multi-point calibration or DUT inference is complete.

The public follow-up retains both upload attempts, the exact firmware and
host used, the ARM record, all three raw blocks, and unfiltered descriptive
statistics. The first pre-fix rejected block remains rejected.

## Finer midpoint displays and subsequent handshake failure

The operator answered the DC 2 V range instruction with
`1.631/1.630 / 1.631/1.629이렇게고 1번칩 3번핀도 1.629`:

| Probe point | Operator display |
| --- | --- |
| D35, A1 source | 1.631 V |
| D40, A2 source | 1.630 V |
| D45, A3 source | 1.631 V |
| D50, buffered REF | 1.629 V |
| U1 pin 3, divider input | 1.629 V |

These are sequential displays relative to Arduino GND, with 1 mV display
resolution, not established 1 mV accuracy. Equal REF/divider displays do
not establish a zero amplifier offset. No one-point calibration was fitted.

At 11:28:39 KST, one same-setting HOLD capture was attempted to compare with
these displays. Its preflight found the expected Minima, but the initial
PING returned zero bytes before the 60-second read timeout. The host never
sent CAPTURE, ARM or STOP; the run was invalidated with zero accepted
samples. The requested CAPTURE string recorded in its configuration is
not evidence that the command was sent. No current ADC/DMM comparison
was computed, and the three earlier valid blocks remain separate.

A separate read-only diagnostic at 11:33 KST sent only one PING, again
receiving zero bytes within five seconds. The expected Minima serial port
and VID/PID were listed both before and after that check. No other process
holding the serial device was found in the preceding snapshot. This is
currently an enumerated-but-unresponsive observation, distinct from the
earlier WiFi disappearance. There was no continuous USB-presence monitor
over the intervening period, so a transient removal is not excluded. No
boot ID or uptime was returned; a reset, firmware stall or USB-path fault
cannot yet be distinguished. No automatic capture retry or re-arm occurred.

Before changing wiring or resetting, the next requested physical check is
DC 2 V at D50 and the board header explicitly labelled SDA, both relative
to the same GND. The [official Minima pinout](https://docs.arduino.cc/resources/pinouts/ABX00080-full-pinout.pdf)
identifies SDA and A4 as the same signal; the installed core also maps both
to pin 18. This checks for a lead/contact voltage drop between the
breadboard REF node and the board ADC node. The operator should report if
the label/contact is unclear rather than guess. The result is pending.
The earlier A4 ADC/DMM discrepancy is still unresolved; neither an ADC
offset nor a wiring drop is established from the available readings.

Exact operator report, failed handshake and separate diagnostic records
are retained in `precise-midpoint-attempt/`,
`precise-midpoint-handshake-failed/` and `minima-handshake-review/` in the
October 29 public follow-up bundle. No firmware or wiring changed during
these software checks.

## Operator USB reconnection and a new-boot midpoint block

The operator subsequently reported `D50 1.633V, SDA 1.633V` on DC 2 V,
relative to the same Arduino GND rail. At the displayed precision this
does not show a breadboard-to-board lead/contact voltage drop. The two
contacts were measured sequentially; no resistance bound or ADC offset
is inferred. Both readings also differ from the earlier 1.629 V display,
so they are not substituted into the earlier capture records.

At 14:46 KST a PING-only status check returned boot ID
`00577aec01ebd2245c7d99edcd14432b`, uptime 397490 ms, `armed:false` and
all four used ADC sampling states at 255. No output or reset command was
sent during that check. The user then confirmed `USB를 다시 연결했어`.
The exact reconnection time and whether DMM readings preceded/followed it
were not supplied. This report is consistent with the new boot; it does
not establish the cause of the earlier enumerated-but-unresponsive state.
The new session is not a continuation of the old boot's measurements.

With the existing no-DUT calibration wiring, an explicit new-ID ARM at
code 1373 was followed by one 512-frame HOLD block at 2000 us requested
intervals. Both operations and their post-PING checks passed. The uploaded
firmware source is unchanged. The conversion retains the earlier 4.86 V
supply value, pending a fresh DMM reading after reconnection.

| Channel | Mean raw counts | Nominal mean using earlier 4.86 V | Within-block SD |
| --- | --- | --- | --- |
| A1 | 5482.87 | 1.62649 V | 1.39 mV |
| A2 | 5477.43 | 1.62487 V | 2.08 mV |
| A3 | 5482.25 | 1.62630 V | 1.63 mV |
| A4 | 5479.18 | 1.62539 V | 1.45 mV |

Frame intervals were 1999–2003 us, with zero overruns and ADC state 255
on all four used channels before/after. The same new boot ID was verified
through both operations. All raw samples are retained; the largest
within-block deviation was approximately 17.33 mV on A2. No Gaussian
noise model, outlier removal or accuracy claim is applied.

A4 is approximately 3.07 counts below A3 in this block, whereas it was
about 40–45 counts above A3 in the previous boot's three blocks. The
previous difference was not reproduced, but its cause is unestablished.
The DMM readings and acquisitions were not simultaneous and do not
support a cross-boot offset correction. The output is now parked at code
1373. Next requested check: supply on DC 20 V, then D45 and D50 on DC 2 V,
with USB, RESET and wiring unchanged. No multi-point calibration or
long-duration reliability claim follows from this short successful block.

See `minima-sda-check/`, `minima-reconnected-midpoint/`,
`minima-reconnected-arm/` and `minima-reconnected-block/` in the October 29
public evidence bundle for exact sources and raw records. Earlier failed
records remain unchanged.

## Fresh supply comparison and persistent DC calibration setup

The operator reported `4.89V / 1.636V / 1.633V` for supply (DC 20 V),
D45 and D50 (DC 2 V), respectively. Recomputing the preceding new-boot
block with 4.89 V rather than 4.86 V gives nominal A3=1.63634 V and
A4=1.63543 V. Their differences from the later DMM displays are +0.34 mV
and +2.43 mV. The original raw block and its original conversion remain
unchanged; this offline comparison has its own record. It assumes the
later supply display is representative of capture time. Sequential
measurements and unestablished meter accuracy preclude a millivolt accuracy
claim or a one-point ADC calibration fit.

The instrument gained a separate, boot-bound `DC` command so a human can
read a persistent calibration level with the DMM. CAPTURE HOLD continues
to return to REF after acquisition. DC uses the armed envelope, bounded
moves and A2 settling, reports its held code, and is checked by a subsequent
PING. The host requires advertised support before sending it; malformed,
stale-boot, unarmed and out-of-range requests do not change the output.
Settling/cancellation errors park at REF, while host communication ambiguity
is recorded without automatic retries or an assumed output state.

Seventy-one targeted tests cover real-sketch parsing with fake IO, host
reset/timeout/code-mismatch paths and CLI routing. Minima compiled to
66,476 B flash / 15,920 B static RAM; WiFi to 69,932 B / 18,356 B.
These are software checks, separate from the physical operation below.

The operator reported `Minima 두 번 완료` in response to manual DFU
instructions with wiring retained and no DUT. The identified Minima
bootloader accepted the checked binary. Four unarmed PINGs, 31/31 USB
presence samples over 30 seconds and all used ADC readbacks at 255 passed.
PING advertised DC support, with new boot ID
`cd496fa1aa18dcb15bae7d05553fe560`. No output command was sent by the
upload controller. The earlier preparation record's `uploaded:false`
remains historical; the subsequent upload record establishes completion.

With supply conversion 4.89 V and REF target 1.633 V, an explicit ARM
established code 1368. The first persistent DC target was 0.633 V; integer
envelope clamping produces code 531. The `dc_held` acknowledgement and
post-PING agreed on code 531 and the same boot. This confirms firmware
state, not the physical voltage. D35/D40/D45/D50 DC 2 V displays are now
requested; the first three are driven low, while A4 remains on fixed REF.
No ADC block or fit at this point is claimed. Varying A1–A3's driven level
does not calibrate A4's gain across a range.

The offline comparison, preparation, upload, explicit ARM and first held
point are retained separately in the October 29 bundle. Prior failures,
pending-at-the-time instructions and raw capture records are unchanged.

## First low-point report and accepted raw block

The DC 2 V displays at D35/D40/D45/D50 were reported as
`0.629V / 0.628V / 0.629V / 1.633V`. With the same boot ID, the initial
PING still reported held code 531. A 512-frame HOLD capture passed the
complete-block, timing, used-ADC-register and boot-continuity checks.
Intervals were 1998–2003 us, with zero overruns. No samples were trimmed.

| Channel | Mean raw counts | DMM display | Nominal ADC value using 4.89 V |
| --- | --- | --- | --- |
| A1 | 2110.25 | 0.629 V | 0.62987 V |
| A2 | 2112.81 | 0.628 V | 0.63063 V |
| A3 | 2114.90 | 0.629 V | 0.63125 V |
| A4, fixed REF | 5478.31 | 1.633 V | 1.63517 V |

Within-block SDs span approximately 1.40–2.85 mV and larger tails remain.
These are sequential comparisons, not calibrated error bounds. After the
capture returned to REF, a separate DC command and post-PING verified
midpoint code 1368 with the same boot. Fresh midpoint DMM readings are
pending; this new-boot sweep does not reuse a previous boot's midpoint.
The low-point report, source snapshots, raw block and next held level are
retained separately in `minima-dc-low-point/`, `minima-dc-low-block/` and
`minima-dc-mid-held/`. No three-point fit or A4 gain calibration is complete.

## Midpoint anomaly and reported power-rail probe contact

The operator reported `35/40/45가 3.28V로 포화됐어`, instead of the expected
midpoint near 1.63 V. D50 and the actual DMM range were not supplied. The
preceding instruction was DC 2 V; the reported value is retained without
inventing a range or treating "saturation" as an established diagnosis.
The calibration sequence stopped before a midpoint capture or high-level
command. The last acknowledged code 1368 is a historical software state,
not confirmation of the current physical voltage.

At 15:19:43 KST the controller sent only one PING. Zero bytes arrived in
five seconds, although the Minima serial identity was listed before and
after. A later kernel-log review of 15:09:00–15:20:30 KST found:

- 15:14:47.964: Minima `hardware connection lost`.
- 15:14:49.340: the same product/VID/PID was enumerated again.
- Repeated device transaction errors followed, including during the failed
  PING window. Port-list snapshots therefore did not establish uninterrupted
  USB presence.

The operator then stated that the red and blue rail probe posts touched
while probing, and separately reported `USB·RESET 모두 건드리지 않았어`.
The posts belong to +5 V and Arduino GND, so contact can short the supply.
This is a plausible explanation for the disturbance, but contact time and
duration were not supplied. A main-MCU restart, DAC state, permanent damage
or a cause for all earlier communication faults is not established.

The powered voltage-reading request was withdrawn. The next instruction
is to unplug USB, wait for the power LED to go out, remove only the two
extra rail probe posts, then check for persistent continuity between the
unpowered red and blue rails. Arduino 5 V/GND supply leads and fixture
wiring stay installed. USB must remain disconnected pending the result.
Completion has not yet been reported. Before powered measurements resume,
the probe arrangement must prevent the bare +5 V and GND ends from touching.

No further output command, ADC capture, firmware upload or automatic
recovery was performed. The prior low-point block is retained separately;
the 3.28 V report is not accepted as a calibration point. Exact operator
reports and the failed PING are in `minima-midpoint-anomaly/` and
`minima-probe-contact/`. Only selected Minima-specific timestamp/message
excerpts and the full local log's hash are published, not the broad kernel
log or unrelated device messages.

## Confirmed power-off check and revised probe access request

After an initially ambiguous `해결했어`, the operator explicitly confirmed
`USB 분리·기둥 제거 완료, 지속 통전음 없음`. This records USB disconnected,
the two added rail probe posts removed, and no persistent tone between the
unpowered supply rails. A brief initial tone versus silence from the start
was not distinguished. This check does not establish that every component
is undamaged or that powered operation has recovered.

The next requested arrangement has only one added ground probe, at J27
(bottom J row, column 27 using the top numbering). The recorded wiring
graph shows J27 is unoccupied and connected through H27/H23/J23 to Arduino
GND. The operator must verify J27-to-blue-rail continuity with USB off.
Power voltage is then read by touching the existing A3-side lead of the
first divider resistor, which is connected to +5 V; no second part is
inserted into occupied A3 and no loose +5 V probe post is added. REF is
read at existing J10. The black probe stays at the secured J27 ground
contact. The meter switches to DC 20 V before USB is reconnected.

The coordinate check is a design check, not confirmation of installation.
The single ground-probe placement, continuity and fresh power/REF values
are pending. No ARM, capture, reset or upload is performed while waiting.
After reconnecting, the boot identity and output state must be established
again; the old midpoint setting must not be assumed to survive.
See `minima-unpowered-check/` for the clarification and coordinate-check
provenance. Prior anomaly records remain unchanged.

## Actual probe arrangement and recovery after single RESET

The operator clarified `파랑 레일 기둥은 그대로 사용중이라 괜찮아.
빨강 레일 기둥 제거 완료 / 4.88V / 1.63V`. The actual arrangement retains
the original blue-rail GND probe and removes only the red +5 V probe post.
J27 was proposed, not installed; the earlier generic report of removing
both posts is superseded by this specific clarification. Fresh supply/REF
displays are 4.88/1.63 V on the instructed DC 20 V range.

A new status check found the expected Minima USB identity but received
no PING response within five seconds. No ARM or capture followed that
failed attempt. USB/power restoration therefore had not by itself
established communication recovery.

The operator subsequently confirmed `RESET 한 번 완료`, with USB and
wiring retained. Two reopened PING checks returned a new boot ID
`c7992fcbd2cba35e53aa1b2d805b84e4`, unarmed state, current/ref codes zero,
DC capability and all four active ADC states at 255. Only after these
checks did an explicit ARM use the fresh 4.88 V supply conversion and
1.63 V target. Its post-PING confirmed code 1368 and the same boot.
No firmware was changed or uploaded, and no ADC block or higher voltage
was requested. This verifies short-term communication and command state,
not physical output accuracy or complete recovery from damage.

The next requested check is B13 (DAC/input), A11 (driver output), D50
(REF), on DC 20 V relative to the retained original blue-rail GND post.
The red +5 V post stays absent. Those physical voltage results are pending;
the original three-point sweep remains incomplete and is not silently
continued across the power interruption. Both the failed reconnect check
and the successful post-RESET check are retained in
`minima-contact-power-recovery-failed/`, `minima-contact-reset-recovery/`
and `minima-contact-recovery-arm/`.

## Driver voltage mismatch after communication recovery

The operator's subsequent B13/A11/D50 report is `1.62V /  3.4V / 1.64V`,
following the DC 20 V instruction with the retained blue-rail GND reference.
These sequential readings do not show a recovered voltage follower:
B13 is the requested DAC input node, but the U1 driver output at A11 is
substantially higher. No fresh supply reading was supplied in this report.
The report is retained as fault evidence, not accepted for calibration.

The next instruction is to disconnect Minima USB, confirm the power LED
is off, retain the absent red +5 V probe post, and leave all other wires
and ICs in place. This power-off confirmation is pending. U1's input and
negative-feedback contacts will then be checked unpowered, including
contact at the actual package legs. A loose path, IC fault or other
electrical cause has not yet been distinguished. No serial, stimulus,
capture or firmware command was sent for this report. See
`minima-driver-voltage-mismatch/` in the evidence bundle. The earlier
successful PING and ARM remain evidence of communication and command
state only; they do not establish correct physical output.

## Actual voltage contacts and limited feedback continuity confirmation

The operator clarified that B13 and A11 probe posts had been removed the
previous night. The prior 1.62 V and 3.4 V displays were measured directly
on U1 package pins 5 and 7, respectively, rather than on those posts.
The earlier raw report retains the requested node labels; this subsequent
clarification records the actual probe contacts without rewriting it.
There are no new powered voltage readings in this clarification.

USB disconnected and power LED off are now explicitly confirmed. The
operator skipped the two post-to-pin checks and reported a beep between
B12 and D11. This establishes reported continuity between the breadboard
feedback nodes but does not verify the actual pin 6 contact. The inference
that the chip is latched is not established. The next request is one
unpowered continuity check directly between U1 metal pins 6 (E12) and 7
(E11), avoiding contact between the probe tips, or a report that access is
too difficult. No wires or ICs are to be moved; USB remains disconnected.
No hardware command was sent. See `minima-driver-contact-clarification/`.

## Direct feedback-pin check passed; power reapplication requested

The operator answered `삐 소리 났어` to the unpowered continuity request
between actual U1 metal pins 6 (E12) and 7 (E11). This completes the
requested direct feedback-contact check; no numeric resistance was given.
It does not establish powered operation or a latched/damaged IC.
With wiring and chips unchanged, the next request is DC 20 V mode,
same-cable/port USB reconnection, then fresh supply (existing divider
resistor A3-side lead) and REF (D50) readings relative to the retained
blue-rail GND post. The red +5 V post stays removed. No DAC command is
sent until this report and a new boot/status check. Reconnection and
new voltage readings are pending. See `minima-driver-pin-feedback/`.

## Power reapplication: new boot and REF command verified

After the direct feedback check, the operator reported
`연결완료 / 4.86V / 1.62V`. The instruction used DC 20 V, the retained
blue-rail GND post, the existing divider resistor A3-side supply lead,
and D50 REF; wiring and ICs were to remain unchanged. The power-off
duration was not measured.

The identified Minima answered PING with new boot
`b4ab5f3bf78ec9374ac381996885027b`, unarmed state, current/ref code zero,
DC capability and all four active ADC states at 255. An explicit ARM
then used supply conversion 4.86 V and target 1.62 V (code 1365, maximum
jump 842). Its pre/post checks kept the same boot, and the postcheck
confirmed the target code. No firmware upload, ADC block, high point,
automatic retry or wiring change occurred.

This confirms the command state only. The next requested sequential DMM
readings are the actual U1 metal pins 5 (E13), 6 (E12), 7 (E11), then D50,
on DC 20 V relative to the retained GND post. Those values are pending;
the output and firmware remain unchanged during the operator check.
Physical driver recovery and the cause of the earlier 3.4 V remain
unestablished. Exact controller/host snapshots and the separate ARM record
are in `minima-driver-power-reapplication/` and
`minima-driver-power-reapplication-arm/`.

## Physical midpoint recovery; subsequent USB failure before low command

The operator reported `4개 다 1.62V` for actual U1 pins 5/6/7 and D50 on
the instructed DC 20 V range. This establishes follower agreement at the
displayed resolution after power reapplication; it does not prove a latch
mechanism, precise offset accuracy, or performance across the full range.

Before changing to a low target, the controller sent only PING. No bytes
arrived within five seconds. No DC, ARM or capture command followed, so
the attempted 0.62 V setting was not issued. The Minima port remained
listed at 16:34:52 KST. A kernel query limited to named Minima messages
over 16:20:00–16:35:00 found 9,180 transaction errors on endpoint 0x81,
first at 16:27:41.650. It contained no named connection-loss or enumeration
messages. The filtered pmset review found no matching Sleep/Wake events
in the same window. Neither review establishes a unique host, firmware,
cable, board or probing cause. Selected kernel excerpts and a hash of
the raw local log are retained; the full log is not published.

See `minima-recovered-midpoint-low-attempt/` for the physical recovery
report and failed status check, and `minima-recovered-usb-review/` for
the review and prepared comparison controller. No firmware change or
automatic recovery was made. The prior software state cannot by itself
establish current physical voltage after the failed PING.

## Single-connection comparison started after confirmed RESET

The operator confirmed `RESET 한 번 완료, 손 뗐음`. New unarmed boot
`e522aadc799575eae297808f4df573c8` was verified, then explicit REF ARM
set code 1365 using the latest 4.86/1.62 V supply/REF report. The controller
keeps one serial connection open and checks PING every two seconds for
600 seconds, holding the same DAC code. Its first checked held state was
16:45:59.503 KST; nominal end is 16:55:59 KST. No ADC block, firmware or
wiring change is part of this comparison, and any error stops the run
without retry or re-arm. The operator was instructed to avoid touching
the board, cable and probes; completion and final no-touch confirmation
are pending. Continuous-open plus periodic traffic differs from the
previous closed-port wait; success would not isolate a single cause.

## Continuous-connection result and same-level DC preparation

The comparison completed in 600.011 s with 300 successful PINGs, one boot
`e522aadc799575eae297808f4df573c8` and code 1365 throughout. The port closed
after the final check. The Minima-only kernel query for 16:45:59–16:55:59
KST returned no messages. Its summary/hash is a post-run sidecar, not a
change to the event chain. Final operator no-touch confirmation is pending.
Success under continuous-open/periodic-traffic conditions does not prove
a unique cause for earlier failures or general long-duration stability.

The host then explicitly requested DC at the same 1.62 V target on that
boot; firmware settling and held-code postcheck passed. No ARM, firmware
upload or ADC block was added. See `minima-persistent-ref-watch/`,
`minima-post-watch-ref/` and `minima-post-watch-ref-held/`.

A PING-only monitor now checks the completed DC record's boot/code/limits
without output changes or retry. Its source supports a STOP-file request
and a 30-minute maximum. It must close before another serial controller
opens. Current live record:
`runs/hardware-minima-held-level-watch/20261029T075643-17798d7400`.
Incomplete records are not exported. The pending DC 2 V readings are
actual U1 pin 5 (E13), D35, D40, D45 and D50, relative to the retained
blue-rail GND. An overrange display requires DC 20 V and reporting that
range change. These DMM readings and a matched ADC block are pending;
the prior coarse readings are not silently used as calibration anchors.

## Precise midpoint paired with ADC; interior low point held

The operator confirmed `10분 동안 손대지 않았어` for the earlier
16:45:59–16:55:59 comparison. The new sequential DC 2 V report is
`1.620V / 1.620V / 1.619V / 1.620V / 1.628V`, ordered actual U1 pin 5,
D35, D40, D45, D50. Display resolution is 1 mV; meter accuracy has not
been established. Only D35/D40/D45/D50 are paired with A1/A2/A3/A4;
the extra pin 5 reading documents the DAC input separately.

The intervening PING-only monitor completed 650 checks over 1305.597 s,
maintaining boot `e522aadc799575eae297808f4df573c8` and code 1365. An
explicit STOP file closed it after a final successful PING before capture.
This is a separate connection from the earlier ten-minute test, and its
interval includes operator DMM probing, not a claimed no-touch condition.

One 512-frame HOLD block then passed same-boot, active ADC-state and timing
checks: intervals 1998–2003 us, no overruns. A1/A2/A3/A4 means are
5447.0293/5448.8535/5450.0371/5488.9746 counts, with sample SDs
7.8200/4.3434/7.5653/7.0103 counts. Using the earlier 4.86 V supply display
gives nominal SDs 1.29–2.32 mV; rare deviations remain, up to about 19 mV
from the channel mean. All samples are retained, with no trimming or
per-channel calibration fit. DMM and ADC were sequential, not simultaneous.

The next DC command on the same boot held code 548, target 0.65 V.
This interior calibration point replaces the previously proposed 0.62 V
low target now that REF reads 1.628 V, leaving margin inside REF minus
1 V and moving less than 1 V from the held midpoint. It is not a new
claim about calibrated range. No old-boot low point is combined into this
series. Exact records are `minima-midpoint-held-watch/`,
`minima-dc-recovery-mid-point/`, `minima-dc-recovery-mid-block/` and
`minima-dc-recovery-low-held/`.

A new PING-only monitor keeps the low level under observation at
`runs/hardware-minima-held-level-watch/20261029T081953-070229121d`.
It remains incomplete and unexported. The pending low-point DMM instruction
uses the same five contacts and DC 2 V range; D50 remains fixed REF.
Output and firmware stay unchanged while the operator reads the values.

## Standing conventions (current)

- The intended supply rails are the UPPER LEFT red section for +5 V and
  UPPER LEFT blue section for Arduino GND (0 V). The operator reports the
  fixture-side jumpers installed and has supplied the first powered DC
  readings after the requested Arduino 5 V/GND wiring step.
- REF is a separate buffered reference near one third of the measured
  supply; it is NOT the Arduino GND rail.
- Configure both halves of each powered LM358 deliberately; the auxiliary
  input is parked at REF by the current table.
- The old loopback must remain isolated. A1–A3 retain their series
  resistors. A4 fixed-REF sensing now uses the operator-confirmed short
  jumper at D50–G50 after the measured pull-up-like board path.
  A5 is unconnected.
- Keep USB unplugged during wiring, resistance or continuity checks.
