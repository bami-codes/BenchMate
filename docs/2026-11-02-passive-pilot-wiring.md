# Passive pilot: design-01 first

Operator-only wiring instructions. Do not send this file, specimen truth or the
case mapping JSON to the diagnosis model. Tonight's runs are pilots and excluded
from evaluation. Follow the [common amendment](2026-11-02-passive-pilot-amendment.md).
The Spark reading must be confirmed before physical acquisition.

## Order

Start 01 → 04 → 02 → 05 → 03, then LED 06. This retains the 4.7 kΩ resistor
between 01/04, the 22 kΩ branch between 04/02, and the 1 µF capacitor between
02/05/03. The three instrument leads stay at their established nodes. Each case
finishes its fault diagnosis, photograph, restoration and fresh-context rerun
before moving to the next. This is a practical low-change order, not a measured
optimality result. Only design-01 wiring is requested now.

## Shared large-board state

Power off throughout wiring. Replace jumper 11 B28–B35 with 1 kΩ and keep it
for all five passive cases. Keep feedback B11–B12 and the existing ADC paths.
Remove calibration bridge C35–C30 if present. Initial unloaded: E30–A55 and
A55–C35 both absent. Keep D55–D60 (9.99 kΩ), C23–A60 and B50–B23 in place.
REF at C50 is not the blue GND rail.

## Design-01 intended mini-board

Preserve the current D01 photograph before changing anything. Coordinates use
the [established mini-board orientation](b1-assembly.md): A–E upper, F–J lower,
columns 1–17 left to right. A3–E3 share a node; upper and lower halves are separate.

| Action | Contacts | Value / purpose |
|---|---|---|
| Replace the old 10 kΩ R1 | Mini B3–B8 | 4.7 kΩ intended R1 |
| Retain the original C1 | Mini D8–D13 | 105, nominal 1 µF |
| Remove added D01 capacitor, if still present | Mini I8–I13 | No second 1 µF in this design |
| Remove old D01 cross-trench bridges, if present | Mini E8–F8 and E13–F13 | Leave only intended upper-half R/C |
| Retain OUT lead | Large D30 → mini A8 | OUT |
| Retain REF lead | Large C50 → mini A13 | REF, not GND |

## Planted external series resistance

The public 1 kΩ at B28–B35 is upstream of measured IN. The following two
10 kΩ parts form the separate 20 kΩ fault downstream of measured IN, outside
the mini-board. Columns 31 and 37 are unassigned in the documented large-board
wiring table; stop and report if the actual board has anything there.

| Action | Contacts | Purpose |
|---|---|---|
| Add first 10 kΩ resistor | Large E35–E31 | Measured IN → intermediate node 31 |
| Add second 10 kΩ resistor | Large D31–D37 | Node 31 → fault output node 37 |
| Move only the large-board end of the green IN lead | Large A35 → large A37; mini end remains A3 | Route DUT input through both resistors |

Do not retain any parallel A35→mini A3 jumper. The path must be:

`U1B → known 1k → measured IN → 10k → 10k → mini R1 4.7k → OUT → C1 → REF`

Before USB reconnection check: both 10 kΩ parts connect through upper column 31;
the green lead joins the second resistor through upper column 37; C35–C30 is
absent; no IN-to-OUT bypass exists; the mini-board has only one 1 µF capacitor.
Keep component readings and assembly truth in operator records, not Spark input.
Remove probes and loose wires. After the operator confirms completion, reconnect
the same USB port for a logged PING-only identity check before ARM or stimulus.

The diagnosis is allowed to identify an increased effective series path. It cannot
distinguish a larger R1 from a separate series resistor by terminal voltage alone.

## Restoration, only after the fault run and photograph

Disconnect USB. Remove both added 10 kΩ resistors and move the green lead from
large A37 back to A35. Retain the mini 4.7 kΩ, its single 1 µF capacitor, and the
public B28–B35 1 kΩ. Disconnect the optional OUT-load jumper initially and leave
the load resistor/REF return intact. After confirmation and USB reconnection,
start a new Spark context with the same reviewed design and common settings.
Preserve all failed guards, forecasts and attempts; never erase them with a rerun.
