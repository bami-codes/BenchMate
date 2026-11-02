# Passive pilot amendment: fixed 1 kΩ driver isolation

The user authorized Spark and physical pilot work on Nov 2, with design-01 first.
All tonight's runs are pilots, excluded from evaluation. No historical D01 run,
source, calibration file or firmware is changed.

## Common instrument configuration

With USB and other power disconnected, replace jumper 11 at B28–B35 with a 1 kΩ
resistor. Keep the driver's original voltage-follower feedback B11–B12 unchanged.
Apply this configuration to all five passive cases, including their restored runs.
The topology is:

`U1B output / A3 monitor → B28 → 1 kΩ → B35 / A1 measured IN → specimen → OUT`

The 1 kΩ is public instrument impedance, not an intended DUT component and not
the planted fault. A planted input-series resistance is AFTER measured IN.
The 10/30 D01 used the bypass jumper; its input drive path therefore differs.
The existing ADC sensing resistors and voltage conversions are retained, subject
to fresh guards; no new absolute calibration is claimed.

Reason: design-05 restored has IN tied to OUT with 1 µF and 10 kΩ in parallel to
REF. A direct capacitor load on the LM358 follower is avoided. ST's LM358
datasheet, Figure 18, shows phase margin depends on capacitive loading. Selecting
1 kΩ is an engineering choice, not a manufacturer guarantee of fixture stability.
At the largest 1 V commanded step the resistor limits the capacitor-path initial
incremental current to approximately 1 mA under an ideal driver. Real stability,
reference drift and guard compliance still require physical checks.

Source: https://www.st.com/resource/en/datasheet/lm358.pdf

## Predictions and the changed drive path

Fitting and conditional predictions retain measured IN downstream of the 1 kΩ;
the known instrument resistor must not be diagnosed as a DUT defect. Before
physical execution, command-input forecasts must explicitly include the known
1 kΩ and DUT input loading. In particular, design-05 restored is not an ideal
command-to-OUT wire even though measured-IN-to-OUT is a wire. Command forecasts
remain ideal-buffer forecasts; their scores are reported separately from measured
IN conditional scores. No failed forecast is relabelled a pass.

Spark receives the common instrument description and reviewed DUT, never the
case mapping JSON, assembly truth, fault labels or photographs during diagnosis.
Spark alone selects each training action. Parameter fitting uses training OUT
only; publication precedes both reserved inputs. A frozen-source new runner is
required; the archived v1/v2 files remain unchanged.

## Before first physical connection

1. Preserve a photograph of the current two-capacitor D01 wiring before changes.
2. USB and external power off; change only jumper 11 to 1 kΩ initially.
3. Confirm U1/U2 supply, follower feedback and A1–A4 sensing match the retained
   build; A4 remains a REF drift guard, not an absolute voltage anchor.
4. With a DUT, calibration bridge C35–C30 is absent. Both optional branch
   jumpers A55–C35 and E30–A55 are absent for initial unloaded measurements.
   Retain B50–B23 and the known 9.99 kΩ load/REF return; only its OUT connection
   is removed. REF and GND remain separate.
5. Remove probes and loose exposed wires. Confirm the new design-01 DUT wiring
   against the Spark reading before reconnecting the same USB port.
6. Inventory the real matching USB identity. A logged PING precedes any ARM;
   no reset command, firmware upload, automatic retry or unreported rewiring.
7. Any failed electrical/timing/boot guard stops the attempt and is retained.

The final LED stage needs a separate known 47k/10k collector measurement path
and absolute-DC qualification. This passive amendment does not qualify it.

## Image intake provenance correction

The earlier review's empty Pillow `.info` check missed PNG `caBX` provenance
chunks. Claude identified this correctly. All six originals contain such chunks;
this does not change their visible circuit content. Intake decodes/re-encodes
pixels and then checks PNG chunks/CRCs with `verify_clean_png`, accepting only
IHDR/IDAT/IEND. No original SVG/PNG metadata or local filenames reach Spark.
The new R/C/D/Q reader and operator handoff passed nine local boundary checks
before the first paid call. The original frozen reader is unchanged.

## New runner readiness

`scripts/passive_pilot.py` connects the preserved physical adapter to the real
Spark tool loop. `prepare` is offline. `probe --execute` accepts only the pinned
Minima USB identity and sends PING only; ARM and stimulus belong to a confirmed
`run --execute`. Missing/ambiguous USB identity stops before a paid diagnostic
call. The source manifest preserves all 73 archived runtime files and adds only
the new intake, pilot session and runner, for 76 files total.

Command forecasts insert the known resistor upstream of DUT IN and retain all
DUT input-loading branches. Measured-IN conditional prediction does not insert
it a second time. Independent RC step solutions check both unloaded and loaded
direct-wire DUT behavior. The common runtime suite passed 66 checks; four further
runner checks passed after adding assembly gating and PING-only preflight.
Unconfirmed assembly, a bypassed instrument resistor, a different reviewed design,
or an absent USB device stops before opening serial or using a paid provider.

Every run requires a separately retained, operator-confirmed structured assembly
record with the 1 kΩ instrument setting, matching reviewed design digest, USB-off
wiring assertion and actual specimen truth. That record is never transmitted to
Spark. Load changes use only the preserved fixed English choices and explicit
matching pending request IDs. Predictions and the common instrument/source
envelope are committed, pushed and remotely verified before reserved captures.

No prepared real-design approval, assembly confirmation or initial wiring report
has been fabricated. At this revision's creation the user's schematic confirmation
and large-board preparation reports are pending; real hardware commands remain
zero. The six actual vision calls are retained in
[the intake report](../examples/schematic-intake/2026-11-02-pilot/REPORT.md).
